"""YouTube channel scraper.

Uses the public channel RSS feed by default
(https://www.youtube.com/feeds/videos.xml?channel_id=...). No API key required.
Falls back to feedparser entries for video metadata.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from time import mktime
from typing import List, Optional

import feedparser
from pydantic import BaseModel

from ..config import YOUTUBE_CHANNELS, YouTubeChannel


log = logging.getLogger(__name__)


class YouTubeVideoItem(BaseModel):
    video_id: str
    channel_id: str
    channel_title: Optional[str] = None
    url: str
    title: str
    description: Optional[str] = None
    published_at: Optional[datetime] = None


class YouTubeScraper:
    def __init__(self, channels: Optional[List[YouTubeChannel]] = None):
        self.channels = channels if channels is not None else YOUTUBE_CHANNELS

    def _feed_url(self, channel_id: str) -> str:
        return f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"

    def get_articles(self, hours: int = 24) -> List[YouTubeVideoItem]:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        out: List[YouTubeVideoItem] = []
        seen: set[str] = set()

        for ch in self.channels:
            log.info("Fetching YouTube channel: %s (%s)", ch.name, ch.channel_id)
            parsed = feedparser.parse(self._feed_url(ch.channel_id))
            channel_title = parsed.feed.get("title") if parsed.feed else ch.name
            for entry in parsed.entries:
                video_id = entry.get("yt_videoid") or entry.get("id", "").split(":")[-1]
                if not video_id or video_id in seen:
                    continue
                published = None
                tp = entry.get("published_parsed") or entry.get("updated_parsed")
                if tp:
                    published = datetime.fromtimestamp(mktime(tp), tz=timezone.utc)
                if published and published < cutoff:
                    continue
                seen.add(video_id)

                description = None
                media = entry.get("media_description")
                if media:
                    description = media
                else:
                    description = entry.get("summary")

                out.append(
                    YouTubeVideoItem(
                        video_id=video_id,
                        channel_id=ch.channel_id,
                        channel_title=channel_title,
                        url=entry.get("link", f"https://www.youtube.com/watch?v={video_id}"),
                        title=entry.get("title", "(untitled)"),
                        description=description,
                        published_at=published,
                    )
                )
        log.info("Scraped %d YouTube videos", len(out))
        return out
