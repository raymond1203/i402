"""CLI entry for Stage 2 behavioral simulation.

  uv run python -m behavior_sim.behavior_simulator \\
    --agents safe_paybot mid_paybot vuln_paybot \\
    --n-trials 200 --seed 42 \\
    --out reports/behavior_outcomes.json

Reads `ANTHROPIC_API_KEY` from the environment (load .env first).
Defaults the target and judge to `claude-sonnet-4-6` unless overridden
by `ANTHROPIC_MODEL_AGENT` / `ANTHROPIC_MODEL_JUDGE`.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from agents import KNOWN_AGENTS, load_agent

from .orchestrator import run_behavior_simulation


def _parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="python -m behavior_sim.behavior_simulator",
        description="Stage 2 agent behavioral simulator.",
    )
    p.add_argument("--agents", nargs="*", default=list(KNOWN_AGENTS))
    p.add_argument("--n-trials", type=int, default=50)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--max-concurrency", type=int, default=8)
    p.add_argument("--out", type=Path, default=None)
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Skip real API calls; emit a placeholder outcome with rate=0 for every category. "
        "Useful to wire end-to-end before the API key is in place.",
    )
    return p.parse_args(argv)


async def _real_run(args: argparse.Namespace) -> dict:
    # Defer the import so --dry-run works without the SDK installed.
    from anthropic import AsyncAnthropic

    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key or api_key.startswith("<"):
        raise SystemExit(
            "ANTHROPIC_API_KEY is not set (see .env.example). "
            "Use --dry-run to wire end-to-end without an API key."
        )
    target_model = os.environ.get("ANTHROPIC_MODEL_AGENT", "claude-sonnet-4-6")
    judge_model = os.environ.get("ANTHROPIC_MODEL_JUDGE", "claude-sonnet-4-6")
    client = AsyncAnthropic(api_key=api_key)

    applicants = []
    for name in args.agents:
        a = load_agent(name)
        # Force the declared model to the env override (operator's actual key
        # may not have access to the agent's declared model).
        a.model = target_model
        applicants.append(a)

    return await run_behavior_simulation(
        applicants=applicants,
        target_client=client,
        judge_client=client,
        judge_model=judge_model,
        n_trials=args.n_trials,
        seed=args.seed,
        max_concurrency=args.max_concurrency,
    )


def _dry_run(args: argparse.Namespace) -> dict:
    from .corpus import CATEGORIES
    from .orchestrator import OUTPUT_KEY

    placeholder = {}
    for name in args.agents:
        placeholder[name] = {}
        for cat in CATEGORIES:
            placeholder[name][OUTPUT_KEY[cat]] = {
                "vector": cat,
                "rate": 0.0,
                "unsafe_count": 0,
                "ambiguous_count": 0,
                "trials": 0,
                "paper_anchor": "DRY_RUN — no API calls made",
                "sample": [],
            }
    return placeholder


def main(argv: list[str] | None = None) -> None:
    load_dotenv()
    args = _parse_args(sys.argv[1:] if argv is None else argv)

    result = _dry_run(args) if args.dry_run else asyncio.run(_real_run(args))

    rendered = json.dumps(result, indent=2)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(rendered)
        print(f"wrote {args.out}")
    else:
        sys.stdout.write(rendered + "\n")


if __name__ == "__main__":
    main()
