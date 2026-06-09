"""Public archive site for past AI news digests.

Routes:
  GET /            — landing page + today's top digests
  GET /archive     — paginated list of all past digests grouped by date
  GET /digest/{id} — full single-digest page (deep-link from email or archive)

Reuses the same Neon Postgres DB as the cron pipeline. Read-only.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select

from ..config import EMAIL_TOP_N
from ..database import Digest, get_session
from ..profiles import USER_PROFILE


BASE_DIR = Path(__file__).parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

app = FastAPI(
    title="AI News Digest Archive",
    description="Personalized AI news, delivered daily.",
    docs_url=None,
    redoc_url=None,
)


# -- helpers ----------------------------------------------------------------


_SOURCE_LABEL = {
    "anthropic": "Anthropic",
    "openai": "OpenAI",
    "youtube": "YouTube",
    "huggingface": "Hugging Face",
    "importai": "Import AI",
    "latentspace": "Latent Space",
}


def _serialize(d: Digest) -> dict:
    return {
        "id": d.id,
        "source_type": d.source_type,
        "source_label": _SOURCE_LABEL.get(d.source_type, d.source_type),
        "title": d.title,
        "url": d.url,
        "summary": d.summary,
        "score": d.score,
        "published_at": d.published_at,
        "sent_at": d.sent_at,
    }


def _latest_digest_day() -> Optional[date]:
    """Return the calendar date of the most recent sent digest."""
    with get_session() as s:
        stmt = select(func.max(Digest.sent_at))
        latest = s.scalar(stmt)
    if latest is None:
        return None
    return latest.astimezone(timezone.utc).date()


def _digests_for_day(day: date) -> List[Digest]:
    start = datetime.combine(day, datetime.min.time(), tzinfo=timezone.utc)
    end = start + timedelta(days=1)
    with get_session() as s:
        stmt = (
            select(Digest)
            .where(Digest.sent_at.is_not(None))
            .where(Digest.sent_at >= start)
            .where(Digest.sent_at < end)
            .order_by(Digest.score.desc().nullslast(), Digest.published_at.desc().nullslast())
            .limit(EMAIL_TOP_N)
        )
        return list(s.scalars(stmt))


# -- routes -----------------------------------------------------------------


@app.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    day = _latest_digest_day()
    digests = _digests_for_day(day) if day else []
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "day": day,
            "items": [_serialize(d) for d in digests],
            "profile": USER_PROFILE,
        },
    )


@app.get("/archive", response_class=HTMLResponse)
def archive(request: Request, page: int = Query(1, ge=1)) -> HTMLResponse:
    page_size = 7  # one week per page
    with get_session() as s:
        # distinct sent dates, newest first
        date_col = func.date(Digest.sent_at)
        stmt = (
            select(date_col)
            .where(Digest.sent_at.is_not(None))
            .group_by(date_col)
            .order_by(date_col.desc())
            .offset((page - 1) * page_size)
            .limit(page_size + 1)  # +1 to detect next page
        )
        rows = list(s.scalars(stmt))

    has_next = len(rows) > page_size
    days = rows[:page_size]

    grouped = []
    for day in days:
        digests = _digests_for_day(day)
        grouped.append({"day": day, "items": [_serialize(d) for d in digests]})

    return templates.TemplateResponse(
        request,
        "archive.html",
        {
            "groups": grouped,
            "page": page,
            "has_prev": page > 1,
            "has_next": has_next,
            "profile": USER_PROFILE,
        },
    )


@app.get("/digest/{digest_id}", response_class=HTMLResponse)
def digest_detail(request: Request, digest_id: int) -> HTMLResponse:
    with get_session() as s:
        d = s.get(Digest, digest_id)
        if d is None or d.sent_at is None:
            raise HTTPException(status_code=404, detail="Digest not found")
        item = _serialize(d)
    return templates.TemplateResponse(
        request,
        "digest.html",
        {"item": item, "profile": USER_PROFILE},
    )


@app.get("/health")
def health() -> dict:
    return {"ok": True}
