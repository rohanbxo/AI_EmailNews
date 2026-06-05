from dataclasses import dataclass

from .base import BaseAgent


@dataclass
class DigestResult:
    summary: str


class DigestAgent(BaseAgent):
    system_prompt = (
        "You summarize AI/ML news content for a technical reader. "
        "Produce a tight 3-5 sentence summary capturing: (1) what was "
        "announced/discussed, (2) why it matters, (3) any concrete numbers, "
        "model names, or benchmarks. No marketing language. No bullet points."
    )
    temperature = 0.2

    def summarize(self, *, title: str, body: str, source: str) -> DigestResult:
        body = body[:12000]  # keep token usage bounded
        prompt = (
            f"Source: {source}\nTitle: {title}\n\n"
            f"Content:\n{body}\n\n"
            "Write the summary."
        )
        text = self.complete(prompt).strip()
        return DigestResult(summary=text)
