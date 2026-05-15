"""Pretty CLI orchestrator — runs the full I402 pipeline on the 3 toy
agents and prints a competition-ready summary.

Default is paper-scale: 5,000 trials per stage, real Claude API for
Stage 2. Budget roughly $1–$3 per agent in Anthropic credit and
30–60 minutes of wall clock (free tier rate limits).

Usage:
    uv run python -m demo.run_demo                       # 5,000 trials per stage, real Claude calls
    uv run python -m demo.run_demo --dry-run             # skip Stage 2 LLM calls (CI / debugging)
    uv run python -m demo.run_demo --n-trials 600        # smaller Stage 1 budget
    uv run python -m demo.run_demo --mutate safe_paybot  # add the "edit prompt → coverage void" demo at the end
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
from agents.identity import compute_identity_hash
from gate.precondition_gate import check_preconditions
from simulator import simulate_endpoint
from verdict.verdict import apply_verdict

ACE_ROOT = Path(__file__).resolve().parent.parent
REPORTS_DIR = ACE_ROOT / "reports"

# ---- ANSI helpers ----------------------------------------------------------
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
CYAN = "\033[36m"


def _color(text: str, code: str) -> str:
    return f"{code}{text}{RESET}"


def _verdict_color(verdict: str) -> str:
    return {"PASS": GREEN, "CONDITIONAL": YELLOW, "DECLINE": RED}.get(verdict, "")


def _header(title: str) -> None:
    bar = "═" * 70
    print(f"\n{_color(bar, CYAN)}")
    print(f"{_color('  ' + title, CYAN + BOLD)}")
    print(f"{_color(bar, CYAN)}")


def _subheader(title: str) -> None:
    print(f"\n{_color('— ' + title, BOLD)}")


# ---- Stage runners ---------------------------------------------------------


def _run_gate(name: str) -> tuple[bool, str]:
    result = check_preconditions(load_agent(name))
    if result.passed:
        return True, "all preconditions verified"
    return False, "; ".join(f.check for f in result.failures)


async def _run_stage_1(name: str, n_trials: int, seed: int) -> dict:
    applicant = load_agent(name)
    out = await simulate_endpoint(
        {
            "idempotency": applicant.endpoint_config.idempotency,
            "cache_control": applicant.endpoint_config.cache_control,
            "settle_before_grant": applicant.endpoint_config.settle_before_grant,
            "confirmation_depth_k": applicant.endpoint_config.confirmation_depth_k,
            "byzantine_facilitator_assumed": applicant.endpoint_config.byzantine_facilitator_assumed,
        },
        n_trials=n_trials,
        seed=seed,
    )
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    (REPORTS_DIR / f"{name}_protocol.json").write_text(json.dumps(out, indent=2))
    return out


async def _run_stage_2(real_llm: bool, agents: list[str], n_trials: int, seed: int) -> dict:
    """Stage 2 — behavioural simulator. `real_llm=False` writes a zero-rate
    placeholder so downstream verdict logic still has the expected shape."""
    if not real_llm:
        from behavior_sim.corpus import CATEGORIES
        from behavior_sim.orchestrator import OUTPUT_KEY

        out = {
            name: {
                OUTPUT_KEY[cat]: {
                    "vector": cat,
                    "rate": 0.0,
                    "unsafe_count": 0,
                    "ambiguous_count": 0,
                    "trials": 0,
                    "paper_anchor": "DRY_RUN (Stage 2 not invoked)",
                    "sample": [],
                }
                for cat in CATEGORIES
            }
            for name in agents
        }
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        (REPORTS_DIR / "behavior_outcomes.json").write_text(json.dumps(out, indent=2))
        return out

    from anthropic import AsyncAnthropic

    from behavior_sim.orchestrator import run_behavior_simulation

    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key or api_key.startswith("<"):
        raise SystemExit(
            "ANTHROPIC_API_KEY not set. Fill .env (see .env.example), "
            "or pass --dry-run to skip Stage 2 entirely."
        )
    model = os.environ.get("ANTHROPIC_MODEL_AGENT", "claude-sonnet-4-6")
    judge_model = os.environ.get("ANTHROPIC_MODEL_JUDGE", model)
    # max_retries=8 covers Anthropic's automatic 429 backoff for low-tier accounts.
    client = AsyncAnthropic(api_key=api_key, max_retries=8, timeout=120.0)
    applicants = []
    for name in agents:
        a = load_agent(name)
        a.model = model
        applicants.append(a)
    out = await run_behavior_simulation(
        applicants=applicants,
        target_client=client,
        judge_client=client,
        judge_model=judge_model,
        n_trials=n_trials,
        seed=seed,
        max_concurrency=2,  # tuned for ~30k tokens/min rate limits on free tier
    )
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    (REPORTS_DIR / "behavior_outcomes.json").write_text(json.dumps(out, indent=2))
    return out


def _final_verdict(name: str, stage_1: dict, stage_2_for_agent: dict | None) -> dict:
    merged: dict = {"stage_1_protocol": stage_1}
    if stage_2_for_agent is not None:
        merged["stage_2_behavioral"] = stage_2_for_agent
    v = apply_verdict(name, merged)
    return v


# ---- Pretty printing ------------------------------------------------------


def _print_agent_declaration(name: str) -> None:
    a = load_agent(name)
    ec = a.endpoint_config
    bc = a.behavioral_config
    print(f"  {BOLD}{name}{RESET}  ({a.model})")
    print(
        f"    endpoint:  idempotency={ec.idempotency:6s} cache={ec.cache_control:7s} "
        f"settle_before_grant={ec.settle_before_grant!s:5s} k={ec.confirmation_depth_k}"
    )
    print(
        f"    behavior:  discovery={bc.discovery_method:9s} prompt-guard={bc.prompt_injection_guardrail:6s} "
        f"sdk={bc.sdk_family}"
    )
    print(f"    identity:  {compute_identity_hash(a)[:18]}…")


def _print_stage_1_row(name: str, out: dict) -> None:
    o = out["outcomes"]
    DGR = o["II_replay"]["DGR_overall"]
    leak = o["III_cache"]["leak_rate"]
    RGP = o["IA_revert"]["RGP_k_expected"]
    Tgf = o["IA_revert"]["T_gf_sec"]
    print(
        f"  {name:14s}  II DGR={DGR:7.2f}   III leak={leak:.2f}   "
        f"I-A RGP_k={RGP:.4f}   T_gf={Tgf:5.1f}s"
    )


def _print_stage_2_row(name: str, stage_2: dict) -> None:
    keys = [
        ("IV_selection", "IV"),
        ("AP1_prompt_injection", "AP1"),
        ("AP1_4_hallucinated", "AP1.4"),
        ("AP3_tool_poisoning", "AP3"),
        ("AP6_confused_deputy", "AP6"),
    ]
    parts = []
    for k, label in keys:
        parts.append(f"{label}={stage_2[k]['rate']:.2f}")
    print(f"  {name:14s}  " + "   ".join(parts))


def _print_verdict_row(name: str, v) -> None:
    color = _verdict_color(v.verdict)
    badge = _color(f" {v.verdict:11s} ", color + BOLD)
    note = f"({len(v.failed_vectors)} failed vector(s)"
    if v.provisional:
        note += ", PROVISIONAL"
    note += ")"
    print(f"  {name:14s}  {badge}  {DIM}{note}{RESET}")
    if v.failed_vectors:
        for fv in v.failed_vectors:
            arrow = "→" if fv.decision == "DECLINE" else "·"
            print(f"     {arrow} {fv.key:30s} value={fv.value!s:8s}  threshold={fv.decline_above}")


def _print_mutation_demo(name: str) -> None:
    """Show that mutating the agent's declaration changes the identity
    hash, which would invalidate any previously-minted NFT."""
    _header(f"Immutability demo — mutating {name}")
    a = load_agent(name)
    before = compute_identity_hash(a)
    print(f"  before:  {before}")
    a.system_prompt = a.system_prompt + " "  # one trailing space
    after = compute_identity_hash(a)
    print(f"  after:   {after}")
    if before == after:
        print(_color("  ✗ unexpected: hash did not change", RED))
        return
    print(_color("  ✓ hash flipped on a 1-character edit", GREEN))
    print(_color("    ⇒ NFT.verifyIdentity() would return false ⇒ coverage VOID", YELLOW))


# ---- Main ----------------------------------------------------------------


def _parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="python -m demo.run_demo")
    p.add_argument("--agents", nargs="*", default=list(KNOWN_AGENTS))
    p.add_argument(
        "--n-trials",
        type=int,
        default=5000,
        help="Stage 1 trials per agent (default: 5000 — paper-scale)",
    )
    p.add_argument(
        "--stage-2-trials",
        type=int,
        default=5000,
        help="Stage 2 trials per agent. Real Claude API calls. Budget ~$1–$3 per agent.",
    )
    p.add_argument("--seed", type=int, default=42)
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Skip Stage 2 LLM calls (Stage 1 still runs at full scale). "
             "Use for CI / fast iteration / debugging without spending API budget.",
    )
    p.add_argument(
        "--mutate",
        type=str,
        default=None,
        help="Agent name to use for the immutability demo at the end",
    )
    return p.parse_args(argv)


async def _main_async(args: argparse.Namespace) -> int:
    load_dotenv(ACE_ROOT / ".env")

    _header("ACE — Agentic Commerce Endorsement (demo)")
    print(
        f"  trial budget:    Stage 1 = {args.n_trials}  "
        f"Stage 2 = {'DRY-RUN (0)' if args.dry_run else 'real Claude × ' + str(args.stage_2_trials)}"
    )
    print(f"  seed:            {args.seed}")
    print(f"  agents:          {', '.join(args.agents)}")

    _subheader("Agents under audit")
    for name in args.agents:
        _print_agent_declaration(name)

    _subheader("Stage 0  precondition gate")
    gate_results: dict[str, tuple[bool, str]] = {}
    passers: list[str] = []
    for name in args.agents:
        ok, detail = _run_gate(name)
        gate_results[name] = (ok, detail)
        badge = _color(" PASS ", GREEN + BOLD) if ok else _color(" DECLINE ", RED + BOLD)
        print(f"  {name:14s}  {badge}  {DIM}{detail}{RESET}")
        if ok:
            passers.append(name)

    if not passers:
        print(_color("\nno agents cleared the gate; pipeline stops here.", RED))
        return 1

    _subheader("Stage 1  protocol simulator  (replay / cache / revert)")
    stage_1_outcomes: dict[str, dict] = {}
    for name in passers:
        out = await _run_stage_1(name, args.n_trials, args.seed)
        stage_1_outcomes[name] = out
        _print_stage_1_row(name, out)

    _subheader(
        "Stage 2  behavioral simulator  (server-selection / prompt-injection / tool-poisoning / confused-deputy)"
    )
    stage_2_all = await _run_stage_2(not args.dry_run, passers, args.stage_2_trials, args.seed)
    for name in passers:
        _print_stage_2_row(name, stage_2_all[name])

    _subheader("Stage 3  rule-based verdict")
    verdicts: dict[str, object] = {}
    for name in passers:
        v = _final_verdict(name, stage_1_outcomes[name], stage_2_all.get(name))
        verdicts[name] = v
        _print_verdict_row(name, v)

    _subheader("Stage 4  NFT mint hint")
    for name in passers:
        v = verdicts[name]
        a = load_agent(name)
        h = compute_identity_hash(a)
        if v.verdict == "PASS":
            print(f"  {name:14s}  ready to mint  ⟶  uv run python -m nft.mint {name}")
            print(f"  {DIM}                identity_hash = {h}{RESET}")
        else:
            print(f"  {name:14s}  {_color(v.verdict, _verdict_color(v.verdict))}  — no NFT")

    if args.mutate:
        _print_mutation_demo(args.mutate)

    print()
    print(_color("Done.", GREEN + BOLD))
    return 0


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    return asyncio.run(_main_async(args))


if __name__ == "__main__":
    raise SystemExit(main())
