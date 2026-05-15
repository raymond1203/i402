"""Pricing engine tests — locks in docs/THRESHOLDS_AND_PREMIUM.md § 2.

Covers:
  - Loading constant L = 1.645 (Cruz 2002 OpRisk, § 2.6)
  - Frequency-severity formula λ_p = α · p̂_p (§ 2.3 stress-test convention)
  - Truncated lognormal severity E[min(L, c)]
  - Multiplier clip to [0.6, 1.4] (§ 2.7)
  - Wilson 95% upper bound monotonicity
  - Reproduction of doc § 2.10 Case A pure premium (= $113.60)
  - Realistic-frequency convention (§ 2.12) scales pure by 0.001
  - Economic uninsurable safety net at π_gross / aggregate_cap > 30%
"""

from __future__ import annotations

import math

import pytest

from pricing.engine import (
    CLASS_A,
    CLASS_B,
    L_BASE,
    REALISTIC_ALPHA_FRACTION,
    UNINSURABLE_RATIO,
    VECTORS,
    Applicant,
    applicant_from_pipeline,
    compute_gross_premium,
    compute_lambda_v,
    compute_pure_premium,
    truncated_lognormal_mean,
    wilson_upper,
)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


def test_L_base_equals_1_645():
    """Doc § 2.6: L = (1+0.15)(1+0.30)(1+0.10) ≈ 1.645."""
    assert abs(L_BASE - 1.15 * 1.30 * 1.10) < 1e-12
    assert abs(L_BASE - 1.6445) < 1e-4


def test_eight_vectors_split_into_class_a_b():
    assert len(VECTORS) == 8
    assert set(CLASS_A) | set(CLASS_B) == set(VECTORS)
    assert set(CLASS_A) & set(CLASS_B) == set()
    assert len(CLASS_A) == 4
    assert len(CLASS_B) == 4


# ---------------------------------------------------------------------------
# Statistical helpers
# ---------------------------------------------------------------------------


def test_wilson_upper_monotonic_in_p_at_fixed_n():
    n = 300
    assert wilson_upper(0.0, n) < wilson_upper(0.01, n) < wilson_upper(0.1, n)


def test_wilson_upper_tightens_as_n_grows_at_fixed_p():
    p = 0.0
    u100 = wilson_upper(p, 100)
    u1000 = wilson_upper(p, 1000)
    u50000 = wilson_upper(p, 50_000)
    assert u100 > u1000 > u50000
    assert u100 > 0.03  # ≈ 3.7 %
    assert u50000 < 1e-3  # ≈ 0.0077 %


def test_truncated_lognormal_mean_below_uncapped_mean():
    mu, sigma = 6.0, 1.5
    uncapped = math.exp(mu + 0.5 * sigma**2)
    capped = truncated_lognormal_mean(mu, sigma, 500.0)
    assert 0.0 < capped < uncapped


def test_truncated_lognormal_mean_micro_cap_saturates_to_cap():
    """When cap is much smaller than the lognormal scale, E[min(L,c)] ≈ c."""
    cap = 0.50
    e = truncated_lognormal_mean(6.0, 1.5, cap)  # E[L] ≈ $1240, cap = $0.50
    assert abs(e - cap) < 0.01


# ---------------------------------------------------------------------------
# Frequency-severity primitives
# ---------------------------------------------------------------------------


def test_lambda_v_is_alpha_times_p_hat():
    """λ_p = α · p̂_p — no p_floor, no multiplier (§ 2.3)."""
    assert compute_lambda_v(annual_tx_count=1000, sim_rate=0.01) == 10.0
    assert compute_lambda_v(annual_tx_count=3600, sim_rate=0.0) == 0.0


def test_realistic_convention_scales_alpha_by_0_001():
    lam = compute_lambda_v(annual_tx_count=10_000, sim_rate=0.01,
                           convention="realistic")
    assert lam == pytest.approx(10_000 * REALISTIC_ALPHA_FRACTION * 0.01)


# ---------------------------------------------------------------------------
# Doc § 2.10 worked-example reproduction
# ---------------------------------------------------------------------------


def _doc_case_a() -> Applicant:
    """Doc § 2.10 Case A (Micro paybot).

    α = 3600, c_tx = $0.50 ⇒ every peril cap = $0.50 (so E[min(L,c)] ≈ $0.50).
    """
    return Applicant(
        name="micro_paybot",
        annual_tx_count=3600,
        caps={v: 0.50 for v in VECTORS},
        aggregate_cap=5000,
        multipliers={
            "AVID": 0.95, "MITRE": 0.95, "Klaimee": 0.95,
            "AIUC": 1.0, "MCP": 1.0, "InjecAgent": 1.0,
        },
        sim_rates={
            "P1_revert": 0.0027, "P3_replay": 0.0004,
            "P4_cache": 0.00001, "IV_select": 0.002,
            "AP1": 0.018, "AP1_4": 0.025, "AP3": 0.004, "AP6": 0.011,
        },
    )


def test_case_a_pure_premium_matches_doc():
    """Doc § 2.10 Case A: π_pure = $113.60 to the cent."""
    r = compute_gross_premium(_doc_case_a())
    assert abs(r.pure - 113.60) < 0.05  # nearest cent
    assert r.verdict == "PASS"


