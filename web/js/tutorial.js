// Tutorial walkthrough — animated cursor + tooltip that travels between
// elements with a description of each step.
//
// Design notes (after Playwright-instrumented review):
//   - Cursor SVG tip is at (6, 4); the cursor div is sized 28×28 with
//     negative margins so the tip lands on the (left, top) CSS pixel.
//     We always pass an anchor point in viewport coords.
//   - Tooltip is placed *opposite* to the cursor and adapts to fit
//     within the viewport without covering the target.
//   - Each step calls `waitForElement` so race conditions during screen
//     transitions don't strand the cursor on stale coordinates.
//   - `sleep` is cancellable: pressing Next or End breaks the current
//     step immediately.

import { state, go } from "./state.js";
// v2: file-picker removed. The dashboard auto-loads safe_paybot, so
// the tutorial walks straight from intro → Start Review → arena.
import { playVectorByKey, finishArenaAndTransition, setActiveVector } from "./screens/arena.js";

// ---------- Tunable timings ----------
const STEP_READ_MS = 1600;        // time we leave the tooltip on screen to read
const POST_ACTION_MS = 200;       // pause after an action runs before next step
const POSITION_SETTLE_MS = 180;   // give the layout one paint before measuring
const TRANSITION_HIDE_MS = 280;   // how long to hide cursor between screen changes

// Test-time overrides (do not use in production).
function readMs() {
  return (typeof window !== "undefined" && Number.isFinite(window.__tutorialReadMs))
    ? window.__tutorialReadMs : STEP_READ_MS;
}

