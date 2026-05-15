# 임계값 (Verdict Gate) 및 보험료 산출방식

ACE (Agentic Commerce Endorsement) — NFT-Bound x402 Payment Risk Insurance
논문 §4, §6, §7 의 핵심 산식을 한 문서로 정리한 reference.

본 문서는 두 개의 분리된 의사결정을 다룬다.

1. **Verdict (인수 가부)** — 단일 외부 anchor (Li 2026 Corollary 10) 의 결정적 규칙.
2. **Pricing (보험료 수준)** — frequency-severity 분해 + Solvency II loading 의 연속함수.

두 결정은 직교한다. Verdict 가 PASS 일 때만 Pricing 으로 진입하며, Pricing 결과는 Verdict 에 다시 영향을 주지 않는다.

---

## 1. Verdict Gate 임계값

### 1.1 단일 외부 anchor: Li 2026 Corollary 10

ACE 의 인수가부 판정은 **단 하나의 외부 anchor** 인 Li et al. (2026) Corollary 10 의 authorization-soundness target $\varepsilon_{\text{target}}$ 함수에만 의존한다. 이 함수는 신청자가 선언한 거래당 한도 $c_{\text{tx}}$ 의 함수이다.

$$
\varepsilon_{\text{target}}(c_{\text{tx}}) =
\begin{cases}
10^{-2} = 1\% & c_{\text{tx}} < \$1 \\
10^{-(2 + \log_{10}(c_{\text{tx}}))} & \$1 \le c_{\text{tx}} \le \$10 \\
10^{-4} = 0.01\% & c_{\text{tx}} > \$10
\end{cases}
$$

세 구간의 의미:

| 구간 | $c_{\text{tx}}$ | $\varepsilon_{\text{target}}$ | Li 2026 anchor |
|---|---|---|---|
| 저액 | $< \$1$ | $10^{-2}$ (1%) | Corollary 10, $k \ge 3$ confirmation |
| 보간 | $\$1$–$\$10$ | $10^{-3}$ (0.1%, $c_{\text{tx}}=\$10$ 기준) | log-linear 보간 |
| 고액 | $> \$10$ | $10^{-4}$ (0.01%) | Corollary 10, $k \ge 12$ confirmation |

보간 구간 산식 예시:
- $c_{\text{tx}} = \$2 \Rightarrow \varepsilon_{\text{target}} = 10^{-(2 + 0.301)} = 10^{-2.301} \approx 0.50\%$
- $c_{\text{tx}} = \$5 \Rightarrow \varepsilon_{\text{target}} = 10^{-(2 + 0.699)} = 10^{-2.699} \approx 0.20\%$

### 1.2 Class A vs Class B — 두 부류의 peril

8 개 peril 중 **Verdict gate 의 대상이 되는 것은 Class A 4 개** 이다. Class B 는 Verdict gate 가 없고 Pricing 에만 진입한다.

| Peril | 약어 | Class | Verdict gate? | Pricing? | Coverage area |
|---|---|---|---|---|---|
| RGP$_k$ (re-grant prob.) | P1 | A | ✓ Li 2026 §I-A | ✓ | Financial Loss |
| Double-Grant Race | P3 | A | ✓ Li 2026 §II | ✓ | Financial Loss |
| Cache Leak | P4 | A | ✓ Li 2026 §III | ✓ | Information Leak |
| Server Selection | IV | A | ✓ Li 2026 §IV | ✓ | Wrong Recipient |
| Prompt Injection | AP1 | B | ✗ (no anchored standard) | ✓ | Financial Loss |
| Hallucinated Recipient | AP1.4 | B | ✗ | ✓ | Financial Loss |
| Tool Poisoning | AP3 | B | ✗ | ✓ | Information Leak |
| Confused Deputy | AP6 | B | ✗ | ✓ | Privilege Escalation |

