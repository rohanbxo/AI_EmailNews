# Deployment — Free Stack

Run the daily digest entirely for free with:

| Component | Provider | Cost |
| --- | --- | --- |
| LLM | Groq (`llama-3.3-70b-versatile`) | Free, 14,400 req/day, no billing |
| Database | Neon (Postgres) | Free, 0.5 GB, doesn't expire |
| Scheduler | GitHub Actions cron | Free, 2000 min/mo (public repo) |
| Email | Gmail SMTP | Free |

---

## 1. Get a Groq API key

1. Open https://console.groq.com and sign up (email or Google login)
2. Go to **API Keys** → **Create API Key**
3. Copy the key (starts with `gsk_...`)

No credit card. No billing setup. You're rate-limited (30 req/min, 14,400 req/day) — way more than this project needs.

If you prefer Gemini or OpenAI, the code falls back to either — just set `GEMINI_API_KEY` or `OPENAI_API_KEY` instead. Resolution order is Groq → Gemini → OpenAI.

## 2. Create a Neon Postgres database

1. Open https://neon.tech and sign up (GitHub login is fastest)
2. Create a new project. Region: pick one near you.
3. From the project dashboard, copy the **Connection string** — it looks like
   `postgresql://user:pass@ep-xxx.neon.tech/neondb?sslmode=require`.
4. That's your `DATABASE_URL`.

## 3. Get a Gmail App Password

Required because Gmail SMTP doesn't accept your normal password.

1. Enable 2-Step Verification on your Google account: https://myaccount.google.com/security
2. Open https://myaccount.google.com/apppasswords
3. Create an app password (name it "AI News"). Copy the 16-char password.
4. That's your `APP_PASSWORD`. `MY_EMAIL` is the Gmail address itself.

## 4. Push this repo to GitHub

```powershell
git init
git add .
git commit -m "Initial commit"
gh repo create ai-news-aggregator --public --source=. --push
# or create the repo on github.com and push the usual way
```

A **public** repo gets 2000 free Actions minutes/month — plenty.
A private repo gets 500/month — also enough for a daily run.

## 5. Add secrets to the GitHub repo

In the repo on github.com: **Settings → Secrets and variables → Actions → New repository secret**. Add:

| Name | Value |
| --- | --- |
| `GROQ_API_KEY` | from step 1 |
| `DATABASE_URL` | from step 2 |
| `MY_EMAIL` | your Gmail address |
| `APP_PASSWORD` | from step 3 |
| `WEBSHARE_USERNAME` | *(optional)* Webshare proxy username |
| `WEBSHARE_PASSWORD` | *(optional)* Webshare proxy password |

Optionally also set repo **Variables** (same settings page, "Variables" tab) to tune behavior without editing code:

| Variable | Default |
| --- | --- |
| `LLM_MODEL` | `llama-3.3-70b-versatile` |
| `DIGEST_LOOKBACK_HOURS` | `24` |
| `EMAIL_TOP_N` | `10` |

## 6. Initialize the database tables

The daily pipeline auto-creates tables on first run. To initialize them by hand:

```powershell
# locally, with DATABASE_URL pointed at Neon
uv run python -m app.database.create_tables
```

## 7. Trigger the first run

In the repo: **Actions → Daily AI News Digest → Run workflow**. After ~2 minutes you should get an email.

After that, it runs automatically every day at 13:00 UTC. Change the schedule by editing the `cron:` line in `.github/workflows/daily.yml`.

---

## Running locally

```powershell
Copy-Item app\example.env .env
# edit .env with your Groq key, Neon URL, Gmail creds
uv sync
uv run python -m app.database.check_connection
uv run python -m app.database.create_tables
uv run python main.py
```

---

## Troubleshooting

- **`No LLM key found`** — set `GROQ_API_KEY` (or `GEMINI_API_KEY` / `OPENAI_API_KEY`) in the env/secrets.
- **`model_decommissioned` or `model_not_found` from Groq** — model names change. Check https://console.groq.com/docs/models and update `LLM_MODEL`. Current good defaults: `llama-3.3-70b-versatile`, `llama-3.1-8b-instant`.
- **`rate_limit_exceeded` from Groq** — you've hit 30 req/min. The retry logic in `BaseAgent` handles short bursts; if it keeps happening, lower `EMAIL_TOP_N` or switch to `llama-3.1-8b-instant` (separate quota).
- **No email arrives** — confirm `APP_PASSWORD` is a Gmail App Password, not your normal password, and that 2FA is on for the Google account.
- **`SSL connection has been closed unexpectedly`** — make sure your Neon `DATABASE_URL` includes `?sslmode=require` (Neon URLs usually do by default).
- **No YouTube transcripts** — GitHub Actions IPs are data-center ranges, which YouTube often blocks. Add Webshare residential proxy credentials, or accept that transcripts may be missing on some runs.
- **Empty digest emails** — usually means no new source items in the last 24h. Increase `DIGEST_LOOKBACK_HOURS` to verify.

---

## Alternative: deploy to Render

`render.yaml` is still in the repo if you'd rather use Render's blueprint deploy. It provisions a Postgres database and a cron job. Note Render's free Postgres expires after 30 days; the GitHub Actions + Neon stack above doesn't have that limit.
