"""
autoresearch NATS Reporter

Post-experiment hook that reads run.log and publishes results
to the PMOVES NATS bus. Run after each experiment completes:

    uv run train.py > run.log 2>&1
    python nats_reporter.py

Does NOT modify train.py or prepare.py — wrapper only.
"""

import asyncio
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone

NATS_URL = os.getenv("NATS_URL", "nats://nats:pmoves@nats:4222")
SUBJECT_EXPERIMENT = "research.autoresearch.experiment.v1"
SUBJECT_RESULT = "research.autoresearch.result.v1"
LOG_FILE = "run.log"


def parse_run_log(path: str = LOG_FILE) -> dict | None:
    """Extract metrics from run.log using the same patterns as the experiment loop."""
    if not os.path.exists(path):
        print(f"[nats_reporter] {path} not found", file=sys.stderr)
        return None

    with open(path, "r") as f:
        content = f.read()

    metrics = {}
    for line in content.splitlines():
        line = line.strip()
        for key in ("val_bpb", "peak_vram_mb", "training_seconds", "total_seconds",
                     "mfu_percent", "total_tokens_M", "num_steps", "num_params_M", "depth"):
            match = re.match(rf"^{key}:\s+(.+)$", line)
            if match:
                try:
                    metrics[key] = float(match.group(1))
                except ValueError:
                    metrics[key] = match.group(1)

    if not metrics:
        return None

    return metrics


def get_git_info() -> dict:
    """Get current git commit and branch."""
    info = {}
    try:
        info["commit"] = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], text=True
        ).strip()
    except Exception:
        info["commit"] = "unknown"
    try:
        info["branch"] = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"], text=True
        ).strip()
    except Exception:
        info["branch"] = "unknown"
    return info


async def publish_result(metrics: dict, git_info: dict) -> bool:
    """Publish experiment result to NATS."""
    try:
        from nats.aio.client import Client as NATS

        payload = {
            "commit": git_info.get("commit", "unknown"),
            "branch": git_info.get("branch", "unknown"),
            "val_bpb": metrics.get("val_bpb"),
            "peak_vram_mb": metrics.get("peak_vram_mb"),
            "training_seconds": metrics.get("training_seconds"),
            "num_steps": metrics.get("num_steps"),
            "num_params_M": metrics.get("num_params_M"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        nc = NATS()
        await nc.connect(NATS_URL, connect_timeout=5)
        nc.publish(SUBJECT_RESULT, json.dumps(payload).encode())
        await nc.flush()
        await nc.close()

        print(f"[nats_reporter] Published to {SUBJECT_RESULT}: val_bpb={metrics.get('val_bpb')}")
        return True
    except Exception as e:
        print(f"[nats_reporter] NATS publish failed: {e}", file=sys.stderr)
        return False


def main():
    metrics = parse_run_log()
    if metrics is None:
        print("[nats_reporter] No metrics found in run.log — skipping NATS publish")
        sys.exit(0)

    git_info = get_git_info()
    asyncio.run(publish_result(metrics, git_info))


if __name__ == "__main__":
    main()
