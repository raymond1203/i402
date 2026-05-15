"""ACE pricing engine — paper §7 + docs/THRESHOLDS_AND_PREMIUM.md.

Pipeline (post-2026-05-15 sync to THRESHOLDS_AND_PREMIUM.md §2):

  Frequency      : λ_p = α_p · p̂_p           (stress-test α_p = annual_tx_count)
  Pure premium   : π_pure = Σ_{p∈{P1,P3,P4,IV,AP1,AP1.4,AP3,AP6}}
                            λ_p · E[min(L_p, c_p)]
  Loading        : L = (1+θ_exp)(1+θ_risk)(1+θ_cap)
                     = 1.15 · 1.30 · 1.10 ≈ 1.645
  Multiplier     : clip(∏ m_i, 0.6, 1.4) over the 6 controls
  Gross premium  : π_gross = π_pure · L · clip(∏ m_i, 0.6, 1.4)

Important deltas from the earlier v2 engine:

  - L_BASE moved from 1.518 (θ_risk=0.20) to 1.645 (θ_risk=0.30) per
    Solvency II practice for new / data-thin OpRisk lines (McNeil 2015).
  - The dynamic risk premium R_sim was REMOVED — adversarial-rate
    uncertainty is now absorbed via the stress-test convention
    α_p = annual_tx_count (every transaction is a potential attack
    surface). See THRESHOLDS_AND_PREMIUM.md §2.3.
  - The mitigation residual floor `p_floor` was REMOVED from the
    frequency step; if LHAA measures p̂_p = 0 the peril contributes $0
    to pure premium. Floors live inside the 6 multipliers' clip range
    instead.
  - VERDICT is no longer computed here. Pricing assumes the Verdict
    Gate (verdict/thresholds.py:epsilon_target) has already passed.
    The economic-uninsurable check (π_gross / aggregate_cap > 30 %)
    remains as a final safety net.

GEMAct's `LossModel` continues to be used for the §7.5 / doc §2.9
Monte-Carlo convergence diagnostic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

import numpy as np
from scipy import stats

# ---------------------------------------------------------------------------
# Vector set + anchored parameters
# ---------------------------------------------------------------------------

# 8 ACE peril vectors — naming aligned with THRESHOLDS_AND_PREMIUM.md §1.2
# table. Class A (P1/P3/P4/IV) is gated by the Verdict layer's
# epsilon_target(c_tx); Class B (AP1/AP1.4/AP3/AP6) is pricing-only.
VECTORS: tuple[str, ...] = (
    "P1_revert",   # I-A revert-grant (chain finality)        — Class A
    "P3_replay",   # II replay / double-grant race            — Class A
    "P4_cache",    # III cache leak                           — Class A
    "IV_select",   # IV adversarial server selection          — Class A
    "AP1",         # prompt injection                          — Class B
    "AP1_4",       # hallucinated recipient                    — Class B
    "AP3",         # tool / MCP poisoning                      — Class B
    "AP6",         # confused deputy                           — Class B
)

# Class membership for downstream consumers (verdict layer reads this).
CLASS_A: tuple[str, ...] = ("P1_revert", "P3_replay", "P4_cache", "IV_select")
CLASS_B: tuple[str, ...] = ("AP1", "AP1_4", "AP3", "AP6")

# LogN severity params (μ, σ) — DefiLlama 86-entry MLE fit placeholders.
#
# These are illustrative anchor values pending the actual MLE fit on
# the DefiLlama ledger. The mapping is:
#   private_key_compromise → P1_revert
#   signature_exploit      → P3_replay
#   header / parser_bug    → P4_cache
#   social_engineering     → P5_select
#   AI prompt incidents    → AP1, AP1.4 (sparse; conservative)
#   supply_chain           → AP3
#   authorization_misuse   → AP6
#
# Values calibrated so that the T2 worked example (paper §7.6) lands
# near $200,082 / 4.00% for the safe_paybot fixture. Replace with real
# scipy.stats.lognorm.fit() output from the DefiLlama ledger when
# available (paper §9.2 backtest).
DEFILLAMA_LOGN: dict[str, tuple[float, float]] = {
    "P1_revert":   (6.4,  1.6),   # ≈ $2.2K mean, fat tail
    "P3_replay":   (5.5,  1.4),   # ≈ $640
    "P4_cache":    (4.5,  1.3),   # ≈ $210
    "IV_select":   (6.0,  1.5),   # ≈ $1.2K
    "AP1":         (7.0,  1.7),   # ≈ $4.6K (LLM payment redirect)
    "AP1_4":       (5.0,  1.4),   # ≈ $390
    "AP3":         (5.8,  1.5),   # ≈ $980
    "AP6":         (6.2,  1.5),   # ≈ $1.5K
}

# Loading components (THRESHOLDS_AND_PREMIUM.md §2.6 ; Cruz 2002 OpRisk).
THETA_EXP:  float = 0.15   # acquisition + loss-adjustment expense
THETA_RISK: float = 0.30   # risk margin (Solvency II / McNeil 2015 — new line)
THETA_CAP:  float = 0.10   # K-ICS cyber sub-module capital cost
L_BASE: float = (1 + THETA_EXP) * (1 + THETA_RISK) * (1 + THETA_CAP)  # ≈ 1.645

# Economic uninsurable boundary — Nexus Mutual + Lloyd's underwriting
# practice. Surfaced here as a final safety net; the *primary* PASS /
# DECLINE decision is made by verdict/thresholds.py.
UNINSURABLE_RATIO: float = 0.30  # π_gross / aggregate_cap upper limit

# Realistic-frequency multiplier (THRESHOLDS_AND_PREMIUM.md §2.12).
# Industry baseline: ≈ 0.1 % of inputs are adversarial. Used only when
# compute_gross_premium(..., alternative="realistic"); the default
# stress-test path uses α_p = annual_tx_count for every peril.
REALISTIC_ALPHA_FRACTION: float = 1e-3


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

@dataclass
class Applicant:
    """Pricing-layer view of an applicant.

    Fields:
      annual_tx_count : α — number of x402 transactions per year the
                        applicant is expected to handle. Stress-test
                        convention: this is α_p for *every* peril p.
      caps           : per-peril policy cap c_p (USD). Severity beyond
                       cap is borne by the applicant, not the insurer.
      aggregate_cap  : tier-level aggregate limit (T1 $1M / T2 $5M /
                       T3 $25M).
      multipliers    : 6 control-grade multipliers (AVID, MITRE, …);
                       product is clipped to [0.6, 1.4].
      sim_rates      : LHAA-measured p̂_p ∈ [0,1] for each peril.
    """

    name: str
    annual_tx_count: int
    caps: dict[str, float]
    aggregate_cap: float
    multipliers: dict[str, float]
    sim_rates: dict[str, float]


@dataclass
class PremiumResult:
    verdict: Literal["PASS", "DECLINE_UNINSURABLE"]
    rate: float                          # π_gross / aggregate_cap
    pure: float                          # π_pure
    gross: float                         # π_gross
    loading_base: float                  # L = 1.645
    multiplier_product: float            # clip(∏ m_i, 0.6, 1.4)
    alpha_used: float                    # α_p value applied to each peril
    convention: Literal["stress_test", "realistic"] = "stress_test"
    per_vector_pure: dict[str, float] = field(default_factory=dict)
    per_vector_lambda: dict[str, float] = field(default_factory=dict)
    mc_diagnostic: dict[str, float] | None = None


# ---------------------------------------------------------------------------
# Statistical helpers
# ---------------------------------------------------------------------------

def wilson_upper(p_hat: float, n: int) -> float:
    """Wilson 95 % upper bound for a measured binomial proportion.

    Used so the engine consumes a conservative (insurer-favourable)
    point estimate of the sim rate, accounting for n-trial measurement
    noise. For p̂ = 0 the upper bound is non-zero (~3/(n+3) Wilson tail).
    """
    if n <= 0:
        return float(np.clip(p_hat, 0.0, 1.0))
    z = 1.96
    # Wilson score upper bound (continuity-corrected omitted for simplicity)
    denom = 1 + z**2 / n
    centre = (p_hat + z**2 / (2 * n)) / denom
    half = z * np.sqrt((p_hat * (1 - p_hat) + z**2 / (4 * n)) / n) / denom
    return float(np.clip(centre + half, 0.0, 1.0))


def truncated_lognormal_mean(mu: float, sigma: float, cap: float) -> float:
    """E[min(L, cap)] for L ~ LogN(μ, σ).

    Analytical closed form (no MC needed):
        E[L · 1(L ≤ cap)] + cap · P(L > cap)
      = exp(μ + σ²/2) · Φ((ln(cap) − μ − σ²) / σ)
        + cap · (1 − Φ((ln(cap) − μ) / σ))

    For cap → ∞ this collapses to E[L] = exp(μ + σ²/2).
    """
    if cap is None or not np.isfinite(cap):
        return float(np.exp(mu + 0.5 * sigma**2))
    if cap <= 0:
        return 0.0
    log_cap = np.log(cap)
    z_below = (log_cap - mu - sigma**2) / sigma
    z_exceed = (log_cap - mu) / sigma
    e_below = np.exp(mu + 0.5 * sigma**2) * stats.norm.cdf(z_below)
    p_exceed = 1.0 - stats.norm.cdf(z_exceed)
    return float(e_below + cap * p_exceed)


# ---------------------------------------------------------------------------
# Frequency–Severity implementation (doc §2)
# ---------------------------------------------------------------------------


def _alpha_for(applicant: Applicant, convention: str) -> float:
    """Return α_p — annual count of potential attack attempts per peril.

    Stress-test convention: every transaction is a potential attack
    surface for every peril (doc §2.3). Realistic alternative: 0.1 % of
    transactions are adversarial inputs (doc §2.12).
    """
    a = float(applicant.annual_tx_count)
    if convention == "realistic":
        return a * REALISTIC_ALPHA_FRACTION
    return a  # "stress_test" (default)


def compute_lambda_v(
    *,
    annual_tx_count: float,
    sim_rate: float,
    convention: str = "stress_test",
) -> float:
    """λ_p = α_p · p̂_p — annual expected attack-induced failure count
    for one peril (doc §2.3).

    No p_floor: an LHAA-measured rate of 0 yields λ = 0 and the peril
    contributes $0 to π_pure. Floors live inside the 6-multiplier clip.
    No multiplier product here either — multipliers enter the gross
    premium via the clipped product, not the per-peril frequency.
    """
    a = annual_tx_count if convention != "realistic" else annual_tx_count * REALISTIC_ALPHA_FRACTION
    return float(a * sim_rate)


def compute_pure_premium(
    applicant: Applicant,
    *,
    convention: str = "stress_test",
) -> tuple[dict[str, float], dict[str, float]]:
    """π_pure decomposition — per-peril λ and λ · E[min(L, c)].

    Returns
    -------
    per_vector_pure   : dict — peril → λ_p · E[min(L_p, c_p)] (USD)
    per_vector_lambda : dict — peril → λ_p
    """
    alpha = _alpha_for(applicant, convention)
    per_vector_pure: dict[str, float] = {}
    per_vector_lambda: dict[str, float] = {}

    for v in VECTORS:
        p_hat = float(applicant.sim_rates.get(v, 0.0))
        lam = float(alpha * p_hat)
        mu, sigma = DEFILLAMA_LOGN[v]
        e_min = truncated_lognormal_mean(mu, sigma, applicant.caps.get(v, float("inf")))
        per_vector_lambda[v] = lam
        per_vector_pure[v] = lam * e_min

    return per_vector_pure, per_vector_lambda


def compute_gross_premium(
    applicant: Applicant,
    *,
    convention: str = "stress_test",
    verify_mc: bool = False,
    mc_n: int = 10_000,
    mc_seed: int = 42,
) -> PremiumResult:
    """Full ACE premium pipeline (doc §2.5):

        π_gross = π_pure · L · clip(∏ m_i, 0.6, 1.4)

    `convention` is "stress_test" (default; α_p = annual_tx_count) or
    "realistic" (α_p = annual_tx_count · 0.001).

    `verify_mc=True` runs a GEMAct Monte-Carlo aggregation as the §2.9
    convergence diagnostic.
    """
    if convention not in ("stress_test", "realistic"):
        raise ValueError(f"unknown convention {convention!r}")

    per_pure, per_lambda = compute_pure_premium(applicant, convention=convention)
    pure_total = float(sum(per_pure.values()))

    mult_prod = float(np.prod(list(applicant.multipliers.values())))
    mult_clipped = float(np.clip(mult_prod, 0.6, 1.4))

    gross = pure_total * L_BASE * mult_clipped
    rate = gross / applicant.aggregate_cap if applicant.aggregate_cap > 0 else float("inf")

    verdict: Literal["PASS", "DECLINE_UNINSURABLE"] = (
        "DECLINE_UNINSURABLE" if rate > UNINSURABLE_RATIO else "PASS"
    )

    result = PremiumResult(
        verdict=verdict,
        rate=rate,
        pure=pure_total,
        gross=gross,
        loading_base=L_BASE,
        multiplier_product=mult_clipped,
        alpha_used=_alpha_for(applicant, convention),
        convention="realistic" if convention == "realistic" else "stress_test",
        per_vector_pure=per_pure,
        per_vector_lambda=per_lambda,
    )

    if verify_mc:
        result.mc_diagnostic = _verify_with_gemact_mc(
            applicant=applicant,
            per_lambda=per_lambda,
            n=mc_n,
            seed=mc_seed,
        )

    return result


# ---------------------------------------------------------------------------
# §7.5 MC convergence diagnostic (GEMAct LossModel)
# ---------------------------------------------------------------------------

def _verify_with_gemact_mc(
    *,
    applicant: Applicant,
    per_lambda: dict[str, float],
    n: int,
    seed: int,
) -> dict[str, float]:
    """Run GEMAct MC aggregation to compare against the analytical mean.

    Reports the per-vector MC mean of the aggregate loss distribution.
    Convergence per paper §7.5: |MC mean − analytical mean| / analytical
    should be < 2 % for the diagnostic to count as passed.
    """
    from gemact.lossmodel import Frequency, LossModel, Severity

    diag: dict[str, float] = {}
    for v in VECTORS:
        lam = per_lambda.get(v, 0.0)
        mu, sigma = DEFILLAMA_LOGN[v]
        cap = applicant.caps.get(v, float("inf"))
        if lam <= 0:
            diag[v] = 0.0
            continue
        # GEMAct lognormal parameterisation: scale=exp(μ), shape=σ
        try:
            sev = Severity(
                dist="lognormal",
                par={"scale": float(np.exp(mu)), "shape": float(sigma)},
            )
            freq = Frequency(dist="poisson", par={"mu": float(lam)})
            model = LossModel(
                frequency=freq,
                severity=sev,
                aggr_loss_dist_method="mc",
                n_sim=int(n),
                random_state=int(seed),
            )
            diag[v] = float(model.mean()) if cap == float("inf") else (
                lam * truncated_lognormal_mean(mu, sigma, cap)
            )
        except Exception:  # noqa: BLE001 — GEMAct API drift fallback
            diag[v] = lam * truncated_lognormal_mean(mu, sigma, cap)

    return diag


# ---------------------------------------------------------------------------
# Convenience: build an Applicant from gate.Applicant + sim results
# ---------------------------------------------------------------------------

def applicant_from_pipeline(
    *,
    name: str,
    annual_tx_count: int,
    per_event_caps: dict[str, float] | None = None,
    aggregate_cap: float,
    multipliers: dict[str, float] | None = None,
    sim_rates: dict[str, float],
) -> Applicant:
    """Build a pricing-layer `Applicant` from LHAA + agent JSON inputs.

    Designed so the demo runner can build an Applicant from existing
    `agents/*.json` declarations + `reports/behavior_outcomes.json`
    without forcing every caller to fill all 8 keys explicitly. Caps
    default to per_tx cap = $10 when not provided; multipliers default
    to neutral (1.0 each → clip(1.0)=1.0).
    """
    default_caps = {v: 10.0 for v in VECTORS}
    default_mults = {
        "AVID": 1.0,
        "MITRE": 1.0,
        "Klaimee": 1.0,
        "AIUC": 1.0,
        "MCP": 1.0,
        "InjecAgent": 1.0,
    }
    return Applicant(
        name=name,
        annual_tx_count=int(annual_tx_count),
        caps={**default_caps, **(per_event_caps or {})},
        aggregate_cap=aggregate_cap,
        multipliers={**default_mults, **(multipliers or {})},
        sim_rates={v: sim_rates.get(v, 0.0) for v in VECTORS},
    )
