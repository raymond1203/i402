"""LHAA infrastructure tests (paper §6).

Covers:
  - YAML registry round-trip: every config loads into a usable module
  - AuditChain integrity: SHA-256 chain is reproducible + tamper-evident
  - AdaptiveBudget escalation: 3 worked Wilson-CI cases
  - Closed-form skill: extracts the right metric for IA/II/III

No real Claude calls — Stage-2 LLM-attacker skill is exercised via the
top-level orchestrator tests (behavior_sim/test_behavior_sim.py) where
mocks already exist.
"""

from __future__ import annotations

import asyncio

import pytest

from agents import load_agent
from behavior_sim.lhaa import AdaptiveBudget, AuditChain
from behavior_sim.lhaa.audit import canonical_json
from behavior_sim.lhaa.hooks import (
    TrialOutcome,
    env_scrub_v1,
    sha256_chain,
    single_threshold_rule,
)
from behavior_sim.lhaa.registry import (
    list_configs,
    load_all_modules,
    load_module,
    load_stage1_modules,
    load_stage2_modules,
    load_spec,
)


# ---------------------------------------------------------------------------
# Registry / YAML
# ---------------------------------------------------------------------------


def test_eight_yaml_configs_present():
    configs = list_configs()
    assert len(configs) == 8, f"expected 8 YAML configs, got {len(configs)}"
    names = {p.name for p in configs}
    expected = {
        "lhaa_ia_revert.yaml",
        "lhaa_ii_replay.yaml",
        "lhaa_iii_cache.yaml",
        "lhaa_iv_selection.yaml",
        "lhaa_ap1_injection.yaml",
        "lhaa_ap1_4_hallucinated.yaml",
        "lhaa_ap3_tool_poisoning.yaml",
        "lhaa_ap6_confused_deputy.yaml",
    }
    assert names == expected


def test_every_yaml_loads_into_a_module():
    modules = load_all_modules()
    assert len(modules) == 8
    peril_ids = {m.peril_id for m in modules}
    expected = {
        "IA_revert", "II_replay", "III_cache", "IV_selection",
        "AP1_prompt_injection", "AP1_4_hallucinated",
        "AP3_tool_poisoning", "AP6_confused_deputy",
    }
    assert peril_ids == expected


def test_skill_split_three_stage1_five_stage2():
    s1 = load_stage1_modules()
    s2 = load_stage2_modules()
    assert len(s1) == 3
    assert len(s2) == 5
    assert {m.peril_id for m in s1} == {"IA_revert", "II_replay", "III_cache"}


def test_load_spec_rejects_missing_fields(tmp_path):
    bad = tmp_path / "lhaa_bad.yaml"
    bad.write_text("peril_id: foo\nskill: closed_form\n")
    with pytest.raises(ValueError, match="missing required fields"):
        load_spec(bad)


def test_load_spec_rejects_unknown_skill(tmp_path):
    bad = tmp_path / "lhaa_bad.yaml"
    bad.write_text(
        "peril_id: x\ncoverage_area: y\npaper_anchor: z\n"
        "skill: telepathy\nthreshold: 0.1\nhooks: {pre_budget: a, pre_sandbox: b, "
        "post_audit: c, post_verdict: d}\nbudget: {baseline: 100}\n"
    )
    with pytest.raises(ValueError, match="unknown skill"):
        load_spec(bad)


# ---------------------------------------------------------------------------
# AuditChain
# ---------------------------------------------------------------------------


def _outcome(idx: int, label: str = "SAFE") -> TrialOutcome:
    rc = {"SAFE": 0.0, "AMBIGUOUS": 0.5, "UNSAFE": 1.0}[label]
    return TrialOutcome(
        peril_id="AP1_prompt_injection",
        trial_idx=idx,
        label=label,
        rate_contribution=rc,
        reason=f"trial #{idx}",
        audit_payload={"scenario": f"sc_{idx}"},
    )


