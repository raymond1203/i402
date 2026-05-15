"""ACE pricing engine — paper §7 + docs/THRESHOLDS_AND_PREMIUM.md §2.

Pipeline (post-2026-05-15 sync):

  Verdict gate (verdict/thresholds.py) → Pricing (this module)
                                          │
                                          ├─ λ_p = α · p̂_p          (eq 3a)
                                          ├─ π_pure  (eq 3)         — Σ over 8 perils
                                          ├─ L = 1.645              (§2.6)
                                          ├─ clip(∏ m_i, 0.6, 1.4)  (§2.7)
                                          └─ π_gross + econ uninsurable check

External anchors:
  - GEMAct (Cambridge, CC-BY 4.0) — collective risk LossModel + MC aggregation
  - DefiLlama hacks ledger — LogN(μ, σ) severity params via MLE fit
  - Cruz 2002 OpRisk / McNeil 2015 QRM — loading composition
"""

from .engine import (
    CLASS_A,
    CLASS_B,
    L_BASE,
    REALISTIC_ALPHA_FRACTION,
    UNINSURABLE_RATIO,
    VECTORS,
    Applicant,
    PremiumResult,
    applicant_from_pipeline,
    compute_gross_premium,
    compute_lambda_v,
    compute_pure_premium,
    truncated_lognormal_mean,
    wilson_upper,
)

__all__ = [
    "Applicant",
    "CLASS_A",
    "CLASS_B",
    "L_BASE",
    "PremiumResult",
    "REALISTIC_ALPHA_FRACTION",
    "UNINSURABLE_RATIO",
    "VECTORS",
    "applicant_from_pipeline",
    "compute_gross_premium",
    "compute_lambda_v",
    "compute_pure_premium",
    "truncated_lognormal_mean",
    "wilson_upper",
]
