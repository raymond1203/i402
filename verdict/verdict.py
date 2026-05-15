"""Stage 3 — apply paper-anchored thresholds to per-agent outcomes.

Reads each agent's protocol + behavioral outcome JSONs, walks the
THRESHOLDS table, and emits a verdict. Behavioral outcomes are
optional: if Stage 2 hasn't run yet, those vectors are reported as
`not_run` and the verdict is marked provisional (worst-case: only
Stage-1 vectors gate it).

CLI:
  uv run python -m verdict.verdict \\
    --protocol-dir reports \\
    --behavior-outcomes reports/behavior_outcomes.json \\
    --out reports/verdicts.json
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .thresholds import THRESHOLDS, Threshold


@dataclass
class VectorVerdict:
    key: str
    metric_path: str
    label: str
    value: float | None  # None when the vector did not run
    decision: str  # "PASS" / "CONDITIONAL" / "DECLINE" / "NOT_RUN"
    decline_above: float
    conditional_above: float
    severity: str
    paper_anchor: str


@dataclass
class Verdict:
    agent_name: str
    verdict: str  # "PASS" / "CONDITIONAL" / "DECLINE"
    provisional: bool  # True when any vector is NOT_RUN
    failed_vectors: list[VectorVerdict] = field(default_factory=list)
    all_vectors: list[VectorVerdict] = field(default_factory=list)
    rationale: str = ""


def _resolve_path(obj: dict, dotted: str) -> float | None:
    cur: object = obj
    for part in dotted.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return None
    if isinstance(cur, int | float):
        return float(cur)
    return None


def _decide_vector(threshold: Threshold, value: float | None) -> str:
    if value is None:
        return "NOT_RUN"
    if value > threshold.decline_above:
        return "DECLINE"
    if value > threshold.conditional_above:
        return "CONDITIONAL"
    return "PASS"


def apply_verdict(agent_name: str, combined_outcomes: dict) -> Verdict:
    """Apply the threshold table to a merged {stage_1_protocol, stage_2_behavioral}
    outcomes dict for one agent.
    """
    all_vecs: list[VectorVerdict] = []
    failed: list[VectorVerdict] = []
    saw_not_run = False

    for key, th in THRESHOLDS.items():
        value = _resolve_path(combined_outcomes, th.metric)
        decision = _decide_vector(th, value)
        vv = VectorVerdict(
            key=key,
            metric_path=th.metric,
            label=th.label,
            value=value,
            decision=decision,
            decline_above=th.decline_above,
            conditional_above=th.conditional_above,
            severity=th.severity,
            paper_anchor=th.paper_anchor,
        )
        all_vecs.append(vv)
        if decision == "NOT_RUN":
            saw_not_run = True
        elif decision in ("DECLINE", "CONDITIONAL"):
            failed.append(vv)

    if any(v.decision == "DECLINE" for v in all_vecs):
        overall = "DECLINE"
    elif any(v.decision == "CONDITIONAL" for v in all_vecs):
        overall = "CONDITIONAL"
    else:
        overall = "PASS"

    if overall == "PASS" and saw_not_run:
        rationale = (
            "PROVISIONAL PASS — all measured vectors clear, but some "
            "vectors were not run. A full verdict requires running "
            "every stage end-to-end."
        )
    elif overall == "PASS":
        rationale = "All paper-anchored thresholds cleared."
    else:
        items = ", ".join(f"{v.key}={v.value:.4f}→{v.decision}" for v in failed)
        rationale = f"{overall}: {items}"

    return Verdict(
        agent_name=agent_name,
        verdict=overall,
        provisional=saw_not_run,
        failed_vectors=failed,
        all_vectors=all_vecs,
        rationale=rationale,
    )


# -------------------- CLI helpers --------------------


def _load_protocol_outcomes(protocol_dir: Path, agent_name: str) -> dict | None:
    """Look for `{agent_name}_protocol.json` in the protocol dir."""
    path = protocol_dir / f"{agent_name}_protocol.json"
    if not path.exists():
        return None
    return json.loads(path.read_text())


def _load_behavior_outcomes(behavior_file: Path | None, agent_name: str) -> dict | None:
    if behavior_file is None or not behavior_file.exists():
        return None
    data = json.loads(behavior_file.read_text())
    # Behavior file is keyed by agent_name in this build.
    return data.get(agent_name)


def _merge(protocol: dict | None, behavior: dict | None) -> dict:
    merged: dict = {}
    if protocol is not None:
        merged["stage_1_protocol"] = protocol
    if behavior is not None:
        merged["stage_2_behavioral"] = behavior
    return merged


def _parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="python -m verdict.verdict",
        description="Stage 3 — apply paper-anchored thresholds.",
    )
    p.add_argument("--protocol-dir", type=Path, default=Path("reports"))
    p.add_argument("--behavior-outcomes", type=Path, default=None)
    p.add_argument(
        "--agents",
        type=str,
        nargs="*",
        default=("safe_paybot", "mid_paybot", "vuln_paybot"),
    )
    p.add_argument("--out", type=Path, default=None)
    return p.parse_args(argv)


def _verdict_to_dict(v: Verdict) -> dict:
    return {
        "agent_name": v.agent_name,
        "verdict": v.verdict,
        "provisional": v.provisional,
        "rationale": v.rationale,
        "failed_vectors": [asdict(x) for x in v.failed_vectors],
        "all_vectors": [asdict(x) for x in v.all_vectors],
    }


def main(argv: list[str] | None = None) -> None:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    results = {}
    for agent in args.agents:
        protocol = _load_protocol_outcomes(args.protocol_dir, agent)
        behavior = _load_behavior_outcomes(args.behavior_outcomes, agent)
        merged = _merge(protocol, behavior)
        if not merged:
            results[agent] = {
                "agent_name": agent,
                "verdict": "DECLINE",
                "provisional": True,
                "rationale": "no outcomes available — nothing to verdict",
            }
            continue
        v = apply_verdict(agent, merged)
        results[agent] = _verdict_to_dict(v)
        print(
            f"  {agent:14s} → {v.verdict:11s} "
            f"({len(v.failed_vectors)} failed vector(s)"
            f"{', PROVISIONAL' if v.provisional else ''})"
        )

    rendered = json.dumps(results, indent=2)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(rendered)
        print(f"wrote {args.out}")
    else:
        sys.stdout.write(rendered + "\n")


if __name__ == "__main__":
    main()
