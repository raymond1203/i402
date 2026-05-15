"""Stage 2 orchestrator — thin wrapper around the LHAA module system.

Each Stage-2 peril is now declared as a YAML config in `lhaa/configs/`
and instantiated via `lhaa.registry.load_stage2_modules()`. This module's
job is to:

  1. Load the 5 LLM-attacker modules (IV / AP1 / AP1.4 / AP3 / AP6).
  2. For each (applicant × module), call `module.execute(...)` which
     internally enforces paper §6.1 hook ordering:
         pre_budget → pre_sandbox → trials → post_audit → post_verdict
  3. Aggregate per-peril `ModuleResult`s into the legacy dict shape
     plus two new keys: `audit_root` (C3 SHA-256) and `audit_phase`
     (adaptive-budget exit state).

The function signature is preserved so `demo/run_demo.py` and tests
need no changes. The `n_trials` parameter is interpreted as the *total*
Stage-2 trial budget; we divide it across the 5 modules and use it as
the adaptive baseline (escalate_to scales up to 3× baseline by default).
"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from typing import Any

from gate.applicant import Applicant

from .attacker_agent import AttackerClient
from .corpus import CATEGORIES, Category  # re-export for callers
from .judge import JudgeClient
from .lhaa.registry import load_stage2_modules
from .target import TargetClient

log = logging.getLogger(__name__)

# Map output keys → internal `Category` ids (legacy contract).
OUTPUT_KEY: dict[Category, str] = {
    "IV":    "IV_selection",
    "AP1":   "AP1_prompt_injection",
    "AP1_4": "AP1_4_hallucinated",
    "AP3":   "AP3_tool_poisoning",
    "AP6":   "AP6_confused_deputy",
}

# Peril-id (LHAA module) → output key (orchestrator dict key).
_PERIL_TO_OUTPUT_KEY: dict[str, str] = {
    "IV_selection":         "IV_selection",
    "AP1_prompt_injection": "AP1_prompt_injection",
    "AP1_4_hallucinated":   "AP1_4_hallucinated",
    "AP3_tool_poisoning":   "AP3_tool_poisoning",
    "AP6_confused_deputy":  "AP6_confused_deputy",
}

# Peril-id → short vector label (legacy "vector" field).
_PERIL_TO_VECTOR: dict[str, str] = {
    "IV_selection":         "IV",
    "AP1_prompt_injection": "AP1",
    "AP1_4_hallucinated":   "AP1_4",
    "AP3_tool_poisoning":   "AP3",
    "AP6_confused_deputy":  "AP6",
}


async def run_behavior_simulation(
    *,
    applicants: Iterable[Applicant],
    target_client: TargetClient,
    judge_client: JudgeClient,
    judge_model: str,
    attacker_client: AttackerClient,
    attacker_model: str,
    n_trials: int = 100,
    seed: int = 42,
    max_concurrency: int = 8,
    sample_limit: int = 3,
) -> dict[str, Any]:
    """Run all 5 Stage-2 LHAA modules against each applicant.

    Returns the legacy dict shape (verdict-layer compatible) with two
    additional keys per peril: `audit_root` and `audit_phase`.
    """
    out: dict[str, dict] = {}

    modules = load_stage2_modules()
    if not modules:
        raise RuntimeError(
            "no Stage-2 LHAA modules found — check behavior_sim/lhaa/configs/"
        )

    # Distribute the trial budget across the loaded modules; floor at the
    # YAML baseline so adaptive escalation still has headroom on small
    # budgets. Each module's escalate_to is scaled to 3× baseline.
    per_module_baseline = max(1, n_trials // len(modules))
    for m in modules:
        if per_module_baseline > m.baseline:
            m.baseline = per_module_baseline
            m.escalate_to = max(m.escalate_to, 3 * m.baseline)
        m.sample_limit = sample_limit

    for applicant in applicants:
        per_peril: dict[str, dict] = {}
        for m in modules:
            try:
                result = await m.execute(
                    applicant,
                    seed=seed,
                    extra={
                        "target_client": target_client,
                        "judge_client": judge_client,
                        "judge_model": judge_model,
                        "attacker_client": attacker_client,
                        "attacker_model": attacker_model,
                        "max_concurrency": max_concurrency,
                    },
                )
            except Exception as e:  # noqa: BLE001 — log + degrade per peril
                log.exception(
                    "LHAA module %s failed on applicant=%s: %s",
                    m.peril_id, applicant.agent_name, e,
                )
                continue

            out_key = _PERIL_TO_OUTPUT_KEY[m.peril_id]
            per_peril[out_key] = {
                "vector": _PERIL_TO_VECTOR[m.peril_id],
                "rate": result.rate,
                "unsafe_count": result.unsafe_count,
                "ambiguous_count": result.ambiguous_count,
                "trials": result.trials,
                "paper_anchor": result.paper_anchor,
                "audit_root": result.audit_root,
                "audit_phase": result.audit_phase,
                "lhaa_verdict": result.verdict,
                "notes": result.notes,
                "sample": result.sample,
            }
        out[applicant.agent_name] = per_peril

    return out


__all__ = ["CATEGORIES", "OUTPUT_KEY", "run_behavior_simulation"]
