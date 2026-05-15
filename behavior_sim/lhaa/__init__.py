"""LHAA — LLM Harness Attack Agent (paper §6).

The LHAA subpackage decomposes the 8 attack-vector "perils" the underwriting
pipeline must defend against into uniform `LHAAInterface` modules, each
declared by a YAML config in `configs/`. Modules differ only in their
`_run_trials()` implementation:

  - Stage 1 (P1=IA / P3=II / P4=III)  → closed_form skill — wraps simulator/
  - Stage 2 (IV / AP1 / AP1.4 / AP3 / AP6) → llm_attacker skill — wraps
                                            behavior_sim/attacker_agent.py

Each `execute()` call runs the locked Hook ordering required by paper §6.1:

    pre_budget_hook    →  pre_sandbox_hook  →  _run_trials
    →  post_audit_hook →  post_verdict_hook

so the 4 harness conditions (C1 determinism, C2 sandbox isolation, C3
SHA-256 audit chain, C4 fixed-rule verdict) are uniformly enforced across
every peril.
"""

from .audit import AuditChain, canonical_json
from .budget import AdaptiveBudget, AdaptiveBudgetDecision
from .hooks import Hooks, TrialContext, TrialOutcome
from .interface import LHAAInterface, ModuleResult

__all__ = [
    "AdaptiveBudget",
    "AdaptiveBudgetDecision",
    "AuditChain",
    "Hooks",
    "LHAAInterface",
    "ModuleResult",
    "TrialContext",
    "TrialOutcome",
    "canonical_json",
]