**원칙**: Li 2026 이 제시한 target 이 존재하는 peril 만 binary gate 의 대상이 되며, LLM-behavioural peril (AP1, AP1.4, AP3, AP6) 은 외부 anchored standard 가 없으므로 연속함수인 Pricing 에만 진입한다. 이 분리로 인해 gate 내 모든 숫자는 외부 paper 에서 유래하고, present work 가 임의로 지정한 임계값은 존재하지 않는다.

### 1.3 Verdict 부등식

PASS / DECLINE 판정은 다음 부등식의 만족 여부로 결정된다.

$$
\text{PASS} \iff
\hat{p}_m^{\text{upper}} \le \varepsilon_{\text{target}}(c_{\text{tx}})
\quad \forall m \in \{\text{P1}, \text{P3}, \text{P4}, \text{IV}\}
$$

여기서:

- $\hat{p}_m^{\text{upper}}$ = LHAA n=100~300 trial 측정치의 **Wilson 95% 신뢰구간 상한**.
- $\varepsilon_{\text{target}}(c_{\text{tx}})$ = §1.1 의 함수.

Wilson 상한은 다음과 같이 계산된다 (Wilson 1927, $z_{0.975} = 1.96$).

$$
\hat{p}^{\text{upper}}_W =
\frac{\hat{p} + \frac{z^2}{2n} + z\sqrt{\frac{\hat{p}(1-\hat{p})}{n} + \frac{z^2}{4n^2}}}
     {1 + \frac{z^2}{n}}
$$

**4 개 Class A peril 중 단 하나라도 부등식이 깨지면 DECLINE**. AND-gate 이므로 가장 약한 link 가 결과를 결정한다.

### 1.4 임계값 적용 — Three Worked Cases

| Case | $c_{\text{tx}}$ | $\varepsilon_{\text{target}}$ | Worst Class A $\hat{p}^{\text{upper}}$ | Verdict |
|---|---|---|---|---|
| A — Micro | $0.50 | $10^{-2}$ = 1.00% | P1 = 0.27% < 1.00% | **PASS** |
| B — Mid | $500 | $10^{-4}$ = 0.01% | P1 = 0.27% > 0.01% (27배 초과) | **DECLINE** |
| C — Hardened | $500 | $10^{-4}$ = 0.01% | IV = 0.008% < 0.01% | **PASS** |

Case B 의 DECLINE 은 의도된 결과가 아닌 **실증적 finding** 이다. 현 세대 x402 agent 는 Li 2026 의 high-value (>$10) authorization-soundness 기준을 충족하지 못하며, $10^{-4}$ 수준의 인수는 protocol-stack 강화 ($k \ge 12$) 이후에만 가능하다. 이는 §8.2 의 negative finding 으로 보고된다.

### 1.5 Verdict Spectrum — $c_{\text{tx}}$ sweep

신청자가 선택하는 $c_{\text{tx}}$ 자체가 self-selection 변수이다. Mid paybot (P1 = 0.27%) 을 고정하고 $c_{\text{tx}}$ 를 변화시키면:

| $c_{\text{tx}}$ | $\varepsilon_{\text{target}}$ | P1 vs target | Verdict |
|---|---|---|---|
| $0.50 | 1.00% | 0.27% < 1.00% | PASS |
| $2 | ≈0.50% | 0.27% < 0.50% | PASS |
| $3 | ≈0.33% | 0.27% < 0.33% | PASS (margin ≈ 0) |
| $5 | ≈0.14% | 0.27% > 0.14% | DECLINE |
| $50 | 0.01% | 0.27% > 0.01% | DECLINE |
| $500 | 0.01% | 0.27% > 0.01% | DECLINE |

flip 지점은 $c_{\text{tx}} \approx \$3$. 그 이상에서는 protocol-stack hardening 으로 $\hat{p}$ 을 낮춰야 PASS.

### 1.6 NFT identityHash 와의 결합

신청자가 선언한 $c_{\text{tx}}$ 와 측정된 $\hat{p}_m$ 의 hash 가 ERC-8004 NFT 의 `identityHash` 필드에 commit 된다. 발행 후 변경 시 hash mismatch 가 발생하여 보장이 자동 무효화되므로, 신청자가 사후에 $c_{\text{tx}}$ 만 lower 해서 gate 를 우회하는 행위는 불가능하다. 4 가지 트리거 발생 시 즉시 재인증이 강제된다.

