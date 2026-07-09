# Spec 0004 — Construct library from YAML (brief)

**Status:** implemented (2026-07-09)
**Phase:** 0/1    **Design doc ref:** §10.1, §11
**Context:** Mohammad's assistant will send questionnaires to add.

Replace `backend/app/seed_constructs.py` seeding with `packages/construct_library/constructs/*.yaml`
as the source of truth: loader validates via the same rules as `validate_constructs.py`,
computes item_hash with the reference algorithm, seeds/updates DB rows keyed
(construct_id, version) — append-only, never mutate an existing version. Run metadata embeds
the full construct snapshot. UI shows verification_status (verified prominently; others with
a "wording not yet verified" chip). New questionnaires from the lab = new YAML files + validator
run; item wordings marked needs_verification until checked verbatim against the publication.
Reverse-scored flags flow through to exports per design §11 (raw + flags in v1).

**Key tests:** loader/validator parity, append-only enforcement (same id+version re-seed is
idempotent; changed items under same version = hard error), snapshot-in-metadata, status chip logic.
