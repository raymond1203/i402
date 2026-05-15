"""Stage 1 sanity tests — paper-aligned outputs.

Run from repo root:  uv run pytest simulator/
"""

from __future__ import annotations

import pytest

from simulator import simulate_endpoint
from simulator.cache import simulate_cache
from simulator.replay import simulate_replay
from simulator.revert import simulate_revert

# ---- Attack II: replay -----------------------------------------------------


async def test_ii_replay_naive_DGR_grows_with_N():
    out = await simulate_replay("naive", 12)
    assert out["vector"] == "II"
    assert out["DGR_overall"] > 5
    p500 = next(p for p in out["points"] if p["n_replays"] == 500)
    assert p500["DGR_mean"] > 100


async def test_ii_replay_atomic_DGR_is_1():
    out = await simulate_replay("atomic", 12)
    assert out["DGR_overall"] == 1.0
    for p in out["points"]:
        assert p["DGR_mean"] == 1
        assert p["DGR_max"] == 1


async def test_ii_replay_racy_partial_overgrant():
    out = await simulate_replay("racy", 12)
    assert out["DGR_overall"] > 1


# ---- Attack III: cache -----------------------------------------------------


async def test_iii_cache_nostore_zero_leak():
    out = await simulate_cache("nostore", 200)
    assert out["vector"] == "III"
    assert out["leak_rate"] == 0


async def test_iii_cache_none_full_leak():
    out = await simulate_cache("none", 200)
    assert out["leak_rate"] == 1


async def test_iii_cache_weak_leaks_majority():
    out = await simulate_cache("weak", 200)
    assert out["leak_rate"] > 0.5


# ---- Attack I-A: revert ----------------------------------------------------


def test_ia_revert_byzantine_is_100pct():
    out = simulate_revert(
        {
            "settle_before_grant": True,
            "confirmation_depth_k": 12,
            "byzantine_facilitator_assumed": True,
        },
        2000,
        7,
    )
    assert out["vector"] == "I-A"
    assert out["RGP_k_expected"] == 1.0
    assert out["RGP_k"] == 1.0


def test_ia_revert_honest_k0_approx_5pct():
    """Paper §4.2: RGP_0 ≈ 5.18% under δ=400ms, p_reorg=0.05."""
    out = simulate_revert(
        {
            "settle_before_grant": True,
            "confirmation_depth_k": 0,
            "byzantine_facilitator_assumed": False,
        },
        20000,
        11,
    )
    assert out["RGP_k_expected"] == 0.0518
    assert abs(out["RGP_k"] - 0.0518) < 0.015


def test_ia_revert_k12_deep_ci_floor():
    out = simulate_revert(
        {
            "settle_before_grant": True,
            "confirmation_depth_k": 12,
            "byzantine_facilitator_assumed": False,
        },
        2000,
        13,
    )
    assert out["RGP_k_expected"] < 0.001
    assert out["T_gf_sec"] == 25.1


def test_ia_revert_no_settle_before_grant_collapses_to_k0():
    out = simulate_revert(
        {
            "settle_before_grant": False,
            "confirmation_depth_k": 12,
            "byzantine_facilitator_assumed": False,
        },
        2000,
        17,
    )
    assert out["RGP_k_expected"] == 0.0518


def test_ia_revert_deterministic_under_same_seed():
    cfg = {
        "settle_before_grant": True,
        "confirmation_depth_k": 3,
        "byzantine_facilitator_assumed": False,
    }
    a = simulate_revert(cfg, 1000, 42)
    b = simulate_revert(cfg, 1000, 42)
    assert a["RGP_k"] == b["RGP_k"]


# ---- End-to-end composition ------------------------------------------------


async def test_simulate_endpoint_composes_three_vectors():
    config = {
        "idempotency": "atomic",
        "cache_control": "nostore",
        "settle_before_grant": True,
        "confirmation_depth_k": 12,
        "byzantine_facilitator_assumed": False,
    }
    out = await simulate_endpoint(config, n_trials=600, seed=7)
    assert out["outcomes"]["II_replay"]["DGR_overall"] == 1.0
    assert out["outcomes"]["III_cache"]["leak_rate"] == 0
    assert out["outcomes"]["IA_revert"]["vector"] == "I-A"
    assert out["per_vector_trials"] == 200  # 600 / 3 vectors


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
