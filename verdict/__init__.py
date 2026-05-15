"""Stage 3 — rule-based verdict layer.

Takes Stage 1 protocol outcomes + (optional) Stage 2 behavioral outcomes
per agent, applies paper-anchored thresholds, emits PASS / CONDITIONAL /
DECLINE plus the list of failed vectors.

No ML — the user explicitly chose option "A" on 2026-05-14: with the
full simulation in hand, a thresholded rule is sufficient.
"""

from .thresholds import THRESHOLDS, Severity
from .verdict import VectorVerdict, Verdict, apply_verdict

__all__ = ["THRESHOLDS", "Severity", "VectorVerdict", "Verdict", "apply_verdict"]
