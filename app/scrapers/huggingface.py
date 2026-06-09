from typing import List

from .base import Article, BaseScraper


class HuggingFaceArticleItem(Article):
    pass


class HuggingFaceScraper(BaseScraper):
    """Scrapes the official Hugging Face blog RSS.

    Note: `huggingface.co/blog/feed.xml` mixes engineering posts (good signal)
    with daily-papers digest items. The curator agent handles ranking — we
    just ingest everything in-window.
    """

    @property
    def rss_urls(self) -> List[str]:
        return ["https://huggingface.co/blog/feed.xml"]

    def get_articles(self, hours: int = 24) -> List[HuggingFaceArticleItem]:
        return [HuggingFaceArticleItem(**a.model_dump()) for a in super().get_articles(hours)]
