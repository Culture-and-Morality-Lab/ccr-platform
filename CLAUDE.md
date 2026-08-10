# CCR Platform (Culture and Morality Lab)

Research software for Contextualized Construct Representation (CCR) psychological text
analysis. Upload corpus → select validated construct → embed items + texts locally
(sentence-transformers) → cosine similarity = loadings → inspect → export with a
reproducibility record. PI: Dr. Mohammad Atari. Maintainer: Deva Anand.

Design of record: `docs/design/CCR_Platform_Design_Doc_v1.2.docx` (§ references below point there).
Current state: Phase 0 (visible features on the demo codebase). Roadmap: @ROADMAP.md

## Commands

- Backend tests: `cd backend && python -m pytest tests/ -q`  (fast - fake embedder, no torch needed)
- Run app locally: `./run.sh` → http://127.0.0.1:8000
- Frontend build: `cd frontend && npm install && npm run build`  (outputs to backend/static/)
- Frontend dev: `cd frontend && npm run dev`  (proxies /api to :8000)
- Validate registries: `python packages/model_registry/validate_models.py && python packages/construct_library/validate_constructs.py`
- Real-model smoke test: `python scripts/verify_install.py`  (downloads MiniLM once)

## Architecture rules (from design §15 - non-negotiable)

- Analysis/NLP logic lives ONLY in the engine (today `backend/app/ccr.py`; Phase 1 extracts it to `packages/ccr_engine/`). Never in UI components or API route handlers.
- ALL model-specific behavior (prefixes, normalization, dims, max length, language support) goes through `packages/model_registry/models.yaml`. No hardcoded model behavior anywhere.
- Predefined constructs live ONLY in `packages/construct_library/constructs/*.yaml` - versioned, append-only; edits create new versions. (Migration from `backend/app/seed_constructs.py` is a Phase 0 task.)
- Every analysis run must produce metadata + a reproduction script (design §14). Exports mirror `ccr_wrapper` output shape.
- MiniLM (all-MiniLM-L6-v2) is the default model - it is the CCR reference model. E5-family models REQUIRE the "query: " prefix on both items and texts.
- The published `ccr_wrapper` implementation is the correctness spec (parity tests, design §16).

## Hard rules

- Never silently change output column names (bump output_schema_version in metadata instead).
- Never remove or weaken warnings to make tests pass.
- Never log uploaded text content.
- Never edit files under `evals/expected_outputs/` - golden outputs change only via explicit human approval (enforced by a PreToolUse hook).
- No new infrastructure (Redis, GPU, new vendors, new services) without a DECISIONS.md entry.
- Reverse scoring: v1 exports raw similarities + flags only; adjustment_strategy is a recorded parameter (design §11). Do not invent adjustments.
- Do not restructure directories big-bang; follow the strangler steps (design §7).
- No em dashes anywhere in project text: UI strings, docs, comments, commit messages, YAML. Use a hyphen or restructure the sentence (Deva's rule, 2026-07-09; enforced by a PostToolUse hook).

## Workflow

1. Non-trivial features start from a spec in `docs/specs/` (template: `docs/specs/TEMPLATE.md`). Read it before implementing.
2. Plan → smallest viable diff → tests updated in the same change → run relevant checks.
3. After completing a feature: update CHANGELOG.md; add a DECISIONS.md entry if any architecture choice was made.
4. Commit style: `feat(scope): ...` / `fix(scope): ...` / `docs: ...` / `test: ...`; small commits, one concern each.

## PI working norms

- Mohammad (2026-07-09): "you can always suggest better options that I might not know about -
  take initiative (newer NLP models, lighter options, less expensive options)." Consequence:
  when a decision involves a model, service, or cost, ALWAYS check for newer/lighter/cheaper
  candidates and present the better option with evidence - recommending beats asking.
  New models enter via the registry + benchmark-before-adopt (golden/parity harness), never
  by swapping defaults silently. Cost options favor free tiers and annual-friendly services.

## Context notes

- Python 3.10+ backend (FastAPI, SQLAlchemy, pandas, numpy, sentence-transformers). Tests use a deterministic hash embedder (`CCR_FAKE_EMBEDDINGS=1` / model `fake-deterministic`).
- SQLite + local disk today by design; Postgres + object storage arrive in Phase 2 behind existing interfaces (design §4.1 staged rollout map).
- The original demo repo (`../ccr-platform`) stays deployed and untouched; this repo is the mainline going forward.
