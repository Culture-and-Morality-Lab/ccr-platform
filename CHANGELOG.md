# Changelog

Format: [Keep a Changelog](https://keepachangelog.com/). User-visible changes only.

## [Unreleased]

### Changed
- Construct library verified against the source publications. All 525 items across the
  94 constructs were reviewed (wording, reverse-scoring keys, subscale grouping,
  citations); 88 constructs are now marked verified and show who reviewed them and
  when, instead of the blanket "needs verification" flag every construct carried. The
  review corrected 61 reverse-scoring flags across 14 constructs (the library had 35
  flagged items, it now has 96), 8 item wordings, the item order of two scales that did
  not match their own source (which decides what the per-item export columns line up
  with, though not the scores), one subscale grouping in the SCS-SF, and a batch of dead
  or incomplete citation links. Corrected constructs ship as a new
  version: the picker offers the corrected one, and runs that used the earlier version
  still open, export, and reproduce exactly as before. Six constructs stay flagged, all
  for the same two open wording questions: the five IPIP Big Five scales and the K10.
  (spec 0007)

### Added
- Runs now warn when every item in a construct is reverse-scored. Scores are raw
  similarities with no reverse adjustment, so for such a construct a higher score means
  the text expresses the OPPOSITE of the construct's name. The results page previously
  told every run that higher meant more of the construct; it now defers to this warning,
  which names the construct affected. Four library constructs are in this position after
  the review: De Jong Gierveld social loneliness and the three SCS-SF negative subscales.
- Model picker timing estimates are real measurements instead of placeholders. Every
  model in the registry now records seconds per 1,000 texts for short, medium, and long
  texts, with the machine and date they were measured on.

### Fixed
- PsyEmbedding models now load through the standard sentence-transformers path.
  The lab's four Hugging Face repos were missing the 1_Pooling config their
  modules.json references; the fix was pushed upstream (2026-08-22), the
  registry re-pins each model to the fixed revision (one commit above the old
  pin, identical weights, identical scores), and the pooling_fallback
  workaround is gone from models.yaml. Reproduction scripts for new runs use
  the plain one-line loader; scripts from older runs still carry the explicit
  module assembly and keep working.
- Signed-in users no longer see other people's anonymous projects. A signed-in
  account's project list shows only its own projects; projects created without
  signing in stay in the shared anonymous space.
- The site identity footer now shows only on the public welcome page, not on the
  dashboard and results views.

### Added
- Anchor vectors (bipolar constructs): a run can score texts along the axis between a
  target construct and a contrasting "opposite" construct (anchor vector = target
  centroid minus opposite centroid), with a cosine (default) or dot-product metric.
  Results are bipolar - the distribution is centered on zero, top/bottom texts are
  labeled "most <target>" / "most <opposite>", and item loadings show per pole. The
  export adds target_/opposite_ per-item similarities, both per-pole CCR scores, and
  anchor_score under output_schema_version 1.2; run metadata records both construct
  snapshots and the scoring block; the reproduction script embeds both item sets and
  reproduces the anchor-vector math. (spec 0006)
- Public guide (/guide): a "Sample datasets" section that links ready-to-run example
  corpora (served from /samples) so new users can try CCR without their own data, with
  a pointer from the upload step. Suggested by Meriel Burnett.
- Real accounts: register/sign in with email + password (free, no external service).
  Signing in lifts anonymous limits and keeps your data. No self-service password
  reset yet (contact the admin); Google sign-in arrives with the managed-auth swap.
- Anonymous usage tiers (PI decisions): 3 runs/day (counter shown under the Run
  button, resets daily), uploads deleted immediately after analysis (results stay
  downloadable), whole anonymous projects purged after 24h on hosted instances.
- Saved-run cap for signed-in users (15): new runs are refused at the cap; nothing
  is ever auto-deleted from an account.
- Project ownership: signed-in projects are private to their owner; anonymous
  projects remain shared.
- Custom constructs can be uploaded from CSV/XLSX (item column or one per row;
  reverse-scored via a "reverse" column or trailing "(R)"), with a review-before-
  save preview. Typed items also support the "(R)" reverse marker.
- Runs table now shows the model and language of every run.
- Corpus-embedding cache: re-running new constructs against the same corpus skips
  document embedding entirely (seconds instead of minutes). Duplicate texts are
  embedded once. Gzip compression on API responses. Optional model pre-warm at
  startup (CCR_WARM_MODEL=1).
- MANUAL_TESTING.md: click-through scenarios for everything built so far.
- Deployment-ready container: updated Dockerfile (bakes MiniLM, retention on,
  persistent-volume instructions), production env vars documented in .env.example
  (CCR_SESSION_SECRET, CCR_COOKIE_SECURE, CCR_ANON_TTL_HOURS).
- Demo/test corpus kit in sample_data/ (one file per behavior): all text-QA warnings,
  French and mixed-language corpora for every language check, token-window truncation,
  multi-column text suggestion, semicolon and latin-1 ingestion, XLSX upload, and an
  MFQ-2-themed corpus showing per-foundation score spread. sample_data/README.md maps
  each file to what it triggers.
- Searchable construct picker replacing the flat dropdown: search by scale, construct, or
  category; results grouped by category; recently-used constructs pinned on top; full
  keyboard navigation. Scales to hundreds of library entries.
- Construct library expanded from 5 to 99 entries from the lab's questionnaire collection
  (38 questionnaires; multi-dimensional scales split per dimension, incl. MFQ-2's six
  foundations). Reverse-scored flags imported where the source marked them; filler items
  excluded; everything flagged needs-verification pending verbatim wording checks.
- Reusable importer for the lab's questionnaire spreadsheet format
  (packages/construct_library/import_from_xlsx.py).
- Anonymous vs signed-in upload tiers: anonymous uploads capped at 2 MB / 500 rows with a
  clear sign-in hint; signing in lifts limits. Sign-in is a labeled placeholder (name only)
  until managed auth arrives with lab accounts; tampered sessions are treated as anonymous.
- Project lifecycle: archive/unarchive (reversible, collapses into an Archived sidebar
  group) and permanent delete with type-the-name confirmation. Delete cascades to datasets,
  runs, uploaded files, and result files, and is logged without retaining any text.
- Public how-to guide at /guide (open to everyone): the upload to construct to run to
  export walkthrough, the four ways to add a construct (library, typed, uploaded, AI
  drafting) with the live AI model and prompt-version details, the models table, and a
  reproducibility section covering the results CSV, run metadata, and the offline
  reproduction script.
- AI construct path shows the drafting model on demand: a "Drafted by <model>" line with
  a hover/focus info bubble listing the model, provider, prompt version, item rules, and
  daily cap, read live from the API so it always matches the configured model.

### Changed
- Project-wide style rule: no em dashes in any project text (enforced by an edit hook).
- Guides split: /guide is now the public how-to guide; the click-through testing guide
  moved to /testing and is lab-only (same gate as /product). Lab members reach both from
  the header.
- Landing page links the PI's name (Mohammad Atari) to his website.

### Fixed
- Google sign-in no longer breaks when CCR_APP_URL is pasted with a trailing
  newline or space: the app trims the value before building the sign-in return
  URL. Untrimmed, the newline reached Supabase as %0A inside the redirect, so
  the redirect never matched the allow list and browsers flagged the link.
- Existing local databases no longer 500 after schema additions: additive
  SQLite auto-migration adds missing columns at startup (Alembic replaces this in
  Phase 2 with Postgres).
- Job worker survives lifespan restarts (dev reload previously killed job submission
  permanently).

### Fixed
- Project sidebar redesigned for growing lists: always-visible search, recency groups
  (Today / This week / Earlier), per-project run count + relative last-activity time,
  and ordering by last activity instead of creation date.
- Improved dashboard responsive layout, focus states, and table overflow handling on
  narrow screens.
- Aligned the run-analysis action with the model/language controls and made the project
  sidebar scroll cleanly as project counts grow.

### Added
- Repository initialized from the public demo (v0.1 feature set: projects, tolerant CSV/XLSX
  ingestion, seeded constructs, MiniLM/mpnet/multilingual models, async runs with progress,
  results dashboard with descriptive stats + per-item loadings + top/bottom texts,
  data-quality warnings, CSV export mirroring ccr_wrapper shape, reproducibility metadata).
- Model registry (packages/model_registry) and versioned construct library
  (packages/construct_library) with validators - not yet wired into the app (specs 0003/0004).
- Claude Code project config: CLAUDE.md, path-scoped rules, 3 review agents, 4 commands,
  golden-file protection + Python syntax hooks.

## [0.2.0] - 2026-07-09

### Added
- Language selection per run (English default) with corpus-level language detection:
  warnings for language mismatch, uncertain detection, and model/language coverage
  (multilingual model checked against its real ISO language set). (spec 0001/0003)
- Very-short-text warning (< 4 words) with affected-row samples. (spec 0001)
- Downloadable Python reproduction script per run - offline-runnable, embeds construct
  items, model revision, and E5 prefix logic - plus pinned requirements file. (spec 0002)
- Model registry drives the model dropdown, validation, prefixes, and metadata:
  MiniLM (default), E5-Large-v2, Multilingual-E5-base. (spec 0003)
- Construct library loaded from versioned YAML files with item hashes, citations, and
  verification status shown in the UI; custom constructs support reverse-scored flags. (spec 0004)
- Run metadata now records: output_schema_version, scoring.adjustment_strategy, language
  block, construct snapshot, model revision, environment pins.

### Changed
- All warnings are structured objects (code/severity/message/count/rows) - UI renders codes.
- /api/models response shape changed (registry ids like "all-minilm-l6-v2" replace provider ids).
- Delimiter detection restricted to real candidates (, ; tab |) - fixes single-column
  sentence CSVs being split on spaces.

### Removed
- backend/app/seed_constructs.py (replaced by packages/construct_library YAML).
