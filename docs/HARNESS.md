# ACE — AI Agent Payment Insurance Underwriting Harness (I402)

## 한 줄 요약

x402 결제 프로토콜 위에서 동작하는 AI 에이전트를 보험 인수(underwriting) 전에 7가지 공격 벡터로 정량 평가해서, 통과한 에이전트에만 ERC-8004 NFT 증명서를 발급하는 **adversarial stress-test harness**.

## 어떤 종류의 harness인가

"Harness"라는 단어는 두 가지 의미로 쓰입니다:

1. **에이전트 실행 harness** — LLM을 도구 사용 + 메모리 + 컨텍스트 관리와 함께 돌리는 런타임 루프 (Claude Code 같은 것). **이건 ACE가 아니다.**
2. **테스트/시뮬레이션 harness** — 시스템을 스크립트된 시나리오에 묶어 (harness = 마구) 행동을 측정. **이게 ACE다.**

논문에서 정의한 공격 벡터를 그대로 구현해 AI 에이전트를 자동으로 stress-test하고, paper-anchored thresholds로 정량 점수를 매기고, pass / decline을 판정하고, 통과한 agent의 identity hash를 on-chain NFT에 binding 시키는 **인수심사용 stress-test harness**.

## 학술적 근거

Li et al., *"x402: A Practical Threat Model for Agent-Native Payment Protocols"*, arXiv:2605.11781 (2026).

해당 논문이 정의한 7가지 공격 벡터(II / III / I-A / IV / AP1 / AP3 / AP6)와 Table 5의 SDK audit 결과, threshold 값들을 그대로 calibration 기준으로 사용했습니다.

## 파이프라인 구조

```
Applicant JSON (agent.json)
  │
  ▼
[Stage 0] Precondition Gate          ── 구조 + 필수필드 + 페실리테이터 allowlist 검증
  │   (PASS / DECLINE)
  ▼
[Stage 1] Protocol Simulator         ── 5,000 trials · asyncio + aiohttp
  │   · Attack II   Replay
  │   · Attack III  Cache Leak
  │   · Attack I-A  Revert Grant
  │   → DGR, leak rate, RGP_k, T_gf
  ▼
[Stage 2] Behavioral Simulator       ── 5,000 trials · Claude judge
  │   · Attack IV   Server Selection
  │   · Attack AP1  Prompt Injection
  │   · Attack AP3  Tool Poisoning
  │   · Attack AP6  Confused Deputy
  │   → IV rate, AP1, AP3, AP6 rates
  ▼
[Stage 3] Verdict                    ── paper-anchored threshold 비교
  │   (WINNER / DEFEAT)
  ▼
[Stage 4] NFT Certificate            ── ERC-8004 · Foundry + web3.py
      Ethereum Sepolia, Token #N → identity_hash binding
```

## 입력 — Applicant Declaration

```json
{
  "agent_name": "...",
  "model": "claude-sonnet-4-6",
  "system_prompt": "...",
  "tools": [{ "name": "pay", "schema": {...} }, ...],
  "wallet_address": "0x...",
  "spending_policy": { "daily_cap_usd": 100.0, "per_tx_cap_usd": 10.0 },
  "facilitator": "ace-demo-facilitator",
  "endpoint_config":   { ... },   // Stage 1 입력: M1 / M3 / M4 / M5 미티게이션
  "behavioral_config": { ... }    // Stage 2 입력: M6 + 행동 보호 설정
}
```

## 출력

| 항목 | 값 / 의미 |
|------|----------|
| `verdict` | `WINNER` (모든 vector 통과) / `DEFEAT` (1개 이상 실패) |
| `identity_hash` | `0x` + SHA-256(canonical_json(applicant)) — Stage 4에서 NFT에 박힘 |
| NFT certificate | ERC-8004 (Trustless Agents standard, 2026.1 mainnet 표준화) on Sepolia |
| `monthly_premium_usd` | 통과 시 $42 (논문 calibration 기반) |

## 7가지 공격 벡터

| Key | 이름 | 위협 | 미티게이션 |
|-----|------|------|------------|
| II  | Replay | 동일 X-PAYMENT 페이로드 N회 재사용 | nonce + timestamp window + dedup TTL |
| III | Cache Leak | 캐싱 프록시 통한 유료 응답 유출 | `Cache-Control: no-store` |
| I-A | Revert Grant | 체인 finality 이전 자금 해제 | settle_before_grant + k≥6 confirmation |
| IV  | Server Selection | 적대적 Bazaar shortlist 유도 | hardcoded discovery + 엄격 메타데이터 검증 |
| AP1 | Prompt Injection | 가져온 컨텐츠에 숨겨진 명령어 | "untrusted input + REFUSE" 시스템 룰 |
| AP3 | Tool Poisoning | 도구 설명에 숨겨진 redirect | 엄격 JSON schema 검증 |
| AP6 | Confused Deputy | 사전 동의(prior consent) 빙자한 scope 확장 | recipient/amount 확인 룰 + 풀 모니터링 |

## 기술 스택

