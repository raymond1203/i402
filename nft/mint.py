"""Mint an ACE underwriting certificate NFT for an agent that passed.

  uv run python -m nft.mint safe_paybot

Steps:
  1. Load the agent JSON via `agents.load_agent`.
  2. Recompute the canonical identity hash via `agents.identity`.
  3. Write the ERC-8004 registration JSON to `reports/<agent>_registration.json`
     and use its file:// URI as the agentURI (good enough for the demo;
     swap to IPFS in production).
  4. Call ACEAgentIdentity.mintCertificate(applicant_wallet, agent_name,
     identity_hash, agentURI) from the underwriter's wallet.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import sys
from pathlib import Path

from agents import load_agent
from agents.identity import compute_identity_hash

from .common import contract_address, deployer_account, load_artifact, make_w3
from .registration import build_registration_json

REPORTS_DIR = Path(__file__).resolve().parent.parent / "reports"


def _parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="python -m nft.mint")
    p.add_argument("agent_name", type=str)
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="compute identity hash + write registration JSON, but don't send tx",
    )
    return p.parse_args(argv)


def _write_registration(agent_name: str, applicant, hash_hex: str) -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    audit_roots = _read_audit_roots(agent_name)
    registration = build_registration_json(
        applicant,
        verdict="PASS",
        underwritten_at_iso=_dt.datetime.now(_dt.UTC).isoformat(),
        audit_roots=audit_roots,
    )
    path = REPORTS_DIR / f"{agent_name}_registration.json"
    path.write_text(json.dumps(registration, indent=2))
    return path


def _read_audit_roots(agent_name: str) -> dict[str, str]:
    """Pull this agent's per-peril LHAA audit roots from
    reports/behavior_outcomes.json. Returns {} if Stage 2 hasn't been
    run for this agent (e.g. mint-only smoke tests)."""
    bf = REPORTS_DIR / "behavior_outcomes.json"
    if not bf.exists():
        return {}
    try:
        data = json.loads(bf.read_text())
    except json.JSONDecodeError:
        return {}
    agent_block = data.get(agent_name) or {}
    return {
        peril: blk["audit_root"]
        for peril, blk in agent_block.items()
        if isinstance(blk, dict) and blk.get("audit_root")
    }


def main(argv: list[str] | None = None) -> None:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    applicant = load_agent(args.agent_name)
    h_hex = compute_identity_hash(applicant)
    h_bytes = bytes.fromhex(h_hex[2:])

    reg_path = _write_registration(args.agent_name, applicant, h_hex)
    agent_uri = f"file://{reg_path.absolute()}"

    print(f"agent:          {args.agent_name}")
    print(f"identity hash:  {h_hex}")
    print(f"registration:   {reg_path}")
    print(f"agentURI:       {agent_uri}")

    if args.dry_run:
        print("\n--dry-run set; not sending tx.")
        return

    w3 = make_w3()
    acct = deployer_account()
    abi, _ = load_artifact()
    addr = contract_address()
    contract = w3.eth.contract(address=w3.to_checksum_address(addr), abi=abi)

    # Demo: mint to the underwriter's own wallet. In production the `to`
    # would be the applicant's wallet, but the demo keeps things in one place.
    recipient = acct.address

    tx = contract.functions.mintCertificate(
        recipient, args.agent_name, h_bytes, agent_uri
    ).build_transaction(
        {
            "from": acct.address,
            "nonce": w3.eth.get_transaction_count(acct.address),
            "chainId": w3.eth.chain_id,
            "gas": 400_000,
            "gasPrice": w3.eth.gas_price,
        }
    )
    signed = w3.eth.account.sign_transaction(tx, acct.key)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    print(f"mint tx:        {tx_hash.hex()}")
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)

    # Recover the minted tokenId from the Underwritten event.
    token_id: int | None = None
    underwritten_topic = w3.keccak(text="Underwritten(uint256,address,string,bytes32,string)")
    for log in receipt.logs:
        if log.address.lower() == addr.lower() and log.topics[0] == underwritten_topic:
            token_id = int(log.topics[1].hex(), 16)
            break
    print(f"tokenId:        {token_id}")


if __name__ == "__main__":
    main()
