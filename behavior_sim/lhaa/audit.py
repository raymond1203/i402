"""C3 audit chain — SHA-256 per-trial chain with canonical-JSON inputs.

Each LHAA module accumulates `TrialOutcome`s into an `AuditChain`. The
chain is initialised with a zero-hash prev; every `append()` computes
`SHA-256(prev || canonical_json(trial))` and replaces prev. The final
`root()` is the last hash in the chain, which is what gets surfaced on
`behavior_outcomes.json["<agent>"]["<peril>"]["audit_root"]` and
ultimately committed via the tokenURI JSON's `ace.audit_root` field —
since `identity_hash = SHA-256(canonical_json(applicant + ace_block))`,
modifying any trial outcome after the fact would mutate the audit root,
mutate the ace block, mutate the identity hash, and invalidate the NFT.

That cryptographic property is the C3 guarantee: even though the chain
itself sits off-chain, its integrity is anchored on Sepolia through the
already-deployed ACEAgentIdentity NFT (tokenId=1).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any

from .hooks import TrialOutcome


def canonical_json(obj: Any) -> str:
    """Deterministic JSON serialisation (sorted keys, no whitespace,
    no NaN). Mirrors `agents/identity.py:canonical_json` semantics so
    audit_root → identity_hash composition stays consistent.
    """
    return json.dumps(
        obj,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
        default=_fallback,
    )


def _fallback(o: Any) -> Any:
    """Convert non-JSON-native objects to JSON-friendly forms."""
    if hasattr(o, "__dataclass_fields__"):
        from dataclasses import asdict

        return asdict(o)
    if hasattr(o, "isoformat"):
        return o.isoformat()
    return str(o)


_ZERO = "0" * 64


@dataclass
class AuditChain:
    """Append-only SHA-256 chain of trial outcomes."""

    _prev: str = _ZERO
    _entries: list[dict[str, Any]] = field(default_factory=list)

    def append(self, outcome: TrialOutcome) -> str:
        payload = {
            "peril_id": outcome.peril_id,
            "trial_idx": outcome.trial_idx,
            "label": outcome.label,
            "rate_contribution": outcome.rate_contribution,
            "reason": outcome.reason,
            "audit_payload": outcome.audit_payload,
        }
        body = canonical_json(payload)
        h = hashlib.sha256((self._prev + body).encode("utf-8")).hexdigest()
        self._entries.append({"prev": self._prev, "body": body, "hash": h})
        self._prev = h
        return h

    def root(self) -> str:
        return self._prev

    def __len__(self) -> int:
        return len(self._entries)

    def entries(self) -> list[dict[str, Any]]:
        """Return the chain entries for audit replay. Caller-owned copy."""
        return [dict(e) for e in self._entries]

    @classmethod
    def verify(cls, entries: list[dict[str, Any]]) -> str:
        """Re-derive the root hash from serialised entries; raise on
        mismatch. Used by judges / auditors who hold the offline chain
        and want to confirm it produces a given root.
        """
        prev = _ZERO
        for e in entries:
            h = hashlib.sha256((prev + e["body"]).encode("utf-8")).hexdigest()
            if h != e["hash"]:
                raise ValueError(
                    f"audit chain integrity broken at entry {e}: derived {h}"
                )
            prev = h
        return prev
