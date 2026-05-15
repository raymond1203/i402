import { register, go, state } from "../state.js";

function spawnConfetti(container) {
  container.innerHTML = "";
  const palette = ["#00c573", "#3ecf8e", "#fafafa", "#1f4b37"];
  for (let i = 0; i < 60; i++) {
    const piece = document.createElement("span");
    piece.className = "confetti-piece";
    piece.style.left = `${50 + (Math.random() - 0.5) * 20}%`;
    piece.style.top = `${50}%`;
    piece.style.background = palette[i % palette.length];
    piece.style.setProperty("--px", `${(Math.random() - 0.5) * 600}px`);
    piece.style.setProperty("--py", `${-200 - Math.random() * 200}px`);
    piece.style.animationDelay = `${Math.random() * 200}ms`;
    container.appendChild(piece);
  }
}

register("result", {
  onEnter() {
    const v = state.underwritingVerdict ?? "WINNER";
    const head = document.getElementById("resultHeadline");
    const sub = document.getElementById("resultSub");
    const next = document.getElementById("resultNextBtn");
    const back = document.getElementById("resultBackBtn");
    const confetti = document.getElementById("confetti");
    head.classList.remove("defeat");

    if (v === "WINNER") {
      head.textContent = "WINNER";
      sub.textContent = "all paper-anchored thresholds cleared";
      next.style.display = "";
      next.textContent = "Check Monthly Premium →";
      spawnConfetti(confetti);
    } else {
      head.textContent = "DEFEAT";
      sub.textContent = "your agent failed one or more paper-anchored thresholds";
      head.classList.add("defeat");
      next.style.display = "none";
      confetti.innerHTML = "";
    }

    // Footnote — Stage 2 is always the adaptive attacker; surface
    // how many patterns the attacker logged before giving up.
    const mem = state.lastArenaMemory || 0;
    const modeEl = document.getElementById("resultMode");
    const modeVal = document.getElementById("resultModeVal");
    if (modeEl && modeVal) {
      modeVal.textContent = `ADAPTIVE attacker · ${mem} patterns logged`;
      modeEl.hidden = false;
    }
  },
});

export function bootResult() {
  document.getElementById("resultBackBtn").addEventListener("click", () => go("dashboard"));
  document.getElementById("resultNextBtn").addEventListener("click", () => go("premium"));
}
