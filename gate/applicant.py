"""Applicant data model — what an AI-agent operator submits to ACE.

Carries every field the precondition gate, simulators, and ERC-8004
identity-hash binding need. Keep field names stable: the canonical-JSON
serialization of an `Applicant` IS the input to the identity hash, so
renaming a field invalidates all previously-minted NFT certificates.

Field source mapping (paper anchor: Li et al. arXiv:2605.11781):
  Top-level + spending_policy ........ baseline insurability (Stage 0)
  facilitator ........................ Stage 0 + Attack I-B (M2)
  endpoint_config .................... Stage 1 simulator inputs
                                       (M1, M3, M4, M5 properties)
  behavioral_config .................. Stage 2 simulator inputs
                                       (M6 + agent_payment_risks.md §1–§7)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


@dataclass
class Tool:
    name: str
    schema: dict  # JSON Schema for the tool's input arguments


@dataclass
class SpendingPolicy:
    daily_cap_usd: float
    per_tx_cap_usd: float


@dataclass
class EndpointConfig:
    """Server-side payment-handling properties — Stage 1 simulator inputs.

    Maps directly to paper mitigations M1, M3, M4, M5.
    """

    # M1 — canonical encoding and freshness
    payment_encoding: Literal["eip712", "raw_json", "base64"] = "raw_json"
    timestamp_window_enforced: bool = False
    pay_id_dedup_window_ttl_sec: int = 0

    # M3 — single-use grants and resource binding
    idempotency: Literal["atomic", "racy", "naive"] = "naive"
    resource_id_binding: bool = False

    # M4 — two-phase settlement + k-confirmation gating
    settle_before_grant: bool = False
    confirmation_depth_k: int = 0

    # M5 — cache and header hygiene
    cache_control: Literal["nostore", "weak", "none"] = "none"

    # Byzantine facilitator self-disclosure. True ⇒ RGP_k = 1.0 (Table 1).
    byzantine_facilitator_assumed: bool = False


@dataclass
class BehavioralConfig:
    """Agent-side decision-making properties — Stage 2 simulator inputs.

    Maps to paper M6 (server-selection defenses) and the LLM-side risk
    categories in agent_payment_risks.md (prompt injection, memory
    poisoning, tool poisoning, confused deputy, etc).
    """

    # M6 — server-selection defenses (Attack IV surface)
    discovery_method: Literal["hardcoded", "bazaar", "registry", "none"] = "none"
    metadata_validation: Literal["strict", "lax", "none"] = "none"

    # agent_payment_risks.md §1
    prompt_injection_guardrail: Literal["strong", "weak", "none"] = "none"

    # SDK family from paper Table 5 audit — calibration anchor
    sdk_family: Literal[
        "typescript-coinbase",
        "python-thirdparty",
        "rust-thirdparty",
        "custom",
    ] = "custom"

    # Operational monitoring level
    monitoring: Literal["full", "partial", "none"] = "none"


@dataclass
class Applicant:
    agent_name: str  # demo handle, e.g. "safe_paybot"
    model: str  # LLM id, e.g. "claude-sonnet-4-6"
    system_prompt: str  # full system prompt text
    tools: list[Tool] = field(default_factory=list)
    wallet_address: str = ""
    spending_policy: SpendingPolicy | None = None
    facilitator: str = ""  # facilitator handle, looked up in gate.registry
    endpoint_config: EndpointConfig | None = None
    behavioral_config: BehavioralConfig | None = None
