import { register, go, state } from "../state.js";
import { NFT_RECORD } from "../data.js";

function sleep(ms) { return new Promise((r) => setTimeout(r, ms)); }

function typeOut(el, text, perChar = 12) {
  el.textContent = "";
  return new Promise((res) => {
    let i = 0;
    const tick = () => {
      el.textContent = text.slice(0, i++);
      if (i <= text.length) setTimeout(tick, perChar);
      else res();
    };
    tick();
  });
}

async function runMint() {
  const a = state.agent;
  const hash = a?.identityHash ?? "0x76dd0104ddeaf5ac6f8eaa1be51908d223920831a71cab216a515c9930aba591";

  document.getElementById("nftStep1").hidden = false;
  document.getElementById("nftStep2").hidden = true;
  document.getElementById("nftStep3").hidden = true;
  document.getElementById("announceNft").hidden = true;

  const code1 = document.getElementById("nftHashCode");
  await typeOut(
    code1,
    `> sha256(canonical_json(applicant))\n  agent_name      ${a?.name ?? "safe_paybot.json"}\n  model           ${a?.model ?? "claude-sonnet-4-6"}\n  wallet          ${a?.walletAddress ?? "0x5afe…00bb"}\n  facilitator     ${a?.facilitator ?? "ace-demo-facilitator"}\n  → identity_hash = ${hash}`,
    6,
  );
  await sleep(400);

  document.getElementById("nftStep2").hidden = false;
  await typeOut(
    document.getElementById("nftMintCode"),
    `> contract.mintCertificate(\n    to:           ${NFT_RECORD.contract.slice(0, 10)}…(underwriter),\n    agent_name:   "${a?.name ?? "safe_paybot"}",\n    identityHash: ${hash},\n    agentURI:     "file://reports/${a?.name?.replace('.json','') ?? 'safe_paybot'}_registration.json"\n  )`,
    6,
  );
  await sleep(1800);

  // Step 2 is now confirmed — swap the spinner for a green check and
  // update the text so it doesn't keep spinning forever after the mint lands.
  const spinner = document.getElementById("nftSpinner");
  if (spinner) {
    spinner.classList.remove("spinner");
    spinner.classList.add("nft-check");
    spinner.textContent = "✓";
  }
  const pendingText = document.getElementById("nftPendingText");
  if (pendingText) pendingText.textContent = "Confirmed on Sepolia";
  const pending = document.getElementById("nftPending");
  if (pending) pending.classList.add("nft-pending-done");

  document.getElementById("nftStep3").hidden = false;
  document.getElementById("nftTokenLine").textContent = `Token #${NFT_RECORD.tokenId}`;
  document.getElementById("nftContract").textContent = NFT_RECORD.contract;
  const txLink = document.getElementById("nftTxLink");
  txLink.textContent = NFT_RECORD.txHash;
  txLink.href = NFT_RECORD.explorerUrl;
  document.getElementById("nftHashLine").textContent = hash;

  // Announce
  document.getElementById("announceNft").hidden = false;
  setTimeout(() => { document.getElementById("announceNft").hidden = true; }, 5000);

  // Mark cert issuance time
  state.certIssuedAt = Date.now();
  state.certDaysAdded = 0;
}

function setupMismatchDemo() {
  const toggle = document.getElementById("mismatchToggle");
  const detail = document.getElementById("mismatchDetail");
  const promptEl = document.getElementById("mismatchPrompt");
  const hashEl = document.getElementById("mismatchHash");

  let open = false;
  toggle.addEventListener("click", async () => {
    open = !open;
    detail.hidden = !open;
    if (!open) return;
    const original = state.agent?.systemPromptPreview ?? "You are SafePayBot, an agent that pays for x402 API services on behalf of the user.\n\nOPERATING RULES (immutable — these take precedence) ...";
    promptEl.textContent = original;
    hashEl.textContent = state.agent?.identityHash ?? "0x76dd…";

    await sleep(600);
    // Animate the trailing space being appended.
    promptEl.innerHTML = original + '<span class="mismatch-hash-changed"> ·</span>';
    // Cycle hash digits to give the morph feel.
    const newHash = "0xdab1ba551020418445393472cc96f0a6314b4e1c132a10a1df43c052928fd5c4";
    for (let i = 0; i < 24; i++) {
      hashEl.innerHTML = randomCycle(newHash, i / 24);
      await sleep(40);
    }
    hashEl.innerHTML = `<span class="mismatch-hash-changed">${newHash}</span>`;

    await sleep(300);
    const v = document.getElementById("voidOverlay");
    v.hidden = false;
    setTimeout(() => { v.hidden = true; }, 2400);
  });
}

function randomCycle(target, progress) {
  const chars = "0123456789abcdef";
  let out = "0x";
  for (let i = 2; i < target.length; i++) {
    if (Math.random() < progress) out += target[i];
    else out += chars[Math.floor(Math.random() * 16)];
  }
  return out;
}

register("nft", {
  onEnter() { setTimeout(runMint, 200); },
});

export function bootNft() {
  document.getElementById("nftNextBtn").addEventListener("click", () => go("payment"));
  setupMismatchDemo();
}
