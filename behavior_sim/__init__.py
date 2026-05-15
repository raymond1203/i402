"""Stage 2 — agent behavioral simulator.

Drives each toy agent through adversarial scenarios using Claude
(or any client implementing the `JudgeClient` / `TargetClient`
protocols) and aggregates per-category unsafe-decision rates.

Five categories tested per agent (5,000 trials default, ~1,000 each):
    IV    server selection            (paper Attack IV)
    AP1   prompt injection            (agent_payment_risks.md §1)
    AP1_4 hallucinated recipient      (agent_payment_risks.md §1.4)
    AP3   tool / MCP poisoning        (agent_payment_risks.md §3)
    AP6   confused deputy             (agent_payment_risks.md §6.1)

Output schema matches what `verdict/thresholds.py` reads at
`stage_2_behavioral.<category>.rate`.
"""

from .corpus import CATEGORIES, Scenario, load_corpus
from .orchestrator import run_behavior_simulation

__all__ = ["run_behavior_simulation", "Scenario", "CATEGORIES", "load_corpus"]
