from typing import List

from .base import Article, BaseScraper


class AnthropicArticleItem(Article):
    pass


class AnthropicScraper(BaseScraper):
    @property
    def rss_urls(self) -> List[str]:
        return ["https://www.anthropic.com/news/rss.xml"]

    def get_articles(self, hours: int = 24) -> List[AnthropicArticleItem]:
        return [AnthropicArticleItem(**a.model_dump()) for a in super().get_articles(hours)]
