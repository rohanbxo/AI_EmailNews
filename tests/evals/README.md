# Summary quality evals

Hand-crafted evaluation harness for the digest agent. Runs the agent against
a fixed set of articles and grades the output with an LLM-as-judge plus
deterministic checks.

## Why this exists

Prompt/model changes are the easiest thing to ship without noticing you broke
something. This suite catches regressions before they hit the daily email:

- **CI-gated:** [`.github/workflows/evals.yml`](../../.github/workflows/evals.yml) runs on any PR that touches `app/agent/**` or `app/services/process_digest.py`. Fails the PR if the composite score drops below `EVAL_PASS_THRESHOLD` (default 55/100).
- **Visible:** results are published as a PR comment and available at [`/evals`](https://ai-news-web-5lhy.onrender.com/evals) on the live site.

## What we measure

Each candidate summary is scored on four LLM-judged axes (1-5) and two deterministic checks:

| Axis | What it catches |
|---|---|
| **faithfulness** | Hallucinated facts, invented numbers. |
| **informativeness** | Preserves concrete numbers, names, benchmarks. |
| **concision** | 3-5 sentences, no padding. |
| **no_hype** | Avoids "revolutionary", "game-changing", etc. |
| **required_facts** | Fraction of expected key terms present (deterministic substring). |
| **forbidden_terms** | Any listed forbidden term appearing costs 15 points each. |

Composite score = `70% × normalized_llm_avg + 30% × required_facts_recall − 15 × forbidden_hits`.

## The dataset

[`data/cases.json`](data/cases.json). Each case has a specific purpose — from
faithful-numbers-preservation to adversarial-empty-content. Add cases when
you find real-world failures. Format:

```json
{
  "id": "unique-slug",
  "purpose": "what regression this case is designed to catch",
  "source": "Anthropic blog",
  "title": "...",
  "body": "the article body — long enough that summarization is non-trivial",
  "required_facts": ["term", "A OR B (either is fine)", ...],
  "forbidden_terms": ["revolutionary", ...]
}
```

## Judge design

`SummaryJudge` inherits from `BaseAgent`, so it uses whichever LLM the app
uses (Groq by default). Two decisions worth noting:

1. **Same-model judge:** we use the same model to summarize *and* to judge.
   This introduces self-preference bias (Zheng et al. 2023). We accept it
   because the goal here is *regression detection* — catching that a prompt
   or model change made things worse — not absolute quality measurement.
2. **Deterministic side-checks:** `required_facts` and `forbidden_terms` are
   pure substring matches, no LLM. They pin down the objective bits — a
   summary that drops "SWE-bench" gets penalized regardless of what the
   judge thinks.

## Running locally

```bash
# One-off
uv run python -m tests.evals.run_evals

# CI-style, exit 1 on regression
EVAL_PASS_THRESHOLD=55 uv run python -m tests.evals.run_evals --check

# Machine-readable
uv run python -m tests.evals.run_evals --json > report.json
```

The latest report is written to `tests/evals/latest.json`, which the web
app reads for the `/evals` route.

## Cost

Each run makes `2 × n_cases` LLM calls (one summary + one judge per case).
With the default 6 cases on Groq's free tier, a full run is ~12 requests,
finishes in ~15-30 seconds, and costs $0.

## Known limitations

- **Small dataset:** 6 cases is enough to catch obvious regressions but not
  fine-grained quality shifts. Grow to 20-30 by adding real failures you
  spot in the daily digest.
- **English-only:** all cases are English AI news; the judge prompt is too.
- **Self-preference:** see "Judge design" above. If it becomes a problem,
  swap `SummaryJudge` to hit a different provider (e.g. Anthropic via
  `OPENAI_API_KEY` fallback pointing at a bridge).
