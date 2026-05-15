"""Tests for the three demo agents — schema validity, gate behavior,
identity-hash sensitivity.

Run from repo root:  uv run pytest agents/
"""

from __future__ import annotations

from agents import KNOWN_AGENTS, load_agent, load_all_agents
from agents.identity import compute_identity_hash, identity_payload
from gate.precondition_gate import check_preconditions


def test_all_three_agents_load():
    agents = load_all_agents()
    assert set(agents.keys()) == set(KNOWN_AGENTS)


def test_safe_paybot_passes_gate():
    """SafePayBot is the ideal — must clear every Stage 0 check."""
    applicant = load_agent("safe_paybot")
    result = check_preconditions(applicant)
    assert result.passed, f"SafePayBot failed gate: {result.summary()}"


def test_mid_paybot_passes_gate():
    """MidPayBot has weaker config but must still clear Stage 0; failures
    surface later in Stage 1/2 simulation, not at the gate."""
    applicant = load_agent("mid_paybot")
    result = check_preconditions(applicant)
    assert result.passed, f"MidPayBot failed gate: {result.summary()}"


def test_vuln_paybot_passes_gate():
    """VulnPayBot is the audit's weakest profile but uses ace-demo-facilitator
    and declares the required fields, so it MUST clear Stage 0 — the demo
    relies on Stage 1+2 catching its failures, not the gate."""
    applicant = load_agent("vuln_paybot")
    result = check_preconditions(applicant)
    assert result.passed, f"VulnPayBot failed gate: {result.summary()}"


def test_endpoint_configs_match_calibration_table():
    """Lock in the paper-anchored calibration so unintended edits to the
    JSON files surface as test failures."""
    safe = load_agent("safe_paybot").endpoint_config
    assert safe.idempotency == "atomic"
    assert safe.cache_control == "nostore"
    assert safe.settle_before_grant is True
    assert safe.confirmation_depth_k == 12

    mid = load_agent("mid_paybot").endpoint_config
    assert mid.idempotency == "racy"
    assert mid.cache_control == "weak"
    assert mid.confirmation_depth_k == 0

    vuln = load_agent("vuln_paybot").endpoint_config
    assert vuln.idempotency == "naive"
    assert vuln.cache_control == "none"
    assert vuln.settle_before_grant is False
    assert vuln.resource_id_binding is False


def test_identity_hash_is_deterministic():
    a1 = load_agent("safe_paybot")
    a2 = load_agent("safe_paybot")
    assert compute_identity_hash(a1) == compute_identity_hash(a2)


def test_identity_hash_changes_on_system_prompt_edit():
    a = load_agent("safe_paybot")
    h_before = compute_identity_hash(a)
    a.system_prompt = a.system_prompt + " "  # single trailing space
    h_after = compute_identity_hash(a)
    assert h_before != h_after, "identity hash MUST flip on any prompt change"


def test_identity_hash_changes_on_tool_schema_edit():
    a = load_agent("safe_paybot")
    h_before = compute_identity_hash(a)
    a.tools[0].schema["properties"]["amount_usd"]["maximum"] = 100
    h_after = compute_identity_hash(a)
    assert h_before != h_after


def test_identity_hash_changes_on_wallet_swap():
    a = load_agent("safe_paybot")
    h_before = compute_identity_hash(a)
    a.wallet_address = "0x" + "a" * 40
    h_after = compute_identity_hash(a)
    assert h_before != h_after


def test_identity_hash_changes_on_endpoint_config_tweak():
    a = load_agent("safe_paybot")
    h_before = compute_identity_hash(a)
    a.endpoint_config.confirmation_depth_k = 6
    h_after = compute_identity_hash(a)
    assert h_before != h_after


def test_three_agents_have_distinct_hashes():
    hashes = {name: compute_identity_hash(load_agent(name)) for name in KNOWN_AGENTS}
    assert len(set(hashes.values())) == 3


def test_identity_payload_contains_required_fields():
    payload = identity_payload(load_agent("safe_paybot"))
    assert payload["type"] == "ace.AgentIdentity.v1"
    assert payload["agent_name"] == "safe_paybot"
    assert payload["model"].startswith("claude")
    assert "system_prompt_sha256" in payload
    assert "tools" in payload and len(payload["tools"]) >= 1
    assert all("schema_sha256" in t for t in payload["tools"])
    assert "endpoint_config" in payload
    assert "behavioral_config" in payload
