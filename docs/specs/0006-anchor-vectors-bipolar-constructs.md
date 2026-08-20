# Spec 0006 - Anchor vectors (bipolar constructs)

**Status:** implemented
**Phase:** 0    **Design doc ref:** §11 (scoring), ROADMAP feature 2; Teitelbaum & Simchon (2025) Appendix B

## Problem
Plain CCR scores a text's similarity to a single construct C. Constructs with a
natural opposite (happiness vs sadness, internal vs external locus of control)
are better measured along the direction BETWEEN the two poles. Scoring along
that direction also cancels shared confounds like "questionnaire-ness": both
poles are worded as questionnaire items, so their difference subtracts the
common style component. Today a researcher has to run each pole separately and
subtract by hand, with no bipolar score, no reproducibility record for the
subtraction, and no results view centered on zero.

## Contract

### Inputs (API/UI)
- `POST /api/jobs` gains two optional fields:
  - `opposite_construct_id: str | None` - the contrasting (opposite-pole)
    construct. Its presence is what makes a run "anchored".
  - `similarity_metric: "cosine" | "dot"` - default `"cosine"` (the PI's
    formula). `"dot"` is offered so we can compare against the paper's finding
    that dot product sometimes does better (Appendix B).
- An anchored run scores exactly one target construct against one opposite
  construct. It is mutually exclusive with multi-construct runs: if
  `opposite_construct_id` is set, `construct_ids` must resolve to exactly one
  target id.
- UI: the construct picker gains an "Add contrasting construct (anchor vector)"
  affordance that opens the same selection flows (library / typed / uploaded)
  for the opposite pole. Both item sets show side by side before running, with
  a cosine/dot toggle.

### Scoring (engine, design §15 - math lives only in the engine)
With L2-normalized embeddings:
- `C`      = centroid (mean) of the target construct's item embeddings
- `C_opp`  = centroid of the opposite construct's item embeddings
- `AV`     = `C - C_opp`
- target pole score  = mean over target items of cos(T, item) = `T · C`
- opposite pole score = mean over opposite items of cos(T, item) = `T · C_opp`
- anchored score:
  - `dot`:    `T · AV`  = target_score - opposite_score  (exact identity)
  - `cosine`: `cos(T, AV) = (T · AV) / ||AV||`            (default)

Higher = toward the target pole; negative = toward the opposite pole. The dot
metric equals the difference of the two per-pole scores by construction, so the
export is self-checking.

### Outputs (exact columns) - `output_schema_version` 1.2
Per input row, appended to the passthrough columns:
- `target_sim_item_N`   - cos(T, target item N)
- `opposite_sim_item_N` - cos(T, opposite item N)
- `target_ccr_score`    - target pole score
- `opposite_ccr_score`  - opposite pole score
- `anchor_score`        - the bipolar score (metric per the run)

Single-construct (1.0) and multi-construct (1.1) exports are unchanged.

### Results UI
- Score is bipolar: histogram centered on 0, negative scores meaningful.
- Top texts labeled "most <target>", bottom texts labeled "most <opposite>".
- Per-item loadings shown per pole (target items, opposite items).
- The card names the metric used (cosine / dot) and both constructs.

### Warnings & edge cases
- `opposite_construct_id` equals the target id -> 400 (a pole cannot oppose
  itself).
- `opposite_construct_id` set together with more than one target construct ->
  400 (anchored runs are single-target vs single-opposite in v1).
- Opposite construct missing / empty items -> 404 / existing empty-items guard.
- `ANCHOR_DEGENERATE_POLES` (warning): `||AV||` is ~0 (the two poles embed to
  nearly the same direction), so cosine is numerically unstable. The run still
  completes; the warning tells the reader the poles are not well separated.

### Metadata additions
- `scoring` becomes `{"method": "anchored_vector", "similarity": <metric>,
  "adjustment_strategy": "none"}`.
