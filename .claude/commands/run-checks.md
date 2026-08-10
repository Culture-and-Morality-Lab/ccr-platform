---
description: Run the full local check suite and report results compactly
allowed-tools: Bash(cd backend && python -m pytest*), Bash(python packages/*), Bash(python -m py_compile*)
---

Run all local checks and report one compact table:

1. Backend tests: cd backend && python -m pytest tests/ -q
2. Model registry validation: python packages/model_registry/validate_models.py
3. Construct library validation: python packages/construct_library/validate_constructs.py

For any failure: show the failing name + one-line cause + proposed smallest fix. Do not fix anything without confirming unless it's a trivial syntax error you just introduced.