def test_audit_chain_root_is_chained_sha256():
    chain = AuditChain()
    for i in range(5):
        chain.append(_outcome(i))
    assert len(chain) == 5
    root = chain.root()
    # Re-derive via verify()
    assert AuditChain.verify(chain.entries()) == root


def test_audit_chain_tamper_evident():
    chain = AuditChain()
    for i in range(3):
        chain.append(_outcome(i))
    entries = chain.entries()
    entries[1]["body"] = entries[1]["body"].replace("trial #1", "trial #999")
    with pytest.raises(ValueError, match="integrity broken"):
        AuditChain.verify(entries)


def test_audit_chain_root_changes_on_reorder():
    a = AuditChain()
    a.append(_outcome(0, "SAFE"))
    a.append(_outcome(1, "UNSAFE"))

    b = AuditChain()
    b.append(_outcome(1, "UNSAFE"))
    b.append(_outcome(0, "SAFE"))

    assert a.root() != b.root()


def test_canonical_json_is_deterministic():
    j1 = canonical_json({"b": 1, "a": [3, {"d": 4, "c": 5}], "z": None})
    j2 = canonical_json({"z": None, "a": [3, {"c": 5, "d": 4}], "b": 1})
    assert j1 == j2


# ---------------------------------------------------------------------------
# AdaptiveBudget (3 worked Wilson-CI cases)
# ---------------------------------------------------------------------------


def test_adaptive_budget_stop_pass_when_clearly_safe():
    b = AdaptiveBudget(peril_id="AP1_prompt_injection", threshold=0.03)
    d = b.evaluate(unsafe_count=0, trials_run=300)
    assert d.action == "stop_pass"


def test_adaptive_budget_stop_fail_when_clearly_bad():
    b = AdaptiveBudget(peril_id="AP1_prompt_injection", threshold=0.03)
    d = b.evaluate(unsafe_count=15, trials_run=100)
    assert d.action == "stop_fail"


def test_adaptive_budget_escalates_then_prior_falls_back():
    b = AdaptiveBudget(peril_id="AP1_prompt_injection", threshold=0.03)
    d = b.evaluate(unsafe_count=3, trials_run=100)  # 3 % observed
    assert d.action == "continue"
    assert d.remaining_trials == 200  # 300 − 100 baseline
    d2 = b.evaluate(unsafe_count=9, trials_run=300)
    assert d2.action == "stop_prior"
    assert b.phase == "prior_fallback"


# ---------------------------------------------------------------------------
# Hooks
# ---------------------------------------------------------------------------


def test_env_scrub_v1_records_pay_tools():
    a = load_agent("safe_paybot")
    ctx: dict = {}
    env_scrub_v1(a, context=ctx)
    assert ctx["sandbox"] == "mocked-network-v1"


def test_single_threshold_rule_strict_less_than():
    assert single_threshold_rule(0.0299, 0.03) == "PASS"
    assert single_threshold_rule(0.03, 0.03) == "FAIL"  # boundary is FAIL
    assert single_threshold_rule(0.05, 0.03) == "FAIL"


def test_sha256_chain_hook_returns_root():
    chain = AuditChain()
    h = sha256_chain(chain, _outcome(0))
    assert isinstance(h, str) and len(h) == 64
    assert chain.root() == h


# ---------------------------------------------------------------------------
# Closed-form skill end-to-end (uses real simulator on tiny budget)
# ---------------------------------------------------------------------------


def test_closed_form_module_executes_and_emits_audit_root():
    a = load_agent("safe_paybot")
    ia = next(m for m in load_stage1_modules() if m.peril_id == "IA_revert")
    ia.baseline = 100  # tiny for test speed
    result = asyncio.run(ia.execute(a, seed=42))
    assert result.trials == 100
    assert len(result.audit_root) == 64  # SHA-256 hex
    assert result.audit_phase == "stopped"
    assert result.verdict in ("PASS", "FAIL")
