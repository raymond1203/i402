# I402 — demo frontend

Cinematic single-page web app that walks judges through the entire
underwriting → NFT → enrollment flow of the ACE pipeline.

## Run

```bash
cd ace_ml/web
python3 -m http.server 8000
# open http://localhost:8000
```

No build step. No dependencies beyond the browser. The Inter and Source
Code Pro fonts are loaded from Google Fonts at first paint.

## Login

Demo credentials are shown beneath the form:

```
id: GAIP
pw: 2026
```

## Screen map

```
splash    ── intro morph + login
  └─ postlogin ── Start Tutorial / Skip Tutorial
       └─ dashboard ── agent slot, policy card
            ├─ (Add Agent) → file-picker modal (Windows-style)
            └─ (Start Review) → arena → result
                                          ├─ DEFEAT → dashboard
                                          └─ WINNER → premium → cert → nft → payment → dashboard (policy active)
```

## Key cinematic moments

- **Intro morph (4.6s)** — "X402 insurance with AI agent" reveals, the I from
  *insurance* flies to replace the X in X402, the I floods Supabase Green,
  single bounce, then the I402 logo migrates into the top bar and the login
  form slides up. ESC or click anywhere skips.
- **Arena (~12s)** — defender vs attacker SVG combat with one animation
  primitive per attack vector (II replay, III cache, I-A revert, IV
  selection, AP1 injection, AP3 tool poison, AP6 confused deputy). HUD
  ticker + score bar track the result. Skippable.
- **Identity-mismatch demo** — on the NFT receipt, the "edit agent" toggle
  appends one character to the system prompt; the identity hash visibly
  mutates digit-by-digit, then a full-screen COVERAGE VOID overlay flashes.
- **Re-cert countdown** — dashboard pill cycles ACTIVE → RE-CERT DUE SOON
  → RE-CERT URGENT → COVERAGE CANCELLED as time advances. A debug
  "Fast-forward 6mo" button on the dashboard runs the whole cycle.

## On-chain values shown in the demo

These are the **real** values from the live Sepolia mint we performed:

```
contract:   0xfBc26464eaf11a9b82b81e8f2e7D68Bb00E9878F
tokenId:    1
tx hash:    0x26a742bb0b9bf154ba9a68c1ba1365c58a75b9bb53b4db7c2366f03aa3a92b25
network:    Ethereum Sepolia
```

The NFT receipt's "View on Etherscan" link opens the real Sepolia transaction.

## File layout

```
web/
  index.html              # single-page shell
  css/
    tokens.css            # Supabase palette (fixed hex typos #3ecf8e, #2e2e2e)
    base.css              # reset + typography + body grain
    components.css        # buttons, pills, cards, inputs, banners
    animations.css        # keyframes (glow, sparkle, shake, glitch, particle)
    screens.css           # per-screen layouts
  js/
    app.js                # entry — boots every screen module
    state.js              # central state + screen registry
    data.js               # mock pipeline data + real on-chain values
    tutorial.js           # finger-cursor walkthrough
    screens/
      splash.js           # intro morph + login
      postlogin.js        # tutorial chooser
      dashboard.js        # agent slot + policy card
      file-picker.js      # Windows-style file picker
      arena.js            # LLM attack animation
      result.js           # DEFEAT / WINNER
      premium.js          # animated counter
      cert.js             # 180-day window card
      nft.js              # 3-stage mint sequence + identity-mismatch demo
      payment.js          # mock card form
```

## Paper anchor

Calibration values (DGR, leak_rate, RGP_k, T_gf_sec) and the seven attack
vector names come directly from Li et al., *Five Attacks on x402 Agentic
Payment Protocol*, arXiv:2605.11781 (Table 1, Table 5, Theorem 7,
Corollary 10).
