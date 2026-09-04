# Spec 0009 - Anonymous session identity, construct lifecycle, and creation cap

Status: implemented 2026-09-04
Follows spec 0008, which scoped custom constructs to signed-in owners but left
the anonymous tier as one shared bucket.

## Problem

Three separate defects were being read as one "constructs are public" bug.

1. **No anonymous identity.** `owner_user_id == ""` meant "anonymous", so every
   anonymous visitor shared a single bucket and saw each other's projects and
   custom constructs. Spec 0008 and 049074a fixed signed-in users only.
2. **Constructs had no lifecycle.** `retention.py` imported `Corpus, Job,
   Project`; `Construct` was not in it, and constructs hang off no project so
   nothing cascaded to them. Corpora are deleted when a run finishes and
   projects expire on a TTL, but a custom construct anyone typed stayed in the
   database and in the picker permanently. This, not visibility, is what filled
   the public picker.
3. **Creation was ungated.** `POST /api/constructs` had no auth check, no daily
   cap and no per-session limit - the only unbounded, permanent, ungated write
   path in the anonymous tier, next to a 3/day run cap and a signed-in-only
   gate on AI drafting.

## Contract

**Identity.** A signed cookie (`ccr_anon`) carries a random session id, minted
on an anonymous visitor's first create. `auth.owner_key(request, user)` returns
the user id when signed in and `anon:<session id>` otherwise, and that value is
what `owner_user_id` stores. A visitor with no cookie owns nothing.

**Visibility.** Projects and constructs are listed where
`owner_user_id == owner_key`. Seeds are always listed. Legacy `""` rows belong
to no reachable session, so they disappear from every listing and expire on the
TTL.

**Adoption.** Registering or signing in moves this browser's `anon:<id>`
projects and constructs onto the account. Without it, scoping anonymous work to
a session would strand it at sign-in, and the UI's "sign in to keep it" would be
false. This also replaces the reason 049074a left the anonymous bucket open to
everyone (anonymous-then-sign-in continuity).

**Lifecycle.** `purge_expired_anonymous_constructs` deletes anonymous custom
constructs older than `CCR_ANON_TTL_HOURS`, skipping any a run still
references. It runs after the project sweep, which removes most of those runs.

**Cap.** Anonymous construct creation is capped per day
(`CCR_ANON_MAX_CONSTRUCTS_PER_DAY`, default 5) via a signed counter cookie,
mirroring the run counter, returning 429 with a sign-in hint.

**UI.** After an anonymous visitor saves a construct, a notice says it is saved
to this browser only, expires in 24 hours, and moves to their account if they
sign in.

## Non-goals

- Blocking anonymous construct creation behind sign-in. Testing a construct
  that is not in the library is the most valuable thing a visiting researcher
  can do; gating persistence rather than creation keeps that path open.
- Deleting legacy `""` rows on upgrade. They stop being listed and expire on
  the normal TTL, so no destructive migration is needed.

## Tests

- a separate browser's anonymous construct is invisible both to a signed-in
  user and to another anonymous visitor;
- signing in adopts this browser's anonymous constructs;
- the daily cap returns 429 and names sign-in;
- expired anonymous constructs are purged; one a run references is kept;
- the existing TTL/ownership suite still passes with anonymous rows now
  carrying `anon:<id>`.

## Implementation notes

`auth.is_anonymous_owner` / `anonymous_owner_clause` match both shapes (`""` and
`anon:`). Every place that treated `""` as "anonymous" had to move to them:
`jobs.py` (whether to delete the corpus after a run), `retention.py` (the TTL
sweep), and the admin counters. Missing one of those silently stops anonymous
data expiring, which is why they are called out here.

The cap is a signed cookie, so like the run counter it stops casual
over-creation rather than a determined script. The TTL sweep is what actually
bounds storage.

## Deviations (filled after implementation)

Two existing tests changed because adoption is new behaviour, not because they
were wrong: the TTL purge test now signs in BEFORE creating its anonymous
projects (otherwise registering adopts them and they stop being TTL
candidates), and spec 0008's leak test now uses a second `TestClient` to stand
in for a different browser.
