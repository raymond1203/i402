// I402 — splash: intro morph + login
//
// The intro is a single ~4.6s scripted sequence using the Web Animations API.
// Skippable with ESC or click. After the morph, the login form slides in and
// the I402 logo is migrated into the sticky top bar.

import { register, go, state } from "../state.js";

const TIMING = {
  PHASE1_HOLD: 1500,
  PHASE2_DURATION: 900,
  PHASE3_PULSE: 200,
  PHASE3_BOUNCE: 600,
  PHASE4_TAGLINE: 700,
  PHASE5_MIGRATE: 600,
};

let introState = { running: false, finished: false };

function phase1Reveal() {
  const phrase = document.getElementById("introPhrase");
  // Trigger the CSS-based filter+opacity fade-in.
  requestAnimationFrame(() => phrase.classList.add("entered"));
}

function getCenterRect(el) {
  const r = el.getBoundingClientRect();
  return { x: r.left + r.width / 2, y: r.top + r.height / 2, w: r.width, h: r.height };
}

async function phase2Converge() {
  const flyingI = document.getElementById("flyingI");
  const xLetter = document.querySelector(".intro-phrase .word.w-x402 .x");
  const insurance = document.querySelector(".intro-phrase .word.w-insurance");
  const withWord = document.querySelector(".intro-phrase .word.w-with");
  const aiagent = document.querySelector(".intro-phrase .word.w-aiagent");
  const x402Word = document.querySelector(".intro-phrase .word.w-x402");

  const xRect = getCenterRect(xLetter);
  const iRect = getCenterRect(flyingI);
  const dx = xRect.x - iRect.x;
  const dy = xRect.y - iRect.y;

  // Lift the I from "insurance" so it visually leaves the word.
  flyingI.style.position = "relative";
  flyingI.style.zIndex = "10";
  flyingI.style.display = "inline-block";

  // I flies along a slight arc to where X is.
  const fly = flyingI.animate(
    [
      { transform: "translate(0,0)", color: "#fafafa" },
      { transform: `translate(${dx * 0.6}px, ${dy - 30}px)`, offset: 0.6, color: "#fafafa" },
      { transform: `translate(${dx}px, ${dy}px) scale(1.2)`, color: "#00c573" },
    ],
    { duration: TIMING.PHASE2_DURATION, easing: "cubic-bezier(0.7, 0, 0.3, 1)", fill: "forwards" }
  );

  // The rest of "nsurance" dissolves to particles.
  const ns = insurance.querySelector(".ns");
  ns.animate(
    [
      { opacity: 1, transform: "translateY(0)" },
      { opacity: 0, transform: "translateY(20px)" },
    ],
    { duration: 700, fill: "forwards", easing: "ease-in" }
  );

  withWord.animate([{ opacity: 1 }, { opacity: 0 }], {
    duration: 300, delay: 200, fill: "forwards",
  });
  aiagent.animate([{ opacity: 1 }, { opacity: 0 }], {
    duration: 400, delay: 400, fill: "forwards",
  });

  // X dims and shrinks; rest of x402 holds.
  xLetter.animate(
    [
      { color: "#00c573", transform: "scale(1)", textShadow: "0 0 8px rgba(0,197,115,0.5), 0 0 24px rgba(0,197,115,0.3)" },
      { color: "#898989", transform: "scale(0.5)", textShadow: "0 0 0 transparent" },
    ],
    { duration: 700, fill: "forwards", easing: "ease-out" }
  );

  await fly.finished;
}

