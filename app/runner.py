"""Scraper registry and execution.

Each entry: (name, scraper_instance, save_fn(scraper, repo, hours) -> int).
"""
from __future__ import annotations

import logging
from typing import Callable, List, Tuple

from .config import DIGEST_LOOKBACK_HOURS
from .database import Repository, get_session
from .scrapers import AnthropicScraper, OpenAIScraper, YouTubeScraper


log = logging.getLogger(__name__)


def _rss_to_rows(articles) -> List[dict]:
    return [
        {
            "url": a.url,
            "title": a.title,
            "author": a.author,
            "published_at": a.published_at,
            "summary": a.summary,
            "raw_html": a.raw_html,
        }
        for a in articles
    ]


def _save_rss_articles(scraper, repo: Repository, hours: int, bulk_fn) -> int:
    rows = _rss_to_rows(scraper.get_articles(hours=hours))
    return bulk_fn(rows)


def _save_anthropic(scraper, repo: Repository, hours: int) -> int:
    return _save_rss_articles(scraper, repo, hours, repo.bulk_create_anthropic_articles)


def _save_openai(scraper, repo: Repository, hours: int) -> int:
    return _save_rss_articles(scraper, repo, hours, repo.bulk_create_openai_articles)


def _save_youtube(scraper, repo: Repository, hours: int) -> int:
    videos = scraper.get_articles(hours=hours)
    rows = [
        {
            "video_id": v.video_id,
            "channel_id": v.channel_id,
            "channel_title": v.channel_title,
            "url": v.url,
            "title": v.title,
            "description": v.description,
            "published_at": v.published_at,
        }
        for v in videos
    ]
    return repo.bulk_create_youtube_videos(rows)


SCRAPER_REGISTRY: List[Tuple[str, object, Callable]] = [
    ("anthropic", AnthropicScraper(), _save_anthropic),
    ("openai", OpenAIScraper(), _save_openai),
    ("youtube", YouTubeScraper(), _save_youtube),
]


def run_all_scrapers(hours: int = DIGEST_LOOKBACK_HOURS) -> dict:
    results: dict = {}
    with get_session() as session:
        repo = Repository(session)
        for name, scraper, save_fn in SCRAPER_REGISTRY:
            try:
                n = save_fn(scraper, repo, hours)
                results[name] = n
                log.info("Scraper %s: saved %d new", name, n)
            except Exception as e:  # noqa: BLE001
                log.exception("Scraper %s failed: %s", name, e)
                results[name] = -1
    return results


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    run_all_scrapers()


if __name__ == "__main__":
    main()