// ---------- Step definitions ----------
// `targetSelector`: CSS selector resolved AT THE TIME of the step (waits up to 3s).
// `anchor`: 'center'|'top'|'right' — where on the target the cursor tip lands.
// `tooltipSide`: 'auto'|'below'|'above'|'right'|'left' — fallback layout intent.
// `action`: function to run after the read window. Can be async.
// `extraWait`: extra ms to wait after action (e.g., for the arena's 12s).
const STEPS = [
  {
    body: "Welcome to I402 — insurance on top of x402. Let me show you around.",
    targetSelector: "#brandLogo",
    anchor: "center",
    tooltipSide: "below",
    action: null,
  },
  {
    body: "Your safe_paybot agent is pre-loaded. The identity hash here is the same one we will bind on-chain — Stage 2 runs an adaptive Claude attacker against it. Click Start Review.",
    targetSelector: "#startReviewBtn",
    anchor: "center",
    tooltipSide: "above",
    action: async () => { go("arena"); await sleep(300); },
  },
  {
    body: "II Replay — the same X-PAYMENT payload is reused. Five ghost projectiles fly at your agent. Your shield must parry each one.",
    targetSelector: ".vt-item[data-key='II']",
    anchor: "center",
    tooltipSide: "above",
    keepOverlay: true,
    prepare: () => setActiveVector("II"),
    action: async () => { await playVectorByKey("II"); },
  },
  {
    body: "III Cache Leak — the paid response slips out via a caching proxy. Data particles try to escape past the defender.",
    targetSelector: ".vt-item[data-key='III']",
    anchor: "center",
    tooltipSide: "above",
    keepOverlay: true,
    prepare: () => setActiveVector("III"),
    action: async () => { await playVectorByKey("III"); },
  },
  {
    body: "I-A Revert Grant — funds are released before chain finality. A time-rewind ripple tests grant-policy enforcement.",
    targetSelector: ".vt-item[data-key='IA']",
    anchor: "center",
    tooltipSide: "above",
    keepOverlay: true,
    prepare: () => setActiveVector("IA"),
    action: async () => { await playVectorByKey("IA"); },
  },
  {
    body: "IV Server Selection — adversarial Bazaar shortlist. Decoy attackers swarm; the defender must pick the genuine one.",
    targetSelector: ".vt-item[data-key='IV']",
    anchor: "center",
    tooltipSide: "above",
    keepOverlay: true,
    prepare: () => setActiveVector("IV"),
    action: async () => { await playVectorByKey("IV"); },
  },
  {
    body: "AP1 Prompt Injection — an indirect injection beam rides in via fetched content. Watch for a REFUSE bubble.",
    targetSelector: ".vt-item[data-key='AP1']",
    anchor: "center",
    tooltipSide: "above",
    keepOverlay: true,
    prepare: () => setActiveVector("AP1"),
    action: async () => { await playVectorByKey("AP1"); },
  },
  {
    body: "AP3 Tool Poisoning — a reroute hidden in a tool description. A corrupted weapon is offered; the defender must drop it.",
    targetSelector: ".vt-item[data-key='AP3']",
    anchor: "center",
    tooltipSide: "above",
    keepOverlay: true,
    prepare: () => setActiveVector("AP3"),
    action: async () => { await playVectorByKey("AP3"); },
  },
  {
    body: "AP6 Confused Deputy — scope expansion via prior consent. A false-flag scroll is waved as if pre-authorised.",
    targetSelector: ".vt-item[data-key='AP6']",
    anchor: "center",
    tooltipSide: "above",
    keepOverlay: true,
    prepare: () => setActiveVector("AP6"),
    action: async () => {
      await playVectorByKey("AP6");
      // Hide cursor before transitioning so it doesn't ghost on the result screen.
      document.getElementById("tutorialCursor").style.opacity = "0";
      document.getElementById("tutorialTooltip").style.opacity = "0";
      await finishArenaAndTransition();
    },
  },
  {
    body: "Your agent passed every threshold. Click \"Check Monthly Premium\" to see your quote.",
    targetSelector: "#resultNextBtn",
    anchor: "center",
    tooltipSide: "below",
    action: async () => { go("premium"); await sleep(300); },
  },
  {
    body: "Premium is $42/month — derived from your agent's risk profile (DGR, cache hygiene, revert exposure, behavioral robustness).",
    targetSelector: "#premiumNextBtn",
    anchor: "center",
    tooltipSide: "above",
    action: async () => { go("cert"); await sleep(300); },
  },
  {
    body: "We're locking in a 180-day certification period. Re-certify before expiry or coverage automatically cancels.",
    targetSelector: "#certNextBtn",
    anchor: "center",
    tooltipSide: "above",
    action: async () => { go("nft"); await sleep(300); },
  },
  {
    body: "We're issuing your ERC-8004 NFT certificate on Sepolia. This identity hash binds to your exact agent — modify it and coverage voids.",
    targetSelector: "#nftStep3",
    anchor: "top",
    tooltipSide: "above",
    waitTimeout: 6500,  // mint sequence takes ~3.8s to reveal step3
    extraWait: 1000,    // a beat to read the receipt after it lands
    action: null,
  },
  {
    body: "Receipt confirmed on-chain. Token #1 minted. Click Enroll in Insurance to activate coverage.",
    targetSelector: "#nftNextBtn",
    anchor: "center",
    tooltipSide: "above",
    action: async () => { go("payment"); await sleep(300); },
  },
  {
    body: "Card is pre-filled with a demo number. Click Pay & Activate Coverage to complete enrollment.",
    targetSelector: "#payBtn",
    anchor: "center",
    tooltipSide: "right",
    action: async () => {
      document.getElementById("paymentForm").dispatchEvent(new Event("submit", { cancelable: true }));
      // Wait for the mock processing spinner (1800ms) + a beat.
      await sleep(2200);
    },
  },
  {
    body: "You're covered. Policy is active for 180 days. Re-certify before expiry or coverage will auto-cancel.",
    targetSelector: "#payDoneBtn",
    anchor: "center",
    tooltipSide: "above",
    action: async () => {
      document.getElementById("payDoneBtn").click();
      await sleep(200);
    },
  },
];

// ---------- Cursor + tooltip positioning ----------

function getAnchorPoint(rect, anchor) {
  switch (anchor) {
    case "top":
      return { x: rect.left + rect.width / 2, y: rect.top + 6 };
    case "right":
      return { x: rect.right - 6, y: rect.top + rect.height / 2 };
    case "center":
    default:
      return { x: rect.left + rect.width / 2, y: rect.top + rect.height / 2 };
  }
}

function placeCursor(cursor, point) {
  cursor.style.left = `${Math.round(point.x)}px`;
  cursor.style.top = `${Math.round(point.y)}px`;
}

