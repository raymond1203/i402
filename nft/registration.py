"""Build the ERC-8004 registration JSON that the NFT's tokenURI points to.

Per EIP-8004's `registration-v1` schema (see ToolSearch fetch results),
the JSON must include `type`, `name`, `description`, `image`, and may
carry custom fields like our `ace` block holding the identity hash and
underwriting summary.
"""

from __future__ import annotations

from typing import Any

from agents.identity import compute_identity_hash, identity_payload
from gate.applicant import Applicant


def build_registration_json(
    applicant: Applicant,
    *,
    verdict: str = "PASS",
    outcome_summary_uri: str | None = None,
    underwritten_at_iso: str | None = None,
) -> dict[str, Any]:
    """Return the JSON dict that the NFT's tokenURI resolves to."""
    return {
        "type": "https://eips.ethereum.org/EIPS/eip-8004#registration-v1",
        "name": applicant.agent_name,
        "description": (
            f"ACE-underwritten x402 payment agent ({applicant.model}). "
            "This certificate binds to the agent's canonical identity hash; "
            "any modification to the agent's declaration invalidates this NFT."
        ),
        "image": "",
        "x402Support": True,
        "active": True,
        "supportedTrust": ["crypto-economic"],
        "ace": {
            "identity_hash": compute_identity_hash(applicant),
            "identity_payload": identity_payload(applicant),
            "verdict": verdict,
            "outcome_summary_uri": outcome_summary_uri or "",
            "underwritten_at": underwritten_at_iso or "",
            "paper_anchor": "arXiv:2605.11781 §6.3 (ERC-8004 complementary layer)",
        },
    }
