from dataclasses import dataclass
from typing import List

from .base import BaseAgent


@dataclass
class ScoredItem:
    id: int
    score: int  # 0-100


class CuratorAgent(BaseAgent):
    system_prompt = (
        "You rank AI/ML news items by relevance to a specific reader's "
        "profile. Output strict JSON: {\"scores\": [{\"id\": <int>, "
        "\"score\": <0-100 int>}]}. Higher = more relevant. Be discerning: "
        "use the full 0-100 range, do not cluster scores."
    )
    temperature = 0.0

    def rank(self, *, profile_prompt: str, items: List[dict]) -> List[ScoredItem]:
        if not items:
            return []
        lines = []
        for it in items:
            summary = (it.get("summary") or "")[:600]
            lines.append(
                f"- id={it['id']} | source={it['source_type']} | "
                f"title={it['title']!r}\n  summary: {summary}"
            )
        prompt = (
            f"Reader profile:\n{profile_prompt}\n\n"
            f"Items to rank:\n" + "\n".join(lines) + "\n\n"
            "Return JSON of the form {\"scores\":[{\"id\":..,\"score\":..}]}."
        )
        data = self.complete_json(prompt)
        scores = data.get("scores", [])
        result: List[ScoredItem] = []
        for s in scores:
            try:
                result.append(ScoredItem(id=int(s["id"]), score=max(0, min(100, int(s["score"])))))
            except (KeyError, TypeError, ValueError):
                continue
        return result
