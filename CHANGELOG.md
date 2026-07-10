# Changelog

Format: [Keep a Changelog](https://keepachangelog.com/). User-visible changes only.

## [Unreleased]

### Added
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

### Changed
- Project-wide style rule: no em dashes in any project text (enforced by an edit hook).

### Fixed
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
