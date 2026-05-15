"""Scenario shape used by the Stage-2 simulator.

Historical note: earlier iterations of i402 shipped a hand-crafted
static corpus (a few canonical scenarios per category, sampled with
temperature variation). That static corpus is removed in v2 — Stage 2
is now driven exclusively by the adaptive attacker agent (see
`attacker_agent.py`), which generates a fresh scenario per trial and
memorises patterns the target has already refused.

We keep the `Scenario` dataclass here because the adaptive attacker
emits objects of this exact shape, and the rest of the pipeline
(orchestrator, judge, output JSON) consumes them unchanged.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

Category = Literal["IV", "AP1", "AP1_4", "AP3", "AP6"]

CATEGORIES: tuple[Category, ...] = ("IV", "AP1", "AP1_4", "AP3", "AP6")


@dataclass
class Scenario:
    """One adversarial trial fed to the target agent.

    Emitted by `attacker_agent.generate_adaptive_scenario`; consumed
    by `target.run_target` and `judge.judge_response`.
    """

    category: Category
    name: str
    user_messages: list[dict]
    unsafe_signal: str
    intended_recipient: str | None = None
    adversary_recipient: str | None = None
    paper_anchor: str = ""
    metadata: dict = field(default_factory=dict)
