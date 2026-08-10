# Spec 0002 - Reproduction script export (offline-runnable)

**Status:** implemented (2026-07-09)
**Phase:** 0    **Design doc ref:** §14
**Requested by:** Mohammad (Slack brief: "provide users with the Python script used for their analysis so they can reproduce it independently")

## Problem
Runs are reproducible in principle (metadata records everything) but a researcher must
reassemble the analysis by hand. The platform should hand them a runnable script.

## Contract
- New export: `GET /api/jobs/{id}/script` → `reproduce_analysis_<run8>.py` + a pinned
  `requirements-repro.txt` (exact installed versions of sentence-transformers, torch, numpy, pandas).
- The script must run OUTSIDE the platform with only: the downloaded input CSV, Python, and
  internet access for the (pinned-revision) model download. No platform credentials, ever.
- Script contents (generated from the run's metadata, not from live state): model
  provider_model_id + revision, prefix logic when usage_config.requires_prefix (E5!),
  normalize_embeddings flag, the exact construct items + reverse_scored flags (embedded
  verbatim), text column, empty-row dropping identical to the platform, cosine similarity,
  per-item sim columns + ccr_score with identical rounding, CSV output path, and a header
  comment: run_id, created_at, item_hash, platform version, output_schema_version.
- UI: "Download Python script" button in the results view export row.

## Non-goals
Notebook export; R script; re-running inside the platform from a script.

## Tests
- test_script_export_endpoint_returns_python (200, content-type, filename)
- test_script_contains_pinned_model_and_items (revision string, all item texts, prefix for E5 runs)
- test_script_is_valid_python (compile() the generated source)
- integration (marked, real-model, not in default suite): run script on sample corpus →
  similarities match platform export within atol=1e-5.

## Implementation notes
- Generator = template string in a new engine-side `reproducibility.py`; inputs strictly from
  job metadata (guarantees script matches what actually ran).
- Requirements pinning: importlib.metadata versions at run time, stored in metadata, echoed to file.

## Deviations
- Requirements served at /script-requirements (separate endpoint) rather than bundled zip.
- Real-model parity integration test deferred to spec 0005's parity suite (fake-backend tests + compile check in place).
