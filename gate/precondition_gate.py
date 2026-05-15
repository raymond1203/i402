"""Stage 0 — Precondition gate.

Binary admission gate that runs before the simulator and any downstream
scoring. Verifies (a) structural facts about the applicant's payment
setup and (b) baseline insurability of the declared agent.

A failure here is a hard decline. The simulator never runs; the rule
verdict never runs; no NFT is minted. Remediation is the only path
forward.

Notably handled here (NOT in the simulator):
- Attack I-B settlement preemption (Li et al. arXiv:2605.11781).
  A perfectly coded endpoint is still wide open to preemption if its
  facilitator does not enforce facilitator-bound settlement, so this is
  a verified fact, not a fuzz target.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .applicant import Applicant
from .registry import (
    ALLOWLISTED_FACILITATORS,
    FACILITATOR_BOUND_SETTLEMENT,
    PAYMENT_PATH_SECURED,
)


@dataclass
class GateFailure:
    check: str  # short identifier, e.g. "facilitator_bound_settlement"
    reason: str  # human-readable description of the failure
    remediation: str  # what the applicant should do to clear this check


@dataclass
class GateResult:
    passed: bool
    failures: list[GateFailure] = field(default_factory=list)

    def summary(self) -> str:
        if self.passed:
            return "PASS — all preconditions verified."
        lines = [f"DECLINE — {len(self.failures)} precondition(s) failed:"]
        for f in self.failures:
            lines.append(f"  - [{f.check}] {f.reason}")
            lines.append(f"      → {f.remediation}")
        return "\n".join(lines)


def check_preconditions(applicant: Applicant) -> GateResult:
    failures: list[GateFailure] = []

    # ---------- Structural facts (spec §5.0) ----------
    if not FACILITATOR_BOUND_SETTLEMENT.get(applicant.facilitator, False):
        failures.append(
            GateFailure(
                check="facilitator_bound_settlement",
                reason=(
                    f"facilitator '{applicant.facilitator}' is not verified as "
                    "enforcing msg.sender == facilitator on settle()"
                ),
                remediation=(
                    "Migrate to a facilitator whose settlement contract enforces "
                    "facilitator-bound calls (mitigation M2 in arXiv:2605.11781), "
                    "closing Attack I-B (settlement preemption)."
                ),
            )
        )

    if applicant.facilitator not in ALLOWLISTED_FACILITATORS:
        failures.append(
            GateFailure(
                check="facilitator_allowlisted",
                reason=f"facilitator '{applicant.facilitator}' is not on the ACE allowlist",
                remediation=(
                    "Use an ACE-allowlisted facilitator. Allowlist membership "
                    "requires a known, identifiable operator with attributable "
                    "settlement (see gate/registry.py)."
                ),
            )
        )

    if not PAYMENT_PATH_SECURED.get(applicant.facilitator, False):
        failures.append(
            GateFailure(
                check="payment_path_secured",
                reason=(
                    f"payment path for facilitator '{applicant.facilitator}' is "
                    "not verified as TLS-secured with no untrusted middleware"
                ),
                remediation=(
                    "Ensure end-to-end TLS on the X-PAYMENT carrying path; remove "
                    "untrusted proxies between agent, facilitator, and resource server."
                ),
            )
        )

    # ---------- Baseline insurability (declared-agent sanity) ----------
    if not applicant.wallet_address.strip():
        failures.append(
            GateFailure(
                check="wallet_declared",
                reason="applicant did not declare a wallet address",
                remediation="Declare the wallet address that will execute payments.",
            )
        )

    sp = applicant.spending_policy
    if sp is None or sp.daily_cap_usd <= 0 or sp.per_tx_cap_usd <= 0:
        failures.append(
            GateFailure(
                check="spending_cap_declared",
                reason="missing or non-positive spending cap (daily / per-tx)",
                remediation=(
                    "Declare positive daily_cap_usd and per_tx_cap_usd. "
                    "Unbounded spending is uninsurable — loss exposure has no ceiling."
                ),
            )
        )

    if not applicant.model.strip():
        failures.append(
            GateFailure(
                check="model_declared",
                reason="applicant did not declare which LLM the agent runs on",
                remediation=(
                    "Declare the model id and version (e.g. 'claude-sonnet-4-6'). "
                    "Behavioral risk class depends on the model family."
                ),
            )
        )

    if not applicant.system_prompt.strip():
        failures.append(
            GateFailure(
                check="system_prompt_declared",
                reason="applicant submitted an empty system prompt",
                remediation=(
                    "Provide the system prompt that scopes the agent's behavior. "
                    "Identity-hash binding requires it — the NFT becomes invalid "
                    "if the system prompt later changes."
                ),
            )
        )

    if not applicant.tools:
        failures.append(
            GateFailure(
                check="tools_declared",
                reason="applicant declared no tools",
                remediation=(
                    "An agent with no tools cannot transact; there is nothing to "
                    "underwrite. Declare the tool list (name + JSON schema)."
                ),
            )
        )

    if applicant.endpoint_config is None:
        failures.append(
            GateFailure(
                check="endpoint_config_declared",
                reason="applicant did not declare an endpoint_config",
                remediation=(
                    "Declare endpoint_config (M1/M3/M4/M5 properties: payment_encoding, "
                    "idempotency, resource_id_binding, settle_before_grant, "
                    "confirmation_depth_k, cache_control, ...). Stage 1 simulator "
                    "cannot run without this."
                ),
            )
        )
    elif applicant.endpoint_config.byzantine_facilitator_assumed:
        # Self-disclosed Byzantine facilitator ⇒ paper RGP_k = 1.0 ⇒ uninsurable.
        failures.append(
            GateFailure(
                check="byzantine_facilitator_disclosure",
                reason=(
                    "applicant disclosed byzantine_facilitator_assumed=true; "
                    "paper Table 1 reports RGP_k = 100% under Byzantine facilitator"
                ),
                remediation=(
                    "Migrate to an honest, allowlisted facilitator. Byzantine "
                    "facilitator self-disclosure is uninsurable — every settlement "
                    "is a certain revert-grant exposure."
                ),
            )
        )

    if applicant.behavioral_config is None:
        failures.append(
            GateFailure(
                check="behavioral_config_declared",
                reason="applicant did not declare a behavioral_config",
                remediation=(
                    "Declare behavioral_config (discovery_method, metadata_validation, "
                    "prompt_injection_guardrail, sdk_family, monitoring). Stage 2 "
                    "behavioral simulator cannot run without this."
                ),
            )
        )

    return GateResult(passed=not failures, failures=failures)
