"""Verify that an agent's current declaration still matches its NFT.

  uv run python -m nft.verify safe_paybot 1

Recomputes the canonical identity hash from the agent's current JSON
declaration, reads the on-chain hash for tokenId, and reports MATCH or
MISMATCH. The demo flow:

  1. Mint NFT for SafePayBot (hash = H1)
  2. Edit safe_paybot.json (e.g. one char in system_prompt)
  3. Re-run verify  →  hash mismatch  →  "coverage VOID"
"""

from __future__ import annotations

import argparse
import sys

from agents import load_agent
from agents.identity import compute_identity_hash

from .common import contract_address, load_artifact, make_w3


def _parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="python -m nft.verify")
    p.add_argument("agent_name", type=str)
    p.add_argument("token_id", type=int)
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    applicant = load_agent(args.agent_name)
    current_hex = compute_identity_hash(applicant)
    current_bytes = bytes.fromhex(current_hex[2:])

    w3 = make_w3()
    abi, _ = load_artifact()
    addr = contract_address()
    contract = w3.eth.contract(address=w3.to_checksum_address(addr), abi=abi)

    on_chain = contract.functions.identityHashOf(args.token_id).call()
    on_chain_hex = "0x" + on_chain.hex()
    matched = on_chain == current_bytes

    print(f"agent:           {args.agent_name}")
    print(f"tokenId:         {args.token_id}")
    print(f"current hash:    {current_hex}")
    print(f"on-chain hash:   {on_chain_hex}")
    if matched:
        print("✓ MATCH  — coverage ACTIVE")
        return 0
    print("✗ MISMATCH — coverage VOID (agent declaration has changed since underwriting)")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
