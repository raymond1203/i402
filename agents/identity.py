"""Canonical agent identity hashing.

Any non-trivial change to the Applicant declaration — model, system
prompt, tool list, wallet, spending policy, facilitator,
endpoint_config, behavioral_config — yields a different hash. The NFT
minted in Stage 4 binds to this hash; mutation post-mint invalidates
coverage.

The serialization is cross-language canonical so a Node.js mint script
and the Python pipeline produce identical hashes:
  - keys sorted lexicographically
  - no whitespace between tokens
  - UTF-8, no ASCII escaping
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
from typing import Any

from gate.applicant import Applicant


def canonical_json(obj: Any) -> str:
    """JSON serialization that is byte-identical across Python and Node."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def identity_payload(applicant: Applicant) -> dict[str, Any]:
    """The dict that gets hashed. Exposed for debugging and for the
    ERC-8004 registration JSON to include audit-friendly subhashes.
    """
    if applicant.spending_policy is None:
        raise ValueError("spending_policy must be set to compute identity hash")
    if applicant.endpoint_config is None:
        raise ValueError("endpoint_config must be set to compute identity hash")
    if applicant.behavioral_config is None:
        raise ValueError("behavioral_config must be set to compute identity hash")

    return {
        "type": "ace.AgentIdentity.v1",
        "agent_name": applicant.agent_name,
        "model": applicant.model,
        "system_prompt_sha256": _sha256_hex(applicant.system_prompt),
        "tools": [
            {
                "name": t.name,
                "schema_sha256": _sha256_hex(canonical_json(t.schema)),
            }
            for t in applicant.tools
        ],
        "wallet_address": applicant.wallet_address,
        "spending_policy": dataclasses.asdict(applicant.spending_policy),
        "facilitator": applicant.facilitator,
        "endpoint_config": dataclasses.asdict(applicant.endpoint_config),
        "behavioral_config": dataclasses.asdict(applicant.behavioral_config),
    }


def compute_identity_hash(applicant: Applicant) -> str:
    """Canonical SHA-256 of the full Applicant declaration. Hex with 0x prefix."""
    return "0x" + _sha256_hex(canonical_json(identity_payload(applicant)))
