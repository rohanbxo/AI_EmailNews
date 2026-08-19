"""LLM-as-judge for digest summaries.

Scores a candidate summary on four axes, each 1-5:
  - faithfulness: no invented facts; every claim is supported by the source.
  - informativeness: preserves the concrete numbers, names, benchmarks.
  - concision: 3-5 sentences, no padding.
  - no_hype: avoids marketing language ("revolutionary", "game-changing").

Plus two deterministic checks that don't need an LLM:
  - required_facts: fraction of expected key terms present (case-insensitive substring).
  - forbidden_terms: any forbidden term appearing costs the case.

The judge itself uses the same LLM the app uses (Groq via BaseAgent). Judge
biases (see Zheng et al. 2023, "Judging LLM-as-a-Judge"):
  - position bias: N/A here (single-candidate).
  - verbosity bias: mitigated by the concision axis.
  - self-preference: mitigated by scoring against explicit source facts.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Dict, List

from app.agent.base import BaseAgent


log = logging.getLogger(__name__)


_JUDGE_PROMPT = """You are grading a news-digest summary.

SOURCE ARTICLE:
---
{body}
---

CANDIDATE SUMMARY:
---
{summary}
---

Score the CANDIDATE SUMMARY on each axis (integer 1-5, 5 is best).
Then give one short sentence of reasoning per axis.

Axes:
- faithfulness: every claim in the summary is supported by the source. Hallucinations = 1.
- informativeness: preserves the specific numbers, names, benchmarks, and mechanisms from the source. Vague summary = 1.
- concision: 3-5 sentences, no padding or filler. Padding = 1.
- no_hype: avoids marketing language ("revolutionary", "unprecedented", "game-changing"). Any such term = 1.

Return strict JSON of the form:
{{"faithfulness": <int>, "informativeness": <int>, "concision": <int>, "no_hype": <int>,
  "notes": {{"faithfulness": "...", "informativeness": "...", "concision": "...", "no_hype": "..."}}}}
"""


@dataclass
class CaseScore:
    case_id: str
    faithfulness: int
    informativeness: int
    concision: int
    no_hype: int
    required_facts_hit: float  # 0..1
    forbidden_terms_hit: List[str]
    notes: Dict[str, str] = field(default_factory=dict)
    summary_text: str = ""

    @property
    def llm_avg(self) -> float:
        return (self.faithfulness + self.informativeness + self.concision + self.no_hype) / 4.0

    @property
    def total(self) -> float:
        """Composite 0-100: 70% LLM axes (avg 1-5 -> 0-70), 30% required-facts."""
        llm_component = ((self.llm_avg - 1) / 4) * 70  # 1->0, 5->70
        facts_component = self.required_facts_hit * 30
        penalty = 15 * len(self.forbidden_terms_hit)
        return max(0.0, llm_component + facts_component - penalty)


class SummaryJudge(BaseAgent):
    system_prompt = (
        "You are a strict, calibrated evaluator of news-digest summaries. "
        "You never invent scores; you ground every judgment in the source text."
    )
    temperature = 0.0

    def judge(self, *, case: dict, summary: str) -> CaseScore:
        # deterministic checks first
        req = _check_required(summary, case.get("required_facts", []))
        forb = _check_forbidden(summary, case.get("forbidden_terms", []))

        # LLM check
        data = self.complete_json(
            _JUDGE_PROMPT.format(body=case["body"], summary=summary)
        )
        try:
            return CaseScore(
                case_id=case["id"],
                faithfulness=_clamp(int(data["faithfulness"])),
                informativeness=_clamp(int(data["informativeness"])),
                concision=_clamp(int(data["concision"])),
                no_hype=_clamp(int(data["no_hype"])),
                required_facts_hit=req,
                forbidden_terms_hit=forb,
                notes=data.get("notes", {}) if isinstance(data.get("notes"), dict) else {},
                summary_text=summary,
            )
        except (KeyError, TypeError, ValueError) as e:
            log.warning("Judge returned malformed response for %s: %s", case["id"], e)
            # score 1s on axes if the judge couldn't parse — flag for manual review
            return CaseScore(
                case_id=case["id"],
                faithfulness=1,
                informativeness=1,
                concision=1,
                no_hype=1,
                required_facts_hit=req,
                forbidden_terms_hit=forb,
                notes={"error": f"judge parse failure: {e}"},
                summary_text=summary,
            )


def _clamp(x: int) -> int:
    return max(1, min(5, x))


def _check_required(summary: str, expected: List[str]) -> float:
    if not expected:
        return 1.0
    s = summary.lower()
    hits = 0
    for e in expected:
        # "A OR B" -> pass if either substring is present
        alternatives = [a.strip().lower() for a in e.split(" OR ")]
        if any(a in s for a in alternatives):
            hits += 1
    return hits / len(expected)


def _check_forbidden(summary: str, forbidden: List[str]) -> List[str]:
    s = summary.lower()
    return [f for f in forbidden if f.lower() in s]
