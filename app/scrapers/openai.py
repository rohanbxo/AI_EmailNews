from typing import List

from .base import Article, BaseScraper


class OpenAIArticleItem(Article):
    pass


class OpenAIScraper(BaseScraper):
    @property
    def rss_urls(self) -> List[str]:
        return ["https://openai.com/news/rss.xml"]

    def get_articles(self, hours: int = 24) -> List[OpenAIArticleItem]:
        return [OpenAIArticleItem(**a.model_dump()) for a in super().get_articles(hours)]
