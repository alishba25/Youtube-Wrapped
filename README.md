# YouTube Wrapped

A "Spotify Wrapped"-style site for YouTube, with three ways in:

- **Takeout upload** — upload a real Google Takeout watch-history export for the deepest, most accurate wrapped
- **Taste wrapped** — instant, one-click Google sign-in, built from liked videos + subscriptions
- **Creator wrapped** — instant, for channel owners, built from real YouTube Analytics data

Results are revealed as a tap/swipe-through slide story (Instagram Stories / Spotify Wrapped) rather than a static page — see `static/app.js`'s story engine and `app/personas.py`'s expanded, roast-flavored persona set.

Full write-up of *why* it's built this way (including the YouTube API's watch-history limitation that shaped the whole design) is in the chat history where this was designed — worth keeping for your own README/portfolio notes.

## Architecture

```
app/
  main.py             FastAPI app setup, middleware, route mounting
  config.py           All environment variables in one place
  models.py           Signal + WrappedResult - the shared data shape all 3 paths normalize into
  auth.py             Hand-rolled Google OAuth2 authorization-code flow
  takeout_parser.py   Parses Takeout's watch-history.json
  youtube_client.py   All calls to YouTube Data API v3 + YouTube Analytics API v2
  insights_engine.py  Converts each path's raw data into list[Signal]
  personas.py         Rule-based persona matching + stat aggregation
  card_generator.py   Renders the shareable PNG card with Pillow
  routes/
    auth_routes.py    /auth/login/{path}, /auth/callback, /auth/logout
    takeout.py        POST /api/takeout/wrapped
    taste.py          POST /api/taste/wrapped
    creator.py        POST /api/creator/wrapped
    card.py           POST /api/card (shared by all 3 paths)
static/
  index.html, style.css, app.js   Single-page frontend, no build step
  assets/fonts/                   Bundled Poppins weights used by card_generator.py
sample_data/
  sample_watch-history.json       Fake but correctly-shaped file for testing the upload flow
```

**Why no database:** nothing is persisted server-side. OAuth access tokens live only in a signed session cookie for the duration of the browser session. This was a deliberate scope decision — it means zero user-data storage/retention questions to worry about, at the cost of not being able to show a user their wrapped again later without redoing the flow. If you want persistence later, add a `results` table keyed by a random share-link ID.

**Why Pillow instead of a headless browser for card generation:** a single, fairly simple card layout doesn't need Chromium — Pillow renders it in milliseconds with a fraction of the memory, which matters on a free-tier deploy.

**Why rule-based personas instead of ML clustering:** YouTube's own video categories are already a clean taxonomy. Scoring against them directly is more reliable than unsupervised clustering for a v1, and has zero extra ML dependencies to deploy. `personas.py` has a comment on exactly how to swap in sentence-transformer embeddings + KMeans later if you want to extend it — and comparing the two approaches would make a genuinely good addition to your project writeup.

## 1. Google Cloud Console setup (do this first)

