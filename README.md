# I402 — Agentic Commerce Endorsement

**Simulation‑gated insurance underwriting for AI‑agent autonomous payments over the x402 protocol family.**

An applicant submits a declared AI agent (model + system prompt + tool list + payment‑stack config). I402 stress‑tests it against the seven attack vectors from Li et al. *"Five Attacks on x402 Agentic Payment Protocol"* (arXiv:2605.11781). If every paper‑anchored threshold clears, it mints an **ERC‑8004 Trustless‑Agents NFT** whose on‑chain `identity_hash` binds to the exact declared agent. Editing one character of the declaration flips the hash → on‑chain verification fails → coverage is automatically void.

This is the **canonical reference implementation** — runs real Claude API trials and broadcasts real transactions to a testnet. There is no public hosted instance: every Anthropic call and every gas fee comes out of *your* wallet, so you set up locally.

---

## Pipeline

```
applicant AI agent (JSON)
  │
  ├─▶ Stage 0  Precondition gate           binary structural facts          ──fail──▶ DECLINE
  │             • facilitator‑bound settle (M2)
  │             • payment‑path secured     (M1+M3+M4+M5 minimum bar)
  │
  ├─▶ Stage 1  Protocol simulator          5,000 trials · aiohttp           ──fail──▶ DECLINE
  │             • Attack II  Replay                                          (DGR threshold)
  │             • Attack III Cache Leak                                      (leak rate)
  │             • Attack I‑A Revert Grant                                    (RGP_k threshold)
  │
  ├─▶ Stage 2  Behavioral simulator        5,000 trials · Claude judge      ──fail──▶ DECLINE
  │             • Attack IV  Server Selection
  │             • Attack AP1 Prompt Injection
  │             • Attack AP3 Tool Poisoning
  │             • Attack AP6 Confused Deputy
  │
  ├─▶ Stage 3  Verdict gate                Li 2026 Corollary 10 AND-gate    ──fail──▶ DECLINE
  │            ε_target(c_tx) over Class A (P1·P3·P4·IV) only
  │
  ├─▶ Stage 4  Pricing                     π_gross = π_pure · 1.645
  │            frequency × severity        · clip(∏m_i, 0.6, 1.4)
  │
  └─▶ Stage 5  NFT certificate             ERC‑8004 · audit_roots committed ──▶ PASS + Token
                                           identity_hash bound on‑chain
```

The verdict gate uses **one external anchor** (Li 2026 Corollary 10) and no
invented numbers. Pricing uses frequency-severity per Klugman / Panjer /
Willmot (2019) with Solvency II loading per Cruz (2002) and McNeil (2015).
See `docs/THRESHOLDS_AND_PREMIUM.md` for the full derivation and
`docs/LHAA_ARCHITECTURE.md` for the harness internals.

---

## Setup

### Prerequisites

