import { register, go, state } from "../state.js";
import { renderPolicy } from "./dashboard.js";

register("payment", {
  onEnter() {
    document.getElementById("paymentForm").hidden = false;
    document.getElementById("paymentResult").hidden = true;
    document.getElementById("announcePolicy").hidden = true;
  },
});

export function bootPayment() {
  const form = document.getElementById("paymentForm");
  const result = document.getElementById("paymentResult");
  const btn = document.getElementById("payBtn");

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> &nbsp; Processing…';
    await new Promise((r) => setTimeout(r, 1800));
    form.hidden = true;
    result.hidden = false;
    state.policyActive = true;
    document.getElementById("announcePolicy").hidden = false;
    setTimeout(() => { document.getElementById("announcePolicy").hidden = true; }, 5000);
    btn.disabled = false;
    btn.innerHTML = "Pay & Activate Coverage";
  });

  document.getElementById("payDoneBtn").addEventListener("click", () => {
    go("dashboard");
    renderPolicy();
  });
}
