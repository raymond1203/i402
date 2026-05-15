"""Pretty CLI orchestrator — runs the full I402 pipeline on the 3 toy
agents and prints a competition-ready summary.

Default is paper-scale: 5,000 trials per stage, real Claude API for
Stage 2. Budget roughly $1–$3 per agent in Anthropic credit and
30–60 minutes of wall clock (free tier rate limits).

Usage:
    uv run python -m demo.run_demo                       # 5,000 trials per stage, real Claude calls (adaptive attacker)
    uv run python -m demo.run_demo --attacker-model claude-opus-4-7  # cross-family attacker
    uv run python -m demo.run_demo --dry-run             # skip Stage 2 LLM calls (CI / debugging)
    uv run python -m demo.run_demo --n-trials 600        # smaller Stage 1 budget
    uv run python -m demo.run_demo --mutate safe_paybot  # add the "edit prompt → coverage void" demo at the end

Stage 2 is adaptive-only in v2: a Claude attacker generates each
trial's scenario conditioned on prior refused patterns. Budget per
agent: ~$1.5–4.5 (target + judge + attacker LLM calls × 5,000 trials).
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
from pricing.engine import (
    PremiumResult,
    applicant_from_pipeline,
    compute_gross_premium,
)
from simulator import simulate_endpoint
from verdict.thresholds import normalize_rate
from verdict.verdict import Verdict, apply_verdict

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
    return {"PASS": GREEN, "DECLINE": RED}.get(verdict, "")


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


async def _run_stage_2(
    real_llm: bool,
    agents: list[str],
    n_trials: int,
    seed: int,
    attacker_model: str | None = None,
) -> dict:
    """Stage 2 — adaptive behavioural simulator.

    `real_llm=False` writes a zero-rate placeholder so downstream verdict
    logic still has the expected shape. With `real_llm=True`, every trial
    triggers three Claude calls (attacker + target + judge); see
    behavior_sim/attacker_agent.py for the attacker design.
    """
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
                    "audit_root": "",
                    "audit_phase": "dry_run",
                    "lhaa_verdict": "PASS",
                    "notes": ["dry-run placeholder"],
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
        attacker_client=client,
        attacker_model=attacker_model or model,
        n_trials=n_trials,
        seed=seed,
        max_concurrency=2,  # tuned for ~30k tokens/min rate limits on free tier
    )
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    (REPORTS_DIR / "behavior_outcomes.json").write_text(json.dumps(out, indent=2))
    return out


def _final_verdict(name: str, stage_1: dict, stage_2_for_agent: dict | None) -> Verdict:
    merged: dict = {"stage_1_protocol": stage_1}
    if stage_2_for_agent is not None:
        merged["stage_2_behavioral"] = stage_2_for_agent
    return apply_verdict(load_agent(name), merged)


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


def _print_verdict_row(name: str, v: Verdict) -> None:
    color = _verdict_color(v.verdict)
    badge = _color(f" {v.verdict:7s} ", color + BOLD)
    note = (
        f"(c_tx=${v.c_tx_usd:.2f}, ε_target={v.epsilon_target:.4%}"
        f"{', PROVISIONAL' if v.provisional else ''})"
    )
    print(f"  {name:14s}  {badge}  {DIM}{note}{RESET}")
    if v.failed_perils:
        for fp in v.failed_perils:
            print(
                f"     → {fp.peril_id:10s} Wilson_upper={fp.wilson_upper:.4%}"
                f"  vs ε={fp.epsilon_target:.4%}"
                f"  ({fp.wilson_upper/fp.epsilon_target:.1f}× over)"
            )


def _collect_audit_roots(stage_2_for_agent: dict | None) -> dict[str, str]:
    """Pull `audit_root` off each peril's stage-2 block (LHAA C3 chain)."""
    if not stage_2_for_agent:
        return {}
    out: dict[str, str] = {}
    for k, v in stage_2_for_agent.items():
        if isinstance(v, dict) and v.get("audit_root"):
            out[k] = v["audit_root"]
    return out


# Stage-2 dict key → pricing peril id.
_STAGE2_TO_PRICING_PERIL: dict[str, str] = {
    "IV_selection":         "IV_select",
    "AP1_prompt_injection": "AP1",
    "AP1_4_hallucinated":   "AP1_4",
    "AP3_tool_poisoning":   "AP3",
    "AP6_confused_deputy":  "AP6",
}


