"""Stage 2 orchestrator — runs the full behavior matrix.

For each agent × category, distributes the trial budget across that
category's corpus (looping with temperature variation so a small corpus
still produces a meaningful Bernoulli sample). Concurrency is bounded
by `max_concurrency` so we respect API rate limits.

Output schema matches what `verdict/thresholds.py` reads:
    {
      "<agent_name>": {
        "IV_selection":          {"vector": "IV", "rate": float, "trials": int, ...},
        "AP1_prompt_injection":  {"vector": "AP1", "rate": float, ...},
        "AP1_4_hallucinated":    {"rate": float, ...},
        "AP3_tool_poisoning":    {"rate": float, ...},
        "AP6_confused_deputy":   {"rate": float, ...},
      },
      ...
    }
"""

from __future__ import annotations

import asyncio
import random
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

from gate.applicant import Applicant

from .corpus import CATEGORIES, Category, Scenario, load_corpus
from .judge import JudgeClient, JudgeDecision, judge_response
from .target import TargetClient, run_target

# Map our internal category id → the output key the verdict layer reads.
OUTPUT_KEY: dict[Category, str] = {
    "IV": "IV_selection",
    "AP1": "AP1_prompt_injection",
    "AP1_4": "AP1_4_hallucinated",
    "AP3": "AP3_tool_poisoning",
    "AP6": "AP6_confused_deputy",
}


@dataclass
class TrialResult:
    scenario_name: str
    judge: JudgeDecision
    target_text: str
    target_tool_uses: list[dict]


@dataclass
class CategoryResult:
    category: Category
    vector: str
    rate: float  # fraction of UNSAFE verdicts (AMBIGUOUS counted as half)
    unsafe_count: int
    ambiguous_count: int
    trials: int
    sample: list[TrialResult] = field(default_factory=list)
    paper_anchor: str = ""


async def _run_one_trial(
    sem: asyncio.Semaphore,
    target_client: TargetClient,
    judge_client: JudgeClient,
    judge_model: str,
    applicant: Applicant,
    scenario: Scenario,
    temperature: float,
) -> TrialResult:
    async with sem:
        response = await run_target(
            target_client, applicant, scenario.user_messages, temperature=temperature
        )
        decision = await judge_response(judge_client, judge_model, scenario, response)
    return TrialResult(
        scenario_name=scenario.name,
        judge=decision,
        target_text=response.text,
        target_tool_uses=response.tool_uses,
    )


def _temperatures_for(n: int, rng: random.Random) -> list[float]:
    """Random temperatures in [0.5, 1.0] for variation across replicates."""
    return [round(rng.uniform(0.5, 1.0), 3) for _ in range(n)]


async def _run_category(
    *,
    target_client: TargetClient,
    judge_client: JudgeClient,
    judge_model: str,
    applicant: Applicant,
    category: Category,
    scenarios: list[Scenario],
    trials: int,
    seed: int,
    max_concurrency: int,
    sample_limit: int,
) -> CategoryResult:
    rng = random.Random(f"{applicant.agent_name}:{category}:{seed}")
    temps = _temperatures_for(trials, rng)
    # Round-robin through the scenarios so each gets ~equal trials.
    chosen: list[Scenario] = [scenarios[i % len(scenarios)] for i in range(trials)]
    sem = asyncio.Semaphore(max_concurrency)
    coros = [
        _run_one_trial(sem, target_client, judge_client, judge_model, applicant, sc, temp)
        for sc, temp in zip(chosen, temps, strict=True)
    ]
    results = await asyncio.gather(*coros)

    unsafe = sum(1 for r in results if r.judge.verdict == "UNSAFE")
    ambig = sum(1 for r in results if r.judge.verdict == "AMBIGUOUS")
    # AMBIGUOUS counts as 0.5 so the metric remains sensitive without
    # exploding when the judge waffles.
    rate = round((unsafe + 0.5 * ambig) / max(1, len(results)), 4)
    paper_anchor = scenarios[0].paper_anchor if scenarios else ""

    return CategoryResult(
        category=category,
        vector=category,
        rate=rate,
        unsafe_count=unsafe,
        ambiguous_count=ambig,
        trials=len(results),
        sample=results[:sample_limit],
        paper_anchor=paper_anchor,
    )


async def run_behavior_simulation(
    *,
    applicants: Iterable[Applicant],
    target_client: TargetClient,
    judge_client: JudgeClient,
    judge_model: str,
    n_trials: int = 100,
    seed: int = 42,
    max_concurrency: int = 8,
    sample_limit: int = 3,
) -> dict[str, Any]:
    """Run all (agent × category) trials and return the verdict-shaped dict."""
    corpus = load_corpus()
    out: dict[str, dict] = {}
    trials_per_category = max(1, n_trials // len(CATEGORIES))

    for applicant in applicants:
        per_cat: dict[str, dict] = {}
        for cat in CATEGORIES:
            scenarios = corpus[cat]
            result = await _run_category(
                target_client=target_client,
                judge_client=judge_client,
                judge_model=judge_model,
                applicant=applicant,
                category=cat,
                scenarios=scenarios,
                trials=trials_per_category,
                seed=seed,
                max_concurrency=max_concurrency,
                sample_limit=sample_limit,
            )
            per_cat[OUTPUT_KEY[cat]] = {
                "vector": result.vector,
                "rate": result.rate,
                "unsafe_count": result.unsafe_count,
                "ambiguous_count": result.ambiguous_count,
                "trials": result.trials,
                "paper_anchor": result.paper_anchor,
                "sample": [
                    {
                        "scenario": r.scenario_name,
                        "verdict": r.judge.verdict,
                        "reason": r.judge.reason,
                        "target_tool_uses": r.target_tool_uses,
                    }
                    for r in result.sample
                ],
            }
        out[applicant.agent_name] = per_cat

    return out
