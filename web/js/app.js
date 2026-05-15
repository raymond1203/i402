// I402 — app entry.

import { go } from "./state.js";

// Import screens (each registers itself on load).
import { bootSplash } from "./screens/splash.js";
import { bootPostLogin } from "./screens/postlogin.js";
import { bootDashboard } from "./screens/dashboard.js";
import { bootArena } from "./screens/arena.js";
import { bootResult } from "./screens/result.js";
import { bootPremium } from "./screens/premium.js";
import { bootCert } from "./screens/cert.js";
import { bootNft } from "./screens/nft.js";
import { bootPayment } from "./screens/payment.js";
import { bootTutorial } from "./tutorial.js";

function boot() {
  bootSplash();
  bootPostLogin();
  bootDashboard();
  bootArena();
  bootResult();
  bootPremium();
  bootCert();
  bootNft();
  bootPayment();
  bootTutorial();

  go("splash");
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", boot);
} else {
  boot();
}
