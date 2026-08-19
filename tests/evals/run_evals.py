"""Run the digest agent against every eval case, judge each, write a report.

Usage:
    uv run python -m tests.evals.run_evals              # human summary + writes JSON
    uv run python -m tests.evals.run_evals --json       # only JSON to stdout
    uv run python -m tests.evals.run_evals --check      # exit 1 if avg below threshold

The report is written to `tests/evals/latest.json`. The `/evals` route on the
web app reads that file. The GitHub Actions workflow uploads the file as an
artifact and comments a summary table on the PR.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import statistics
import sys
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

# Load .env for local runs (CI supplies env directly).
import app.database.connection  # noqa: F401  side-effect: loads .env

from app.agent.digest_agent import DigestAgent
from app.config import LLM_MODEL
from tests.evals.judge import CaseScore, SummaryJudge


DATA_DIR = Path(__file__).parent / "data"
REPORT_PATH = Path(__file__).parent / "latest.json"

# CI threshold: fail if avg score drops below this.
PASS_THRESHOLD = float(os.getenv("EVAL_PASS_THRESHOLD", "55"))


log = logging.getLogger(__name__)


def _load_cases() -> List[dict]:
    return json.loads((DATA_DIR / "cases.json").read_text(encoding="utf-8"))


def _summarize_one(agent: DigestAgent, case: dict) -> str:
    return agent.summarize(
        title=case["title"], body=case["body"], source=case["source"]
    ).summary


def run_evals() -> dict:
    cases = _load_cases()
    log.info("Loaded %d eval cases", len(cases))

    agent = DigestAgent()
    judge = SummaryJudge()

    started = time.time()
    scores: List[CaseScore] = []
    for i, case in enumerate(cases, start=1):
        log.info("[%d/%d] %s", i, len(cases), case["id"])
        summary = _summarize_one(agent, case)
        score = judge.judge(case=case, summary=summary)
        scores.append(score)
        log.info(
            "  total=%.1f  facts=%.0f%%  forbidden=%d  llm_avg=%.2f",
            score.total,
            score.required_facts_hit * 100,
            len(score.forbidden_terms_hit),
            score.llm_avg,
        )

    return _build_report(scores, started)


def _build_report(scores: List[CaseScore], started: float) -> dict:
    if not scores:
        return {"error": "no cases scored"}

    totals = [s.total for s in scores]
    per_axis: Dict[str, float] = {}
    for axis in ("faithfulness", "informativeness", "concision", "no_hype"):
        per_axis[axis] = round(statistics.mean(getattr(s, axis) for s in scores), 2)

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "elapsed_seconds": round(time.time() - started, 1),
        "model": LLM_MODEL,
        "n_cases": len(scores),
        "avg_total": round(statistics.mean(totals), 1),
        "min_total": round(min(totals), 1),
        "max_total": round(max(totals), 1),
        "per_axis": per_axis,
        "cases": [
            {**asdict(s), "total": round(s.total, 1), "llm_avg": round(s.llm_avg, 2)}
            for s in scores
        ],
    }


def _write_report(report: dict) -> None:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    log.info("Report -> %s", REPORT_PATH)


def _print_human(report: dict) -> None:
    print()
    print(f"=== Eval report — {report['model']} ===")
    print(f"  cases: {report['n_cases']}   elapsed: {report['elapsed_seconds']}s")
    print(f"  avg total: {report['avg_total']}  (min {report['min_total']}, max {report['max_total']})")
    print(f"  axis means:")
    for axis, val in report["per_axis"].items():
        print(f"    {axis:>16}: {val}/5")
    print()
    print(f"  {'case':<32} {'total':>6} {'facts':>6} {'forb':>4} {'llm':>4}")
    for c in report["cases"]:
        print(
            f"  {c['case_id']:<32} {c['total']:>6.1f} "
            f"{c['required_facts_hit']*100:>5.0f}% {len(c['forbidden_terms_hit']):>4} "
            f"{c['faithfulness']}/{c['informativeness']}/{c['concision']}/{c['no_hype']}"
        )
    print()


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true", help="print only JSON to stdout")
    parser.add_argument(
        "--check",
        action="store_true",
        help=f"exit 1 if avg_total < EVAL_PASS_THRESHOLD (default {PASS_THRESHOLD})",
    )
    args = parser.parse_args()

    report = run_evals()
    _write_report(report)

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        _print_human(report)

    if args.check and report.get("avg_total", 0) < PASS_THRESHOLD:
        log.error(
            "FAIL: avg_total %.1f below threshold %.1f",
            report["avg_total"],
            PASS_THRESHOLD,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
