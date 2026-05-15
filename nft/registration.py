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
    audit_roots: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Return the JSON dict that the NFT's tokenURI resolves to.

    `audit_roots` carries the per-peril LHAA C3 audit-chain roots
    (peril_id → SHA-256 hex). Because the canonical identity hash
    commits the entire `ace` block, embedding the audit roots here is
    sufficient to anchor them on-chain transitively — modifying any
    post-mint trial outcome would change a peril's audit root, which
    would change the identity hash, which would invalidate the NFT.
    No Solidity change required.
    """
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
            "audit_roots": dict(audit_roots or {}),
            "paper_anchor": "arXiv:2605.11781 §6.3 (ERC-8004 complementary layer)",
            "harness_conditions": {
                "C1_determinism": "canonical_json + fixed-seed simulators",
                "C2_sandbox_isolation": "env_scrub_v1 hook + network mocking",
                "C3_audit_chain": "SHA-256 per-trial chain → audit_roots[*]",
                "C4_fixed_rule_verdict": "Li 2026 Corollary 10 AND-gate on Class A",
            },
        },
    }
