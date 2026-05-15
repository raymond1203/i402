import { register, go, state } from "../state.js";

function animateCounter(el, target, duration = 1200) {
  const start = performance.now();
  function step(now) {
    const t = Math.min(1, (now - start) / duration);
    const eased = 1 - Math.pow(1 - t, 3);
    el.textContent = Math.round(target * eased).toString();
    if (t < 1) requestAnimationFrame(step);
  }
  requestAnimationFrame(step);
}

register("premium", {
  onEnter() {
    const amount = state.agent?.monthlyPremiumUsd ?? 42;
    const el = document.getElementById("premiumAmount");
    el.textContent = "0";
    setTimeout(() => animateCounter(el, amount), 400);
  },
});

export function bootPremium() {
  document.getElementById("premiumNextBtn").addEventListener("click", () => go("cert"));
}
