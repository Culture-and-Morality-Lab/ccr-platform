# Spec 0007 - construct library verification pass

**Status:** implemented
**Phase:** 0    **Design doc ref:** §10.1

## Problem

Every one of the 94 library constructs shipped as `needs_verification`: item wording
was imported from the lab's questionnaire spreadsheet and never checked verbatim
against the source publications, and reverse-scored flags were only partly filled in
(35 of 525 items flagged, 68 of 94 constructs marked
`reverse_flags_source: not_provided_pending_verification`). A researcher picking a
construct could not tell whether its wording matched the published scale, and CCR
loadings computed from mis-flagged items are wrong in a way nothing surfaces.

Noor Skhiri reviewed all 525 items (returned 2026-08-25), checking wording, reverse
keying, subscale grouping, and citation for each. This spec applies her review.

Two of her findings raise questions that are the PI's to answer, so they are
deliberately NOT applied here (see Non-goals).

## Contract

**Inputs.** `packages/construct_library/reviews/CCR_construct_library_review_2026-08-25.xlsx`
(the returned review, committed for provenance) plus
`packages/construct_library/apply_review.py`, which recomputes the plan from that file
and rewrites the YAML library. Corrected item text is hand-specified in that script,
one entry per correction, rather than parsed from free-text notes.

**Outputs.**

Item-level changes create a NEW construct version (a second YAML file, `version: 2`),
because item text, item order, and reverse flags all feed `item_hash`:

- 61 reverse-scoring flags flipped `false -> true` across 14 constructs. No flag went
  the other way; the library goes from 35 to 96 reverse-flagged items.
- 9 verbatim wording corrections, one item each, in 9 constructs.
- 1 subscale regrouping: `scs_sf_self_judgment_1` moves to `scs_sf_over_identification`
  per the SCS-SF coding key, changing the item list of both constructs.

23 constructs get a `version: 2` file. The `version: 1` files stay exactly as they are:
append-only means old versions remain resolvable for runs that already used them.

Metadata-level changes do NOT feed `item_hash` and are therefore applied in place on
the existing version:

- `verification_status` promoted `needs_verification -> verified` for 88 constructs.
- Citation and `source_url` repairs across 13 metadata-only constructs (dead links
  replaced with the URLs the reviewer supplied, one missing DOI added).
- A `review:` provenance block on every construct recording reviewer, review date, and
  outcome, so `verified` is attributable rather than an unsourced claim.

**Loader changes.** Two gaps made the above impossible to ship as data alone:

1. `sync_library` only ever inserted rows. A `verification_status` change on an
   existing version was silently ignored on any database that had already seeded, so
   the promotion would never reach a deployed instance. It now updates the mutable,
   non-hash fields (`verification_status`, `name`, `description`, `reference`,
   `category`) on an existing row when the item hash still matches. Items, flags,
   language, and version remain append-only: a hash change under an existing version
   is still a hard error.
2. `GET /api/constructs` returned every row, so publishing a v2 would show both
   versions of the same construct in the picker. Seed constructs are now collapsed to
   the highest version per `construct_slug`. Superseded rows stay in the database and
   remain reachable by id, so existing runs, results, and reproduction scripts are
   untouched.

**Warnings & edge cases.** Four constructs become entirely reverse-scored once the
reviewer's flags are applied: De Jong Gierveld social loneliness (3 items), and the
SCS-SF isolation, over-identification, and self-judgment subscales (2 items each).
The existing validator warning fires for each, and under `exclude_reversed` their
aggregate is blocked. This is a faithful reading of the source scales - the De Jong
Gierveld social loneliness items are all positively worded, and the SCS-SF negative
subscales are reverse-keyed in the published coding key - so the flags are correct and
the warning is doing its job. It is called out here because it changes what those four
constructs do at scoring time.

**Metadata additions.** None. No output column changes, no `output_schema_version`
bump: scores, columns, and the export shape are unchanged. Runs that pin a v1
construct reproduce exactly as before, because v1 rows are never mutated.

## Non-goals

Two findings are left pending an explicit PI decision and keep
`verification_status: needs_verification`:

- **IPIP "I" prefix** (50 items across the 5 Big Five constructs). CCR prepends "I" to
  the IPIP item stems; the reviewer confirmed the wording otherwise matches the source
  exactly and asked whether the prefix is deliberate. Stripping it is more literally
  verbatim; keeping it yields full sentences, which is generally the better embedding
  target. Their reverse-flag corrections ARE applied (uncontroversial, 25 items), so
  these constructs get a v2 - they just stay unverified.
- **K10 stem** (10 items). Items are stored as bare fragments (`nervous?`,
  `worthless?`) because the source puts the stem in a shared header. Restoring
  "During the last 30 days, about how often did you feel..." makes the embedding
  correct but the printed item less literally identical to the source. Not applied; K10
  gets no v2.

Also out of scope: re-verifying the 5 hand-written seed constructs against anything
beyond this review, and any change to reverse-scoring BEHAVIOR (v1 still exports raw
similarities plus flags; `adjustment_strategy` remains a recorded parameter).

## Tests

- `test_construct_library_versions.py::test_v2_constructs_supersede_v1_in_listing` -
  the API lists one row per seed slug, at the highest version.
- `test_construct_library_versions.py::test_superseded_version_still_resolvable_by_id` -
  a superseded row is still fetchable and usable for a run.
- `test_construct_library_versions.py::test_sync_updates_verification_status_in_place` -
  re-syncing after a status change updates the existing row.
- `test_construct_library_versions.py::test_sync_still_refuses_item_change_under_same_version` -
  the append-only guard is intact.
- `test_construct_library_versions.py::test_review_applied_expected_shape` - 23 v2
  files exist, 88 constructs verified, 6 still needs_verification, 96 reverse flags.
- `validate_constructs.py` passes with 117 files and reports the 4 all-reversed warnings.

## Implementation notes

Files changed: `packages/construct_library/constructs/*.yaml` (23 new v2 files, 94
in-place metadata updates), `packages/construct_library/apply_review.py` (new),
`packages/construct_library/reviews/` (new, the returned review file),
`backend/app/construct_lib.py` (metadata sync), `backend/app/main.py` (collapse to
latest seed version), `backend/tests/test_construct_library_versions.py` (new).

## Deviations (filled after implementation)

- Three source URLs the reviewer supplied carried a PsycNET `auth_token` query
  parameter (a per-session credential that expires and should not be committed). The
  token is stripped and the base URL kept; where that leaves a paywalled link, the
  citation's DOI remains the durable pointer. No DOI was invented: the only DOI added
  is the one the reviewer supplied verbatim for SWLS.
- `bas_2` and `cage_questionnaire` were flagged "source URL not found / no longer
  accessible" with no replacement given. Their `source_url` is left unchanged and the
  gap is recorded in the construct's `review.notes` rather than guessed at.
