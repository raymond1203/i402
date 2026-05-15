"""Stage 2 — agent behavioral simulator.

v2: every Stage 2 trial is driven by a Claude-instantiated *adaptive
attacker* (see `attacker_agent.py`) that generates one fresh scenario
per trial and memorises patterns the target refused. The earlier
static-corpus path is removed.

Five categories tested per agent (5,000 trials default, ~1,000 each):
    IV    server selection            (paper Attack IV)
    AP1   prompt injection            (agent_payment_risks.md §1)
    AP1_4 hallucinated recipient      (agent_payment_risks.md §1.4)
    AP3   tool / MCP poisoning        (agent_payment_risks.md §3)
    AP6   confused deputy             (agent_payment_risks.md §6.1)

Output schema matches what `verdict/thresholds.py` reads at
`stage_2_behavioral.<category>.rate`.
"""

from .attacker_agent import (
    ATTACK_META_SPEC,
    AttackerMemory,
    generate_adaptive_scenario,
    summarize_target_for_attacker,
)
from .corpus import CATEGORIES, Scenario
from .orchestrator import run_behavior_simulation

__all__ = [
    "run_behavior_simulation",
    "Scenario",
    "CATEGORIES",
    "AttackerMemory",
    "generate_adaptive_scenario",
    "summarize_target_for_attacker",
    "ATTACK_META_SPEC",
]
