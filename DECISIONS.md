# Decisions Log

> One entry per architecture/infrastructure/vendor/model decision.
> Format: date - decision - why - rejected alternative - revisit trigger.
> CLAUDE.md hard rule: no new infrastructure without an entry here.

## 2026-07-09 - Repo seeded from demo; demo stays live
Mainline moves to this repo (future home: Culture-and-Morality-Lab org). The public demo repo
and HF Space remain deployed and untouched - the PI links people to it. Rejected: evolving the
demo repo in place (would couple experiments to a live artifact). Revisit: after Phase 1, repo
transfers to the lab org (design §7 step 7).

## 2026-07-09 - Postgres jobs table over Redis/RQ (design §6)
Durable queue via SELECT ... FOR UPDATE SKIP LOCKED + leases + sweeper; job state already in
the DB. Rejected: Redis/RQ (a third stateful service before pressure exists). Trigger to
revisit: multiple workers, scheduling needs, sustained queue depth.

## 2026-07-09 - Managed auth (Supabase Auth recommended), staged Google-first (design §8, §4.1)
Rejected: custom password auth (hashing, reset flows, verification email, lockouts = hidden
security work). Staged: Google sign-in first (zero email infra), email/password second within
the same provider. Trigger: PI sign-off starts Phase 2.

## 2026-07-09 - MiniLM default; e5-large-v2 strong option; multilingual-E5 (design §13)
MiniLM is the CCR reference model → comparability with the published method; E5 models require
"query: " prefixes (encoded in registry usage_config). Rejected: e5-large-v2 as default
(slow on CPU, breaks anonymous inline tier; cross-family scores not comparable). Trigger:
lab validation study could change defaults.

## 2026-07-09 - Reverse scoring: raw + flags only in v1 (design §11)
Aggregates exclude reversed items only when explicitly required; all-reversed blocks aggregate.
Rejected: sign-negation by default (silently invented psychometrics). Trigger: lab methods
decision after discussion with PI.

## 2026-07-09 - Placeholder demo sign-in for tier testing (not security)
Anonymous caps (2 MB / 500 rows, env-tunable) enforce the design §5.1 tiers now; a
name-only signed-cookie session lifts them so the tiered UX is testable before Supabase
auth lands. get_current_user() is the single Phase 2 integration point. Rejected: waiting
for real auth (tiers untestable) and client-only gating (trivially bypassed).

## 2026-07-09 - Open archive/delete until accounts exist
Any visitor can archive/delete any project on the shared instance: there are no owners yet,
and mistake-cleanup matters more than protection on a demo. Delete requires typing the
project name, cascades to all files/rows, and is logged without text (design §9). Phase 2
adds ownership checks to the same endpoints.

## 2026-07-09 - No em dashes in project text (Deva)
Style rule across UI, docs, comments, commits. Enforced by a PostToolUse hook; swept 50
existing files.

## 2026-07-10 - Questionnaire import policy (Mohammad's 40-scale collection)
Multi-dimensional questionnaires split into one construct per dimension (a CCR run scores
one construct; a blended Big Five score would be meaningless): 38 questionnaires -> 94
entries. "(R)" markers in subconstruct labels imported as reverse-scored flags (35 items);
scales without markers default to false with reverse_flags_source recorded as pending.
Filler items excluded (8, LOT-R and Hope Scale). SWLS skipped as duplicate of the existing
seed. All imported entries are needs_verification until wording is checked verbatim.
Importer kept as a permanent tool: packages/construct_library/import_from_xlsx.py.

## 2026-07-11 - Local email+password accounts as the interim auth provider (Deva)
Mohammad delegated technical decisions and asked for the best free option available now.
Supabase remains the Phase 2 target but needs dashboard/OAuth setup on lab accounts;
interim: local accounts with stdlib scrypt password hashing, HMAC-signed session cookie,
register/login/logout endpoints. No email verification and no self-service password reset
(admin action at lab scale) - documented in the UI. get_current_user() stays the single
swap point, so the Supabase move replaces token issuance only. Rejected: waiting on
Supabase (blocks run limits, retention tiers, and real-user testing), shipping the
name-only placeholder to real users (no actual account boundary).

## 2026-07-11 - Anonymous tier: 3 runs/day + delete-after-analysis; signed-in: 15 saved runs (PI 2026-07-10)
Run limit as a signed cookie counter, reset daily (UTC): a nudge toward accounts, not a
security boundary - clearing cookies evades it, acceptable at academic scale (recorded
trade-off). Anonymous corpus files (and embedding caches) are deleted the moment a run
completes; results stay downloadable until the project's TTL purge (CCR_ANON_TTL_HOURS,
24 on deployments, 0 = off in local dev). Signed-in users are never auto-deleted; a
15-saved-run cap (middle of Mohammad's 10-20) refuses new runs until they delete old ones.
All numbers env-tunable. This retention shape is also what fits the infra into free tiers
($0-60/yr vs the earlier ~$600 estimate).

## 2026-07-11 - Ownership model: private owned projects, shared anonymous space
Projects created signed-in are visible/editable only by their owner (403 otherwise);
anonymous projects remain a shared open space subject to TTL purge. Replaces the 07-09
"open archive/delete" decision now that accounts exist.

## 2026-07-11 - Corpus-embedding cache keyed by (corpus, column, model, revision, prefix)
~97% of a run is document embedding and the core CCR workflow is many constructs against
one corpus. Corpora are immutable after upload, so cached .npy embeddings are bit-identical
on reuse; cache skipped for anonymous runs (files deleted anyway) and invalidated by
corpus/project deletion. Rejected: quantization/fp16/GPU speedups - they change embedding
values and would break reproduction-script parity and cross-run comparability. Any faster
model variant must be a separate registry entry, never a silent swap.

## 2026-07-11 - Construct upload from CSV/XLSX: parse -> preview -> confirm
Items are parsed server-side (tolerant ingest, "item"/single/longest-string column,
reverse via column or trailing "(R)" marker - same convention as the lab spreadsheet
importer) but NEVER saved directly: the researcher reviews and edits in the form first,
because item wording IS the instrument. Item files are deleted immediately after parsing.

## 2026-07-13 - Storage interface ships now; R2 enabled at deploy by config (Deva)
Local disk stays the dev default, but the S3-compatible path (Cloudflare R2) is
implemented and tested behind one storage module: uploads, results, exports (streamed
through the API - bucket stays private), and retention deletes all go through locators
stored in the existing path columns (no migration; old local paths keep working).
Flipping production to R2 = CCR_STORAGE=s3 + four env values. Rejected: deferring the
implementation to Phase 2 (turns a deploy-day config flip into deploy-day development),
and presigned public URLs (private bucket + API streaming is simpler and safer at lab
scale). Embedding caches deliberately stay on local disk: derived data, no durability need.

## 2026-07-13 - Google sign-in via Supabase PKCE, server-side, feature-flagged (Deva)
Implemented as a plain redirect flow: /api/auth/google/login sends the browser to
Supabase's Google authorize URL with a PKCE challenge (verifier in a short-lived signed
cookie); the callback exchanges the code server-side (stdlib urllib, no new deps), then
finds-or-creates a local user by email and issues the SAME session cookie as password
accounts. Inert until SUPABASE_URL + SUPABASE_ANON_KEY are set, so dev/tests need no
Supabase project. Google-only accounts have no password hash and password login points
them to the Google button. Rejected: supabase-js in the frontend (breaks the
react+react-dom-only dependency rule for one button) and provider-JWT sessions (would
fork the tier/ownership logic into two session formats for no benefit).
