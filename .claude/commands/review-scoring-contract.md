---
description: Audit scoring/output contract — columns, adjustment_strategy, all-reversed block, metadata completeness
---

Audit the current scoring and output contract end to end:

1. Trace the pipeline from similarity computation to export (backend/app/ccr.py, jobs.py, and any engine packages).
2. Verify against the design contract:
   - raw per-item similarities always preserved and exported as sim_item_N_raw pattern (or current documented schema);
   - reverse_scored flags exported per item;
   - adjustment_strategy recorded in metadata under scoring; no undocumented adjustment applied anywhere;
   - all-reversed + exclude_reversed → aggregate blocked with a methodological warning (never NaN);
   - metadata includes output_schema_version, model id/revision/usage_config, construct snapshot + item_hash.
3. Diff actual export columns (run the test suite's export test or generate a fixture run) against the documented schema.
4. Report: contract violations (blocking), undocumented drift, and the smallest fixes. Do NOT change golden expected outputs.
