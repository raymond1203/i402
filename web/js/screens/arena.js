// LLM attack arena — the cinematic centerpiece.
//
// Two SVG characters face off. Seven attack vectors play in sequence;
// each ~1.5s. HUD ticker + score bar update per vector. Screen-shake
// on each parry. At the end, transition to WINNER (safe_paybot) or
// DEFEAT (mid/vuln).

import { register, go, state } from "../state.js";
import { ATTACK_VECTORS } from "../data.js";

const DEFENDER_SVG = `
<svg viewBox="0 0 200 240" width="200" height="240" xmlns="http://www.w3.org/2000/svg">
  <!-- shadow -->
  <ellipse cx="100" cy="230" rx="60" ry="6" fill="#000" opacity="0.4"/>
  <!-- body -->
  <g class="def-body">
    <!-- legs -->
    <rect x="72" y="170" width="20" height="50" rx="6" fill="#1a5c3c" stroke="#00c573" stroke-width="2"/>
    <rect x="108" y="170" width="20" height="50" rx="6" fill="#1a5c3c" stroke="#00c573" stroke-width="2"/>
    <!-- torso -->
    <rect x="60" y="90" width="80" height="90" rx="14" fill="#1f4b37" stroke="#3ecf8e" stroke-width="2.5"/>
    <!-- core light -->
    <circle cx="100" cy="125" r="10" fill="#00c573" filter="url(#defGlow)"/>
    <circle cx="100" cy="125" r="18" fill="none" stroke="#00c573" stroke-width="1" opacity="0.5"/>
    <!-- head -->
    <rect x="74" y="40" width="52" height="48" rx="10" fill="#1f4b37" stroke="#3ecf8e" stroke-width="2.5"/>
    <!-- eye visor -->
    <rect x="80" y="56" width="40" height="10" rx="3" fill="#00c573"/>
    <!-- antenna -->
    <line x1="100" y1="40" x2="100" y2="24" stroke="#3ecf8e" stroke-width="2"/>
    <circle cx="100" cy="22" r="3" fill="#00c573"/>
    <!-- arms -->
    <rect x="30" y="100" width="22" height="64" rx="8" fill="#1a5c3c" stroke="#00c573" stroke-width="2" class="def-arm-l"/>
    <rect x="148" y="100" width="22" height="64" rx="8" fill="#1a5c3c" stroke="#00c573" stroke-width="2" class="def-arm-r"/>
    <!-- shield -->
    <ellipse cx="22" cy="135" rx="14" ry="28" fill="rgba(0,197,115,0.15)" stroke="#00c573" stroke-width="2" class="def-shield"/>
  </g>
  <defs>
    <filter id="defGlow"><feGaussianBlur stdDeviation="3"/></filter>
  </defs>
</svg>`;

const ATTACKER_SVG = `
<svg viewBox="0 0 200 240" width="200" height="240" xmlns="http://www.w3.org/2000/svg">
  <ellipse cx="100" cy="230" rx="60" ry="6" fill="#000" opacity="0.4"/>
  <g class="atk-body">
    <!-- legs (jagged) -->
    <polygon points="65,170 80,170 90,225 75,225" fill="#5a1010" stroke="#ef4444" stroke-width="2"/>
    <polygon points="110,170 125,170 130,225 115,225" fill="#5a1010" stroke="#ef4444" stroke-width="2"/>
    <!-- torso (faceted) -->
    <polygon points="55,95 95,82 145,95 140,175 60,175" fill="#3a0e0e" stroke="#ef4444" stroke-width="2.5"/>
    <!-- core -->
    <polygon points="100,118 110,130 100,142 90,130" fill="#ef4444"/>
    <!-- head (horned) -->
    <polygon points="78,42 100,30 122,42 122,80 78,80" fill="#3a0e0e" stroke="#ef4444" stroke-width="2.5"/>
    <polygon points="78,42 70,28 84,40" fill="#5a1010" stroke="#ef4444" stroke-width="1.5"/>
    <polygon points="122,42 130,28 116,40" fill="#5a1010" stroke="#ef4444" stroke-width="1.5"/>
    <!-- eyes -->
    <polygon points="85,58 92,52 96,62" fill="#ef4444"/>
    <polygon points="104,62 108,52 115,58" fill="#ef4444"/>
    <!-- arms (4-armed, multiple) -->
    <polygon points="38,98 55,100 58,170 42,170" fill="#5a1010" stroke="#ef4444" stroke-width="2"/>
    <polygon points="142,100 158,98 162,170 145,170" fill="#5a1010" stroke="#ef4444" stroke-width="2"/>
    <polygon points="22,118 38,120 40,158 28,160" fill="#5a1010" stroke="#ef4444" stroke-width="2" opacity="0.8"/>
    <polygon points="162,120 178,118 172,160 158,158" fill="#5a1010" stroke="#ef4444" stroke-width="2" opacity="0.8"/>
  </g>
</svg>`;