def test_case_a_gross_premium_is_loading_times_pure_times_clip():
    r = compute_gross_premium(_doc_case_a())
    # M_clip with these multipliers = (0.95^3 · 1.0^3) ≈ 0.857
    expected_clip = 0.95 ** 3
    assert abs(r.multiplier_product - expected_clip) < 1e-9
    assert abs(r.gross - r.pure * L_BASE * r.multiplier_product) < 1e-6


def test_case_a_per_peril_lambda_correct():
    r = compute_gross_premium(_doc_case_a())
    assert r.per_vector_lambda["P1_revert"] == pytest.approx(3600 * 0.0027)
    assert r.per_vector_lambda["AP1"] == pytest.approx(3600 * 0.018)


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


def test_zero_sim_rate_yields_zero_pure_for_that_peril():
    a = Applicant(
        name="t", annual_tx_count=1000,
        caps={v: 10.0 for v in VECTORS}, aggregate_cap=1e6,
        multipliers={
            "AVID": 1.0, "MITRE": 1.0, "Klaimee": 1.0,
            "AIUC": 1.0, "MCP": 1.0, "InjecAgent": 1.0,
        },
        sim_rates={v: 0.0 for v in VECTORS},
    )
    r = compute_gross_premium(a)
    assert r.pure == 0.0
    assert r.gross == 0.0
    assert r.verdict == "PASS"  # not uninsurable when free


def test_multiplier_product_is_clipped_at_lower_bound():
    """6 multipliers all at 0.5 would give 0.0156, clipped to 0.6."""
    a = Applicant(
        name="t", annual_tx_count=1000,
        caps={v: 10.0 for v in VECTORS}, aggregate_cap=1e6,
        multipliers={
            "AVID": 0.5, "MITRE": 0.5, "Klaimee": 0.5,
            "AIUC": 0.5, "MCP": 0.5, "InjecAgent": 0.5,
        },
        sim_rates={v: 0.01 for v in VECTORS},
    )
    r = compute_gross_premium(a)
    assert r.multiplier_product == 0.6


def test_multiplier_product_is_clipped_at_upper_bound():
    """6 multipliers at 1.3 give 4.83, clipped to 1.4."""
    a = Applicant(
        name="t", annual_tx_count=1000,
        caps={v: 10.0 for v in VECTORS}, aggregate_cap=1e6,
        multipliers={
            "AVID": 1.3, "MITRE": 1.3, "Klaimee": 1.3,
            "AIUC": 1.3, "MCP": 1.3, "InjecAgent": 1.3,
        },
        sim_rates={v: 0.01 for v in VECTORS},
    )
    r = compute_gross_premium(a)
    assert r.multiplier_product == 1.4


def test_economic_uninsurable_triggered_when_gross_over_30pct_of_cap():
    """Tiny aggregate cap forces rate > 30 % → DECLINE_UNINSURABLE."""
    a = Applicant(
        name="t", annual_tx_count=1_000_000,
        caps={v: 1000.0 for v in VECTORS}, aggregate_cap=100,
        multipliers={
            "AVID": 1.0, "MITRE": 1.0, "Klaimee": 1.0,
            "AIUC": 1.0, "MCP": 1.0, "InjecAgent": 1.0,
        },
        sim_rates={v: 0.05 for v in VECTORS},
    )
    r = compute_gross_premium(a)
    assert r.rate > UNINSURABLE_RATIO
    assert r.verdict == "DECLINE_UNINSURABLE"


def test_realistic_convention_reduces_pure_by_1000x():
    """Doc § 2.12: Case A realistic ≈ 0.1 % of stress-test pure."""
    a = _doc_case_a()
    stress = compute_gross_premium(a, convention="stress_test")
    realistic = compute_gross_premium(a, convention="realistic")
    # 1000× drop in α → ~1000× drop in pure (severity identical)
    assert abs(realistic.pure / stress.pure - 1e-3) < 1e-6
    assert realistic.convention == "realistic"


def test_unknown_convention_raises():
    with pytest.raises(ValueError, match="unknown convention"):
        compute_gross_premium(_doc_case_a(), convention="bogus")


# ---------------------------------------------------------------------------
# applicant_from_pipeline convenience
# ---------------------------------------------------------------------------


def test_applicant_from_pipeline_fills_defaults():
    a = applicant_from_pipeline(
        name="t",
        annual_tx_count=5000,
        aggregate_cap=1_000_000,
        sim_rates={"P1_revert": 0.001},
    )
    assert a.caps["P1_revert"] == 10.0   # default cap
    assert a.caps["AP1"] == 10.0
    assert a.multipliers["AVID"] == 1.0
    assert all(a.sim_rates[v] == 0.001 if v == "P1_revert" else
               a.sim_rates[v] == 0.0 for v in VECTORS)


def test_applicant_from_pipeline_overrides_propagate():
    a = applicant_from_pipeline(
        name="t",
        annual_tx_count=5000,
        per_event_caps={"P1_revert": 500.0},
        aggregate_cap=1_000_000,
        multipliers={"AVID": 0.8},
        sim_rates={"P1_revert": 0.001, "AP1": 0.05},
    )
    assert a.caps["P1_revert"] == 500.0
    assert a.caps["AP1"] == 10.0  # default kept for un-overridden
    assert a.multipliers["AVID"] == 0.8
    assert a.multipliers["MITRE"] == 1.0  # default kept
