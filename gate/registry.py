"""Off-band verified facts about payment facilitators.

The precondition gate consults these tables. They are *facts*, not
predictions — populated by ACE's underwriting ops via contract review,
allowlist procedures, and path-attestation. Editable: add a row when a
new facilitator passes review, remove a row when one is revoked.

For the competition demo we ship a small built-in set including one
known-good ("ace-demo-facilitator") and one known-bad
("rogue-facilitator-demo") to make pass / fail flows visible.
"""

from __future__ import annotations

# Facilitators on ACE's verified allowlist.
ALLOWLISTED_FACILITATORS: set[str] = {
    "circle-x402-mainnet",
    "circle-x402-base-sepolia",
    "ace-demo-facilitator",
}


# Per-facilitator: does the settlement contract enforce
# msg.sender == facilitator on settle()?  Closes Attack I-B
# (settlement preemption, Li et al. arXiv:2605.11781).
FACILITATOR_BOUND_SETTLEMENT: dict[str, bool] = {
    "circle-x402-mainnet": True,
    "circle-x402-base-sepolia": True,
    "ace-demo-facilitator": True,
    "rogue-facilitator-demo": False,
}


# Per-facilitator: is the X-PAYMENT carrying path TLS-secured end-to-end
# with no untrusted middleware able to inspect the header?
PAYMENT_PATH_SECURED: dict[str, bool] = {
    "circle-x402-mainnet": True,
    "circle-x402-base-sepolia": True,
    "ace-demo-facilitator": True,
    "rogue-facilitator-demo": False,
}
