# Changelog

Format: [Keep a Changelog](https://keepachangelog.com/). User-visible changes only.

## [Unreleased]

### Fixed
- Improved dashboard responsive layout, focus states, and table overflow handling on
  narrow screens.

### Added
- Repository initialized from the public demo (v0.1 feature set: projects, tolerant CSV/XLSX
  ingestion, seeded constructs, MiniLM/mpnet/multilingual models, async runs with progress,
  results dashboard with descriptive stats + per-item loadings + top/bottom texts,
  data-quality warnings, CSV export mirroring ccr_wrapper shape, reproducibility metadata).
- Model registry (packages/model_registry) and versioned construct library
  (packages/construct_library) with validators — not yet wired into the app (specs 0003/0004).
- Claude Code project config: CLAUDE.md, path-scoped rules, 3 review agents, 4 commands,
  golden-file protection + Python syntax hooks.

## [0.2.0] - 2026-07-09

### Added
- Language selection per run (English default) with corpus-level language detection:
  warnings for language mismatch, uncertain detection, and model/language coverage
  (multilingual model checked against its real ISO language set). (spec 0001/0003)
- Very-short-text warning (< 4 words) with affected-row samples. (spec 0001)
- Downloadable Python reproduction script per run — offline-runnable, embeds construct
  items, model revision, and E5 prefix logic — plus pinned requirements file. (spec 0002)
- Model registry drives the model dropdown, validation, prefixes, and metadata:
  MiniLM (default), E5-Large-v2, Multilingual-E5-base. (spec 0003)
- Construct library loaded from versioned YAML files with item hashes, citations, and
  verification status shown in the UI; custom constructs support reverse-scored flags. (spec 0004)
- Run metadata now records: output_schema_version, scoring.adjustment_strategy, language
  block, construct snapshot, model revision, environment pins.

### Changed
- All warnings are structured objects (code/severity/message/count/rows) — UI renders codes.
- /api/models response shape changed (registry ids like "all-minilm-l6-v2" replace provider ids).
- Delimiter detection restricted to real candidates (, ; tab |) — fixes single-column
  sentence CSVs being split on spaces.

### Removed
- backend/app/seed_constructs.py (replaced by packages/construct_library YAML).
