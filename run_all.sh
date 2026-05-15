#!/usr/bin/env bash
# Reproduces the entire ACE pipeline end-to-end. Seeded, no manual steps.
# Run order: gate sanity → protocol sim → behavior sim → ML train → export.
# NFT mint is intentionally NOT in this script — minting requires a funded
# testnet wallet and is run by hand via `npm run mint -- <agent_name>`.

set -euo pipefail

# Load .env if present (do not fail if missing — Stage 0/1/3 do not need it)
if [ -f .env ]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

: "${N_TRIALS:=5000}"
: "${RANDOM_SEED:=42}"

echo "=== Stage 0+1 sanity tests (gate + protocol simulator) ==="
uv run pytest gate/ agents/ simulator/

echo "=== Stage 1: protocol simulator over the 3 demo agents ==="
mkdir -p reports
for agent in safe_paybot mid_paybot vuln_paybot; do
  config=$(uv run python -c "import json; d = json.load(open('agents/${agent}.json'))['endpoint_config']; print(json.dumps(d))")
  uv run python -m simulator.simulate_endpoint \
    --config "$config" \
    --n-trials "${N_TRIALS}" \
    --seed "${RANDOM_SEED}" \
    --out "reports/${agent}_protocol.json"
done

echo "=== Stage 2: agent behavioral simulation (5k trials per agent) ==="
uv run python -m behavior_sim.behavior_simulator \
  --agents safe_paybot vuln_paybot mid_paybot \
  --n-trials "${N_TRIALS}" \
  --seed "${RANDOM_SEED}" \
  --out reports/behavior_outcomes.json

echo "=== Stage 3: rule-based verdict ==="
uv run python -m verdict.verdict \
  --protocol-dir reports \
  --behavior-outcomes reports/behavior_outcomes.json \
  --out reports/verdicts.json

echo "=== Done. See reports/verdicts.json. Mint NFTs for passing agents with: npm run mint -- <agent_name> ==="
