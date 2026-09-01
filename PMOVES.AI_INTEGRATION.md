# PMOVES.AI Integration Dossier

_Last updated: 2026-08-31 (SPARK wiring audit)_

## Module
- Name: PMOVES-autoresearch
- Path: PMOVES-autoresearch
- Upstream: karpathy/autoresearch (nanochat-class autonomous training experiments)

## Purpose in PMOVES.AI
- Overnight autonomous LLM-experiment loop: an agent edits `train.py` (5-min
  wall-clock budget per experiment, metric `val_bpb`), keeps-or-discards, and
  reports. The "research org" is programmed via `program.md`.

## PMOVES Overlay Surface
- **Agent-driven, not a compose service.** Any PMOVES agent (Agent Zero is the
  designated driver; it can also auto-research ad hoc via its own tools) runs
  inside this repo per `README.md`. No long-running daemon to bring up.
- Post-experiment hook: `nats_reporter.py` (wrapper only — never modifies
  `train.py`/`prepare.py`). Pattern: `uv run train.py > run.log 2>&1 && python nats_reporter.py`.

## Contracts and Topics
- NATS subjects (declared in `nats_reporter.py`, documented in
  `.claude/context/nats-subjects.md` §autoresearch):
  - `research.autoresearch.experiment.v1` — experiment started
  - `research.autoresearch.result.v1` — experiment completed (metrics:
    val_bpb, peak_vram_mb, mfu_percent, num_params_M, depth, ...)
- Supabase: none (metrics ride NATS; persist downstream if a consumer stands up)
- MCP endpoints/skills: none native; `program.md` is the de-facto skill.

## Platform (SPARK GB10 notes)
- Single NVIDIA GPU required (upstream targets H100). GB10 Grace Blackwell
  (sm_121, unified memory) works with the torch cu128 stack already proven on
  this node's media services. For the 5-min budget on GB10, small-model
  guidance from upstream README §"smaller compute platforms" applies
  (lower DEPTH/vocab/MAX_SEQ_LEN, TinyStories-class data).

## Companion model-discovery chain (context)
- `hf-agent` publishes `hf.model.discovered.v1` → `hf-research-agent` scores
  (threshold 110) → `hf.model.evaluated.v1` → `model-registry` G4 auto-register
  → `model.fitness.recorded.v1`. Live-validated 2026-08-31: 2275 models
  discovered, scoring active (recent feed correctly SKIPped at 35-45/110).

## Boot Order and Health
- No boot order (agent-driven). Health = a successful `uv run train.py` cycle.

## Hardening Notes
- No secrets required (public data; HF token optional for gated datasets).
- Runs inside the agent's own execution context — sandbox policy follows the
  driving agent's (agent-sandbox skill recommended for unattended loops).

## Source Documentation
- Upstream docs entrypoint: README.md
- PMOVES docs index reference: pmoves/docs/SUBMODULE_DOCS_DOSSIER.md

## Owner / Audit
- Owning lane: SPARK-KIMI (Crush) — wiring audit 2026-08-31
- Last integration audit run: 2026-08-31
