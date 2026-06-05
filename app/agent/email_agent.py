from dataclasses import dataclass
from typing import List

from .base import BaseAgent


@dataclass
class EmailContent:
    subject: str
    intro: str


class EmailAgent(BaseAgent):
    system_prompt = (
        "You write the opening for a personalized daily AI news email. "
        "Output strict JSON: {\"subject\": \"...\", \"intro\": \"...\"}. "
        "Subject: <70 chars, specific, no clickbait. Intro: 2-3 sentences "
        "framing today's top themes, conversational but not breezy."
    )
    temperature = 0.4

    def compose(self, *, profile_prompt: str, items: List[dict]) -> EmailContent:
        bullets = "\n".join(
            f"- [{it['source_type']}] {it['title']}: {(it.get('summary') or '')[:240]}"
            for it in items
        )
        prompt = (
            f"Reader profile:\n{profile_prompt}\n\n"
            f"Today's items:\n{bullets}\n\n"
            "Return JSON."
        )
        data = self.complete_json(prompt)
        return EmailContent(
            subject=str(data.get("subject", "Your AI news digest")).strip()[:200],
            intro=str(data.get("intro", "")).strip(),
        )
