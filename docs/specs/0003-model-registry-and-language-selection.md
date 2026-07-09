# Spec 0003 — Registry-driven models + language selection (brief)

**Status:** implemented (2026-07-09)
**Phase:** 0    **Design doc ref:** §12, §13

Wire the backend and UI to `packages/model_registry/models.yaml` instead of the hardcoded
AVAILABLE_MODELS list: loader module (yaml → validated dataclasses), `/api/models` serves
registry entries (id, display_name, languages, tiers, warnings), engine applies usage_config
(prefixes for E5 on BOTH items and texts, normalize flag), and run metadata records the full
entry incl. revision. Add a language selector to the run step (default en) whose value flows
into spec-0001 warnings. Add e5-large-v2 and multilingual-e5-base to the UI via registry only.
Validator (`validate_models.py`) runs in tests. Pin revisions before Phase 1 exit.

**Key tests:** loader validation errors, prefix application for E5 (assert embedded strings
receive "query: " — testable via fake backend capturing inputs), /api/models shape, metadata
records registry snapshot, MiniLM stays default.
