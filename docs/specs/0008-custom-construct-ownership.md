# Spec 0008 - Custom construct ownership and deletion

Status: implemented 2026-09-04
Reported by: a PhD student on the public site, via Deva (2026-09-04): custom
constructs someone else created were visible after signing in, with no way to
remove them.

## Problem

`Construct` has no owner column. Every custom construct a visitor creates is
global, so `GET /api/constructs` returns all of them to everyone, and the
picker groups them under a heading that reads "My custom constructs" - which
has never been true. There is also no delete path: nothing in the app, the
admin router, or retention ever removes a construct, so the public picker
accumulates every construct anyone has ever typed.

This is the same defect class as the project listing leak fixed in 049074a
(`_visible_owners`), which was fixed for projects only. Constructs were missed
because they had no ownership concept to get wrong.

## Contract

**Ownership.** `Construct.owner_user_id` (String(32), default `""`), mirroring
`Project.owner_user_id`. Seeds keep `""` and are identified by `is_seed`.

**Visibility.** `GET /api/constructs` returns, for every viewer, all seed
constructs, plus custom constructs whose `owner_user_id` equals the viewer's
id (signed in) or `""` (anonymous). This is exactly `_visible_owners`: a
signed-in user sees only their own; the anonymous bucket stays shared, because
an anonymous visitor has no identity to scope by.

**Deletion.** `DELETE /api/constructs/{id}`:
- 404 when the construct does not exist or is not visible to the caller;
- 403 for seeds (library constructs are not user-deletable) and for a construct
  owned by another account;
- when no run references it: the row is deleted (204);
- when a run references it: the row is retained and `hidden` is set, because
  `Job.construct_id` is a FK and past runs must stay reproducible. The response
  says which happened so the UI can tell the truth.

`hidden` constructs never appear in the listing.

**UI.** Each row under "My custom constructs" gets a delete control that opens
a confirmation dialog naming the construct; deleting refreshes the picker.

## Non-goals

- Per-visitor scoping of ANONYMOUS constructs. There is no anonymous identity
  cookie (the run counter carries only a date and a count), so anonymous
  constructs stay in the shared bucket exactly as anonymous projects do.
  Recorded as a known residual below.
- Transferring constructs created anonymously to an account on sign-in.
- Admin bulk cleanup of pre-existing constructs; the migration default puts
  them in the anonymous bucket, which already removes them from every
  signed-in user's picker.

## Tests

- a signed-in user does not see another account's custom construct, and does
  not see anonymous ones (the reported bug);
- a signed-in user does see their own, and every viewer sees seeds;
- delete removes an unused construct; a second delete 404s;
- delete refuses a seed (403) and another account's construct (403);
- a construct used by a run is hidden rather than deleted, the run and its
  metadata still resolve, and it leaves the listing.

## Implementation notes

Both new columns are additive with scalar defaults, so `auto_migrate_sqlite`
adds them to existing databases. Existing custom constructs migrate to
`owner_user_id = ""`: they become invisible to signed-in users immediately,
which is the reported complaint, and remain in the anonymous bucket because we
cannot know who created them.

## Deviations (filled after implementation)

None.

## Known residual

Anonymous visitors still see each other's anonymous constructs on a public
instance. Closing that needs an anonymous session identity, which would also
let anonymous projects be scoped; it is a larger change and is tracked in
ROADMAP.md rather than bolted on here.