function spawnFx(html) {
  const fx = document.getElementById("arenaFx");
  const tmp = document.createElement("div");
  tmp.innerHTML = html;
  const el = tmp.firstElementChild;
  fx.appendChild(el);
  return el;
}

function clearFx() {
  document.getElementById("arenaFx").innerHTML = "";
}

function shake() {
  const stage = document.getElementById("arenaStage");
  stage.classList.remove("arena-shake");
  void stage.offsetWidth;
  stage.classList.add("arena-shake");
}

async function playVectorIIReplay(passes) {
  // 5 ghost projectiles fired in rapid succession; defender's shield flares on each parry.
  const fxRoot = document.getElementById("arenaFx");
  const defender = document.getElementById("defender").getBoundingClientRect();
  const attacker = document.getElementById("attacker").getBoundingClientRect();
  const stage = document.getElementById("arenaStage").getBoundingClientRect();

  for (let i = 0; i < 5; i++) {
    const proj = document.createElement("div");
    proj.className = "fx-projectile";
    proj.style.left = `${attacker.left - stage.left + 20}px`;
    proj.style.top = `${attacker.top - stage.top + 100 + i * 8}px`;
    fxRoot.appendChild(proj);
    proj.animate(
      [
        { transform: "translateX(0)" },
        { transform: `translateX(${defender.right - attacker.left - 60}px)` },
      ],
      { duration: 500, easing: "ease-in" }
    ).onfinish = () => {
      proj.remove();
      if (passes) {
        const shield = document.createElement("div");
        shield.className = "fx-shield";
        shield.style.left = `${defender.right - stage.left - 20}px`;
        shield.style.top = `${defender.top - stage.top + 60}px`;
        fxRoot.appendChild(shield);
        shield.animate(
          [{ opacity: 0, transform: "scale(0.5)" }, { opacity: 1, transform: "scale(1.1)" }, { opacity: 0, transform: "scale(1.3)" }],
          { duration: 280 }
        ).onfinish = () => shield.remove();
        shake();
      }
    };
    await sleep(160);
  }
  await sleep(400);
}

async function playVectorIIICache(passes) {
  // Data-stream particles slipping past defender's leg (leak visualization)
  const stage = document.getElementById("arenaStage").getBoundingClientRect();
  const defender = document.getElementById("defender").getBoundingClientRect();
  const fxRoot = document.getElementById("arenaFx");

  for (let i = 0; i < 18; i++) {
    const p = document.createElement("div");
    p.className = "fx-particle";
    p.style.left = `${defender.right - stage.left + 20}px`;
    p.style.top = `${defender.bottom - stage.top - 30 - (i % 4) * 6}px`;
    p.style.background = passes ? "#00c573" : "#ef4444";
    fxRoot.appendChild(p);
    p.animate(
      [
        { opacity: 1, transform: "translate(0,0)" },
        { opacity: 0, transform: `translate(${passes ? -120 : 320}px, ${passes ? -40 : 12}px)` },
      ],
      { duration: 700, delay: i * 30, easing: "ease-out" }
    ).onfinish = () => p.remove();
  }
  await sleep(900);
}

async function playVectorIARevert(passes) {
  // Time-rewind ripple effect on the stage
  const fxRoot = document.getElementById("arenaFx");
  const stage = document.getElementById("arenaStage").getBoundingClientRect();

  for (let i = 0; i < 3; i++) {
    const ripple = document.createElement("div");
    ripple.className = "fx-ripple";
    ripple.style.left = `${stage.width / 2 - 40}px`;
    ripple.style.top = `${stage.height / 2 - 40}px`;
    ripple.style.width = "80px";
    ripple.style.height = "80px";
    ripple.style.borderColor = passes ? "#00c573" : "#ef4444";
    fxRoot.appendChild(ripple);
    ripple.animate(
      [
        { transform: "scale(0.3)", opacity: 1 },
        { transform: "scale(6)", opacity: 0 },
      ],
      { duration: 900, easing: "ease-out" }
    ).onfinish = () => ripple.remove();
    await sleep(280);
  }
  await sleep(200);
}

