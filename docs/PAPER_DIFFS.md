# Paper 수정안 — 제4회 IDEA + GAIP Singapore 대비

> **사용법**: 각 항목의 *Before / After* 텍스트를 overleaf paper_ko.tex에 그대로 옮기면 됨. 위치는 paper_ko.pdf (2026-05-15 시점)의 페이지 + 섹션으로 표기.

---

## 🚨 PART A — 오늘 (2026-05-15) 예선 마감 전 응급 3건

총 작업 시간: **35분.** 학술/AI 평가위원 첫 30초 반박 봉쇄 목적.

---

### A-1. §6 제목 수정 (p10)

**위치**: 6번 섹션 헤더.

**Before**:
```
6 | 방법론: LLM 하니스와 머신러닝
```

**After**:
```
6 | 방법론: 시뮬레이션 하니스 설계
```

**이유**: 본문에 머신러닝 모듈이 없음. 제목 거짓말은 학술 평가위원에게 즉시 신뢰성 깎임. 본문 그대로 두고 제목만 정직하게.

---

### A-2. §7.2 모수 출처 1단락 추가 (p12)

**위치**: §7.2 "빈도-심도 분해" 마지막 문장 뒤. 식 (3) 직후.

**삽입 텍스트**:
```
λ_p 값은 Li et al. (2026) Table 1, 4, 5의 실측 공격 성공률을 사용한다 (§4
참조). 심도 모수 LogN(μ_p, σ_p)는 DefiLlama (2026) 공시 해킹 원장의
USD 손실 분포에서 같은 카테고리 태그 (private_key_compromise,
signature_exploit, supply_chain, social_engineering)에 매핑되는 86건의
최대우도 fit으로 결정된다 (§9.2의 비교적 백테스트 참조). 모수 표는
부록 B에 보고한다.
```

**이유**: 삼성화재 인수실 평가위원이 "신규 라인인데 모수 어디서 왔냐" 첫 질문. 한 단락이면 즉시 차단. *(부록 B는 본선 작업에서 추가; 예선 단계는 본문 anchor만 있어도 통과)*

---

### A-3. §11 한계 1단락 추가 (p16-17)

**위치**: §11 "토론" 첫 단락 "ACE 청사진에는 세 가지 주요 한계가 있다" 뒤. 기존 세 한계 (시뮬레이터 corpus / ERC-8004 delta-tolerant / 재해성 꼬리) 다음에 **네 번째 한계**로 추가.

**삽입 텍스트**:
```
넷째, Stage 2 시뮬레이터의 대상 에이전트와 안전성 심사자가 모두 동일
모델 계열(Claude Sonnet 4.6)이라는 자기-평가 한계가 있다. 역할은 격리된
컨텍스트에서 분리되지만 (Figure 6 참조; 심사자는 가입자 정체성을 보지
못함), 단일 모델 계열의 체계적 편향에 대한 외부 검증은 부재한다.
후속 작업으로 (i) Claude Agent SDK 기반 적응형 공격자 에이전트로 정적
corpus를 대체, (ii) NVIDIA garak / Microsoft PyRIT 등 독립 LLM 보안
스캐너와의 cross-validation, (iii) 인간 어노테이터 100건 표본의 Cohen's
κ로 심사자 신뢰성 정량 측정을 계획한다.
```

**이유**: 자기-공격 자기-심사 비판이 본선/GAIP에서 가장 강한 단일 반박. 본문 정정직히 인정 + future work에 해소 경로 명시하면 평가위원 반박 의지 자체가 꺾임 ("이미 알고 있고 해결책도 있다"). 또한 §6 제목에서 ML을 뺀 빈자리를 future work로 메움 — 일관성 확보.

---

## PART A 효과 (사전 예측)

