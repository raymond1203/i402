"""Stage 4 NFT orchestration — deploy, mint, verify the ACE identity NFT.

The Solidity contract lives in `contracts/` (Foundry project). After
`forge build` produces `contracts/out/ACEAgentIdentity.sol/ACEAgentIdentity.json`,
the Python scripts in this package read the ABI from that artifact and
talk to the chain via web3.py.

Three entry points (all use the same .env settings):
    uv run python -m nft.deploy
    uv run python -m nft.mint <agent_name>
    uv run python -m nft.verify <agent_name> <tokenId>
"""

from .common import load_artifact, make_w3
from .registration import build_registration_json

__all__ = ["load_artifact", "make_w3", "build_registration_json"]
