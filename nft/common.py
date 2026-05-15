"""Shared helpers for the NFT scripts: artifact loading, web3 setup."""

from __future__ import annotations

import json
import os
from pathlib import Path

from dotenv import load_dotenv
from eth_account import Account
from eth_account.signers.local import LocalAccount
from web3 import Web3

ACE_ROOT = Path(__file__).resolve().parent.parent
ARTIFACT_PATH = ACE_ROOT / "contracts" / "out" / "ACEAgentIdentity.sol" / "ACEAgentIdentity.json"


def load_artifact() -> tuple[list, str]:
    """Return (abi, bytecode_hex) from the Foundry build output."""
    if not ARTIFACT_PATH.exists():
        raise SystemExit(
            f"Foundry artifact missing at {ARTIFACT_PATH}. Run `cd contracts && forge build` first."
        )
    data = json.loads(ARTIFACT_PATH.read_text())
    abi = data["abi"]
    bytecode = data["bytecode"]["object"]
    return abi, bytecode


def _require_env(key: str) -> str:
    value = os.environ.get(key, "").strip()
    if not value or value.startswith("<"):
        raise SystemExit(
            f"{key} is not set (see .env.example). "
            "Copy .env.example to .env and fill in real values."
        )
    return value


def make_w3() -> Web3:
    load_dotenv(ACE_ROOT / ".env")
    rpc_url = _require_env("RPC_URL")
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    if not w3.is_connected():
        raise SystemExit(f"web3 could not connect to RPC at {rpc_url}")
    return w3


def deployer_account() -> LocalAccount:
    load_dotenv(ACE_ROOT / ".env")
    pk = _require_env("DEPLOYER_PRIVATE_KEY")
    if not pk.startswith("0x"):
        pk = "0x" + pk
    return Account.from_key(pk)


def contract_address() -> str:
    load_dotenv(ACE_ROOT / ".env")
    return _require_env("ACE_IDENTITY_CONTRACT_ADDRESS")