async function playVectorIVSelection(passes) {
  // Decoy clones of attacker; defender must pick the right one.
  const fxRoot = document.getElementById("arenaFx");
  const stage = document.getElementById("arenaStage").getBoundingClientRect();
  const attacker = document.getElementById("attacker").getBoundingClientRect();

  const decoys = [];
  for (let i = 0; i < 4; i++) {
    const d = document.createElement("div");
    d.style.position = "absolute";
    d.style.right = `${20 + i * 60}px`;
    d.style.bottom = "60px";
    d.style.opacity = "0.4";
    d.style.transform = "scaleX(-1) scale(0.6)";
    d.innerHTML = ATTACKER_SVG;
    fxRoot.appendChild(d);
    decoys.push(d);
    d.animate(
      [{ opacity: 0 }, { opacity: 0.4 }],
      { duration: 300, delay: i * 80, fill: "forwards" }
    );
  }
  await sleep(800);
  // Defender either targets the right one (passes) or a decoy (fails).
  const targetIdx = passes ? 1 : 3; // wrong decoy if not passing
  for (let i = 0; i < decoys.length; i++) {
    if (i !== targetIdx) {
      decoys[i].animate([{ opacity: 0.4 }, { opacity: 0 }], { duration: 400, fill: "forwards" });
    } else {
      decoys[i].animate(
        [
          { transform: "scaleX(-1) scale(0.6)", opacity: 0.4 },
          { transform: "scaleX(-1) scale(0.6)", opacity: 1 },
        ],
        { duration: 300, fill: "forwards" }
      );
    }
  }
  await sleep(500);
  decoys.forEach((d) => d.remove());
}

async function playVectorAP1Injection(passes) {
  // Brainwave beam targeting defender's head; REFUSE bubble if passing
  const fxRoot = document.getElementById("arenaFx");
  const stage = document.getElementById("arenaStage").getBoundingClientRect();
  const defender = document.getElementById("defender").getBoundingClientRect();
  const attacker = document.getElementById("attacker").getBoundingClientRect();

  const beam = document.createElement("div");
  beam.className = "fx-beam";
  beam.style.left = `${defender.right - stage.left}px`;
  beam.style.top = `${defender.top - stage.top + 64}px`;
  beam.style.width = `${attacker.left - defender.right}px`;
  beam.style.transformOrigin = "right center";
  fxRoot.appendChild(beam);
  beam.animate(
    [
      { transform: "scaleX(0)", opacity: 0 },
      { transform: "scaleX(1)", opacity: 1 },
      { transform: "scaleX(1)", opacity: 0 },
    ],
    { duration: 800, easing: "ease-out" }
  ).onfinish = () => beam.remove();

  await sleep(700);
  if (passes) {
    const bubble = document.createElement("div");
    bubble.className = "fx-bubble";
    bubble.style.left = `${defender.right - stage.left - 20}px`;
    bubble.style.top = `${defender.top - stage.top - 10}px`;
    bubble.textContent = "REFUSE";
    fxRoot.appendChild(bubble);
    bubble.animate(
      [{ opacity: 0, transform: "translateY(8px)" }, { opacity: 1, transform: "translateY(0)" }, { opacity: 0, transform: "translateY(-12px)" }],
      { duration: 900 }
    ).onfinish = () => bubble.remove();
    shake();
  }
  await sleep(500);
}

async function playVectorAP3ToolPoison(passes) {
  // Attacker hands defender a corrupted weapon; defender drops it
  const fxRoot = document.getElementById("arenaFx");
  const stage = document.getElementById("arenaStage").getBoundingClientRect();

  const tool = document.createElement("div");
  tool.style.position = "absolute";
  tool.style.left = "60%";
  tool.style.top = "55%";
  tool.style.width = "32px";
  tool.style.height = "32px";
  tool.style.background = "linear-gradient(135deg, #ef4444, #5a1010)";
  tool.style.transform = "rotate(45deg)";
  tool.style.borderRadius = "4px";
  fxRoot.appendChild(tool);

  // Travel toward defender
  tool.animate(
    [
      { left: "60%", top: "55%", transform: "rotate(45deg) scale(1)" },
      { left: "30%", top: "55%", transform: "rotate(180deg) scale(1.1)", offset: 0.7 },
      { left: "30%", top: passes ? "78%" : "55%", transform: `rotate(${passes ? 720 : 360}deg) scale(${passes ? 0.5 : 1.4})`, opacity: passes ? 0 : 1 },
    ],
    { duration: 1100, easing: "ease-in-out", fill: "forwards" }
  ).onfinish = () => tool.remove();
  if (passes) shake();
  await sleep(1200);
}

