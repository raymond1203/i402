"""Stage 4 NFT script tests — registration JSON + identity-hash bytes.

Network-touching paths (deploy/mint/verify) are exercised indirectly
via the Foundry suite in contracts/test/. Here we cover the pure-Python
glue: registration JSON shape, hex/bytes round-trip, and that the
identity hash is what gets fed to the chain.

Run from repo root:  uv run pytest nft/
"""

from __future__ import annotations

from agents import load_agent
from agents.identity import compute_identity_hash
from nft.registration import build_registration_json


def test_registration_json_has_eip8004_type():
    a = load_agent("safe_paybot")
    reg = build_registration_json(a)
    assert reg["type"] == "https://eips.ethereum.org/EIPS/eip-8004#registration-v1"
    assert reg["name"] == "safe_paybot"
    assert reg["x402Support"] is True


def test_registration_carries_identity_hash():
    a = load_agent("safe_paybot")
    reg = build_registration_json(a)
    h = compute_identity_hash(a)
    assert reg["ace"]["identity_hash"] == h
    assert reg["ace"]["identity_payload"]["type"] == "ace.AgentIdentity.v1"


def test_registration_verdict_default_is_PASS():
    a = load_agent("safe_paybot")
    reg = build_registration_json(a)
    assert reg["ace"]["verdict"] == "PASS"


def test_registration_paper_anchor_present():
    a = load_agent("safe_paybot")
    reg = build_registration_json(a)
    assert "arXiv:2605.11781" in reg["ace"]["paper_anchor"]


def test_identity_hash_roundtrips_to_bytes32():
    """The chain-side function expects bytes32. Make sure the conversion
    Python uses to feed the contract is bijective."""
    a = load_agent("safe_paybot")
    h_hex = compute_identity_hash(a)
    h_bytes = bytes.fromhex(h_hex[2:])
    assert len(h_bytes) == 32
    assert "0x" + h_bytes.hex() == h_hex


def test_registration_changes_on_agent_mutation():
    a = load_agent("safe_paybot")
    reg_before = build_registration_json(a)
    a.system_prompt = a.system_prompt + " "
    reg_after = build_registration_json(a)
    assert reg_before["ace"]["identity_hash"] != reg_after["ace"]["identity_hash"]
