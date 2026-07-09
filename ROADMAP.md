# Roadmap (from design doc §4 / §20 — capacity: one person, ≤20 hrs/week)

## Phase 0 — Visible progress (now)
- [x] Descriptive stats (mean/SD/min/max) — shipped in demo codebase
- [x] Spec 0001: short-text + language warnings (structured warning objects)
- [x] Spec 0002: offline-runnable Python script export + pinned requirements
- [x] Spec 0003: registry-driven models (E5 prefixes!) + language selection
- [x] Spec 0004: construct library from versioned YAML (assistant's questionnaires land here)

## Phase 1 — Engine hardening (weeks 3–5)
- [ ] Spec 0005: extract packages/ccr_engine + golden evals + ccr_wrapper parity tests
- [ ] Pin model revisions in models.yaml (remove PIN_ME)
- [ ] Registry validation in CI

## Phase 2 — Persistence + auth (weeks 6–9, AFTER §22 sign-off)
- [ ] Supabase Auth (Google first, then email/password) · projects · Postgres metadata + jobs
- [ ] Object storage behind the existing storage interface · TTL cleanup (anonymous 48h)
- [ ] Anonymous caps per design §5.1 starter table

## Phase 3 — Production-lite launch
- [ ] Repo → Culture-and-Morality-Lab org · staging + production hosting (Option B)
- [ ] Backups, monitoring, privacy wording (lab-provided), verified-constructs workflow

## Recurring (PI mandate 2026-07-09: proactively suggest newer/lighter/cheaper options)
- [ ] Model landscape review each phase: check MTEB leaderboard + HF for newer/lighter embedding
      models; benchmark candidates through the golden/parity harness before proposing.
- [ ] Cost review at each infra decision: free tiers first, annual-friendly, no idle spend.

Blocked on PI (design §22): auth provider, hosting path, storage backend, retention windows, anonymous caps.
