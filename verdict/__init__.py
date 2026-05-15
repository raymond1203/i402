"""Stage 3 — Li 2026 Corollary 10 verdict gate.

Takes Stage 1 protocol outcomes + Stage 2 behavioral outcomes per agent,
applies the ε_target(c_tx) AND-gate over the 4 Class A perils, emits
PASS / DECLINE. Class B perils flow only to pricing.

See `docs/THRESHOLDS_AND_PREMIUM.md` §1 for the decision rule and the
external anchor.
"""

from .thresholds import (
    CLASS_A_PERILS,
    CLASS_B_PERILS,
    EPSILON_HIGH,
    EPSILON_LOW,
    METRIC_PATH,
    N_FOR_WILSON,
    PerilGateResult,
    epsilon_target,
    normalize_rate,
)
from .verdict import Verdict, apply_verdict

__all__ = [
    "CLASS_A_PERILS",
    "CLASS_B_PERILS",
    "EPSILON_HIGH",
    "EPSILON_LOW",
    "METRIC_PATH",
    "N_FOR_WILSON",
    "PerilGateResult",
    "Verdict",
    "apply_verdict",
    "epsilon_target",
    "normalize_rate",
]
