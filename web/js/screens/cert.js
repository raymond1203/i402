import { register, go } from "../state.js";

function fmt(d) {
  return d.toISOString().slice(0, 10);
}

register("cert", {
  onEnter() {
    const start = new Date();
    const end = new Date(Date.now() + 180 * 24 * 60 * 60 * 1000);
    document.getElementById("certStart").textContent = fmt(start);
    document.getElementById("certEnd").textContent = fmt(end);
  },
});

export function bootCert() {
  document.getElementById("certNextBtn").addEventListener("click", () => go("nft"));
}
