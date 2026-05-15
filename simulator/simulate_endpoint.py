"""Stage 1 — protocol simulator entry point.

Composes the three Stage-1 attack vectors against an
`Applicant.endpoint_config` dict and returns paper-aligned outcomes:

    II  Replay        → real HTTP, DGR metric
    III Cache leak    → real HTTP, leak_rate metric
    I-A Revert-grant  → mini-sim, RGP_k + T_gf_sec metrics

Out of scope:
    I-B Settlement preemption → Stage 0 precondition gate (binary fact)
    IV  Server selection      → Stage 2 behavioral simulator (LLM-side)

Programmatic use:
    from simulator import simulate_endpoint
    out = await simulate_endpoint(endpoint_config, n_trials=5000, seed=42)

CLI use:
    uv run python -m simulator.simulate_endpoint \\
        --config '{"idempotency":"atomic",...}' \\
        --n-trials 5000 --seed 42 --out reports/proto.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

from .cache import simulate_cache
from .replay import simulate_replay
from .revert import simulate_revert


async def simulate_endpoint(config: dict, n_trials: int = 5000, seed: Any = 42) -> dict:
    """Run II + III + I-A against an endpoint config. Budget is split
    evenly across the three vectors.
    """
    per_vector = max(1, n_trials // 3)

    ii_replay = await simulate_replay(config["idempotency"], per_vector)
    iii_cache = await simulate_cache(config["cache_control"], per_vector)
    ia_revert = simulate_revert(
        {
            "settle_before_grant": config["settle_before_grant"],
            "confirmation_depth_k": config["confirmation_depth_k"],
            "byzantine_facilitator_assumed": config.get("byzantine_facilitator_assumed", False),
        },
        per_vector,
        seed,
    )

    return {
        "stage": "1_protocol",
        "paper_anchor": "arXiv:2605.11781",
        "config": config,
        "n_trials": n_trials,
        "seed": seed,
        "per_vector_trials": per_vector,
        "outcomes": {
            "II_replay": ii_replay,
            "III_cache": iii_cache,
            "IA_revert": ia_revert,
        },
        "notes": {
            "I-B": "settlement preemption handled by Stage 0 precondition gate",
            "IV": "server-selection handled by Stage 2 behavioral simulator",
        },
    }


def _parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="python -m simulator.simulate_endpoint",
        description="Stage 1 protocol simulator (II + III + I-A).",
    )
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--config", type=str, help="endpoint config as JSON string")
    src.add_argument("--config-file", type=Path, help="path to endpoint config JSON")
    p.add_argument("--n-trials", type=int, default=5000)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--out", type=Path, default=None)
    return p.parse_args(argv)


async def _cli_main(argv: list[str]) -> None:
    args = _parse_args(argv)
    raw = args.config if args.config else args.config_file.read_text()
    config = json.loads(raw)
    result = await simulate_endpoint(config, n_trials=args.n_trials, seed=args.seed)
    rendered = json.dumps(result, indent=2)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(rendered)
        print(f"wrote {args.out}")
    else:
        sys.stdout.write(rendered + "\n")


def main() -> None:  # console-script entry
    asyncio.run(_cli_main(sys.argv[1:]))


if __name__ == "__main__":
    main()
