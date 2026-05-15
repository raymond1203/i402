"""Stage 1 — protocol simulator.

Generalizes the seed scripts attack2_replay.js + attack3_cache.js into
Python implementations that probe an endpoint configured per the
applicant's `endpoint_config` and produce paper-aligned outcomes
(DGR, leak_rate, RGP_k, T_gf_sec).

Paper anchor: Li et al. "Five Attacks on x402 Agentic Payment Protocol"
arXiv:2605.11781.
"""

from .cache import simulate_cache
from .replay import simulate_replay
from .revert import simulate_revert
from .simulate_endpoint import simulate_endpoint

__all__ = ["simulate_replay", "simulate_cache", "simulate_revert", "simulate_endpoint"]
