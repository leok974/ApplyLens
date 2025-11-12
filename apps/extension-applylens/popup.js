import { APPLYLENS_API_BASE } from "./config.js";

const apiEl = document.getElementById("api");
const profileEl = document.getElementById("profile");

(async () => {
  apiEl.textContent = APPLYLENS_API_BASE;
  try {
    const resp = await chrome.runtime.sendMessage({ type: "GET_PROFILE" });
    if (resp?.ok) {
      profileEl.innerHTML = `<span class="ok">${resp.data?.name || "OK"}</span>`;
    } else {
      profileEl.innerHTML = `<span class="bad">profile error</span>`;
    }
  } catch {
    profileEl.innerHTML = `<span class="bad">offline</span>`;
  }
})();

document.getElementById("scan").addEventListener("click", async () => {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  const resp = await chrome.tabs.sendMessage(tab.id, { type: "SCAN_AND_SUGGEST" });
  window.close();
});

document.getElementById("dm").addEventListener("click", async () => {
  // naive LinkedIn scrape via content-script (just prompt for now)
  const name = prompt("Recruiter name (e.g., Jane Doe):") || "Recruiter";
  const headline = prompt("Headline (optional):") || "";
  const company = prompt("Company:") || "Company";
  const jobTitle = prompt("Target job title:") || "AI Engineer";
  const jobUrl = prompt("Job link (optional):") || "";

  const payload = {
    profile: { name, headline, company, profile_url: location.href },
    job: { title: jobTitle, url: jobUrl }
  };
  const resp = await chrome.runtime.sendMessage({ type: "GEN_DM", payload });
  if (resp?.ok) {
    const msg = resp.data?.message || "(no message)";
    await navigator.clipboard.writeText(msg);
    alert("Draft copied to clipboard. Paste in LinkedIn.");
    // log outreach
    await chrome.runtime.sendMessage({
      type: "LOG_OUTREACH",
      payload: { company, role: jobTitle, recruiter_name: name, recruiter_profile_url: location.href, message_preview: msg.slice(0, 140), source: "browser_extension" }
    });
    window.close();
  } else {
    alert("Failed to draft DM");
  }
});
