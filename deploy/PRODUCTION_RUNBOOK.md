# Production Deployment Runbook

Moving the CCR Platform from the personal dev setup to the lab's own accounts,
and putting it on a custom domain. Written for a one-sitting migration: the code
is already unified in the lab GitHub repo, the app is feature-complete, and data
already lives on managed services (Postgres + object storage). This runbook
carries all of it over to lab-owned accounts.

Terminology: "the Space" is the Hugging Face Space that runs the app. "Custom
domain" is whatever the PI picks (examples below use `ccr.culturemoralitylab.org`;
swap in the chosen domain everywhere).

There are no em dashes in this file on purpose (project rule).

---

## 0. What is already done

- Code is unified in `Culture-and-Morality-Lab/ccr-platform` (public), with clean
  commit history.
- License texts are staged in the repo root (`LICENSE-MIT`, `LICENSE-APACHE`);
  one gets promoted to `LICENSE` once the PI picks.
- The app is one portable container (`Dockerfile`); the same image runs on any
  host, so "deploy" is a git push to the Space.
- Data services are already in use on the dev instance (Supabase Postgres via
  `DATABASE_URL`, Cloudflare R2 via the `CCR_S3_*` secrets), so this is a
  copy-to-lab-accounts job, not new infrastructure.

## 1. Accounts to create (lab email, free)

| Service | Purpose | Cost |
| --- | --- | --- |
| Hugging Face (account or org) | Hosts the Space | Free (cpu-basic) |
| Supabase | Postgres database + Google sign-in | Free tier |
| Cloudflare | Domain registrar + DNS + R2 storage + the reverse-proxy Worker | Free (domain ~20/yr; R2 needs a card on file but is free at this scale) |
| Groq | AI item-drafting key | Free tier |
| GitHub | Already done (lab org repo exists) | Free |

Save every password and key in a password manager as you go. These are the lab's
institutional credentials, not personal logins.

## 2. Secrets sheet (fill privately, never commit)

The new Space needs these. Collect the values as you complete each section
below, then paste them into the Space in section 7.

| Name | Store | Value source |
| --- | --- | --- |
| `CCR_SESSION_SECRET` | Secret | Generate fresh: `python3 -c "import secrets; print(secrets.token_hex(32))"` (do NOT reuse the dev value) |
| `DATABASE_URL` | Secret | New Supabase project, Session pooler URI, with the DB password in it (section 3) |
| `SUPABASE_URL` | Secret | New Supabase project > Settings > API |
| `SUPABASE_ANON_KEY` | Secret | Same page (anon public key, NOT service_role) |
| `CCR_STORAGE` | Variable | `s3` |
| `CCR_S3_ENDPOINT` | Secret | New R2: `https://<account_id>.r2.cloudflarestorage.com` (section 5) |
| `CCR_S3_BUCKET` | Secret | New R2 bucket name |
| `CCR_S3_ACCESS_KEY_ID` | Secret | New R2 API token |
| `CCR_S3_SECRET_ACCESS_KEY` | Secret | New R2 API token |
| `GROQ_API_KEY` | Secret | New lab Groq key |
| `CCR_APP_URL` | Variable | `https://<custom-domain>` (section 8) |
| `CCR_COOKIE_SECURE` | Variable | `1` |
| `CCR_ANON_TTL_HOURS` | Variable | `24` |
| `ADMIN_EMAILS` | Variable | Comma-separated admin emails (confirm with PI) |
| `CCR_MAX_ROWS` | Variable | `50000` (matches the dev instance) |

Hugging Face keeps Variables and Secrets in two separate stores. A name defined
in BOTH puts the Space into CONFIG_ERROR before it builds. Put each name in one
store only, per the table.

## 3. Supabase project (database + sign-in)

1. New project under the lab's Supabase org. Match the region to the current
   dev project (read it from the dev `DATABASE_URL`: the pooler host contains it,
   e.g. `aws-0-us-east-1...` means US East). Generate a strong DB password and
   save it.
2. Turn OFF "Enable Data API" (the app talks to Postgres directly and never uses
   the REST API; leaving it off closes that surface). Leave "Enable automatic
   RLS" on. Do NOT connect GitHub (the app manages its own schema).
3. Settings > API: copy the Project URL and the anon key into the secrets sheet
   (`SUPABASE_URL`, `SUPABASE_ANON_KEY`).
4. Connect > Session pooler: copy the URI, insert the DB password, into
   `DATABASE_URL`.
5. Google sign-in (do this before launch; the button is hidden without it):
   - Google Cloud console (lab Google account) > OAuth consent screen (External)
     > Credentials > Create OAuth client ID (Web application).
   - Supabase > Authentication > Providers > Google > Enable. Copy the shown
     callback (`https://<PROJECT_REF>.supabase.co/auth/v1/callback`) and add it
     as an authorized redirect URI in the Google client. Paste the Google client
     id and secret back into the Supabase Google form.
   - Supabase > Authentication > URL Configuration: add the redirect URLs
     `http://127.0.0.1:8000/api/auth/google/callback` and, once the domain is
     live, `https://<custom-domain>/api/auth/google/callback`.

## 4. Migrate the database (carry accounts and data over)

Run BEFORE the new Space boots for the first time, so the app finds the data
already present rather than creating empty tables.

```sh
# Dump the app's tables from the current (dev) database. Use the dev
# DATABASE_URL from your local .env. --schema=public keeps it to the app's
# tables; --no-owner --no-acl avoids role mismatches between projects.
pg_dump "$DEV_DATABASE_URL" --schema=public --no-owner --no-acl -Fc -f ccr_public.dump

# Restore into the NEW Supabase project.
pg_restore --no-owner --no-acl --clean --if-exists \
  -d "$NEW_DATABASE_URL" ccr_public.dump
```