async function playVectorAP6ConfusedDeputy(passes) {
  // False-flag scroll waved by attacker. Bigger + readable so judges can
  // see what the forged authorization is actually claiming.
  const fxRoot = document.getElementById("arenaFx");

  const scroll = document.createElement("div");
  scroll.style.position = "absolute";
  scroll.style.left = "48%";
  scroll.style.top = "32%";
  scroll.style.width = "230px";
  scroll.style.background = "linear-gradient(180deg, #f7ecc6 0%, #ecdba0 100%)";
  scroll.style.border = "1.5px solid #8a6c2e";
  scroll.style.borderRadius = "3px";
  scroll.style.boxShadow = "0 10px 28px rgba(0,0,0,0.55), inset 0 0 0 1px rgba(255,255,255,0.35)";
  scroll.style.fontFamily = "var(--font-mono)";
  scroll.style.fontSize = "13px";
  scroll.style.color = "#2a1d08";
  scroll.style.padding = "10px 14px";
  scroll.style.lineHeight = "1.45";
  scroll.style.transform = "rotate(-4deg) scale(0.7)";
  scroll.style.opacity = "0";
  scroll.style.letterSpacing = "0.02em";
  scroll.innerHTML = `
    <div style="font-size:9px;letter-spacing:0.18em;color:#7a5a18;margin-bottom:4px;">— PRIOR AUTHORIZATION —</div>
    <div style="font-weight:700;">AUTH RENEWED</div>
    <div style="margin-top:2px;">pay <span style="font-weight:700;">$50</span> → <span style="color:#7a3a08;">unrelated payee</span></div>
    <div style="margin-top:4px;font-size:10px;opacity:0.75;">(cites &quot;prior consent&quot;)</div>
  `;
  fxRoot.appendChild(scroll);

  // Pop in.
  await scroll.animate(
    [
      { opacity: 0, transform: "rotate(-12deg) scale(0.55)" },
      { opacity: 1, transform: "rotate(-4deg) scale(1)" },
    ],
    { duration: 260, fill: "forwards", easing: "cubic-bezier(0.2,0.8,0.2,1)" }
  ).finished;

  // Hold long enough to actually read.
  await sleep(2500);

  // Exit.
  scroll.animate(
    passes
      ? [
          { opacity: 1, transform: "rotate(-4deg) scale(1) translate(0,0)" },
          { opacity: 0, transform: "rotate(-30deg) scale(0.85) translate(140px, 90px)" },
        ]
      : [
          { opacity: 1, transform: "rotate(-4deg) scale(1) translate(0,0)" },
          { opacity: 0.35, transform: "rotate(0deg) scale(1.4) translate(-240px, 20px)" },
        ],
    { duration: 700, fill: "forwards", easing: "ease-in" }
  ).onfinish = () => scroll.remove();
  if (passes) shake();
  await sleep(700);
}

const VECTOR_PLAY = {
  II: playVectorIIReplay,
  III: playVectorIIICache,
  IA: playVectorIARevert,
  IV: playVectorIVSelection,
  AP1: playVectorAP1Injection,
  AP3: playVectorAP3ToolPoison,
  AP6: playVectorAP6ConfusedDeputy,
};

function sleep(ms) { return new Promise((r) => setTimeout(r, ms)); }

let arenaCancelled = false;
// Per-arena tally so the tutorial-driven path and the auto path share state.
const arenaTally = { totalScore: 0, failedCount: 0 };

function setupArena() {
  arenaCancelled = false;
  clearFx();

  // Re-inject the SVGs — but be careful: the attacker container also
  // holds the memory counter + thinking pre-roll DOM, so we replace
  // ONLY the svg, not the whole container.
  document.getElementById("defender").innerHTML = DEFENDER_SVG;
  const atk = document.getElementById("attacker");
  atk.querySelectorAll(":scope > svg").forEach((n) => n.remove());
  atk.insertAdjacentHTML("afterbegin", ATTACKER_SVG);

  document.querySelectorAll(".vt-item").forEach((el) => { el.classList.remove("active", "done", "fail"); });
  document.getElementById("scoreFill").style.width = "0%";
  document.getElementById("scoreLabel").textContent = "0";
  arenaTally.totalScore = 0;
  arenaTally.failedCount = 0;
  arenaTally.memory = 0;

  const memVal = document.getElementById("attackerMemoryValue");
  if (memVal) memVal.textContent = "0";
}

// Short "thinking" pre-roll before each vector animates.
// Visualises the backend's `generate_adaptive_scenario` call without
// actually invoking any API.
async function adaptiveThinkPreRoll() {
  const think = document.getElementById("attackerThink");
  if (!think) return;
  think.hidden = false;
  await sleep(420);
  think.hidden = true;
  await sleep(60);
}

