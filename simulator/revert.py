"""Attack I-A — Revert-Grant mini-simulator.

Paper anchor: Li et al. arXiv:2605.11781 §4.2 + Theorem 7 + Corollary 10.
    RGP_k ≥ p_reorg · Pr[T_inc + k·T_b > T_verify + δ]

We do not reproduce the full Hardhat reorg-injection harness here; that
would be a separate testbed. Instead we sample paper-calibrated RGP_k
values directly via deterministic Bernoulli trials, and report
`is_mini_sim=true` so the model card never claims this is an
independent measurement — it is paper-anchored re-sampling.
"""

from __future__ import annotations

import hashlib
import random
from typing import Any

# k → RGP_k, calibrated to paper §4.2 + Fig 6
#   k=0 honest:  5.18%   (paper §4.2, δ=400ms p_reorg=0.05)
#   k=3 honest:  CI floor (~0.5%)
#   k=6 honest:  deeper floor
#   k=12 honest: deep floor (paper recommends k=12 for value > $10)
#   Byzantine facilitator: 100% (paper Table 1)
RGP_K_HONEST: dict[int, float] = {
    0: 0.0518,
    1: 0.025,
    2: 0.012,
    3: 0.005,
    6: 0.001,
    12: 0.0001,
}

# k → T_gf (grant-to-finality time in seconds), Base L2 T_b ≈ 2s.
#   paper §6.1: k=3 → ~6s,  k=12 → 25.1s
T_GF_SEC: dict[int, float] = {
    0: 0.3,
    1: 2.3,
    3: 6.0,
    6: 12.3,
    12: 25.1,
}


def _lookup_or_interp(table: dict[int, float], k: int) -> float:
    if k in table:
        return table[k]
    keys = sorted(table.keys())
    if k <= keys[0]:
        return table[keys[0]]
    if k >= keys[-1]:
        return table[keys[-1]]
    lo, hi = keys[0], keys[-1]
    for i in range(len(keys) - 1):
        if keys[i] <= k <= keys[i + 1]:
            lo, hi = keys[i], keys[i + 1]
            break
    t = (k - lo) / (hi - lo)
    return table[lo] * (1 - t) + table[hi] * t


def _expected_rgp(k: int, settle_before_grant: bool, byzantine: bool) -> float:
    if byzantine:
        return 1.0
    # M4 broken (no reserve-then-settle) collapses to k=0 risk regardless of k.
    k_eff = k if settle_before_grant else 0
    return _lookup_or_interp(RGP_K_HONEST, k_eff)


def _seeded_rng(seed: Any) -> random.Random:
    """Deterministic RNG keyed by an arbitrary seed token."""
    digest = hashlib.sha256(str(seed).encode("utf-8")).digest()
    seed_int = int.from_bytes(digest[:8], "little")
    return random.Random(seed_int)


def simulate_revert(config: dict, trial_budget: int, seed: Any) -> dict:
    """Run the I-A mini-sim against an endpoint config.

    config keys consumed:
      - settle_before_grant: bool
      - confirmation_depth_k: int
      - byzantine_facilitator_assumed: bool (optional, defaults to False)
    """
    k = int(config["confirmation_depth_k"])
    settle = bool(config["settle_before_grant"])
    byz = bool(config.get("byzantine_facilitator_assumed", False))
    expected = _expected_rgp(k, settle, byz)
    t_gf = _lookup_or_interp(T_GF_SEC, k if settle else 0)
    rng = _seeded_rng(f"revert:{byz}:{settle}:{k}:{seed}")

    reverts = sum(1 for _ in range(trial_budget) if rng.random() < expected)

    return {
        "vector": "I-A",
        "is_mini_sim": True,
        "paper_anchor": "arXiv:2605.11781 §4.2 / Theorem 7 / Corollary 10",
        "config": {
            "settle_before_grant": settle,
            "confirmation_depth_k": k,
            "byzantine_facilitator_assumed": byz,
        },
        "RGP_k": round(reverts / trial_budget, 6),
        "RGP_k_expected": round(expected, 6),
        "T_gf_sec": round(t_gf, 2),
        "reverts": reverts,
        "trials": trial_budget,
    }
