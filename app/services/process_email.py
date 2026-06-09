"""Compose and send the daily personalized digest email."""
from __future__ import annotations

import logging
import os
from html import escape

from ..agent import EmailAgent
from ..config import DIGEST_LOOKBACK_HOURS, EMAIL_TOP_N
from ..database import Repository, get_session
from ..profiles import USER_PROFILE
from .email import send_email


log = logging.getLogger(__name__)


_SOURCE_LABEL = {
    "anthropic": "Anthropic",
    "openai": "OpenAI",
    "youtube": "YouTube",
    "huggingface": "Hugging Face",
    "importai": "Import AI",
    "latentspace": "Latent Space",
}


def _render_html(intro: str, items) -> str:
    cards = []
    for it in items:
        cards.append(
            f"""
            <div style="margin:0 0 22px 0;padding:14px 16px;border:1px solid #e5e7eb;
                        border-radius:8px;background:#fff;">
              <div style="font-size:12px;color:#6b7280;text-transform:uppercase;
                          letter-spacing:.06em;margin-bottom:4px;">
                {escape(_SOURCE_LABEL.get(it['source_type'], it['source_type']))}
              </div>
              <a href="{escape(it['url'])}"
                 style="color:#111827;text-decoration:none;font-size:17px;font-weight:600;">
                {escape(it['title'])}
              </a>
              <p style="margin:8px 0 0;color:#374151;font-size:14px;line-height:1.5;">
                {escape(it['summary'])}
              </p>
            </div>
            """
        )
    body = "\n".join(cards)
    return f"""<!doctype html>
<html><body style="margin:0;padding:24px;background:#f9fafb;
                   font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;
                   color:#111827;">
  <div style="max-width:680px;margin:0 auto;">
    <h1 style="font-size:22px;margin:0 0 8px;">Your AI news digest</h1>
    <p style="color:#374151;font-size:15px;line-height:1.55;margin:0 0 22px;">{escape(intro)}</p>
    {body}
    <p style="color:#9ca3af;font-size:12px;margin-top:24px;">
      Curated for {escape(USER_PROFILE.name)} — based on your interests profile.
    </p>
  </div>
</body></html>"""


def _render_text(intro: str, items) -> str:
    lines = [intro, ""]
    for it in items:
        lines.append(f"[{_SOURCE_LABEL.get(it['source_type'], it['source_type'])}] {it['title']}")
        lines.append(it["url"])
        lines.append(it["summary"])
        lines.append("")
    return "\n".join(lines)


def run() -> int:
    """Build and send today's digest email. Returns number of items sent."""
    to = os.getenv("MY_EMAIL")
    if not to:
        raise RuntimeError("MY_EMAIL must be set")

    with get_session() as session:
        repo = Repository(session)
        digests = repo.unsent_digests(hours=DIGEST_LOOKBACK_HOURS)
        if not digests:
            log.info("No unsent digests; nothing to email.")
            return 0

        top = digests[:EMAIL_TOP_N]
        items = [
            {
                "id": d.id,
                "source_type": d.source_type,
                "title": d.title,
                "url": d.url,
                "summary": d.summary,
            }
            for d in top
        ]

        agent = EmailAgent()
        content = agent.compose(profile_prompt=USER_PROFILE.as_prompt(), items=items)

        html = _render_html(content.intro, items)
        text = _render_text(content.intro, items)
        send_email(to=to, subject=content.subject, html=html, text=text)

        repo.mark_digests_sent([d.id for d in top])
        return len(top)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    n = run()
    log.info("Sent %d items.", n)


if __name__ == "__main__":
    main()
