/**
 * Cloudflare Worker: reverse proxy that serves the CCR Platform Hugging Face
 * Space at the lab's own domain (e.g. ccr.culturemoralitylab.org or
 * www.psychologicaltextanalysis.org), so the address bar keeps the custom
 * domain throughout. The Space host never appears to the visitor.
 *
 * Why a Worker: Hugging Face Spaces do not support custom domains on ANY tier
 * (free or paid), so the domain has to be served in front of the Space. The
 * Workers free tier (100k requests/day) covers lab traffic comfortably.
 *
 * SETUP
 *   1. Set UPSTREAM_HOST below to the Space's direct host. Find it on the Space
 *      page: Settings > "Embed this Space" > Direct URL. It has the form
 *      https://<owner>-<space>.hf.space (lowercased, non-alphanumerics become
 *      hyphens), e.g. culture-and-morality-lab-ccr-platform.hf.space.
 *   2. Cloudflare dashboard > Workers & Pages > Create Worker > paste this file
 *      > Deploy.
 *   3. That Worker > Settings > Domains & Routes > Add Custom Domain > enter the
 *      subdomain (ccr.culturemoralitylab.org). Cloudflare provisions TLS
 *      automatically. The domain must already be in this Cloudflare account.
 *
 * PAIRS WITH (already on the migration runbook, deploy/PRODUCTION_RUNBOOK.md):
 *   - Space secret CCR_APP_URL = https://<your-custom-domain>
 *     (the app builds the Google sign-in return URL from this).
 *   - Supabase Auth > URL Configuration: add
 *     https://<your-custom-domain>/api/auth/google/callback to the redirect list.
 *
 * NOTES
 *   - redirect: "manual" is required. The app returns 3xx responses (the Google
 *     sign-in hand-off, and the post-login redirect back to "/"). Manual mode
 *     passes those to the browser instead of the Worker following them
 *     server-side, so sign-in works and app redirects stay on the custom domain.
 *   - The app's own redirects are relative ("/"), so they resolve against the
 *     custom domain automatically. The block below rewrites only the rare
 *     absolute redirect that points back at the Space host, as a safety net.
 *   - Host-only cookies (no Domain attribute) scope to the custom domain through
 *     the proxy with no Set-Cookie rewriting needed.
 *   - No websockets in the app; uploads are capped at 50 MB, under the Worker
 *     request-body limit.
 *
 * AFTER DEPLOY, verify once: load the site on the custom domain, sign in with
 * Google (the address bar should return to the custom domain, not hf.space),
 * upload a small corpus, run it. If Google sign-in lands on an error, re-check
 * CCR_APP_URL and the Supabase redirect URL above.
 */

const UPSTREAM_HOST = "culture-and-morality-lab-ccr-platform.hf.space";

export default {
  async fetch(request) {
    const incoming = new URL(request.url);

    // Same path and query, sent to the Space host over HTTPS.
    const target = new URL(request.url);
    target.hostname = UPSTREAM_HOST;
    target.protocol = "https:";
    target.port = "";

    // Clone onto the target URL (preserves method, headers, and body). The
    // Host header is derived from the target URL, so the Space routes correctly.
    const proxied = new Request(target, request);
    const response = await fetch(proxied, { redirect: "manual" });

    // Safety net: rewrite an absolute redirect back at the Space host onto the
    // custom domain. App redirects are relative, so this rarely fires.
    const location = response.headers.get("location");
    if (location && location.startsWith(`https://${UPSTREAM_HOST}`)) {
      const headers = new Headers(response.headers);
      headers.set(
        "location",
        incoming.origin + location.slice(`https://${UPSTREAM_HOST}`.length),
      );
      return new Response(response.body, {
        status: response.status,
        statusText: response.statusText,
        headers,
      });
    }
    return response;
  },
};