async function phase3SwapAndColor() {
  const phrase = document.getElementById("introPhrase");
  const brand = document.getElementById("introBrand");
  const brandI = document.getElementById("brandI");

  // Phase swap: hide phrase, reveal brand.
  phrase.style.opacity = "0";
  brand.hidden = false;
  brand.style.opacity = "0";
  await brand.animate(
    [{ opacity: 0 }, { opacity: 1 }],
    { duration: 100, fill: "forwards" }
  ).finished;

  // Radial pulse on the I.
  const pulse = document.createElement("div");
  pulse.className = "radial-pulse";
  const iRect = brandI.getBoundingClientRect();
  pulse.style.left = `${iRect.left + iRect.width / 2}px`;
  pulse.style.top = `${iRect.top + iRect.height / 2}px`;
  document.body.appendChild(pulse);
  setTimeout(() => pulse.remove(), 800);

  // Flood I with color over ~180ms.
  await new Promise((r) => setTimeout(r, 80));
  brandI.classList.add("lit");
  await new Promise((r) => setTimeout(r, 200));
}

async function phase3bBounce() {
  const brandI = document.getElementById("brandI");
  const anim = brandI.animate(
    [
      { transform: "translateY(0) scaleY(1)", offset: 0 },
      { transform: "translateY(-40px) scaleY(1)", offset: 0.15 },
      { transform: "translateY(0) scaleY(0.85)", offset: 0.25 },
      { transform: "translateY(-12px) scaleY(1)", offset: 0.4 },
      { transform: "translateY(0) scaleY(0.95)", offset: 0.55 },
      { transform: "translateY(0) scaleY(1)", offset: 0.7 },
    ],
    { duration: TIMING.PHASE3_BOUNCE, easing: "ease-out", fill: "forwards" }
  );
  await anim.finished;
}

async function phase4Tagline() {
  const tagline = document.getElementById("introTagline");
  tagline.hidden = false;
  tagline.style.opacity = "0";
  await tagline.animate(
    [
      { opacity: 0, transform: "translateX(-50%) translateY(8px)" },
      { opacity: 1, transform: "translateX(-50%) translateY(0)" },
    ],
    { duration: TIMING.PHASE4_TAGLINE, fill: "forwards", easing: "ease-out" }
  ).finished;
}

async function phase5MigrateAndShowLogin() {
  const brand = document.getElementById("introBrand");
  const tagline = document.getElementById("introTagline");
  const skip = document.getElementById("introSkip");
  const loginCard = document.getElementById("loginCard");
  const topbar = document.getElementById("topbar");

  // Compute where the top-bar brand-mark lives so we can animate into it.
  topbar.classList.remove("hidden");
  const target = document.getElementById("brandLogo");
  const targetRect = target.getBoundingClientRect();
  const brandRect = brand.getBoundingClientRect();
  const dx = targetRect.left + targetRect.width / 2 - (brandRect.left + brandRect.width / 2);
  const dy = targetRect.top + targetRect.height / 2 - (brandRect.top + brandRect.height / 2);

  brand.animate(
    [
      { transform: "translate(0,0) scale(1)", opacity: 1 },
      { transform: `translate(${dx}px, ${dy}px) scale(0.28)`, opacity: 0 },
    ],
    { duration: TIMING.PHASE5_MIGRATE, easing: "cubic-bezier(0.4,0,0.2,1)", fill: "forwards" }
  );
  tagline.animate([{ opacity: 1 }, { opacity: 0 }], { duration: 400, fill: "forwards" });
  skip.style.display = "none";

  // Login card slides up.
  loginCard.hidden = false;
  loginCard.animate(
    [
      { opacity: 0, transform: "translateY(24px)" },
      { opacity: 1, transform: "translateY(0)" },
    ],
    { duration: 500, delay: 200, fill: "forwards", easing: "ease-out" }
  );

  await new Promise((r) => setTimeout(r, TIMING.PHASE5_MIGRATE));

  // Collapse the intro stage so it no longer pushes the login card down.
  document.getElementById("introStage").style.display = "none";
}

export function snapToLoggedOutRest() {
  // Used by skip(). Jumps to the post-intro state cleanly.
  const phrase = document.getElementById("introPhrase");
  const brand = document.getElementById("introBrand");
  const tagline = document.getElementById("introTagline");
  const skip = document.getElementById("introSkip");
  const loginCard = document.getElementById("loginCard");
  const topbar = document.getElementById("topbar");

  // Cancel animations.
  document.getAnimations().forEach((a) => a.cancel());

  phrase.style.opacity = "0";
  phrase.style.display = "none";
  brand.hidden = true;
  tagline.hidden = true;
  skip.style.display = "none";
  document.getElementById("introStage").style.display = "none";
  topbar.classList.remove("hidden");
  loginCard.hidden = false;
  loginCard.style.opacity = "1";
  loginCard.style.transform = "translateY(0)";
}

