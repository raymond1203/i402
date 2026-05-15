// Central state + screen registry.
// Screens register themselves with `register()` providing onEnter/onExit hooks.

const screens = new Map();
let current = null;
let history = [];

export const state = {
  authed: false,
  agent: null,            // selected agent object from SAMPLE_AGENTS
  underwritingVerdict: null, // "WINNER" | "DEFEAT"
  policyActive: false,
  certIssuedAt: null,     // Date when NFT minted (mock)
  certDaysAdded: 0,       // debug fast-forward
  tutorialActive: false,
  lastArenaMemory: 0,     // adaptive attacker memory count at last verdict
};

export function register(name, hooks) {
  screens.set(name, hooks);
}

export function go(name, payload = {}) {
  if (current === name) return;
  const prevName = current;
  const prev = current && screens.get(current);
  const next = screens.get(name);
  if (!next) {
    console.error("unknown screen:", name);
    return;
  }

  // hide all
  document.querySelectorAll("section.screen").forEach((el) => el.classList.remove("active"));
  const el = document.getElementById(`screen-${name}`);
  if (!el) {
    console.error("screen element missing for:", name);
    return;
  }

  if (prev?.onExit) prev.onExit({ from: prevName, to: name });
  el.classList.add("active");
  current = name;
  history.push(name);
  if (next.onEnter) next.onEnter(payload);
}

export function currentScreen() { return current; }
