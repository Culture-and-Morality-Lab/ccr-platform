# Changelog

Format: [Keep a Changelog](https://keepachangelog.com/). User-visible changes only.

## [Unreleased]

### Added
- Repository initialized from the public demo (v0.1 feature set: projects, tolerant CSV/XLSX
  ingestion, seeded constructs, MiniLM/mpnet/multilingual models, async runs with progress,
  results dashboard with descriptive stats + per-item loadings + top/bottom texts,
  data-quality warnings, CSV export mirroring ccr_wrapper shape, reproducibility metadata).
- Model registry (packages/model_registry) and versioned construct library
  (packages/construct_library) with validators — not yet wired into the app (specs 0003/0004).
- Claude Code project config: CLAUDE.md, path-scoped rules, 3 review agents, 4 commands,
  golden-file protection + Python syntax hooks.