async function runIntro() {
  if (introState.running || introState.finished) return;
  introState.running = true;

  phase1Reveal();
  await new Promise((r) => setTimeout(r, TIMING.PHASE1_HOLD));

  await phase2Converge();
  await phase3SwapAndColor();
  await phase3bBounce();
  await new Promise((r) => setTimeout(r, 200));
  await phase4Tagline();
  await new Promise((r) => setTimeout(r, 400));
  await phase5MigrateAndShowLogin();

  introState.running = false;
  introState.finished = true;
}

function setupSkip() {
  const skipBtn = document.getElementById("introSkip");
  const handler = (e) => {
    if (introState.finished) return;
    e?.stopPropagation();
    introState.finished = true;
    snapToLoggedOutRest();
  };
  skipBtn.addEventListener("click", handler);
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && !introState.finished) handler(e);
  });
  // Single click anywhere on the splash also skips during intro.
  document.getElementById("screen-splash").addEventListener("click", (e) => {
    if (introState.finished) return;
    if (e.target.closest(".login-card")) return;
    handler(e);
  });
}

function setupLogin() {
  const form = document.getElementById("loginForm");
  const user = document.getElementById("loginUser");
  const pass = document.getElementById("loginPass");
  const err = document.getElementById("loginError");
  const card = document.getElementById("loginCard");

  // Pre-fill the demo creds so judges can just press Enter.
  user.value = "GAIP";
  pass.value = "2026";

  form.addEventListener("submit", (e) => {
    e.preventDefault();
    if (user.value.trim() === "GAIP" && pass.value === "2026") {
      err.hidden = true;
      state.authed = true;
      document.getElementById("userPill").hidden = false;
      document.getElementById("logoutBtn").hidden = false;
      go("postlogin");
    } else {
      err.hidden = false;
      card.classList.remove("shake");
      void card.offsetWidth;
      card.classList.add("shake");
    }
  });

  // Brand-mark click replays intro.
  document.getElementById("brandLogo").addEventListener("click", () => {
    if (!introState.finished) return;
    // Re-run the intro as an easter egg.
    introState = { running: false, finished: false };
    const phrase = document.getElementById("introPhrase");
    const brand = document.getElementById("introBrand");
    const tagline = document.getElementById("introTagline");
    const skip = document.getElementById("introSkip");
    const loginCard = document.getElementById("loginCard");

    document.querySelectorAll("section.screen").forEach((el) => el.classList.remove("active"));
    document.getElementById("screen-splash").classList.add("active");
    // Restore the stage container for the replay.
    document.getElementById("introStage").style.display = "";
    phrase.style.display = "";
    phrase.style.opacity = "";
    phrase.classList.remove("entered");
    // restore inner spans (the I that flew may have lingering transforms)
    document.getElementById("flyingI").style.transform = "";
    document.getElementById("flyingI").style.color = "";
    phrase.querySelectorAll(".word").forEach((w) => { w.style.opacity = ""; });
    phrase.querySelector(".word.w-x402 .x").style.color = "";
    phrase.querySelector(".word.w-x402 .x").style.transform = "";
    phrase.querySelector(".word.w-insurance .ns").style.opacity = "";
    phrase.querySelector(".word.w-insurance .ns").style.transform = "";
    brand.hidden = true;
    document.getElementById("brandI").classList.remove("lit");
    tagline.hidden = true;
    skip.style.display = "";
    loginCard.hidden = true;
    runIntro();
  });
}

register("splash", {
  onEnter() {
    if (!introState.finished) {
      runIntro();
    } else {
      snapToLoggedOutRest();
    }
  },
});

export function bootSplash() {
  setupSkip();
  setupLogin();
}