| Tool | Version | Why |
|------|---------|-----|
| Python | ≥3.11 | runtime |
| [uv](https://docs.astral.sh/uv/) | ≥0.4 | package + venv management |
| [Foundry](https://book.getfoundry.sh/) | latest | Solidity compile + tests |
| Anthropic API key | any tier | Stage 2 (LHAA adaptive budget: $1.5–4.5 per agent) |
| Testnet wallet | any | Stage 5 (real NFT mint; use a burner) |

### Install

```bash
git clone https://github.com/raymond1203/i402.git

cd i402
uv sync                                          # installs Python deps into .venv
(cd contracts && forge install foundry-rs/forge-std --no-commit)
cp .env.example .env                             # then fill in the FILL lines
```

Open `.env` and provide:
1. `ANTHROPIC_API_KEY` — your Claude key
2. `DEPLOYER_PRIVATE_KEY` + `ACE_UNDERWRITER_ADDRESS` — a testnet wallet with a small amount of gas (Base Sepolia or Ethereum Sepolia). Get faucet funds from links inside `.env.example`.

---

## Run

### Verify the install

```bash
uv run pytest                                    # 110 Python tests
(cd contracts && forge test)                     # 11 Solidity tests
```

Expected: **121 tests pass.**

### Deploy the NFT contract (one time)

```bash
uv run python -m nft.deploy
```

Outputs the deployed contract address. Paste it into `.env` under `ACE_IDENTITY_CONTRACT_ADDRESS`.

### Run the full pipeline

```bash
uv run python -m demo.run_demo
```

**Default is paper-scale.** Each invocation will:
1. Run the Stage 0 gate (instant)
2. Run Stage 1 protocol simulator — **5,000 aiohttp trials per agent** (~30s)
3. Run Stage 2 behavioural simulator — **5,000 real Claude API calls per agent** (~30–60 min on free-tier rate limits; **budget ~$1–$3 per agent in Anthropic credit**)
4. Compute the Stage 3 verdict
5. Print a mint hint for any passing agent. Mint is a separate, deliberate step: `uv run python -m nft.mint safe_paybot` (calls `mintCertificate(...)` on Sepolia, broadcasts the tx, waits for finality, writes the receipt to `reports/<agent>_registration.json`)

**Adaptive attacker — Stage 2 design.** Every trial calls three Claude models in sequence:

```
  Attacker (generates a fresh adversarial scenario, with memory of prior refused patterns)
       ↓
  Target   (the applicant agent under audit)
       ↓
  Judge    (isolated context, classifies SAFE / UNSAFE / AMBIGUOUS)
```

This replaces the earlier hand-crafted static corpus. See `behavior_sim/attacker_agent.py`. The attacker can be a different model family from the target to further break self-attack collusion:

```bash
uv run python -m demo.run_demo --attacker-model claude-opus-4-7
```

**Fast iteration without spending API budget:**

```bash
uv run python -m demo.run_demo --dry-run                 # skip Stage 2 LLM calls entirely
uv run python -m demo.run_demo --n-trials 200            # smaller Stage 1 budget
```

**Reproduce paper-scale runs from a clean state** (also seeded):

```bash
bash run_all.sh                                          # N_TRIALS=5000 by default
```

### Bring your own agent

Drop your file into `agents/`, add its name to the `--agents` flag:

```bash
cp path/to/my_agent.json agents/
uv run python -m demo.run_demo --agents my_agent
```

Schema: see [`agents/safe_paybot.json`](agents/safe_paybot.json) for a complete annotated example. Required top‑level fields:

```
agent_name              str
model                   str         (e.g. "claude-sonnet-4-6")
system_prompt           str
tools                   [{name, schema}, ...]
wallet_address          0x...
spending_policy         {daily_cap_usd, per_tx_cap_usd}
facilitator             str         (must be in gate.registry allowlist)
endpoint_config         {... Stage 1 mitigations: M1/M3/M4/M5 ...}
behavioral_config       {... Stage 2 protections: M6 + LLM defenses ...}
```

### Verify a mint

```bash
uv run python -m nft.verify <token_id>
```

Reads the token's `identity_hash` from chain, re‑canonicalizes the local applicant JSON, recomputes its SHA‑256, and asserts equality. Drift = coverage void.

---

## Layout

```
i402/
├── gate/                # Stage 0 — precondition gate + Applicant dataclass
├── simulator/           # Stage 1 — replay, cache, revert, simulate_endpoint
├── behavior_sim/        # Stage 2 — orchestrator + 8 LHAA modules (lhaa/)
│   └── lhaa/            #   interface · hooks · budget · audit · skills · 8 YAMLs
├── verdict/             # Stage 3 — Li 2026 Corollary 10 ε_target(c_tx) gate
├── pricing/             # Stage 4 — frequency-severity engine + GEMAct MC
├── nft/                 # Stage 5 — deploy, mint, verify, common
├── contracts/           # ERC‑8004 Solidity + forge tests
├── agents/              # 4 example applicants (micro/safe/mid/vuln) + identity.py
├── demo/run_demo.py     # CLI orchestrator
├── docs/
│   ├── LHAA_ARCHITECTURE.md       # harness architecture A→Z (Korean)
│   └── THRESHOLDS_AND_PREMIUM.md  # verdict + pricing derivations
├── reports/             # outputs (gitignored except .gitkeep)
└── run_all.sh           # reproducer script for paper figures
```

---

## What this is **not**

- **Not a SaaS.** There is no hosted endpoint. Each runner pays their own Anthropic + gas costs. This is deliberate — letting strangers DDoS your API key is bad.
- **Not financial advice.** Threshold values are calibrated to a single published paper. Production insurance underwriting needs broader threat coverage.
- **Not a mainnet product.** All defaults point at Sepolia testnets. Never put a mainnet key in `.env`.

A companion cinematic demo SPA (separate repository) walks judges through the pipeline visually without burning API/gas — that's the URL you'll see in the paper.

---

## Reference

- Li, Z. et al. *"Five Attacks on x402 Agentic Payment Protocol."* arXiv:2605.11781 (2026).
- ERC‑8004 Trustless‑Agents Identity Registry — mainnet standardization, January 2026.

---

## License

MIT — see [`LICENSE`](LICENSE).
