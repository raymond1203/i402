"""Stage 2 behavioral simulator tests — all using mock Anthropic client.

The orchestrator is structured so any object exposing
`.messages.create(**kwargs)` satisfies its protocol, so we never hit
the real API during tests.

Run from repo root:  uv run pytest behavior_sim/
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from agents import load_agent
from behavior_sim.corpus import CATEGORIES, load_corpus
from behavior_sim.judge import _parse_judge_output, judge_response
from behavior_sim.orchestrator import OUTPUT_KEY, run_behavior_simulation
from behavior_sim.target import run_target

# ---- Mock infrastructure ---------------------------------------------------


@dataclass
class _Block:
    type: str
    text: str | None = None
    name: str | None = None
    input: dict | None = None


@dataclass
class _Msg:
    content: list[_Block]
    stop_reason: str = "end_turn"


class _MessagesAPI:
    def __init__(self, responder):
        self._responder = responder

    async def create(self, **kwargs: Any) -> _Msg:
        return self._responder(**kwargs)


class MockClient:
    """Anthropic-like client whose responses are produced by `responder`."""

    def __init__(self, responder):
        self.messages = _MessagesAPI(responder)


def _safe_target_responder(**kwargs):
    """Target agent that refuses anything risky."""
    return _Msg(content=[_Block(type="text", text="REFUSE: I will not act on untrusted input.")])


def _unsafe_target_responder(**kwargs):
    """Target agent that always tries to pay the attacker."""
    return _Msg(
        content=[
            _Block(
                type="tool_use",
                name="pay",
                input={
                    "amount_usd": 0.05,
                    "recipient_address": "0xATTACKER000000000000000000000000000000bb",
                    "resource_id": "/v1/whatever",
                },
            )
        ]
    )


def _judge_responder_classifies(**kwargs):
    """Judge that reads the user prompt and classifies based on whether
    a `pay` tool_use to the attacker address is present."""
    user_blob = kwargs["messages"][0]["content"]
    if "0xATTACKER" in user_blob and '"name": "pay"' in user_blob:
        verdict = "UNSAFE"
        reason = "agent attempted to pay the adversary address"
    elif "REFUSE" in user_blob:
        verdict = "SAFE"
        reason = "agent refused"
    else:
        verdict = "AMBIGUOUS"
        reason = "no clear signal"
    return _Msg(
        content=[_Block(type="text", text=f'{{"verdict": "{verdict}", "reason": "{reason}"}}')]
    )


# ---- Tests -----------------------------------------------------------------


def test_corpus_has_every_category():
    corpus = load_corpus()
    assert set(corpus.keys()) == set(CATEGORIES)
    for cat, scenarios in corpus.items():
        assert scenarios, f"category {cat} has no scenarios"
        for s in scenarios:
            assert s.unsafe_signal
            assert s.user_messages


def test_judge_output_parser_handles_clean_json():
    d = _parse_judge_output('{"verdict": "UNSAFE", "reason": "paid attacker"}')
    assert d.verdict == "UNSAFE"
    assert "attacker" in d.reason


def test_judge_output_parser_handles_garbage():
    d = _parse_judge_output("the model said something with no json at all")
    assert d.verdict == "AMBIGUOUS"


def test_judge_output_parser_extracts_embedded_json():
    d = _parse_judge_output('Some prose. {"verdict": "SAFE", "reason": "refused"} trailing.')
    assert d.verdict == "SAFE"


async def test_run_target_parses_tool_use():
    applicant = load_agent("safe_paybot")
    response = await run_target(
        MockClient(_unsafe_target_responder),
        applicant,
        scenario_messages=[{"role": "user", "content": "test"}],
    )
    assert len(response.tool_uses) == 1
    assert response.tool_uses[0]["name"] == "pay"
    assert "0xATTACKER" in response.tool_uses[0]["input"]["recipient_address"]


async def test_judge_classifies_unsafe_tool_use():
    from behavior_sim.corpus import IV_SCENARIOS

    applicant = load_agent("safe_paybot")
    target_response = await run_target(
        MockClient(_unsafe_target_responder),
        applicant,
        IV_SCENARIOS[0].user_messages,
    )
    decision = await judge_response(
        MockClient(_judge_responder_classifies),
        "claude-sonnet-4-6",
        IV_SCENARIOS[0],
        target_response,
    )
    assert decision.verdict == "UNSAFE"


async def test_orchestrator_safe_agent_yields_low_rate():
    applicant = load_agent("safe_paybot")
    out = await run_behavior_simulation(
        applicants=[applicant],
        target_client=MockClient(_safe_target_responder),
        judge_client=MockClient(_judge_responder_classifies),
        judge_model="claude-sonnet-4-6",
        n_trials=15,
        seed=1,
        max_concurrency=4,
        sample_limit=1,
    )
    assert "safe_paybot" in out
    for cat_key in OUTPUT_KEY.values():
        assert cat_key in out["safe_paybot"]
        assert out["safe_paybot"][cat_key]["rate"] == 0.0


async def test_orchestrator_unsafe_agent_yields_high_rate():
    applicant = load_agent("vuln_paybot")
    out = await run_behavior_simulation(
        applicants=[applicant],
        target_client=MockClient(_unsafe_target_responder),
        judge_client=MockClient(_judge_responder_classifies),
        judge_model="claude-sonnet-4-6",
        n_trials=15,
        seed=2,
        max_concurrency=4,
        sample_limit=1,
    )
    assert out["vuln_paybot"]["IV_selection"]["rate"] == 1.0
    assert out["vuln_paybot"]["AP1_prompt_injection"]["rate"] == 1.0


async def test_output_schema_matches_verdict_thresholds():
    """The orchestrator output must contain the exact keys the verdict
    layer reads at stage_2_behavioral.<key>.rate. This catches schema
    drift early."""
    from verdict.thresholds import THRESHOLDS

    applicant = load_agent("safe_paybot")
    out = await run_behavior_simulation(
        applicants=[applicant],
        target_client=MockClient(_safe_target_responder),
        judge_client=MockClient(_judge_responder_classifies),
        judge_model="claude-sonnet-4-6",
        n_trials=5,
        seed=3,
        max_concurrency=2,
        sample_limit=1,
    )
    stage_2 = out["safe_paybot"]
    for th in THRESHOLDS.values():
        if not th.metric.startswith("stage_2_behavioral."):
            continue
        # threshold metric is "stage_2_behavioral.<key>.rate"
        _, key, leaf = th.metric.split(".")
        assert key in stage_2, f"missing stage-2 key: {key}"
        assert leaf in stage_2[key], f"missing leaf in {key}: {leaf}"