- `anchor`: `{"target_construct_id", "opposite_construct_id", "metric"}`.
- Both construct snapshots + item hashes recorded (target and opposite),
  mirroring the multi-construct metadata shape.
- `output_schema_version` = "1.2".
- Reproduction script embeds BOTH item sets verbatim and recomputes the AV math
  (centroids, AV, chosen metric) so exported scores reproduce offline.

## Non-goals
- Reverse-scored item negation stays as v1 today: `(R)` flags are recorded but
  not auto-negated (paper footnote 27 is a later option).
- No combining anchored scoring with multi-construct correlation runs.
- No more than two poles (a single contrast per run).
- No new model behavior; prefixes/normalization come from the registry as usual.

## Tests
- Engine (`test_anchor_vectors.py`, fake embedder):
  - `dot` anchored score equals `target_ccr_score - opposite_ccr_score` to 1e-6.
  - `cosine` anchored score equals `dot / ||AV||`; bounded in [-1, 1].
  - Swapping target/opposite negates the score (dot) / flips its sign (cosine).
  - Degenerate poles (identical item sets) -> `ANCHOR_DEGENERATE_POLES` warning,
    no crash.
  - Per-pole per-item similarity matrices have the right shapes.
- API / job (`test_api.py` / `test_multi_construct.py` neighbors):
  - Anchored job completes; export has exactly the 1.2 columns; metadata carries
    the `scoring.method == "anchored_vector"` block and both snapshots.
  - `opposite_construct_id == construct_id` -> 400.
  - `opposite_construct_id` + 2 target constructs -> 400.
  - `similarity_metric` default is cosine; `"dot"` is honored and recorded.
- Reproduction (`test_script_export.py` neighbor):
  - Generated anchored script compiles, defines both item sets, and its inline
    AV math matches the platform's `anchor_score` to ~1e-5 (fake-embedder path).

## Implementation notes
Files expected to change:
- `backend/app/ccr.py` - `run_ccr_anchored(...)` returning per-pole similarities,
  per-pole scores, the anchored score, and a metadata block. Reuses
  `encode_unique` / `encode_items_cached` and the doc-embedding cache.
- `backend/app/models.py` - `Job.opposite_construct_id`, `Job.similarity_metric`
  (additive columns; startup auto-migration adds them to existing SQLite DBs).
- `backend/app/jobs.py` - anchored branch in `run_job`: export columns, bipolar
  summary (`_anchor_stats`), metadata, `ANCHOR_DEGENERATE_POLES` warning.
- `backend/app/main.py` - `JobCreate`/`JobOut` fields + `create_job` validation
  (single target, distinct poles), pass-through to the Job row.
- `backend/app/reproducibility.py` - `_script_text_anchored(...)` variant,
  dispatched from `script_text` when `scoring.method == "anchored_vector"`.
- `frontend/src/Workspace.jsx` - contrasting-construct selection + metric toggle.
- `frontend/src/ResultsView.jsx` - bipolar histogram, pole labels, per-pole
  loadings.
- `CHANGELOG.md`, `DECISIONS.md` (metric default + per-pole score definition).

Smallest-diff approach: anchored is a separate branch that reuses the existing
embedding/caching plumbing; it never changes the single- or multi-construct
code paths or their schema versions.

## Deviations (filled after implementation)
- Per-pole "plain" score is the standard CCR score (mean of per-item cosines =
  text · pole_centroid), not `cos(text, centroid)` as the ROADMAP open question
  phrased it. This keeps parity with a normal single-construct run and makes the
  dot anchor score exactly `target_score - opposite_score` (self-checking export).
  Recorded in DECISIONS.md (2026-08-12).
- The bipolar distribution reuses the existing `Histogram` component; its bin
  edges already span the negative-to-positive range, so no separate zero-axis
  widget was added in v1.
- Backend and full test suite are green (engine identities + API/export/metadata
  + reproduction script). Pushed to dev for PI review before prod.
