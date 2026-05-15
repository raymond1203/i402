"""Closed-form LHAA skill (Stage-1 perils: IA / II / III).

These three perils are *not* exercised by an LLM attacker: their failure
rate is fully determined by the applicant's declared `endpoint_config`
through `simulator.simulate_endpoint()`. The "trials" the skill records
are the simulator's internal samples (HTTP server probes for II / III,
Bernoulli mini-sim for IA), so the adaptive budget collapses to a
single full-run plus a Wilson interval check.

Mapping from simulator output → peril rate:

    IA_revert  : outcomes.IA_revert.RGP_k_expected
    II_replay  : outcomes.II_replay.DGR_overall
    III_cache  : outcomes.III_cache.leak_rate

The skill caches the simulator result per (applicant, baseline-or-
escalate-budget) so all three closed-form modules share one
`simulate_endpoint()` call per agent in the orchestrator (paper §5.3's
"single sim run, multiple peril extractions").
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from gate.applicant import Applicant
from simulator import simulate_endpoint

from .audit import AuditChain
from .budget import AdaptiveBudget
from .hooks import TrialOutcome
from .interface import LHAAInterface

# Shared cache: (agent_name, n_trials) → simulator output dict.
# Cleared between orchestrator runs by `clear_cache()`.
_SIM_CACHE: dict[tuple[str, int], dict] = {}


def clear_cache() -> None:
    _SIM_CACHE.clear()


_RATE_PATH: dict[str, tuple[str, str]] = {
    "IA_revert": ("IA_revert", "RGP_k_expected"),
    "II_replay": ("II_replay", "DGR_overall"),
    "III_cache": ("III_cache", "leak_rate"),
}


def _endpoint_config_dict(applicant: Applicant) -> dict[str, Any]:
    ec = applicant.endpoint_config
    return {
        "idempotency": ec.idempotency,
        "cache_control": ec.cache_control,
        "settle_before_grant": ec.settle_before_grant,
        "confirmation_depth_k": ec.confirmation_depth_k,
        "byzantine_facilitator_assumed": ec.byzantine_facilitator_assumed,
    }


@dataclass
class ClosedFormSkill(LHAAInterface):
    """Stage-1 closed-form module. `_run_trials` calls simulator once."""

    async def _run_trials(
        self,
        *,
        applicant: Applicant,
        budget: AdaptiveBudget,
        audit: AuditChain,
        seed: int,
        extra: dict[str, Any],
    ) -> tuple[list[TrialOutcome], list[str]]:
        n = budget.baseline
        cfg = _endpoint_config_dict(applicant)
        key = (applicant.agent_name, n)
        if key not in _SIM_CACHE:
            _SIM_CACHE[key] = await simulate_endpoint(cfg, n_trials=n, seed=seed)
        sim_out = _SIM_CACHE[key]

        vector_key, metric_key = _RATE_PATH[self.peril_id]
        vector_block = sim_out["outcomes"][vector_key]
        rate = float(vector_block[metric_key])

        # Convert continuous rate into a Bernoulli-style trial sequence so
        # downstream tooling (audit chain, sample dict) is uniform with
        # Stage-2. We synthesise ⌈rate · n⌉ UNSAFE outcomes and the rest
        # SAFE — this is purely a representational choice; the closed-form
        # rate itself is what flows into the verdict layer.
        n_unsafe = int(round(rate * n))
        # Clip in case sim returns e.g. DGR=N which can exceed 1.
        n_unsafe = max(0, min(n_unsafe, n))

        outcomes: list[TrialOutcome] = []
        for i in range(n):
            label = "UNSAFE" if i < n_unsafe else "SAFE"
            rc = 1.0 if label == "UNSAFE" else 0.0
            payload = {
                "vector": vector_key,
                "metric_key": metric_key,
                "metric_value": rate,
                "closed_form": True,
            }
            if i < 3:
                payload["sim_block_preview"] = {
                    k: vector_block[k]
                    for k in list(vector_block.keys())[:6]
                }
            o = TrialOutcome(
                peril_id=self.peril_id,
                trial_idx=i,
                label=label,
                rate_contribution=rc,
                reason="closed-form simulator result",
                audit_payload=payload,
            )
            outcomes.append(o)
            self.hooks.post_audit(audit, o)

        notes = [
            f"closed-form: extracted rate={rate:.4f} from "
            f"outcomes.{vector_key}.{metric_key} (n={n})",
        ]
        # Closed-form modules don't escalate — set phase explicitly.
        budget.phase = "stopped"
        budget.trials_run = n
        budget.unsafe_observed = float(n_unsafe)
        return outcomes, notes
