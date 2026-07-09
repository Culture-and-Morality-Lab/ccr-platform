# CCR Platform — Culture and Morality Lab

Web platform for **Contextualized Construct Representation (CCR)** psychological text analysis
([method](https://github.com/Ali-Omrani/CCR) · [EMNLP 2024](https://aclanthology.org/2024.emnlp-main.151/)).
Researchers upload a corpus, select a validated construct, run CCR with locally-hosted
sentence embeddings, inspect per-item loadings and distributions, and export results with a
reproducibility record.

**PI:** Dr. Mohammad Atari · **Maintainer:** Deva Anand ·
**Design of record:** `docs/design/CCR_Platform_Design_Doc_v1.2.docx` · **Plan:** `ROADMAP.md`

> This repo is the production mainline, seeded from the public demo
> ([Deva-1903/ccr-platform](https://github.com/Deva-1903/ccr-platform), live on HF Spaces).
> The demo stays deployed and untouched; this codebase evolves per the strangler plan (design §7).

## Quickstart

```bash
./run.sh                     # venv + deps + http://127.0.0.1:8000  (Python 3.10+)
```

```bash
# fast test suite (deterministic fake embedder — no torch needed)
cd backend && pip install -r requirements-dev.txt && python -m pytest tests/ -q

# validate the registries
python packages/model_registry/validate_models.py
python packages/construct_library/validate_constructs.py

# real-model smoke test (downloads MiniLM ~90MB once)
python scripts/verify_install.py
```

## Layout

```
backend/            FastAPI app + tests (current working application)
frontend/           React/Vite SPA source (prebuilt copy served from backend/static/)
packages/
  model_registry/   models.yaml — single source of model truth + validator
  construct_library/ versioned construct YAMLs + validator (append-only)
  ccr_engine/       Phase 1 target: pure analysis package (see spec 0005)
docs/
  design/           design doc of record (v1.2)
  specs/            feature specs 0001–0005 (implementation starts here)
evals/              golden datasets + expected outputs (human-approved only)
.claude/            Claude Code config: rules, agents, commands, hooks
```

## Working on this repo

Read `CLAUDE.md` first — it carries the architecture rules and hard rules (enforced partly by
hooks). Features start from `docs/specs/`; decisions land in `DECISIONS.md`; user-visible
changes land in `CHANGELOG.md`. The published `ccr_wrapper` implementation is the correctness
spec for the engine.

## Status

Phase 0 (see ROADMAP.md): descriptive stats ✅ (from demo) · data-quality warnings incl.
language (spec 0001) · script export (spec 0002) · registry-driven models + language selection
(spec 0003) · construct library from YAML (spec 0004).