def _sim_rates_from_outcomes(stage_1: dict, stage_2: dict | None) -> dict[str, float]:
    """Build pricing.engine sim_rates dict from combined Stage 1+2 outcomes."""
    outcomes = stage_1["outcomes"]
    sim_rates = {
        "P1_revert": normalize_rate("P1_revert", outcomes["IA_revert"]["RGP_k_expected"]),
        "P3_replay": normalize_rate("P3_replay", outcomes["II_replay"]["DGR_overall"]),
        "P4_cache":  normalize_rate("P4_cache",  outcomes["III_cache"]["leak_rate"]),
    }
    if stage_2:
        for s2_key, peril in _STAGE2_TO_PRICING_PERIL.items():
            blk = stage_2.get(s2_key) or {}
            sim_rates[peril] = float(blk.get("rate", 0.0))
    return sim_rates


def _price_agent(name: str, stage_1: dict, stage_2: dict | None) -> PremiumResult:
    a = load_agent(name)
    if a.annual_tx_count_estimate <= 0:
        raise SystemExit(
            f"{name}: annual_tx_count_estimate must be > 0 to price "
            f"(set in agents/{name}.json)"
        )
    c_tx = float(a.spending_policy.per_tx_cap_usd)
    daily_cap = float(a.spending_policy.daily_cap_usd)
    aggregate_cap = max(daily_cap * 365.0, 1000.0)  # heuristic for the toy demo
    sim_rates = _sim_rates_from_outcomes(stage_1, stage_2)
    pricing_applicant = applicant_from_pipeline(
        name=name,
        annual_tx_count=a.annual_tx_count_estimate,
        per_event_caps={v: c_tx for v in sim_rates},
        aggregate_cap=aggregate_cap,
        sim_rates=sim_rates,
    )
    return compute_gross_premium(pricing_applicant)


def _print_premium_row(name: str, r: PremiumResult) -> None:
    color = GREEN if r.verdict == "PASS" else RED
    badge = _color(f" rate={r.rate*100:6.2f}% ", color + BOLD)
    print(
        f"  {name:14s}  {badge}  "
        f"{DIM}π_pure=${r.pure:,.2f}  π_gross=${r.gross:,.2f}  "
        f"L={r.loading_base:.3f}  M_clip={r.multiplier_product:.3f}  "
        f"α={int(r.alpha_used)}{RESET}"
    )


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
        "--attacker-model",
        type=str,
        default=None,
        help="Override the attacker model. Defaults to the target model "
             "(claude-sonnet-4-6). Using a different family — e.g. "
             "claude-opus-4-7 — further weakens the self-attack collusion "
             "concern by making attacker and target structurally different.",
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
        f"Stage 2 = {'DRY-RUN (0)' if args.dry_run else 'adaptive attacker × ' + str(args.stage_2_trials)}"
    )
    print(f"  attacker model:  {args.attacker_model or '(same as target)'}")
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
    stage_2_all = await _run_stage_2(
        not args.dry_run, passers, args.stage_2_trials, args.seed,
        attacker_model=args.attacker_model,
    )
    for name in passers:
        _print_stage_2_row(name, stage_2_all[name])

    _subheader("Stage 3  rule-based verdict")
    verdicts: dict[str, object] = {}
    for name in passers:
        v = _final_verdict(name, stage_1_outcomes[name], stage_2_all.get(name))
        verdicts[name] = v
        _print_verdict_row(name, v)

    _subheader("Stage 4  pricing  (π_gross = π_pure · 1.645 · clip(∏m))")
    premiums: dict[str, PremiumResult] = {}
    for name in passers:
        v = verdicts[name]
        if v.verdict != "PASS":
            print(f"  {name:14s}  {_color('skipped', YELLOW)} — verdict {v.verdict}")
            continue
        try:
            r = _price_agent(name, stage_1_outcomes[name], stage_2_all.get(name))
        except SystemExit as e:
            print(f"  {name:14s}  {_color('error', RED)} — {e}")
            continue
        premiums[name] = r
        _print_premium_row(name, r)

    _subheader("Stage 5  NFT mint hint")
    for name in passers:
        v = verdicts[name]
        a = load_agent(name)
        h = compute_identity_hash(a)
        roots = _collect_audit_roots(stage_2_all.get(name))
        if v.verdict == "PASS":
            print(f"  {name:14s}  ready to mint  ⟶  uv run python -m nft.mint {name}")
            print(f"  {DIM}                identity_hash = {h}{RESET}")
            if name in premiums:
                pr = premiums[name]
                print(f"  {DIM}                premium = ${pr.gross:,.2f}/yr ({pr.rate*100:.2f}% of aggregate cap){RESET}")
            if roots:
                preview = ", ".join(
                    f"{k}={r[:10]}…" for k, r in list(roots.items())[:3]
                )
                print(f"  {DIM}                audit_roots: {preview}{RESET}")
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
