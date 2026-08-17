# Deploying the lab instance (Hugging Face Space)

The Space builds from this repo's Dockerfile. One-time setup lives in the
Space settings; after that, deploys are just `git push prod main`.

This repo deploys to the Space `Culture-and-Morality-Lab/ccr-platform`, which
is served to the public at https://psychologicaltextanalysis.com through the
Cloudflare Worker in `deploy/reverse-proxy-worker.js` (Spaces cannot hold a
custom domain on any tier). Account-by-account setup and the migration from the
personal dev stack live in `deploy/PRODUCTION_RUNBOOK.md`.

## Space settings (Settings > Variables and secrets)

Hugging Face keeps **Variables** and **Secrets** in two separate stores, and a
name defined in BOTH puts the Space into `CONFIG_ERROR` ("Collision on
variables and secrets names") before it even builds. Add each key below to one
store only - if the Space reports a config error after a settings change, look
for a duplicated name first, not a bad value.

Secrets (credentials - encrypted, write-only once set):

| Secret             | Value                                                       |
| ------------------ | ----------------------------------------------------------- |
| CCR_SESSION_SECRET | `python3 -c "import secrets; print(secrets.token_hex(32))"` |
| SUPABASE_URL       | from Supabase > Project Settings > API                      |
| SUPABASE_ANON_KEY  | from the same page (anon public key, NOT service_role)      |
| DATABASE_URL       | Supabase session-pooler URI (see persistent storage below)  |

Variables (non-sensitive tuning - visible in settings, safe to edit):

| Variable               | Value                                               |
| ---------------------- | --------------------------------------------------- |
| CCR_APP_URL            | https://psychologicaltextanalysis.com               |
| CCR_COOKIE_SECURE      | 1                                                   |
| CCR_MAX_ROWS           | 20000 (global row ceiling; code default is 100000)  |
| CCR_MAX_UPLOAD_BYTES   | optional; code default is 52428800 (50 MB)          |
| CCR_ANON_MAX_BYTES     | optional; code default is 5242880 (5 MB)            |

Paste `CCR_APP_URL` with no trailing space or newline. The app builds the
Google sign-in return URL from it, so a stray newline arrives at Supabase as
`%0A` inside `redirect_to`: the redirect stops matching the allow list and
browsers flag the link as dangerous. The app trims the value since 2026-08-17,
but older deployments and any other URL variable still take it literally.

`CCR_MAX_ROWS` is the limit that actually bounds a run - embedding cost scales
with rows and tokens, not file bytes, and on 2 vCPU it is *time*, not memory,
that runs out first. Measured on the cpu-basic Space shape (2 vCPU / 16 GB):
upload + parse peaks at roughly 5x file size, so even a 50 MB corpus costs
about 250 MB of the 16 GB available. The byte ceiling (`CCR_MAX_UPLOAD_BYTES`,
default 50 MB) is an abuse/OOM backstop that should not fire on a legitimate
corpus: at `CCR_MAX_ROWS=20000` it only binds above ~2.6 KB per row, which is
already past every model's token window. Anonymous uploads use the lower of
that and `CCR_ANON_MAX_BYTES` (5 MB), sized as a pre-parse shield so an
unauthenticated request cannot make the server parse a large file only to
reject it at row 201.

Embedding throughput at 2 threads, batch 64 (see `scripts/bench_models.py` to
re-measure on the actual host - these are derated estimates, not Space-measured):

| model         | ~15-word rows | ~60-word rows | ~250-word rows |
| ------------- | ------------- | ------------- | -------------- |
| MiniLM L6 v2  | ~1.2 s/1k     | ~2.1 s/1k     | ~8.4 s/1k      |
| E5 Large v2   | ~7.5 s/1k     | ~27 s/1k      | ~123 s/1k      |

At `CCR_MAX_ROWS=20000` that is ~25 s to ~3 min for MiniLM, but up to ~40 min
for E5 Large on long documents. Jobs that long are also *fragile*: a Space
restart marks any running job failed (`recover_orphaned_jobs`), so worst-case
job duration - not row count alone - is the number to keep in view.

Retention (CCR_ANON_TTL_HOURS=24) and model pre-warm are already defaults in
the Dockerfile.

## Tester guide

The deployed instance serves a click-through testing guide at /guide with
download links for every demo corpus (served from /samples). Send the PI and
students that URL; no files need to be shared out of band.

## Supabase setup for Google sign-in (one time)

1. supabase.com > New project (free tier).
2. Authentication > Providers > Google > Enable. Copy the shown callback URL
   (https://PROJECT_REF.supabase.co/auth/v1/callback).
3. console.cloud.google.com > OAuth consent screen (External) > Credentials >
   Create OAuth client ID (Web application) > add the Supabase callback URL as
   an authorized redirect URI. Paste client id/secret back into the Supabase
   Google provider form.
4. Authentication > URL Configuration: add BOTH redirect URLs:
   - http://127.0.0.1:8000/api/auth/google/callback
   - https://psychologicaltextanalysis.com/api/auth/google/callback
   Each entry must match what the app sends byte for byte, so keep the custom
   domain (not the hf.space host) here once the Worker is live.
5. Project Settings > API: copy the Project URL and anon key into the Space
   secrets (and your local .env).

## Push

```bash
git push origin main        # GitHub
git push prod main          # Hugging Face Space (rebuilds + redeploys)
```

The prod remote has no stored token; use the lab HF username and a WRITE token
as the password when prompted (or a credential helper). Pushing to origin alone
changes nothing on the deployed instance.

## Caveats of the deployed instance

- ~~Ephemeral disk~~ RESOLVED (2026-08-06, verified): the Space now runs with
  `DATABASE_URL` (Supabase Postgres) and the `CCR_STORAGE=s3` R2 secrets set,
  so accounts, constructs, runs, AND uploaded files survive rebuilds and
  restarts. The paragraph below ("Persistent storage") documents that setup
  for anyone redeploying from scratch. Without those secrets, the old caveat
  applies: SQLite + local files reset on every rebuild.
- The lab Space runs on cpu-upgrade hardware, so it does not sleep. On the
  free cpu-basic tier a Space sleeps after ~48 h idle and the first visit
  wakes it (~1 min), which is still the behaviour of the personal dev Space.

## Persistent storage (make accounts/data survive restarts)

HF Spaces free disk is ephemeral - SQLite is wiped on every rebuild. Point the
app at your Supabase Postgres (free, already used for Google auth):

1. Supabase dashboard > Project Settings > Database > Connection string >
   "Session pooler". Copy the URI and put your DB password into it.
2. Add it as a Space secret named `DATABASE_URL`.
3. Restart the Space. First boot creates the tables in Postgres; data now
   persists across restarts and redeploys.

For durable uploaded FILES too (not just the database), also set the
`CCR_STORAGE=s3` R2 secrets (see .env.example). Without that, the database
rows survive but a signed-in user's uploaded corpus file can still vanish on
restart (results CSVs are regenerable by re-running).