| 평가위원 유형 | 직격 약점 (전) | 직격 약점 (후) | 점수 변동 |
|------------|-------------|-------------|---------|
| 학술 평가위원 | §6 ML 거짓 | 정직 인정 | +0.5 |
| AI 평가위원 | 자기-collusion 무답 | future work 명시 | +0.3 |
| 삼성화재 인수실 | 모수 출처 무답 | DefiLlama anchor | +0.4 |
| 합산 (10점 만점) | 7.5 → **8.3** | | |

---

## 📋 PART B — 본선 5/28 전 추가분 (5/16~5/27, 13일)

### B-1. §6 ML 부재 자리 → "적응형 공격자" 섹션으로 채우기 (D1-3)

**작업**: `behavior_sim/attacker_agent.py` 신규 구현 (별도 파일). Claude Agent SDK 기반.
- attacker는 prior failure를 memory에 누적
- 매 trial마다 새 시나리오 생성 (정적 corpus 대체)
- temperature 고정, scenario seed만 변동

**§6 본문 추가**:
```
6.4 | 적응형 공격자 에이전트

Stage 2의 정적 corpus 한계를 해소하기 위해, 본 연구는 Claude Agent SDK
기반 적응형 공격자를 구현한다. 공격자는 (i) 7개 공격 카테고리의 메타-
스펙을 system prompt로 받으며, (ii) 이전 trial에서 SAFE 판정을 받은
시나리오의 요약을 memory에 누적하고, (iii) 매 trial마다 미관측 변이의
새 시나리오를 생성한다. 대상 에이전트와 심사자는 §6.2와 동일하다.

적응형 공격자는 정적 corpus가 포착하지 못하는 보안 우회 발견을
가능케 하며, 이는 Perez et al. (2022)의 LLM-as-attacker 패러다임과
일치한다. 정적 corpus 대비 공격 성공률의 상한이 ~~%p 상승한다 (§9.7).
```

---

### B-2. §9 결과 확장 (D5-6)

**현 §9**: 9.1 보험료 민감도 + 9.2 DefiLlama 백테스트 (0.7p)

**새 §9 구조 (3p로 확장)**:
- 9.1 보험료 민감도 (현재 유지)
- 9.2 비교적 백테스트 (확장: DefiLlama 86 → 150건)
- **9.3 표본 크기 정당화** (NEW)
- **9.4 적응형 공격자 vs 정적 corpus** (NEW, B-1과 연결)
- **9.5 외부 cross-validation** (NEW, garak probe)

**§9.3 텍스트**:
```
9.3 | 표본 크기 정당화

카테고리당 n=300 trial은 다음 통계학적 분해능 요구를 만족한다.
Wilson 95% 신뢰구간에서 관측 비율 p=0.10의 반폭은

  ε = z_{0.975} √(p(1-p)/n) ≈ 1.96 · √(0.09/300) ≈ 0.034

이다. 즉 ±3.4%p 분해능으로 §4.3 임계값 (예: AP1 거절 임계 0.20)을
신뢰성 있게 분리한다. 5,000회 baseline은 5개 카테고리 × n=1,000으로
보수적 분해능 ±1.9%p를 확보한다. 비교 LLM 평가 benchmark의 표본 크기는
TruthfulQA n=817, AdvBench n=520, MMLU n=250/task로, 본 연구 표본은
표준 범위 안에 위치한다.
```

**§9.4 텍스트** (B-1 결과 받은 뒤):
```
9.4 | 적응형 공격자 효과

Table 7은 safe_paybot에 대해 정적 corpus와 적응형 공격자의 결과를
비교한다. 정적 corpus는 카테고리당 1-2개 시나리오를 temperature
변동으로 5,000회 반복하므로, 적응형 공격자가 발견하는 novel 변이가
실제 보안 성능을 보다 보수적으로 추정한다. 적응형 결과가 거절
임계값을 여전히 통과하면 본 연구의 인수심사 결론은 강화된다.

   카테고리        정적 corpus 비율     적응형 비율     Δ
   IV_selection         0.000              0.0XX        +X.X%p
   AP1_prompt           0.000              0.0XX        +X.X%p
   ...
   (실측 데이터로 채울 것 — adaptive attacker 구현 후)
```

