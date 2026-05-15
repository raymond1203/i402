"""Stage 0 — precondition gate.

Binary admission checks. A failure here is a hard decline — the simulator
and downstream scoring never run for that applicant.
"""

from .applicant import (
    Applicant,
    BehavioralConfig,
    EndpointConfig,
    SpendingPolicy,
    Tool,
)
from .precondition_gate import GateFailure, GateResult, check_preconditions

__all__ = [
    "Applicant",
    "Tool",
    "SpendingPolicy",
    "EndpointConfig",
    "BehavioralConfig",
    "check_preconditions",
    "GateResult",
    "GateFailure",
]
