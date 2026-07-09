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
