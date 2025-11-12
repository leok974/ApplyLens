function uniqueSelector(el) {
  if (!el) return "";
  if (el.id) return `#${CSS.escape(el.id)}`;
  const parts = [];
  while (el && el.nodeType === 1 && parts.length < 5) {
    let sel = el.nodeName.toLowerCase();
    if (el.classList?.length) {
      sel += "." + [...el.classList].slice(0, 2).map(c => CSS.escape(c)).join(".");
    }
    const sibs = [...(el.parentNode?.children || [])].filter(n => n.nodeName === el.nodeName);
    if (sibs.length > 1) sel += `:nth-of-type(${sibs.indexOf(el) + 1})`;
    parts.unshift(sel);
    el = el.parentElement;
  }
  return parts.join(" > ");
}

function scanForm() {
  const fields = [];
  const inputs = document.querySelectorAll("input, textarea, select");
  inputs.forEach((el, idx) => {
    const id = el.id || `field_${idx}`;
    let label = "";
    if (el.labels && el.labels.length) {
      label = [...el.labels].map(l => l.innerText.trim()).join(" ");
    } else {
      const lab = el.closest("label") || el.parentElement?.querySelector("label");
      if (lab) label = lab.innerText.trim();
    }
    fields.push({
      field_id: id,
      label: label || el.placeholder || el.name || id,
      type: el.tagName.toLowerCase(),
      name: el.name || "",
      placeholder: el.placeholder || "",
      selector: uniqueSelector(el)
    });
  });
  return { url: location.href, fields };
}

function fillAnswers(answers) {
  answers.forEach(a => {
    if (!a.field_id && !a.selector) return;
    let el = null;
    if (a.selector) el = document.querySelector(a.selector);
    if (!el && a.field_id) el = document.getElementById(a.field_id);
    if (!el) return;
    if (el.tagName === "TEXTAREA" || el.tagName === "INPUT") {
      el.value = a.answer;
      el.dispatchEvent(new Event("input", { bubbles: true }));
      el.dispatchEvent(new Event("change", { bubbles: true }));
    }
  });
}

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  (async () => {
    if (msg.type === "SCAN_AND_SUGGEST") {
      const scan = scanForm();
      const title = document.querySelector("h1,h2,[data-test='job-title']")?.innerText?.trim() || "";
      const company =
        document.querySelector("[data-company], .company, [itemprop='hiringOrganization']")?.innerText?.trim() || "";
      const payload = {
        job: { title: title || "Unknown", company: company || "Unknown", url: location.href },
        fields: scan.fields.map(f => ({ field_id: f.field_id, label: f.label, type: f.type, selector: f.selector }))
      };
      const resp = await chrome.runtime.sendMessage({ type: "GEN_FORM_ANSWERS", payload });
      if (resp?.ok) fillAnswers(resp.data.answers || []);
      sendResponse(resp);
    }
  })();
  return true;
});

// --- TEST HOOK (no-op unless page sets the flag) ---
if (typeof window !== "undefined" && window.__APPLYLENS_TEST === 1) {
  window.addEventListener("message", (ev) => {
    if (!ev?.data || typeof ev.data !== "object") return;
    if (ev.data.type === "APPLYLENS_TEST_SCAN") {
      // simulate popup → content message
      chrome.runtime?.onMessage?.dispatch?.({ type: "SCAN_AND_SUGGEST" }, {}, () => {});
      // Fallback: call main scan if you expose it as a function
      try {
        if (typeof window.__applylens_scan === "function") window.__applylens_scan();
      } catch {}
    }
  });
}
