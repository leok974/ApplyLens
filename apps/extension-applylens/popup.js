import { APPLYLENS_API_BASE } from "./config.js";
import { clearFormMemory } from "./learning/formMemory.js";

const apiEl = document.getElementById("api");
const profileEl = document.getElementById("profile");
const histApps = document.getElementById("hist-apps");
const histOut = document.getElementById("hist-out");
const learningEnabled = document.getElementById("learning-enabled");
const resetLearningBtn = document.getElementById("reset-learning");

// Helper: retry sendMessage if service worker isn't ready
async function sendMessageWithRetry(message, maxRetries = 3, delayMs = 100) {
  for (let i = 0; i < maxRetries; i++) {
    try {
      return await chrome.runtime.sendMessage(message);
    } catch (err) {
      if (i === maxRetries - 1 || !err.message?.includes("Receiving end does not exist")) {
        throw err;
      }
      await new Promise(resolve => setTimeout(resolve, delayMs));
    }
  }
}

function renderList(ul, items, fmt) {
  ul.innerHTML = "";
  for (const it of (items || []).slice(0, 8)) {
    const li = document.createElement("li");
    li.textContent = fmt(it);
    ul.appendChild(li);
  }
}

(async () => {
  apiEl.textContent = APPLYLENS_API_BASE;
  try {
    const resp = await sendMessageWithRetry({ type: "GET_PROFILE" });
    profileEl.innerHTML = resp?.ok
      ? `<span class="ok">${resp.data?.name || "OK"}</span>`
      : `<span class="bad">profile error</span>`;
  } catch {
    profileEl.innerHTML = `<span class="bad">offline</span>`;
  }

  // Load local history
  try {
    const res = await sendMessageWithRetry({ type: "GET_HISTORY" });
    if (res?.ok) {
      renderList(histApps, res.applications, (x) => `${x.company ?? "?"} — ${x.role ?? "?"} (${x.ts?.slice(0,16).replace('T',' ')})`);
      renderList(histOut, res.outreach, (x) => `${x.company ?? "?"} — ${x.recruiter_name ?? "Recruiter"} (${x.ts?.slice(0,16).replace('T',' ')})`);
    }
  } catch {}

  // Load learning settings
  try {
    const settings = await chrome.storage.sync.get(["learningEnabled"]);
    learningEnabled.checked = settings.learningEnabled !== false; // Default to true
  } catch {}
})();

document.getElementById("scan").addEventListener("click", async () => {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  await chrome.tabs.sendMessage(tab.id, { type: "SCAN_AND_SUGGEST" }).catch(() => {});
  window.close();
});

document.getElementById("dm").addEventListener("click", async () => {
  const name = prompt("Recruiter name (e.g., Jane Doe):") || "Recruiter";
  const headline = prompt("Headline (optional):") || "";
  const company = prompt("Company:") || "Company";
  const jobTitle = prompt("Target job title:") || "AI Engineer";
  const jobUrl = prompt("Job link (optional):") || "";

  const payload = { profile: { name, headline, company, profile_url: location.href }, job: { title: jobTitle, url: jobUrl } };
  const r = await sendMessageWithRetry({ type: "GEN_DM", payload });
  if (r?.ok) {
    const msg = r.data?.message || "(no message)";
    await navigator.clipboard.writeText(msg).catch(()=>{});
    alert("Draft copied to clipboard.\nPaste in LinkedIn.");
    await sendMessageWithRetry({
      type: "LOG_OUTREACH",
      payload: { company, role: jobTitle, recruiter_name: name, recruiter_profile_url: location.href, message_preview: msg.slice(0,140), source: "browser_extension" }
    }).catch(()=>{});
    window.close();
  } else {
    alert("Failed to draft DM");
  }
});

// Learning settings handlers
learningEnabled.addEventListener("change", async () => {
  await chrome.storage.sync.set({ learningEnabled: learningEnabled.checked });
});

resetLearningBtn.addEventListener("click", async () => {
  if (confirm("Reset all learning data? This cannot be undone.")) {
    await clearFormMemory();
    alert("Learning data cleared.");
  }
});