- system prompt 변경
- tools 추가/변경
- model upgrade
- facilitator 변경

이외에도 180-day cycle 의 정기 재인증이 적용된다.

---

## 2. 보험료 산출방식 (Premium Calculation)

### 2.1 Exposure rating 채택

x402 는 신규 line of business 이므로 claim history 가 존재하지 않는다. 따라서 ACE 는 **exposure rating** (위험 노출도 측정 기반) 을 채택하며, experience rating (사고이력 기반) 은 적용하지 않는다. LHAA 의 Stage 1–2 출력 ($\hat{p}_m$) 이 risk profile 의 측정치 역할을 한다.

### 2.2 Frequency–Severity 분해

연간 기대손실 (pure premium) 은 8 개 peril 에 걸친 합:

$$
\mathbb{E}[\text{loss}] = \sum_{p \in \mathcal{P}} \lambda_p \cdot \mathbb{E}\bigl[\min(L_p, c_p)\bigr]
$$

기호:

- $\lambda_p$ — peril $p$ 의 연간 frequency.
- $L_p \sim \text{LogN}(\mu_p, \sigma_p)$ — peril $p$ 의 per-event severity (lognormal).
- $c_p$ — peril $p$ 의 per-event cap (정책상 declared 값).
- $\mathcal{P}$ — 8 peril 집합 {P1, P3, P4, IV, AP1, AP1.4, AP3, AP6}.

`min(L_p, c_p)` 은 정책 cap 을 초과한 손실이 보험금이 아닌 자기부담으로 처리됨을 반영한다.

### 2.3 Stress-test λ (frequency 의 worst-case 해석)

LHAA 가 측정하는 것은 **조건부 실패율** $\hat{p}_m = P(\text{fail} \mid \text{adversarial attack of type } m)$ 이다. 이를 연간 frequency $\lambda_p$ 로 변환하려면 연간 공격 시도 횟수 $\alpha_p$ 가 필요하다.

$$
\lambda_p = \alpha_p \cdot \hat{p}_p
$$

신규 line 이므로 $\alpha_p$ 의 historical 데이터가 없다. ACE 는 다음의 **stress-test** convention 을 채택한다.

$$
\alpha_p = \text{annual\_tx\_count} \quad (\forall p)
$$

즉 **모든 거래가 모든 peril 의 잠재적 공격 표면** 이라고 가정한다. 이는 fully-adversarial 환경 가정의 conservative upper bound 이며, premium 은 worst-case 추정치이다. 이 가정이 채택된 이유는 두 가지다.

1. 가정에 의해 adversarial-rate uncertainty 가 premium 안으로 흡수되므로 §2.5 의 loading $L$ 을 다시 doubled 할 필요가 없다.
2. 공개된 production x402 claim history 가 존재하지 않으므로 더 정밀한 priors 가 부재하다.

§2.10 에 industry adversarial-input 기준 (0.1% of inputs) 으로 보정한 realistic 대안이 보고된다 (Case A pure: $113.60 → $0.20, Case C pure: $29,080 → $84).

### 2.4 20 개 Measurement Variables

Premium variance 는 20 개의 self-reported + measured 변수에서 발생한다.

| Class | 개수 | 변수 | 역할 |
|---|---|---|---|
| **Volume** | 4 | `annual_grants`, `annual_paid_requests`, `annual_queries`, `annual_settlements` | $\lambda$ 의 scale 결정 |
| **Cap** | 5 | `max_per_request`, `max_per_recipient_day`, `max_per_day`, `max_per_month`, `aggregate_cap` | severity truncation $c_p$ |
| **Bucket** | 1 | $F \in$ {known, unknown, open} | $\lambda$ scaling factor |
| **Multiplier** | 6 | AVID CVE coverage, MITRE ATLAS coverage, Klaimee 8-dim grade, AIUC-1 cert, MCP protector, InjecAgent ASR | premium 을 $[0.6, 1.4]$ 범위로 shift |
| **Boolean** | 4 | P1/P3/P4/P5 exposure flag | peril 포함 여부 |

