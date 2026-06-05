from dataclasses import dataclass, field
from typing import List


@dataclass(frozen=True)
class UserProfile:
    name: str
    role: str
    interests: List[str] = field(default_factory=list)
    avoid: List[str] = field(default_factory=list)
    tone: str = "concise, technical, no hype"

    def as_prompt(self) -> str:
        bits = [
            f"Reader: {self.name} — {self.role}.",
            "Interests: " + ", ".join(self.interests) + ".",
        ]
        if self.avoid:
            bits.append("Down-rank: " + ", ".join(self.avoid) + ".")
        bits.append(f"Preferred tone: {self.tone}.")
        return " ".join(bits)


USER_PROFILE = UserProfile(
    name="Rohan",
    role="CS student exploring applied AI / ML engineering",
    interests=[
        "frontier LLM research (Anthropic, OpenAI, DeepMind)",
        "agentic systems and tool use",
        "model evaluations and benchmarks",
        "AI safety and alignment",
        "practical engineering: RAG, fine-tuning, inference optimization",
    ],
    avoid=[
        "celebrity AI takes",
        "stock/finance speculation",
        "low-substance hype videos",
    ],
    tone="concise, technical, no hype",
)
