"""Deploy ACEAgentIdentity to the testnet specified by RPC_URL.

Reads constructor arg from ACE_UNDERWRITER_ADDRESS (falls back to the
deployer's own address). Prints the deployed contract address; the
user pastes that into .env as ACE_IDENTITY_CONTRACT_ADDRESS.

  uv run python -m nft.deploy
"""

from __future__ import annotations

import os
import sys

from .common import deployer_account, load_artifact, make_w3


def main(argv: list[str] | None = None) -> None:
    _ = argv  # no flags for now
    w3 = make_w3()
    acct = deployer_account()
    abi, bytecode = load_artifact()

    underwriter = os.environ.get("ACE_UNDERWRITER_ADDRESS", "").strip()
    if not underwriter or underwriter.startswith("<"):
        underwriter = acct.address
    print(f"deployer:    {acct.address}")
    print(f"underwriter: {underwriter}")
    print(f"chain id:    {w3.eth.chain_id}")

    contract = w3.eth.contract(abi=abi, bytecode=bytecode)
    tx = contract.constructor(underwriter).build_transaction(
        {
            "from": acct.address,
            "nonce": w3.eth.get_transaction_count(acct.address),
            "chainId": w3.eth.chain_id,
            "gas": 2_500_000,
            "gasPrice": w3.eth.gas_price,
        }
    )
    signed = w3.eth.account.sign_transaction(tx, acct.key)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    print(f"deploy tx:   {tx_hash.hex()}")
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
    addr = receipt.contractAddress
    print(f"deployed:    {addr}")
    print()
    print("→ Paste this into .env as ACE_IDENTITY_CONTRACT_ADDRESS:")
    print(f"   ACE_IDENTITY_CONTRACT_ADDRESS={addr}")


if __name__ == "__main__":
    main(sys.argv[1:])