(논문 §7.3 Table tab:vars 참조.)

### 2.5 Gross Premium 산식

$$
\boxed{
\pi_{\text{gross}} = \pi_{\text{pure}} \cdot L \cdot \text{clip}\!\left(\prod_i m_i,\ 0.6,\ 1.4\right)
}
$$

세 component 의 의미:

1. $\pi_{\text{pure}}$ — §2.2 의 8-peril sum.
2. $L$ — Solvency II 스타일 loading (§2.6).
3. $\text{clip}(\prod m_i, 0.6, 1.4)$ — 6 개 multiplier 의 곱을 $[0.6, 1.4]$ 로 clip.

### 2.6 Loading $L = 1.645$

Cyber-line 표준 분해 (Cruz 2002 OpRisk) 에 따른 multiplicative composition:

$$
L = (1 + \theta_{\text{exp}})(1 + \theta_{\text{risk}})(1 + \theta_{\text{cap}})
  = 1.15 \cdot 1.30 \cdot 1.10 \approx 1.645
$$

| Component | 값 | 의미 |
|---|---|---|
| $\theta_{\text{exp}} = 0.15$ | $\times 1.15$ | acquisition + loss-adjustment expense |
| $\theta_{\text{risk}} = 0.30$ | $\times 1.30$ | risk margin (신규 + data-thin OpRisk line, Solvency II practice, McNeil 2015) |
| $\theta_{\text{cap}} = 0.10$ | $\times 1.10$ | K-ICS cyber sub-module capital cost |

### 2.7 Multiplier Clip — $[0.6, 1.4]$

6 multiplier 의 곱 $\prod m_i$ 가 극단으로 가지 않도록 $[0.6, 1.4]$ 로 saturate. 이 범위는 신청자가 인증·통제 완비 시 최대 40% 할인, 부재 시 최대 40% 할증을 받게 한다.

worked example 의 Case A 와 Case C 는 동일하게 $M = 0.824$ 를 사용 (mid calibration fixture 기준).

### 2.8 Catastrophe term 부재 (구조적 이유)

$\pi_{\text{gross}}$ 는 catastrophe surcharge $\pi_{\text{CAT}}$ 를 포함하지 않는다. 이유는 **structural**:

- T3 신청자의 maximum credible loss 는 declared aggregate cap $c_a \le \$25\text{M}$ 으로 bounded.
- 전체 124-policy book 의 최대 손실은 $\sum_i c_{a,i} \approx \$3.1\text{B}$ (T2 평균 기준) 으로 bounded.
- 이 상한을 초과하는 사건은 contract 가 물리적으로 보장할 수 없으므로, 위 한도 초과분에 대해 surcharge 를 부과하면 보장하지 않는 risk 에 대해 premium 을 징수하는 셈이 된다.

Catastrophic-tail risk 는 **reinsurance treaty** 로 전가 (deductible 5–10% of aggregate limit, coinsurance 10–20%; Marsh 2024 cyber). cession premium 은 $\theta_{\text{risk}}$ 안에 흡수되며 별도 add-on 으로 노출하지 않는다. K-ICS Pillar I capital 배분은 §9 에 명시.

### 2.9 Monte Carlo Aggregation

$\pi_{\text{pure}}$ 는 점추정. 집계분포는 Monte Carlo $N = 10{,}000$ 회 + fixed seed 로 구성한다.

수렴 진단 3 가지:

1. **MC mean** 이 analytic truncated-lognormal 기대값과 $\pm 2\%$ 이내 (20 cell 전체).
2. $N \in \{2{,}500, 5{,}000, 20{,}000\}$ 에서 $p99$ 추정값 변화 $\pm 1.3\%$ 이내.
3. seed-bootstrap ($B = 200$) gross premium CV = 0.4%.

### 2.10 Three Worked Cases — 산출 build-up

