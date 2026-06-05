"""Convert raw HTML for Anthropic + OpenAI articles to markdown.

Despite the name (kept for parity with project.md), this service handles
both Anthropic and OpenAI articles so we only walk the DB once.
"""
from __future__ import annotations

import logging
from typing import Optional

from bs4 import BeautifulSoup
from markdownify import markdownify

from ..database import Repository
from .base import ProcessService


log = logging.getLogger(__name__)


def html_to_markdown(html: Optional[str]) -> Optional[str]:
    if not html:
        return None
    soup = BeautifulSoup(html, "html.parser")
    # Drop scripts/styles/nav/footers to keep the markdown body focused.
    for tag in soup(["script", "style", "noscript", "nav", "footer", "header", "form"]):
        tag.decompose()

    # Prefer <article>, then <main>, then <body>.
    root = soup.find("article") or soup.find("main") or soup.body or soup
    md = markdownify(str(root), heading_style="ATX", strip=["a"])
    # collapse 3+ newlines
    lines = [ln.rstrip() for ln in md.splitlines()]
    cleaned = "\n".join(lines)
    while "\n\n\n" in cleaned:
        cleaned = cleaned.replace("\n\n\n", "\n\n")
    return cleaned.strip() or None


class ProcessAnthropic(ProcessService):
    name = "process_anthropic_markdown"

    def _run(self, repo: Repository) -> int:
        n = 0
        for art in repo.anthropic_needing_markdown():
            md = html_to_markdown(art.raw_html) or art.summary
            if md:
                art.markdown = md
                n += 1
        for art in repo.openai_needing_markdown():
            md = html_to_markdown(art.raw_html) or art.summary
            if md:
                art.markdown = md
                n += 1
        return n


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    ProcessAnthropic().run()


if __name__ == "__main__":
    main()
