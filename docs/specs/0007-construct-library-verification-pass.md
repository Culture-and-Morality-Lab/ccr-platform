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

Some of her findings are not applied here: two need a PI decision, and several turned
out to be version differences or gaps in the review sheet we sent her (see Non-goals).

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
- 8 verbatim wording corrections, one item each, in 8 constructs.
- 2 item-ORDER corrections (`rses`, `cbi_work_related_burnout`): the stored order did
  not match the printed order of each construct's own recorded source, which mislabels
  every `sim_item_N` export column. Item ids are renumbered by position so `item_id`
  again means "source item number". Scores are unaffected: the CCR score is the mean
  across items, which is order-independent.
- 1 subscale regrouping: `scs_sf_self_judgment_1` moves to `scs_sf_over_identification`
  per the SCS-SF coding key, changing the item list of both constructs.

23 constructs get a `version: 2` file. The `version: 1` files stay exactly as they are:
append-only means old versions remain resolvable for runs that already used them.

Metadata-level changes do NOT feed `item_hash` and are therefore applied in place on
the existing version:

- `verification_status` promoted `needs_verification -> verified` for 88 constructs.
- Citation and `source_url` repairs (dead links replaced with the URLs the reviewer
  supplied, DOIs she supplied added).
- A `review:` provenance block on every construct recording reviewer, review date, and
  outcome, plus a note wherever something is unresolved, so `verified` is attributable
  rather than an unsourced claim and every unverified construct says why.

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
This is a faithful reading of the source scales - the De Jong Gierveld social loneliness
items are all positively worded, and the SCS-SF negative subscales are reverse-keyed in
the published coding key - so the flags are correct.

What that means at scoring time needed fixing, not just noting. `exclude_reversed` is a
design-doc strategy that is NOT implemented: runs record
`adjustment_strategy: "none"` and aggregate `mean_all_items`, so nothing was blocked and
no adjustment was applied. A construct whose items are all reverse-keyed therefore scores
in the opposite direction to its own name, while the results page told every run
"Higher = the text expresses the construct more strongly". This spec adds a
`CONSTRUCT_ALL_ITEMS_REVERSED` warning (severity `warning`, names the construct) emitted
whenever every flag on a scored construct is set, including the opposite pole of an
anchored run, and the results page now defers to that warning instead of asserting a
direction. The validator's existing all-reversed line still fires at build time; its
message mentions `exclude_reversed`, which remains aspirational.

**Metadata additions.** None. No output column changes, no `output_schema_version`
bump: scores, columns, and the export shape are unchanged. Runs that pin a v1
construct reproduce exactly as before, because v1 rows are never mutated.

## Non-goals

Only 6 constructs keep `verification_status: needs_verification`, and both reasons are
PI decisions rather than open verification questions.

Four findings that this spec originally held back were resolved by going back to the
reviewer (2026-08-27). Her answers are worth recording, because in three of the four the
disagreement was about WHICH PRINTING of a scale is authoritative, not about who read it
correctly:

- **MFQ Fairness.** She read the questionnaire printed at the end of Graham et al.
  (2011), the paper this construct cites, which reads "treated differently **from**
  others" (twice). The moralfoundations.org MFQ30 handout reads "than others". The cited
  paper wins, so her correction IS applied, and `source_url` now points at the paper so
  items, citation, and source agree. An earlier draft of this spec reverted her here on
  the strength of the handout; that was wrong.
- **RSES item order.** She used the `source_url` recorded on the construct
  (socy.umd.edu, the Morris Rosenberg Foundation), whose questionnaire starts with "I
  feel that I'm a person of worth" and whose wording and reverse keys match this
  construct exactly. Her mapping is correct against our own recorded source, so the
  reorder is applied.
- **CBI work-related burnout item order.** Same: confirmed against the recorded
  `source_url`, mapping applied.
- **Team Psychological Safety.** She could not reach Edmondson (1999) through her
  library, used a third-party questionnaire, and said to keep the original if the paper
  disagreed. It does ("risk **on** this team"), so the stored wording stands and the
  construct is verified.

Two constructs (`bas_2`, `cage_questionnaire`) had genuinely dead source links (404 and
403 even from a browser user agent). She supplied working replacements, both verified to
contain the items, so both are verified. `mfq_care` and `mfq_fairness` were unverifiable
only because the review sheet shipped with an EMPTY `source_url` for them, which was our
omission.

**Two findings are left pending an explicit PI decision:**

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
- `test_superseded_version_still_resolvable_and_runnable` - a superseded row is hidden
  from the picker, still fetchable by id, and still completes a run whose metadata
  snapshot reports version 1.
- `test_sync_updates_verification_status_in_place` - re-syncing after a status change
  updates the existing row.
- `test_sync_still_refuses_item_change_under_same_version` - the append-only guard is
  intact.
- `test_review_applied_expected_shape` - 23 v2 files, 88 verified, 6
  needs_verification, 96 reverse flags, and every unverified construct carries a recorded
  reason.
- `test_superseded_files_keep_their_original_items` - compares every tracked construct
  against the committed copy in git, so an edit to a published version's items or flags
  fails even though the v1/v2 pair would look consistent.
- `test_all_reversed_construct_warns_about_score_direction` /
  `test_normal_construct_does_not_warn_about_direction` - the direction warning fires for
  an all-reversed construct and stays silent otherwise.
- `validate_constructs.py` passes with 117 files and reports the 4 new all-reversed
  warnings alongside the pre-existing `grit_s_consistency_of_interests`.

## Implementation notes

Files changed: `packages/construct_library/constructs/*.yaml` (23 new v2 files, 94
in-place metadata updates), `packages/construct_library/apply_review.py` (new),
`packages/construct_library/reviews/` (new, the returned review file),
`backend/app/construct_lib.py` (metadata sync), `backend/app/main.py` (collapse to
latest seed version), `backend/app/admin.py` (keep superseded rows out of the review
queue and its backlog count), `backend/app/jobs.py` (the direction warning),
`frontend/src/ResultsView.jsx` (defer to it),
`backend/tests/test_construct_library_versions.py` (new).

## Deviations (filled after implementation)

- Four PsycNET URLs the reviewer supplied carried an `auth_token` query parameter (a
  per-session credential that expires and should not be committed). The token is
  stripped and the base URL kept; where that leaves a login wall, the citation's DOI is
  the durable pointer. For `dirty_dozen_*` this replaces a working ResearchGate link with
  a paywalled one, which is a downgrade worth revisiting.
- Three DOIs were added (SWLS, horizontal collectivism, horizontal individualism). All
  three appear verbatim in the reviewer's notes; none was looked up. An earlier draft of
  this change also added a page range for the Triandis & Gelfand reference that she had
  not supplied - it has been removed, and only the SWLS page range (which she did supply)
  remains.
- The Grit-S replacement links are personal Dropbox share URLs and will rot. Kept because
  the recorded links were dead, but they need a durable replacement.
- `mspss_significant_other` and `shs` wording corrections are applied on the reviewer's
  word alone: neither recorded source served the item text for an independent check.
  Every other applied wording change was confirmed against the cited publication.
