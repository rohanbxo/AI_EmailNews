from typing import List

from .base import Article, BaseScraper


class ImportAIArticleItem(Article):
    pass


class ImportAIScraper(BaseScraper):
    """Jack Clark's Import AI weekly newsletter."""

    @property
    def rss_urls(self) -> List[str]:
        return ["https://jack-clark.net/feed/"]

    def get_articles(self, hours: int = 24) -> List[ImportAIArticleItem]:
        return [ImportAIArticleItem(**a.model_dump()) for a in super().get_articles(hours)]
