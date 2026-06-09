from typing import List

from .base import Article, BaseScraper


class LatentSpaceArticleItem(Article):
    pass


class LatentSpaceScraper(BaseScraper):
    """swyx + Alessio's Latent Space podcast / Substack."""

    @property
    def rss_urls(self) -> List[str]:
        return ["https://www.latent.space/feed"]

    def get_articles(self, hours: int = 24) -> List[LatentSpaceArticleItem]:
        return [LatentSpaceArticleItem(**a.model_dump()) for a in super().get_articles(hours)]