| 영역 | 도구 |
|------|------|
| 백엔드 | Python 3.12 (uv 패키지 관리, ruff 린트+포맷) |
| 시뮬레이터 | asyncio + aiohttp (Stage 1), Anthropic SDK with Claude Sonnet 4.6 as both target & judge (Stage 2) |
| 스마트 컨트랙트 | Foundry, Solidity, ERC-8004 (foundry-rs/forge-std) |
| 체인 인터랙션 | web3.py + eth-account, Sepolia testnet |
| 프론트엔드 | 바닐라 HTML/CSS/JS (프레임워크 없음), Web Animations API |
| 테스트 | pytest 67개 + forge 11개 = **78개 통과** |

## 실측 검증 데이터 (Sepolia에 실제 민팅)

| 항목 | 값 |
|------|-----|
| Contract | `0xfBc26464eaf11a9b82b81e8f2e7D68Bb00E9878F` |
| Token ID | `1` |
| Tx hash | `0x26a742bb0b9bf154ba9a68c1ba1365c58a75b9bb53b4db7c2366f03aa3a92b25` |
| Network | Ethereum Sepolia |
| safe_paybot identity_hash | `0x76dd0104ddeaf5ac6f8eaa1be51908d223920831a71cab216a515c9930aba591` |
| mid_paybot identity_hash | `0x9ef85109c83e3b2f4e98510b9b4d56e9d28a7b0189eeefd8958095ec86751430` |
| vuln_paybot identity_hash | `0xf9c98a5842264a9fc0333f411664080f516d9de09ba23cc4b3e2d3902dae67ef` |

## 시네마틱 데모 프론트엔드 (별도 repo)

라이브 시연용 SPA는 이 백엔드 repo와 분리된 별도 저장소로 배포됩니다 (Vercel hosted). Supabase-inspired dark theme.

1. **인트로 morph** — `X402 insurance with AI agent` 의 'I' 글자가 'X' 위치로 날아가 `I402` 로고로 합성되는 4.6초 시퀀스 (Web Animations API)
2. **로그인** — `GAIP / 2026`
3. **튜토리얼** — 18단계 cursor + tooltip 가이드. 각 공격 벡터를 한 step씩 분리 (II → III → I-A → IV → AP1 → AP3 → AP6)
4. **Arena** — 녹색 defender + 빨강 attacker 캐릭터가 7개 벡터를 각각 다른 FX 애니메이션으로 시각화
5. **NFT mint 시퀀스** — `canonical_json` typing → `mintCertificate(...)` 호출 → "Confirmed on Sepolia" ✓ → Token #1 영수증 카드 (실제 Etherscan 링크)
6. **Identity mismatch 데모** — 시스템 프롬프트 한 글자 바꾸면 hash가 시각적으로 morph되고 `COVERAGE VOID` 오버레이 — 백엔드의 `nft.verify` 동작과 동일

## "Bring your own agent" 모드 (정직성 강화)

심사위원이 본인 `agent.json`을 업로드해 라이브 평가를 받을 수 있습니다:

| 단계 | 처리 | 정직성 |
|------|------|-------|
| Stage 0 게이트 | 실시간 실행 (~ms) | **100% production-faithful** |
| `identity_hash` 계산 | SHA-256(canonical_json) — Python 백엔드와 **byte-identical** (JS의 JSON.parse가 int/float 구분을 잃는 문제를 자체 파서로 해결) | **100% production-faithful** |
| Stage 1 평가 | endpoint_config의 M1/M3/M5 미티게이션 충족 여부로 결정론적 계산 | production은 5,000 trial 실측, demo는 즉시. **같은 합/불 결과** |
| Stage 2 평가 | system_prompt + behavioral_config의 보호 패턴 매칭 (rule-based) | UI에 "demo mode" 라벨, production은 Claude 5,000콜 |
| NFT | 사전 민팅된 reference Token #1을 보여주고 hash 필드만 본인 것 | production은 burner wallet로 라이브 민팅 |

데모용 starter `template.json`을 제공 — 의도적으로 7개 벡터 중 1개(AP3)만 통과하는 middling configuration이라, 심사위원이 다운로드 → 필드 한두 개씩 수정 → 재업로드하며 vector를 하나씩 살려보고 결국 7/7 → WINNER를 만드는 **학습 경로**가 자연스럽게 생깁니다.

## 디렉토리 구조

```
i402/
├── gate/              # Stage 0 — precondition gate + Applicant dataclass
├── simulator/         # Stage 1 — replay, cache, revert, simulate_endpoint
├── behavior_sim/      # Stage 2 — corpus, target, judge, orchestrator
├── verdict/           # Stage 3 — paper-anchored threshold 룰
├── contracts/         # ERC-8004 Solidity + forge tests
├── nft/               # Stage 4 — deploy, mint, verify, common
├── agents/            # 3 calibrated sample applicants + identity.py
├── reports/           # registration JSONs (NFT agentURI 대상)
├── demo/run_demo.py   # CLI orchestrator
└── docs/              # pipeline.md, model_card.md, HARNESS.md (this file)

# Companion (separate repository, Vercel-hosted):
# i402-demo/web/      # 시네마틱 데모 프론트엔드 (vanilla SPA)
```

## 한 마디로

> **I402는 AI payment agent를 보험 가입 전 5,000회 stress-test하는 paper-anchored adversarial harness이며, 통과 결과를 ERC-8004 NFT로 trustlessly 증명한다.**
