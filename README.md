# AI News Aggregator

A daily personalized AI news digest. Scrapes Anthropic + OpenAI blog RSS feeds and a configurable set of YouTube channels, generates summaries with an LLM, ranks them against your interests, and emails you the top items.

Runs on a **fully free stack**: Groq (Llama 3.3 70B) + Neon Postgres + GitHub Actions + Gmail SMTP.

- **Sources:** Anthropic & OpenAI RSS feeds, configurable YouTube channels
- **Pipeline:** scrape → markdown/transcripts → summarize → rank → email
- **Personalized:** ranking uses your interest profile in [app/profiles/user_profile.py](app/profiles/user_profile.py)
- **No duplicates:** sent items are tracked in the DB

See [project.md](project.md) for the architecture overview and [DEPLOYMENT.md](DEPLOYMENT.md) for the free-tier deployment walkthrough.

## Quick start (local)

```powershell
uv sync
Copy-Item app\example.env .env
# edit .env with your Groq key, Postgres URL, Gmail App Password
uv run python -m app.database.create_tables
uv run python main.py
```

## Customize

- **Your interests** — edit `USER_PROFILE` in [app/profiles/user_profile.py](app/profiles/user_profile.py)
- **YouTube channels** — edit `YOUTUBE_CHANNELS` in [app/config.py](app/config.py)
- **How many items in the email** — `EMAIL_TOP_N` in `.env`
- **Schedule** — `cron:` line in [.github/workflows/daily.yml](.github/workflows/daily.yml)
- **LLM model / provider** — `LLM_MODEL` in `.env` (Groq → Gemini → OpenAI fallback)

## License

MIT
