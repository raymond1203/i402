"""Demo toy agents — the three "applicants" the pipeline runs on.

These play the role real insurance customers would in production. Each
agent is declared as a JSON file in this directory; `load_agent` reads
one and returns a fully-populated `Applicant`.

Calibration anchors (paper Table 5 SDK audit, arXiv:2605.11781):
  safe_paybot ≈ "ideal SDK"      — satisfies M1–M6 (does not exist in audit)
  mid_paybot  ≈ SDK-C Rust       — optimistic mode, racy idempotency, k=0
  vuln_paybot ≈ SDK-B Python     — audit's weakest; fails most checks
"""

from __future__ import annotations

import json
from pathlib import Path

from gate.applicant import (
    Applicant,
    BehavioralConfig,
    EndpointConfig,
    SpendingPolicy,
    Tool,
)

AGENTS_DIR = Path(__file__).parent
# Order matters: micro is the doc §1.4 Case A PASS-path; safe/mid/vuln demonstrate
# the §8.2 negative finding at progressively higher c_tx.
KNOWN_AGENTS = ("micro_paybot", "safe_paybot", "mid_paybot", "vuln_paybot")


def load_agent(name: str) -> Applicant:
    path = AGENTS_DIR / f"{name}.json"
    if not path.exists():
        raise FileNotFoundError(f"no agent declaration at {path}")
    data = json.loads(path.read_text())
    return Applicant(
        agent_name=data["agent_name"],
        model=data["model"],
        system_prompt=data["system_prompt"],
        tools=[Tool(name=t["name"], schema=t["schema"]) for t in data["tools"]],
        wallet_address=data["wallet_address"],
        spending_policy=SpendingPolicy(**data["spending_policy"]),
        facilitator=data["facilitator"],
        endpoint_config=EndpointConfig(**data["endpoint_config"]),
        behavioral_config=BehavioralConfig(**data["behavioral_config"]),
        annual_tx_count_estimate=int(data.get("annual_tx_count_estimate", 0)),
    )


def load_all_agents() -> dict[str, Applicant]:
    return {name: load_agent(name) for name in KNOWN_AGENTS}
