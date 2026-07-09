# Spec 0005 — ccr_engine extraction + reference parity tests (brief)

**Status:** draft (Phase 1 opener — refine after Phase 0 ships)
**Phase:** 1    **Design doc ref:** §7 (strangler steps 1–3), §10, §16

Extract the pure analysis package per the strangler plan: move similarity/scoring/warnings/
stats/reproducibility logic from backend/app into `packages/ccr_engine/` with the
`run_ccr_analysis(...)` interface (design §10); backend becomes an orchestration layer. Freeze
behavior first with golden datasets (evals/golden_datasets → evals/expected_outputs, human-
approved). Then add reference parity: same corpus + items through the published `ccr_wrapper`
(pyccr) and through ccr_engine — similarities match within atol (1e-5 target), pinned model
revisions on BOTH paths, run in the same container as production. Document any expected
differences. Editable-install workspace wiring so backend imports the package (no sys.path hacks).

**Key tests:** engine callable without FastAPI, golden stability, parity within tolerance,
import-boundary check (no engine imports from app/).
