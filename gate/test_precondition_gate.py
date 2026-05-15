"""Sanity tests for Stage 0 precondition gate.

Run from repo root:  uv run pytest gate/
"""

from __future__ import annotations

from gate.applicant import (
    Applicant,
    BehavioralConfig,
    EndpointConfig,
    SpendingPolicy,
    Tool,
)
from gate.precondition_gate import check_preconditions


def make_applicant(**overrides) -> Applicant:
    """A clean applicant that passes every check; tests apply targeted overrides."""
    defaults = dict(
        agent_name="test_agent",
        model="claude-sonnet-4-6",
        system_prompt="You are a careful payment agent.",
        tools=[Tool(name="pay", schema={"type": "object"})],
        wallet_address="0x" + "0" * 40,
        spending_policy=SpendingPolicy(daily_cap_usd=100.0, per_tx_cap_usd=10.0),
        facilitator="ace-demo-facilitator",
        endpoint_config=EndpointConfig(
            payment_encoding="eip712",
            timestamp_window_enforced=True,
            pay_id_dedup_window_ttl_sec=300,
            idempotency="atomic",
            resource_id_binding=True,
            settle_before_grant=True,
            confirmation_depth_k=12,
            cache_control="nostore",
            byzantine_facilitator_assumed=False,
        ),
        behavioral_config=BehavioralConfig(
            discovery_method="hardcoded",
            metadata_validation="strict",
            prompt_injection_guardrail="strong",
            sdk_family="typescript-coinbase",
            monitoring="full",
        ),
    )
    defaults.update(overrides)
    return Applicant(**defaults)


def test_clean_applicant_passes():
    result = check_preconditions(make_applicant())
    assert result.passed
    assert result.failures == []


def test_unknown_facilitator_fails_all_three_facilitator_checks():
    result = check_preconditions(make_applicant(facilitator="unknown-rail"))
    assert not result.passed
    checks = {f.check for f in result.failures}
    assert "facilitator_bound_settlement" in checks
    assert "facilitator_allowlisted" in checks
    assert "payment_path_secured" in checks


def test_known_rogue_facilitator_fails_binding_and_path():
    # rogue-facilitator-demo is in the binding map but with value False
    # AND is not in the allowlist.
    result = check_preconditions(make_applicant(facilitator="rogue-facilitator-demo"))
    assert not result.passed
    checks = {f.check for f in result.failures}
    assert "facilitator_bound_settlement" in checks
    assert "facilitator_allowlisted" in checks
    assert "payment_path_secured" in checks


def test_missing_wallet_fails():
    result = check_preconditions(make_applicant(wallet_address=""))
    assert not result.passed
    assert any(f.check == "wallet_declared" for f in result.failures)


def test_whitespace_wallet_fails():
    result = check_preconditions(make_applicant(wallet_address="   "))
    assert not result.passed
    assert any(f.check == "wallet_declared" for f in result.failures)


def test_zero_daily_cap_fails():
    result = check_preconditions(
        make_applicant(spending_policy=SpendingPolicy(daily_cap_usd=0.0, per_tx_cap_usd=10.0))
    )
    assert not result.passed
    assert any(f.check == "spending_cap_declared" for f in result.failures)


def test_negative_per_tx_cap_fails():
    result = check_preconditions(
        make_applicant(spending_policy=SpendingPolicy(daily_cap_usd=100.0, per_tx_cap_usd=-1.0))
    )
    assert not result.passed
    assert any(f.check == "spending_cap_declared" for f in result.failures)


def test_none_spending_policy_fails():
    result = check_preconditions(make_applicant(spending_policy=None))
    assert not result.passed
    assert any(f.check == "spending_cap_declared" for f in result.failures)


def test_empty_model_fails():
    result = check_preconditions(make_applicant(model=""))
    assert not result.passed
    assert any(f.check == "model_declared" for f in result.failures)


def test_empty_system_prompt_fails():
    result = check_preconditions(make_applicant(system_prompt="   "))
    assert not result.passed
    assert any(f.check == "system_prompt_declared" for f in result.failures)


def test_no_tools_fails():
    result = check_preconditions(make_applicant(tools=[]))
    assert not result.passed
    assert any(f.check == "tools_declared" for f in result.failures)


def test_multiple_failures_accumulate():
    result = check_preconditions(
        make_applicant(
            wallet_address="",
            model="",
            tools=[],
        )
    )
    assert not result.passed
    checks = {f.check for f in result.failures}
    assert checks == {"wallet_declared", "model_declared", "tools_declared"}


def test_summary_renders_human_readable():
    result = check_preconditions(make_applicant(facilitator="unknown-rail"))
    text = result.summary()
    assert text.startswith("DECLINE")
    assert "facilitator_bound_settlement" in text
    assert "→" in text  # remediation arrow


def test_missing_endpoint_config_fails():
    result = check_preconditions(make_applicant(endpoint_config=None))
    assert not result.passed
    assert any(f.check == "endpoint_config_declared" for f in result.failures)


def test_missing_behavioral_config_fails():
    result = check_preconditions(make_applicant(behavioral_config=None))
    assert not result.passed
    assert any(f.check == "behavioral_config_declared" for f in result.failures)


def test_byzantine_facilitator_self_disclosure_declines():
    """Paper Table 1: Byzantine facilitator ⇒ RGP_k = 100% ⇒ uninsurable."""
    cfg = EndpointConfig(
        payment_encoding="eip712",
        timestamp_window_enforced=True,
        pay_id_dedup_window_ttl_sec=300,
        idempotency="atomic",
        resource_id_binding=True,
        settle_before_grant=True,
        confirmation_depth_k=12,
        cache_control="nostore",
        byzantine_facilitator_assumed=True,
    )
    result = check_preconditions(make_applicant(endpoint_config=cfg))
    assert not result.passed
    assert any(f.check == "byzantine_facilitator_disclosure" for f in result.failures)
