---
description: Implement a feature from its spec in docs/specs/ following the required loop
argument-hint: <spec number or filename, e.g. 0001>
---

Implement spec: $ARGUMENTS

Follow this loop strictly (CLAUDE.md workflow):

1. Read the spec file in docs/specs/ matching "$ARGUMENTS". If it doesn't exist or is ambiguous, stop and say so.
2. Restate the contract in 3 bullets: inputs, outputs/columns, warnings/edge cases. Flag anything the spec leaves undefined BEFORE coding.
3. Propose an implementation plan: files to change, tests to add, smallest viable diff. Wait for approval if the plan touches architecture rules.
4. Implement in small increments. Add/update tests in the same change.
5. Run: cd backend && python -m pytest tests/ -q — plus registry validators if registries changed.
6. Summarize: changed files, test results, deviations from spec (update the spec's status/notes section), CHANGELOG entry, and whether a DECISIONS.md entry is needed.