Everything below happens at [console.cloud.google.com](https://console.cloud.google.com).

Note: Google restructured this whole section in 2024. What used to be one page called "OAuth consent screen" is now called **Google Auth Platform**, split into 4 tabs: Branding, Audience, Data Access, Clients. If you're following an older tutorial and can't find something it mentions, it's almost certainly living under Google Auth Platform now.

1. **Create a project** (top-left project dropdown → New Project). Name it anything, e.g. "youtube-wrapped".
2. **Enable APIs** — go to *APIs & Services > Library* and enable, one at a time:
   - `YouTube Data API v3`
   - `YouTube Analytics API`
3. **Set up Google Auth Platform** — *APIs & Services > Google Auth Platform* (only appears once an API is enabled):
   - If prompted "not configured yet", click **Get started** and complete the 4-step wizard: App information (name + support email) → Audience (choose **External**) → Contact information (your email) → Finish (agree to the policy)
   - On the **Audience** tab: click **Add users** and add your own Google account email as a test user. While the app is in "Testing" mode, only accounts on this list can sign in — expected and fine for a portfolio project.
   - On the **Data Access** tab: click **Add or remove scopes**, search "youtube", and check both `.../auth/youtube.readonly` and `.../auth/yt-analytics.readonly`. If they don't appear in the search, use the "Manually add scopes" box instead and paste the full scope URLs. Click Update, then Save.
4. **Create the OAuth Client ID** — *Google Auth Platform > Clients* tab → **Create Client**:
   - Application type: **Web application**
   - Authorized redirect URIs: add `http://localhost:8000/auth/callback` for local testing
   - Click Create → copy the **Client ID** and **Client Secret** shown (the secret is shown once here, but you can always find it again by clicking back into this client later)
5. **Create the API key** — this is separate from the OAuth client above and hasn't moved. Go to *APIs & Services > Credentials* → **Create Credentials > API key** → this is your `YOUTUBE_API_KEY`. Click into it and restrict it to "YouTube Data API v3" for safety.

Keep this tab open — you'll add your deployed URL's redirect URI to the Clients tab too, later.

## 2. Run it locally

```bash
cd youtube-wrapped
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# now open .env and fill in GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, YOUTUBE_API_KEY
# generate SESSION_SECRET with:
python3 -c "import secrets; print(secrets.token_hex(32))"

uvicorn app.main:app --reload
```

Visit `http://localhost:8000`.

## 3. Testing each path

**Takeout upload** — click "How do I get that file?" for the in-app export walkthrough, or for a quick smoke test right now, upload `sample_data/sample_watch-history.json`. It has fake video IDs so category enrichment will come back empty for it (you'll still see it complete end-to-end and hit the card generator) — for real category/persona results, use a real Takeout export or swap in real video IDs from your own watch history.

**Taste wrapped** — click "Sign in with Google", pick your test-user account, approve. You need at least a few liked videos or subscriptions on that account for it to return results.

**Creator wrapped** — same sign-in flow, but the signed-in account needs an actual YouTube channel with some view history in the last 90 days. If you don't have a channel with real traffic, this path will return mostly zeros — that's expected, not a bug.

Common early errors and what they mean:
- `redirect_uri_mismatch` on Google's screen → the URI in your `.env` doesn't exactly match what's registered in Cloud Console (check trailing slashes)
- `access_denied` → you clicked cancel on the consent screen, or your account isn't in the Test users list
- `403` from a `/api/...` call → usually API not enabled, API key restricted wrong, or daily quota hit

## 4. Deploying (Render)

1. Push this project to a GitHub repo (see git commands below if you haven't already)
2. Go to [render.com](https://render.com) → New > Blueprint → connect your repo. Render will read `render.yaml` automatically.
3. Render will ask you to fill in the env vars marked `sync: false`: `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI`, `YOUTUBE_API_KEY`, `FRONTEND_URL`.
   - `GOOGLE_REDIRECT_URI` should be `https://YOUR-RENDER-URL.onrender.com/auth/callback`
   - `FRONTEND_URL` should be `https://YOUR-RENDER-URL.onrender.com`
   - `SESSION_SECRET` is auto-generated by Render, you don't need to set it
4. Deploy. Once live, go back to Google Cloud Console → your OAuth client → add `https://YOUR-RENDER-URL.onrender.com/auth/callback` to the Authorized redirect URIs list.
5. Note: Render's free tier spins down after inactivity, so the first request after a while will be slow (~30s cold start) — normal, not a bug.

```bash
git init
git add .
git commit -m "Initial commit: YouTube Wrapped"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/youtube-wrapped.git
git push -u origin main
```

## 5. Known limitations (worth knowing, good interview talking points too)

- **Taste path category depth**: liked-video categories aren't fully enriched in v1 (see the comment in `insights_engine.py::signals_from_taste`) — it categorizes by channel only, not per-video category, to keep the API call count low. Extending this to full category enrichment is a good "v2" to build and describe.
- **Takeout quota cap**: `MAX_VIDEOS_TO_ENRICH = 3000` in `routes/takeout.py` caps how many videos get enriched per request, to protect your daily API quota (10,000 units/day by default — 3000 videos = 60 units per request, so this is generous headroom for plenty of requests per day). Users with fewer videos than the cap automatically get all of them enriched. Raise it further if you have quota to spare.
- **Peak watching hour is shown in IST** (`Asia/Kolkata`) by default, since Takeout timestamps arrive from Google in UTC and need converting before display. Override with the `DISPLAY_TIMEZONE` env var if you're not in India (any [IANA timezone name](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones) works, e.g. `America/New_York`).
- **No persistence**: results and cards aren't stored anywhere, so there's no shareable permalink yet — you download the PNG and share that directly instead.
- **Persona emoji doesn't appear on the downloaded card image**: Poppins (like most text fonts) has no emoji glyphs, so Pillow silently draws a blank placeholder instead of the real character - and the deploy target likely has no system emoji font to fall back to either. The emoji still shows correctly in the browser reveal (browsers always ship a real color emoji font). To add it to the card image too, bundle a color emoji font like Noto Color Emoji and draw it as a separate layer - noted in a comment in `card_generator.py`.
- **OAuth verification**: while in Google's "Testing" mode, only accounts you've explicitly added as test users can sign in. Full public verification requires a Google review process (and for sensitive scopes like these, potentially a security assessment) — reasonable to skip entirely for a portfolio project, but worth knowing about if you ever wanted this fully public.

## 6. Ideas for extending it further

- Swap rule-based personas for sentence-transformer embeddings + clustering, and write up the comparison
- Add Redis-backed rate limiting per IP on the API routes
- Persist results behind a share-link ID so people can send their wrapped to friends without re-generating
- Add a background job queue (e.g. Celery + Redis) for large Takeout files instead of processing synchronously