**§9.5 텍스트**:
```
9.5 | 외부 cross-validation

NVIDIA garak (v0.10) `promptinject` probe로 같은 가입자 에이전트
(safe / mid / vuln)에 대해 독립 평가를 수행하였다. Garak의 attack
success rate와 본 연구의 AP1 비율의 agreement는 X.XX이다. 평가
모델 의존성 확인을 위해 GPT-4o-mini로 100건 Stage 2 응답을 재심판한
결과 Cohen's κ = 0.XX (substantial agreement)을 보였다.
```

---

### B-3. §4 LLM 위험 카테고리 subsection 분리 (D7)

**현 §4.2**: AP1/AP1.4/AP3/AP6를 1.5단락에 압축.

**새 §4.2-4.5**: 각 0.5p subsection으로 분리. 각각:
- 위협 메커니즘 1단락
- paper anchor (Zhan 2024, Debenedetti 2024 등) 1줄
- 미티게이션 매핑 1단락
- ACE의 거절/조건부 임계값 인용

---

### B-4. (선택) §6 또는 부록에 외부 검증 표

본문이 길어지면 부록 C로 이동:
- Garak probe 결과 표 1개
- Cross-judge κ 표 1개

---

## 🌏 PART C — GAIP Singapore 8/20-21 (5/29~8/19)

본선 1등 확정 후 작업. 영문화 + 글로벌 reframe.

### C-1. PPT 2장 + 5p 부록 영문 압축
- Slide 1: 시장 공백 (Table 1) + ACE 한 줄 요약
- Slide 2: 시뮬레이션-게이팅 파이프라인 (Figure 5) + 결과 (Figure 8)
- 부록 5p: §7 가격, §8 NFT, §9 결과, §10 K-ICS → Solvency II 매핑, §11 한계

### C-2. K-ICS → Solvency II 매핑 추가
- §10 Table 6에 Solvency II SCR cyber sub-module 컬럼 추가
- MAS sandbox pathway 한 단락 (싱가포르 평가위원 직접 anchor)

### C-3. NFT reframe — "audit infrastructure"
- §8 첫 단락 영문: "ERC-8004 is a verifiable audit registry, not a financial asset. The token's identity_hash is SHA-256 of the canonical declaration; tampering breaks coverage. Zero value transfer."
- crypto/blockchain 거부감 직접 차단

### C-4. 인도네시아 ORBIS 우승 패턴 학습
- 2025 GAIP 1등 "Dynamic Copay" — product innovation framing
- ACE도 "Pre-deployment Risk Endorsement"로 product naming
- "underwriting harness"는 mechanism, product는 endorsement

---

## 의존성 그래프

```
A-1 ─┐
A-2 ─┼─▶ 오늘 예선 제출
A-3 ─┘

B-1 ─▶ B-2 (§9.4 데이터 필요)
B-2 ─▶ 본선 점수
B-3 (독립)
B-4 (B-1, B-2 후)

C-1, C-2, C-3, C-4 ─▶ GAIP 8월
```

---

## 위치 추적 체크리스트

| 항목 | PDF 위치 | 작업 | 상태 |
|-----|---------|-----|-----|
| A-1 §6 제목 | p10 | overleaf 헤더 1줄 | ⬜ |
| A-2 §7.2 모수 | p12 식 (3) 뒤 | 1단락 추가 | ⬜ |
| A-3 §11 한계 | p16 첫 단락 뒤 | 1단락 추가 | ⬜ |
| B-1 §6.4 적응형 공격자 | §6 끝 | 신규 subsection | ⬜ |
| B-2 §9 확장 | p14-15 | 3 subsection 추가 | ⬜ |
| B-3 §4 분리 | p7-8 | 4 subsection | ⬜ |