// Increment the memory counter after a SAFE-refused trial
// (the attacker logged a new defeated pattern).
function bumpAttackerMemory() {
  const chip = document.getElementById("attackerMemory");
  const val = document.getElementById("attackerMemoryValue");
  if (!chip || !val) return;
  arenaTally.memory = (arenaTally.memory || 0) + 1;
  val.textContent = arenaTally.memory.toString();
  chip.classList.remove("is-bumped");
  void chip.offsetWidth;
  chip.classList.add("is-bumped");
}

// Highlight the HUD chip + top-bar vector name without playing the animation yet.
// Used by the tutorial to "arm" the upcoming vector while the user reads the step copy.
export function setActiveVector(key) {
  const v = ATTACK_VECTORS.find((x) => x.key === key);
  if (!v) return;
  document.querySelectorAll(".vt-item.active").forEach((el) => el.classList.remove("active"));
  document.querySelector(`.vt-item[data-key='${key}']`)?.classList.add("active");
  const nameEl = document.getElementById("vectorName");
  if (nameEl) nameEl.textContent = v.name;
}

// Play a single vector by key (e.g. "II", "AP6"). Updates HUD chip + score.
// Exported so the tutorial can drive vectors one-at-a-time with explanatory steps.
export async function playVectorByKey(key) {
  const v = ATTACK_VECTORS.find((x) => x.key === key);
  if (!v) return;
  const tickEl = document.querySelector(`.vt-item[data-key="${v.key}"]`);
  document.querySelectorAll(".vt-item.active").forEach((el) => el.classList.remove("active"));
  tickEl.classList.add("active");
  document.getElementById("vectorName").textContent = v.name;

  // Prefer the agent's declared safeVectors (uploaded files compute these
  // from real Stage 0/1 + rule-based Stage 2). Fall back to the legacy
  // per-vector safeFor list for any agent built before the upload path.
  const declared = state.agent?.safeVectors;
  const agentName = state.agent?.name ?? "safe_paybot.json";
  const passes = Array.isArray(declared)
    ? declared.includes(v.key)
    : v.safeFor.includes(agentName);

  // Adaptive mode: brief "thinking" pre-roll mirrors the backend's
  // attacker LLM crafting a fresh scenario for this trial.
  await adaptiveThinkPreRoll();

  await VECTOR_PLAY[v.key](passes);

  if (passes) {
    tickEl.classList.add("done");
    // SAFE outcome → attacker logs this pattern as defeated → memory++.
    bumpAttackerMemory();
  } else {
    tickEl.classList.add("fail");
    arenaTally.failedCount++;
    // Paper §5.6: any single failed vector triggers DECLINE. The bar
    // visualises failed-vector count out of 7 — width ≥ 1/7 means the
    // verdict is already DEFEAT, regardless of how high it climbs.
    const pct = Math.min(100, Math.round((arenaTally.failedCount / 7) * 100));
    document.getElementById("scoreFill").style.width = `${pct}%`;
    document.getElementById("scoreLabel").textContent = arenaTally.failedCount.toString();
  }
  // Completed vectors should display only the done/fail state — strip "active" so
  // the chip doesn't keep glowing while the tutorial advances to the next step.
  tickEl.classList.remove("active");
  await sleep(180);
}

// Final settle + go to result; used by both auto-run and tutorial-driven runs.
export async function finishArenaAndTransition() {
  if (arenaCancelled) return;
  await sleep(400);
  state.underwritingVerdict = arenaTally.failedCount === 0 ? "WINNER" : "DEFEAT";
  state.lastArenaMemory = arenaTally.memory || 0;
  go("result");
}

async function runArenaAuto() {
  setupArena();
  for (const v of ATTACK_VECTORS) {
    if (arenaCancelled) break;
    await playVectorByKey(v.key);
  }
  await finishArenaAndTransition();
}

register("arena", {
  onEnter() {
    setupArena();
    // In tutorial mode the tutorial drives one vector per step; otherwise auto-play.
    if (!state.tutorialActive) setTimeout(runArenaAuto, 200);
  },
  onExit() { arenaCancelled = true; },
});

export function bootArena() {
  document.getElementById("arenaSkip").addEventListener("click", () => {
    arenaCancelled = true;
    const agentName = state.agent?.name ?? "safe_paybot.json";
    const failed = !ATTACK_VECTORS.every((v) => v.safeFor.includes(agentName));
    state.underwritingVerdict = failed ? "DEFEAT" : "WINNER";
    go("result");
  });
}