If `pg_dump` version-mismatches against Supabase, use the Postgres client that
matches the server major version (or the `supabase db dump` CLI). The app's
startup auto-migration adds any missing columns after this, so a slightly older
dump still boots cleanly.

## 5. R2 object storage (uploaded files)

1. Cloudflare > R2 > create a bucket under the lab account (this is when R2 asks
   for a card on file; the 10 GB free tier covers this use).
2. Create an R2 API token (Object Read and Write) scoped to that bucket. Put the
   access key id, secret, endpoint, and bucket name into the secrets sheet.
3. Copy the existing files over (R2 is S3-compatible):

```sh
# From the dev R2 to the lab R2. Fill both endpoint/keys from each account.
aws s3 sync \
  --endpoint-url "$DEV_S3_ENDPOINT" "s3://$DEV_BUCKET" ./r2-migrate-tmp
aws s3 sync \
  --endpoint-url "$LAB_S3_ENDPOINT" ./r2-migrate-tmp "s3://$LAB_BUCKET"
# (or use rclone with two remotes: rclone sync dev:bucket lab:bucket)
```

## 6. Domain purchase (on the PI call, card needed)

1. Cloudflare > Domain Registration > register the chosen domain (recommended:
   buy at Cloudflare so domain, DNS, R2, and the Worker share one account).
   Availability was last checked recently and can change daily, so register the
   same day it is chosen.
2. If the domain is bought elsewhere, add it to Cloudflare and point its
   nameservers at Cloudflare, so the Worker route in section 8 can attach.

## 7. Create the lab Space and add secrets

1. New Space under the lab Hugging Face account: SDK = Docker, hardware =
   cpu-basic (free, same as dev). Give it the same repo.
2. Point the local repo's Space remote at the new Space and push:

```sh
git remote set-url hf https://huggingface.co/spaces/<lab-owner>/<space>
git push hf main    # use the lab HF username + a WRITE token when prompted
```

3. Space > Settings > Variables and secrets: enter every row from the secrets
   sheet (section 2), each in the store the table specifies.
4. The Space builds and boots. Because the database was restored in section 4,
   accounts and data are already there.

## 8. Wire the custom domain (reverse proxy)

Hugging Face Spaces cannot serve a custom domain directly, so a small Cloudflare
Worker serves the Space at the lab domain and keeps the domain in the address bar.

1. Get the Space direct host: Space > Settings > Embed this Space > Direct URL,
   of the form `https://<owner>-<space>.hf.space`.
2. Open `deploy/reverse-proxy-worker.js`, set `UPSTREAM_HOST` to that host
   (without the `https://`).
3. Cloudflare > Workers & Pages > Create Worker > paste the file > Deploy.
4. That Worker > Settings > Domains & Routes > Add Custom Domain >
   `ccr.<domain>` (Cloudflare provisions TLS automatically).
5. Set the Space Variable `CCR_APP_URL=https://ccr.<domain>` and confirm the
   Supabase redirect URL from section 3.5 uses the same domain. Restart the
   Space so it picks up `CCR_APP_URL`.

## 9. Launch checklist (verify before announcing)

- Site loads on the custom domain; the address bar stays on the domain while
  navigating.
- Google sign-in completes and returns to the custom domain (not hf.space).
- Password sign-in works; an account created on the dev instance is present
  (confirms the data migration).
- Upload a small corpus, pick a construct, run it, open results.
- AI drafting: "Draft with AI" tab works with the lab Groq key; the drafted
  items appear, and a saved AI construct shows the "AI-generated, not validated"
  label through picker, results, and the metadata download.
- `/guide` loads; `/admin` is reachable for the emails in `ADMIN_EMAILS`.
- Promote the license: `git mv LICENSE-MIT LICENSE && rm LICENSE-APACHE` (or the
  reverse), commit, push. Needed because the site publicly says the tool is
  open-source.

## 10. Cut over and retire the old instance

- Pause (do not delete) the old personal Space once the new one is verified, so
  it is a fallback for a day or two.
- Keep the dev database and R2 until the new instance has run cleanly for a few
  days, then retire them.

---

## Optional, post-launch

### Keep the Space awake (free)

Free Spaces sleep after about 48 hours idle (first visitor then waits about a
minute). A free uptime pinger (for example UptimeRobot) hitting the domain every
few hours keeps it warm without paying. The durable fix is an always-on host
(next item).

### Always-on host (later)

The same container runs on any host (Fly, Railway, Hetzner, a UMass VM). Moving
there removes the sleep behavior AND gives native custom-domain support, so the
Worker in section 8 can be dropped. Not a launch blocker.

### One-push deploys (GitHub Action)

Auto-deploy the Space on every merge to `main`, so nobody needs the Space remote.
Add a GitHub Actions workflow that mirrors `main` to the Space, with an HF write
token stored as a GitHub Actions secret (`HF_TOKEN`):

```yaml
# .github/workflows/deploy-hf.yml
name: Deploy to Hugging Face Space
on:
  push:
    branches: [main]
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with: { fetch-depth: 0 }
      - name: Push to Space
        env:
          HF_TOKEN: ${{ secrets.HF_TOKEN }}
        run: |
          git push "https://lab:${HF_TOKEN}@huggingface.co/spaces/<lab-owner>/<space>" main
```

### Switch AI drafting to Claude Haiku (later)

Add `ANTHROPIC_API_KEY` as a Space secret and the app auto-selects Anthropic over
Groq (`CCR_GENERATION_PROVIDER` can force either). Groq stays as the free
fallback. The provenance stamp records which model drafted each construct, so
constructs drafted during the Groq period stay traceable.
