import { register, go, state } from "../state.js";
import { SAMPLE_AGENTS } from "../data.js";

// v2 cinematic flow: there is no file picker, no "Add agent" stage.
// On first entry the dashboard auto-loads safe_paybot (the WINNER-path
// reference agent). BYO is handled exclusively via the backend CLI
// (`uv run python -m demo.run_demo --agents my_agent`).
const DEFAULT_AGENT_NAME = "safe_paybot.json";

function ensureAgentLoaded() {
  if (state.agent) return;
  const fallback = SAMPLE_AGENTS.find((a) => a.name === DEFAULT_AGENT_NAME)
    || SAMPLE_AGENTS[0];
  if (fallback) state.agent = fallback;
}

function renderLoaded(agent) {
  document.getElementById("loadedAgentName").textContent = agent.name;
  document.getElementById("loadedModel").textContent = agent.model;
  document.getElementById("loadedHash").textContent = agent.identityHash;
  document.getElementById("loadedFacilitator").textContent = agent.facilitator;
  document.getElementById("loadedWallet").textContent = agent.walletAddress;
  const pill = document.getElementById("loadedAgentRisk");
  pill.textContent = `RISK: ${agent.risk.toUpperCase()}`;
  pill.className = "pill " + (agent.risk === "low" ? "pill-active"
                              : agent.risk === "medium" ? "pill-warn"
                              : "pill-alert");
}

function renderPolicy() {
  if (!state.policyActive) {
    document.getElementById("policyEmpty").hidden = false;
    document.getElementById("policyActive").hidden = true;
    return;
  }
  document.getElementById("policyEmpty").hidden = true;
  document.getElementById("policyActive").hidden = false;
  document.getElementById("policyPremium").textContent = state.agent?.monthlyPremiumUsd ?? 42;

  const daysLeft = computeDaysLeft();
  const countdown = document.getElementById("policyCountdown");
  const pill = document.getElementById("policyStatusPill");
  if (daysLeft <= 0) {
    countdown.textContent = "EXPIRED — coverage cancelled";
    pill.className = "pill pill-alert";
    pill.innerHTML = '<span class="pill-dot"></span>COVERAGE CANCELLED';
  } else if (daysLeft <= 7) {
    countdown.textContent = `${daysLeft} days remaining — RE-CERT URGENT`;
    pill.className = "pill pill-alert";
    pill.innerHTML = '<span class="pill-dot"></span>RE-CERT URGENT';
  } else if (daysLeft <= 30) {
    countdown.textContent = `${daysLeft} days remaining — re-cert due soon`;
    pill.className = "pill pill-warn";
    pill.innerHTML = '<span class="pill-dot"></span>RE-CERT DUE SOON';
  } else {
    countdown.textContent = `${daysLeft} days remaining`;
    pill.className = "pill pill-active";
    pill.innerHTML = '<span class="pill-dot"></span>ACTIVE';
  }
}

function computeDaysLeft() {
  if (!state.certIssuedAt) return 180;
  const total = 180 - state.certDaysAdded;
  const elapsed = Math.floor((Date.now() - state.certIssuedAt) / (1000 * 60 * 60 * 24));
  return Math.max(0, total - elapsed);
}

export function refreshDashboard() {
  ensureAgentLoaded();
  if (state.agent) renderLoaded(state.agent);
  renderPolicy();
}

register("dashboard", {
  onEnter: refreshDashboard,
});

export function bootDashboard() {
  document.getElementById("startReviewBtn").addEventListener("click", () => {
    if (!state.agent) return;
    go("arena");
  });

  document.getElementById("fastForwardBtn").addEventListener("click", () => {
    state.certDaysAdded += 180;
    renderPolicy();
  });
  document.getElementById("recertifyBtn").addEventListener("click", () => {
    state.certIssuedAt = Date.now();
    state.certDaysAdded = 0;
    renderPolicy();
  });

  document.getElementById("logoutBtn").addEventListener("click", () => {
    state.authed = false;
    state.agent = null;
    state.policyActive = false;
    document.getElementById("userPill").hidden = true;
    document.getElementById("logoutBtn").hidden = true;
    go("splash");
  });
}

export { renderPolicy };
