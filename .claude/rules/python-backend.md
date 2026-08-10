---
paths:
  - "backend/**/*.py"
  - "packages/**/*.py"
---

# Python rules

- Python 3.10+; type hints on public functions; docstrings explain WHY, not what.
- FastAPI: request/response shapes via Pydantic schemas; HTTPException with clear user-facing detail strings; validation errors are 400s, missing resources 404s, state conflicts 409s.
- All embedding/normalization/similarity math stays in the engine module - API handlers orchestrate, never compute.
- Every user-facing failure path returns an actionable message (what happened + what to do), never a stack trace.
- Tests: pytest; use the deterministic fake embedder (model "fake-deterministic" / CCR_FAKE_EMBEDDINGS=1); no torch imports in the default suite; poll async jobs with a timeout helper, never sleep-and-hope.
- Warnings are structured objects with UPPER_SNAKE codes (design §12), never bare strings.
- Never hardcode a model name outside packages/model_registry (tests may use "fake-deterministic").
