"""Base RSS scraper.

Subclasses declare `rss_urls` and inherit a working `get_articles(hours)`
that returns deduplicated, time-windowed Article items.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from time import mktime
from typing import List, Optional

import feedparser
import requests
from pydantic import BaseModel, Field


log = logging.getLogger(__name__)


class Article(BaseModel):
    url: str
    title: str
    author: Optional[str] = None
    published_at: Optional[datetime] = None
    summary: Optional[str] = None
    raw_html: Optional[str] = None

    model_config = {"arbitrary_types_allowed": True}


class BaseScraper:
    """RSS scraper base. Override `rss_urls`."""

    timeout: int = 20
    user_agent: str = "ai-news-aggregator/0.1 (+https://example.com)"

    @property
    def rss_urls(self) -> List[str]:
        raise NotImplementedError

    @property
    def fetch_full_html(self) -> bool:
        """If True, scrapers fetch each article URL for raw_html.

        Most RSS feeds give partial content; full HTML lets the markdown
        processor produce a better article body.
        """
        return True

    def _parse_published(self, entry) -> Optional[datetime]:
        for key in ("published_parsed", "updated_parsed"):
            val = entry.get(key)
            if val:
                return datetime.fromtimestamp(mktime(val), tz=timezone.utc)
        return None

    def _fetch_html(self, url: str) -> Optional[str]:
        try:
            r = requests.get(
                url,
                timeout=self.timeout,
                headers={"User-Agent": self.user_agent},
            )
            r.raise_for_status()
            return r.text
        except Exception as e:  # noqa: BLE001
            log.warning("Failed to fetch %s: %s", url, e)
            return None

    def get_articles(self, hours: int = 24) -> List[Article]:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        seen: set[str] = set()
        out: List[Article] = []

        for feed_url in self.rss_urls:
            log.info("Fetching feed: %s", feed_url)
            parsed = feedparser.parse(feed_url)
            for entry in parsed.entries:
                url = entry.get("link")
                if not url or url in seen:
                    continue
                published = self._parse_published(entry)
                if published and published < cutoff:
                    continue
                seen.add(url)

                summary = entry.get("summary") or entry.get("description")
                raw_html = None
                if self.fetch_full_html:
                    raw_html = self._fetch_html(url)

                out.append(
                    Article(
                        url=url,
                        title=entry.get("title", "(untitled)"),
                        author=entry.get("author"),
                        published_at=published,
                        summary=summary,
                        raw_html=raw_html,
                    )
                )
        log.info("Scraped %d articles from %s", len(out), type(self).__name__)
        return out