// Place the tooltip near the target. Strategy:
//   (1) If preferredSide fits Y, honour it (clamp X if needed). This keeps the
//       tooltip's vertical band stable as the cursor walks through a row of
//       small targets (e.g. the arena HUD chip ticker), even when individual
//       chips sit too close to the viewport edge for X-centering.
//   (2) Otherwise, try every candidate side for an exact (X+Y) fit.
//   (3) Otherwise, take the first candidate whose Y fits and clamp X.
//   (4) Last resort: clamp both axes around the target's bottom edge.
function placeTooltip(tooltip, anchorPt, targetRect, preferredSide) {
  const margin = 16;
  const W = tooltip.offsetWidth || 340;
  const H = tooltip.offsetHeight || 160;
  const vw = window.innerWidth;
  const vh = window.innerHeight;

  const computeXY = (side) => {
    if (side === "below") return { x: anchorPt.x - W / 2, y: targetRect.bottom + margin };
    if (side === "above") return { x: anchorPt.x - W / 2, y: targetRect.top - H - margin };
    if (side === "right") return { x: targetRect.right + margin, y: anchorPt.y - H / 2 };
    if (side === "left")  return { x: targetRect.left - W - margin, y: anchorPt.y - H / 2 };
    return { x: anchorPt.x - W / 2, y: targetRect.bottom + margin };
  };
  const yFits = (y) => y >= margin && y + H <= vh - margin;
  const xFits = (x) => x >= margin && x + W <= vw - margin;
  const set = (x, y) => {
    tooltip.style.left = `${Math.round(x)}px`;
    tooltip.style.top = `${Math.round(y)}px`;
  };

  // (1) Honour preferredSide aggressively when its Y dimension fits.
  if (preferredSide && preferredSide !== "auto") {
    const { x, y } = computeXY(preferredSide);
    if (yFits(y)) {
      if (xFits(x)) { set(x, y); return preferredSide; }
      const cx = Math.max(margin, Math.min(vw - W - margin, x));
      set(cx, y);
      return `${preferredSide}-xclamp`;
    }
  }

  const order = preferredSide && preferredSide !== "auto"
    ? [preferredSide, "below", "above", "right", "left"]
    : ["below", "above", "right", "left"];

  // (2) Exact fit on any side.
  for (const side of order) {
    const { x, y } = computeXY(side);
    if (xFits(x) && yFits(y)) { set(x, y); return side; }
  }
  // (3) Y-fit on any side, clamp X.
  for (const side of order) {
    const { x, y } = computeXY(side);
    if (yFits(y)) {
      const cx = Math.max(margin, Math.min(vw - W - margin, x));
      set(cx, y);
      return `${side}-xclamp`;
    }
  }
  // (4) Last resort: clamp both axes around the target's bottom edge.
  const cx = Math.max(margin, Math.min(vw - W - margin, anchorPt.x - W / 2));
  const cy = Math.max(margin, Math.min(vh - H - margin, targetRect.bottom + margin));
  set(cx, cy);
  return "clamped";
}

// ---------- State machine ----------

let cursor = null;
let tipEl = null;
let stepNumEl = null;
let stepBodyEl = null;
let aborted = false;
let advanceRequested = false;
let stepIdx = 0;

function sleep(ms) {
  return new Promise((resolve) => {
    const start = Date.now();
    const tick = () => {
      if (aborted || advanceRequested) return resolve();
      // Test hook: if window.__tutorialFreeze is true, hold forever.
      if (typeof window !== "undefined" && window.__tutorialFreeze) {
        return setTimeout(tick, 100);
      }
      const remaining = ms - (Date.now() - start);
      if (remaining <= 0) return resolve();
      setTimeout(tick, Math.min(80, remaining));
    };
    tick();
  });
}

async function waitForElement(selector, timeout = 3500) {
  const start = Date.now();
  while (Date.now() - start < timeout) {
    if (aborted) return null;
    const el = document.querySelector(selector);
    if (el && el.offsetParent !== null) {
      // Ensure layout is settled before returning bounding box.
      await new Promise((r) => requestAnimationFrame(() => r()));
      return el;
    }
    await new Promise((r) => setTimeout(r, 80));
  }
  return null;
}

function hideOverlay() {
  cursor.style.opacity = "0";
  tipEl.style.opacity = "0";
}
function showOverlay() {
  cursor.style.opacity = "1";
  tipEl.style.opacity = "1";
}
function snapPositionWithoutTransition(fn) {
  // Temporarily disable the CSS transition so cursor/tooltip jump to
  // their new positions instantly when crossing screens.
  cursor.classList.add("no-transition");
  tipEl.classList.add("no-transition");
  fn();
  // Restore transitions after one paint.
  requestAnimationFrame(() => requestAnimationFrame(() => {
    cursor.classList.remove("no-transition");
    tipEl.classList.remove("no-transition");
  }));
}