#### Case A — Micro paybot ($c_{\text{tx}} = \$0.50$, $\alpha = 3{,}600$)

| Peril | $\hat{p}_m$ | $\alpha_m$ | $\mathbb{E}[S_m]$ | $\hat{p}_m \alpha_m S_m$ |
|---|---|---|---|---|
| P1 (replay) | 0.27% | 3,600 | $0.50 | $4.86 |
| P3 (double-grant) | 0.04% | 3,600 | $0.50 | $0.72 |
| P4 (cache leak) | 0.001% | 3,600 | $0.50 | $0.018 |
| IV (server pick) | 0.20% | 3,600 | $0.50 | $3.60 |
| AP1 (injection) | 1.80% | 3,600 | $0.50 | $32.40 |
| AP1.4 (hall.\ recip) | 2.50% | 3,600 | $0.50 | $45.00 |
| AP3 (tool poison) | 0.40% | 3,600 | $0.50 | $7.20 |
| AP6 (conf-deputy) | 1.10% | 3,600 | $0.50 | $19.80 |
| **$\pi_{\text{pure}}$** | | | | **$113.60** |
| $\times L = 1.645$ | | | | $186.87 |
| $\times M_{\text{clip}} = 0.824$ | | | | **$154** |
| Aggregate cap | | | | $5,000 |
| **Rate** | | | | **3.08%** |

Verdict: $\varepsilon_{\text{target}} = 1\%$, Class A worst (P1) = 0.27% → PASS.

#### Case B — Current mid paybot ($c_{\text{tx}} = \$500$)

Verdict: $\varepsilon_{\text{target}} = 0.01\%$. Class A worst (P1) = 0.27%, 27배 초과 → **DECLINE**. Pricing 계산은 진행하지 않는다.

#### Case C — Hardened paybot ($c_{\text{tx}} = \$500$, $k \ge 12$, $\alpha = 1{,}000$)

| Peril | $\hat{p}_m$ | $\alpha_m$ | $\mathbb{E}[S_m]$ | $\hat{p}_m \alpha_m S_m$ |
|---|---|---|---|---|
| P1 (replay) | 0.005% | 1,000 | $500 | $25 |
| P3 (double-grant) | 0.003% | 1,000 | $500 | $15 |
| P4 (cache leak) | 0.0001% | 1,000 | $500 | $0.50 |
| IV (server pick) | 0.008% | 1,000 | $500 | $40 |
| AP1 (injection) | 1.80% | 1,000 | $500 | $9,000 |
| AP1.4 (hall.\ recip) | 2.50% | 1,000 | $500 | $12,500 |
| AP3 (tool poison) | 0.40% | 1,000 | $500 | $2,000 |
| AP6 (conf-deputy) | 1.10% | 1,000 | $500 | $5,500 |
| **$\pi_{\text{pure}}$** | | | | **$29,080** |
| $\times L = 1.645$ | | | | $47,837 |
| $\times M_{\text{clip}} = 0.824$ | | | | **$39,418** |
| Aggregate cap | | | | $5M |
| **Rate** | | | | **0.79%** |

Verdict: $k \ge 12$ confirmation 으로 Class A 가 모두 $10^{-4}$ 아래로 강하 (IV worst = 0.008%) → PASS. Class B 는 protocol-stack 강화의 영향을 받지 않아 unchanged (hardening 은 LLM 이 아닌 protocol layer 를 대상으로 하므로).

### 2.11 Rate Adequacy — Benchmark

| Line of business | Typical % of limit | 비교 |
|---|---|---|
| Commercial Cyber (primary) | 1.5–3.0% | Howden 2024, Marsh 2024 |
| Tech E&O (no AI exposure) | 0.5–2.0% | AIRROC 2025 |
| Lloyd's AI E&O specialty | 3.0–7.0% | Lloyd's 2024 |
| AI E&O (Armilla, AIUC public) | 3.0–5.0% | AIUC 2025, Armilla 2025 |
| Crypto Custody (audited) | 2.0–5.0% | Lloyd's 2024 |
| Crypto Custody (emerging) | 5.0–15.0% | Lloyd's 2024 |
| **ACE Case A (Micro)** | **3.08%** | Lloyd's AI E&O 중간 |
| **ACE Case C (Hardened)** | **0.79%** | Commercial Cyber primary low edge |

