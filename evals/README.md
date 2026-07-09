# Golden evals

Purpose: catch silent research-behavior drift — output shape, column names/order, metadata
fields, warning codes — per design doc §16.

- `golden_datasets/` — frozen input corpora (never edit rows in place; add new files).
- `expected_outputs/` — human-approved expected results. **Protected by a PreToolUse hook:**
  Claude Code cannot edit files here. To update after an approved behavior change, regenerate
  manually and review the diff yourself before committing.
- Runner arrives with spec 0005 (engine extraction freezes behavior first). Until then, the
  backend test suite's export-shape tests are the drift guard.

Rule of thumb: if a golden diff surprises you, the code is wrong until proven otherwise.