async function positionStep(step, idx) {
  stepNumEl.textContent = String(idx + 1);
  stepBodyEl.textContent = step.body;

  const target = await waitForElement(step.targetSelector, step.waitTimeout || 3500);
  if (!target) {
    console.warn(`[tutorial] step ${idx + 1} target not found:`, step.targetSelector);
    return null;
  }

  // Scroll the target into the centre of the viewport in case the screen
  // is taller than the window (NFT mint page, dashboard with long content).
  target.scrollIntoView({ behavior: "instant", block: "center" });

  // Give the layout (and any post-scroll reflow) a couple of frames to settle.
  await sleep(POSITION_SETTLE_MS);

  const rect = target.getBoundingClientRect();
  const anchorPt = getAnchorPoint(rect, step.anchor || "center");

  snapPositionWithoutTransition(() => {
    placeCursor(cursor, anchorPt);
    placeTooltip(tipEl, anchorPt, rect, step.tooltipSide || "auto");
  });

  // After the snap, refresh tooltip placement once size is known.
  await new Promise((r) => requestAnimationFrame(() => r()));
  placeTooltip(tipEl, anchorPt, rect, step.tooltipSide || "auto");
  return target;
}

async function runStep(step, idx) {
  // Hide overlay during the transition INTO this step's screen, then
  // position the cursor on the new target, then fade back in.
  hideOverlay();
  const target = await positionStep(step, idx);
  if (!target) {
    await sleep(readMs());
    return;
  }
  // Optional pre-overlay setup (e.g. activate the HUD chip the cursor is pointing at)
  // — run BEFORE showOverlay so the chip is already in its highlighted state by
  // the time the cursor and tooltip fade in.
  if (step.prepare && !aborted) {
    try { await step.prepare(); } catch (err) { console.error("[tutorial] prepare failed:", err); }
  }
  showOverlay();

  // Read window
  advanceRequested = false;
  await sleep(readMs());

  // Action that transitions to the next screen — hide overlay so it
  // doesn't ghost on top of the new layout while we're between steps.
  // For in-screen actions (e.g. arena vector animations) keep the cursor
  // visible so it stays anchored to the active chip while the FX plays.
  if (step.action && !aborted) {
    if (!step.keepOverlay) hideOverlay();
    try { await step.action(); } catch (err) { console.error("[tutorial] action failed:", err); }
  }
  if (step.extraWait && !aborted) await sleep(step.extraWait);

  await sleep(POST_ACTION_MS);
}

async function run() {
  for (stepIdx = 0; stepIdx < STEPS.length; stepIdx++) {
    if (aborted) break;
    await runStep(STEPS[stepIdx], stepIdx);
  }
  finish();
}

function finish() {
  cursor.hidden = true;
  tipEl.hidden = true;
  state.tutorialActive = false;
  if (aborted) return;
  document.getElementById("tutorialEndOverlay").hidden = false;
}

export function startTutorial() {
  aborted = false;
  advanceRequested = false;
  stepIdx = 0;
  cursor = document.getElementById("tutorialCursor");
  tipEl = document.getElementById("tutorialTooltip");
  stepNumEl = document.getElementById("tooltipNum");
  stepBodyEl = document.getElementById("tooltipBody");
  cursor.hidden = false;
  tipEl.hidden = false;
  run();
}

export function bootTutorial() {
  document.getElementById("tutorialSkipBtn").addEventListener("click", () => {
    aborted = true;
    advanceRequested = true;
    // Defer in case the tooltip click is still bubbling.
    setTimeout(() => {
      cursor.hidden = true;
      tipEl.hidden = true;
      document.getElementById("tutorialEndOverlay").hidden = true;
    }, 0);
  });
  document.getElementById("tutorialNextBtn").addEventListener("click", () => {
    advanceRequested = true;
  });
  document.getElementById("tutorialEndCta").addEventListener("click", () => {
    document.getElementById("tutorialEndOverlay").hidden = true;
    go("dashboard");
  });
}