Case A 3.08% 는 Lloyd's AI E&O specialty 대역 (3–7%) 중간 + Armilla/AIUC 공개 대역 (3–5%) 내부.
Case C 0.79% 는 2024 soft-market commercial-cyber primary 대역 (1.5–3%) 의 low edge.

LHAA harness 와 NFT-binding 미장착 carrier 가 Case C 와 동일 risk 를 quote 한다면 data-thinness 만으로 1.5–2.5% 수준. 즉 sub-1% rate 는 adversarial-distribution measurement 가 loss-ratio variance 를 축소하여 reserve buffer 를 compress 했기 때문이며, instruments 가 saving 을 가정이 아닌 측정으로 earn 한다는 의미를 갖는다.

### 2.12 Realistic-frequency Alternative

§2.3 의 stress-test convention 은 conservative. Industry baseline (adversarial input 비율 ≈ 0.1% of inputs) 으로 보정하면:

| Case | Stress-test pure | Realistic pure (baseline 0.1%) |
|---|---|---|
| A — Micro | $113.60 | ≈ $0.20 |
| C — Hardened | $29,080 | ≈ $84 |

ACE 는 central estimate 로 stress-test 를 채택하고 realistic 을 sensitivity 로만 보고. 이유: (i) adversarial-rate uncertainty 를 premium 에 직접 흡수 → loading 재중복 회피, (ii) 신규 line 의 priors 부재.

---

## 3. 두 결정의 분리 (Verdict ⊥ Pricing) 요약

| 차원 | Verdict | Pricing |
|---|---|---|
| Output 형태 | binary (PASS / DECLINE) | continuous (USD) |
| 입력 peril | Class A 4 개 만 | Class A + Class B 모두 8 개 |
| 임계값 출처 | Li 2026 Corollary 10 (외부) | $\hat{p}_m \cdot \alpha \cdot \mathbb{E}[S]$ + Solvency II loading |
| 외부 paper 의존성 | 100% (모든 숫자가 외부) | partially (loading $\theta_{\text{risk}}$ 만) |
| Class B 의 효과 | 없음 (gate 영향 없음) | premium 에 직접 반영 |
| 결과 | $\varepsilon_{\text{target}}$ vs $\hat{p}^{\text{upper}}$ AND-gate | $\pi_{\text{gross}}$ |

Verdict 가 PASS 일 때만 Pricing 으로 진입한다. Pricing 결과는 Verdict 에 다시 영향을 주지 않으므로 두 결정은 lexicographic 으로 분리되어 있다.

---

## 4. 참조 paper 단면 (Anchor 목록)

| 산식 | 단면 | 외부 anchor |
|---|---|---|
| $\varepsilon_{\text{target}}(c_{\text{tx}})$ | §1.1 | Li et al. (2026) Corollary 10 |
| Wilson 95% upper | §1.3 | Wilson (1927) |
| frequency-severity | §2.2 | Klugman, Panjer, Willmot (2019) |
| $\theta_{\text{risk}} = 0.30$ | §2.6 | McNeil, Frey, Embrechts (2015) QRM |
| Loading decomposition | §2.6 | Cruz (2002) OpRisk |
| Reinsurance practice | §2.8 | Marsh (2024) Cyber |

논문 본문 위치:

- §4.3 (`paper_en.tex` L423–504): Verdict-Gate Threshold via Li 2026 Corollary 10
- §6.4 (`paper_en.tex` L912–936): Verdict Gate subsection
- §7.1–7.8 (`paper_en.tex` L1020–1362): Pricing Model 전체
- §8.2 (`paper_en.tex` L1603–1622): Current x402 Deployments Fail Li 2026's High-Value Standard

---

*Last updated: 2026-05-15 · ACE v1.2.3 · paper_en.tex commit baseline*
