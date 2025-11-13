// content.js — adds a lightweight review panel for form answers with learning
import { APPLYLENS_API_BASE } from "./config.js";
import { loadFormMemory, saveFormMemory } from "./learning/formMemory.js";
import { queueLearningEvent, flushLearningEvents } from "./learning/client.js";
import { computeSchemaHash, editDistance } from "./learning/utils.js";
import { fetchLearningProfile } from "./learning.profileClient.js";
import { mergeSelectorMaps } from "./learning.mergeMaps.js";

const PANEL_ID = "__applylens_panel__";
const STYLE_ID = "__applylens_panel_style__";

// Learning state
let learningStartTime = null;
let suggestedMap = {};
let finalMap = {};

function injectStyles() {
  if (document.getElementById(STYLE_ID)) return;
  const css = `
  #${PANEL_ID} {
    position: fixed; top: 16px; right: 16px; z-index: 2147483646;
    width: 360px; max-height: 70vh; overflow: auto;
    background: #0f172a; color: #e2e8f0; border: 1px solid #334155; border-radius: 12px;
    box-shadow: 0 10px 30px rgba(0,0,0,.35); font: 13px/1.4 system-ui, -apple-system, Segoe UI, Roboto, Inter, sans-serif;
  }
  #${PANEL_ID} header {
    display: flex; align-items: center; justify-content: space-between;
    padding: 10px 12px; border-bottom: 1px solid #334155; font-weight: 600;
  }
  #${PANEL_ID} .body { padding: 10px 12px; }
  #${PANEL_ID} .row {
    border: 1px solid #334155; border-radius: 8px; padding: 8px; margin-bottom: 10px; background:#0b1220;
  }
  #${PANEL_ID} .label { color:#94a3b8; margin-bottom:6px; font-size:12px; }
  #${PANEL_ID} textarea {
    width: 100%; min-height: 86px; padding: 8px; border-radius: 8px; border: 1px solid #334155;
    background: #0a0f1c; color: #e2e8f0; resize: vertical;
  }
  #${PANEL_ID} .actions { display:flex; gap:8px; margin-top:8px; }
  #${PANEL_ID} button {
    border:1px solid #334155; background:#111827; color:#e5e7eb; padding:6px 10px; border-radius:8px; cursor:pointer;
  }
  #${PANEL_ID} button.primary { background:#2563eb; border-color:#1d4ed8; }
  #${PANEL_ID} .footer { display:flex; gap:8px; padding:10px 12px; border-top:1px solid #334155; }
  #${PANEL_ID} .muted { color:#94a3b8; }
  `;
  const style = document.createElement("style");
  style.id = STYLE_ID;
  style.textContent = css;
  document.documentElement.appendChild(style);
}

function uniqueSelector(el) {
  if (!el || !el.tagName) return null;
  if (el.id) return `#${CSS.escape(el.id)}`;
  const name = el.getAttribute?.("name");
  if (name) return `${el.tagName.toLowerCase()}[name="${CSS.escape(name)}"]`;
  // fallback path
  const parts = [];
  let n = el;
  while (n && n.nodeType === 1 && parts.length < 4) {
    let seg = n.tagName.toLowerCase();
    if (n.id) { seg += `#${n.id}`; parts.unshift(seg); break; }
    const sibs = Array.from(n.parentElement?.children || []).filter(e => e.tagName === n.tagName);
    if (sibs.length > 1) seg += `:nth-of-type(${sibs.indexOf(n)+1})`;
    parts.unshift(seg); n = n.parentElement;
  }
  return parts.join(" > ");
}

function scanFields() {
  const fields = [];
  const candidates = Array.from(document.querySelectorAll("textarea, input[type='text'], input[type='email'], input[type='url'], input[type='search']"));
  for (const el of candidates) {
    const sel = uniqueSelector(el);
    if (!sel) continue;
    let label = "";
    const id = el.getAttribute("id");
    if (id) {
      const lab = document.querySelector(`label[for="${CSS.escape(id)}"]`);
      if (lab) label = lab.textContent.trim();
    }
    if (!label) {
      const labUp = el.closest("label"); if (labUp) label = labUp.textContent.trim();
    }
    const placeholder = el.getAttribute("placeholder") || "";
    const type = el.tagName.toLowerCase();
    const field_id = id || el.getAttribute("name") || sel;
    fields.push({ field_id, label: label || placeholder || field_id, type, selector: sel });
  }
  return fields;
}

function getPageContext() {
  // Try to infer company & title from common ATS/SEO patterns
  const title = (document.querySelector("h1")?.textContent || document.title || "").trim().slice(0,140);
  const metaCompany = document.querySelector('meta[property="og:site_name"]')?.content
    || document.querySelector('meta[name="application-name"]')?.content
    || location.host;
  return {
    job: { title: title || "AI Engineer", company: metaCompany, url: location.href }
  };
}

async function fetchFormAnswers(job, fields) {
  const res = await fetch(`${APPLYLENS_API_BASE}/api/extension/generate-form-answers`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ job, fields }),
    credentials: "omit",
  });
  if (!res.ok) throw new Error(`gen answers failed: ${res.status}`);
  return res.json(); // { job, answers: [ { field_id, answer } ] }
}

function mountPanel() {
  injectStyles();
  let panel = document.getElementById(PANEL_ID);
  if (panel) panel.remove();

  panel = document.createElement("aside");
  panel.id = PANEL_ID;
  panel.innerHTML = `
    <header>
      <div>ApplyLens — Review answers</div>
      <button id="al_close" title="Close">✕</button>
    </header>
    <div class="body" id="al_body">
      <div class="muted">Scanning form…</div>
    </div>
    <div class="footer">
      <button id="al_fill_all" class="primary">Fill all</button>
      <button id="al_cancel">Cancel</button>
    </div>
  `;
  document.documentElement.appendChild(panel);
  panel.querySelector("#al_close").onclick = () => panel.remove();
  panel.querySelector("#al_cancel").onclick = () => panel.remove();
  return panel;
}

function renderAnswers(panel, answers, fields) {
  const map = new Map(answers.map(a => [a.field_id, a.answer]));
  const body = panel.querySelector("#al_body");
  body.innerHTML = "";
  for (const f of fields) {
    const current = map.get(f.field_id) || "";
    const row = document.createElement("div");
    row.className = "row";
    row.innerHTML = `
      <div class="label">${f.label}</div>
      <textarea data-field="${encodeURIComponent(f.field_id)}">${current}</textarea>
      <div class="actions">
        <button data-act="apply" data-field="${encodeURIComponent(f.field_id)}">Apply</button>
        <button data-act="skip" data-field="${encodeURIComponent(f.field_id)}">Skip</button>
      </div>
    `;
    body.appendChild(row);

    // Store original generated value for edit tracking
    const textarea = row.querySelector("textarea");
    if (textarea) {
      textarea.defaultValue = current;
    }
  }

  body.addEventListener("click", (e) => {
    const btn = e.target.closest("button[data-act]");
    if (!btn) return;
    const fieldId = decodeURIComponent(btn.getAttribute("data-field"));
    const f = fields.find(x => x.field_id === fieldId);
    if (!f) return;
    const ta = body.querySelector(`textarea[data-field="${encodeURIComponent(fieldId)}"]`);
    const val = ta?.value || "";
    const el = document.querySelector(f.selector);
    if (el) {
      if (el.tagName.toLowerCase() === "textarea" || el.tagName.toLowerCase() === "input") {
        el.focus(); el.value = val; el.dispatchEvent(new Event("input", { bubbles: true }));
        el.dispatchEvent(new Event("change", { bubbles: true }));
      }
    }
    btn.textContent = "Applied";
    btn.disabled = true;
  });

  panel.querySelector("#al_fill_all").onclick = () => {
    for (const f of fields) {
      const ta = body.querySelector(`textarea[data-field="${encodeURIComponent(f.field_id)}"]`);
      const val = ta?.value || "";
      const el = document.querySelector(f.selector);
      if (el) {
        el.focus(); el.value = val; el.dispatchEvent(new Event("input", { bubbles: true }));
        el.dispatchEvent(new Event("change", { bubbles: true }));
      }
    }
  };
}

async function runScanAndSuggest() {
  const panel = mountPanel();
  const body = panel.querySelector("#al_body");
  learningStartTime = Date.now();

  try {
    const fields = scanFields();
    if (!fields.length) { body.innerHTML = `<div class="muted">No form fields detected.</div>`; return; }

    const ctx = getPageContext();
    const host = location.host;
    const schemaHash = computeSchemaHash(fields);

    console.log(`[Learning] Phase 2.1: Host: ${host}, Schema: ${schemaHash}`);

    // Phase 2.1: Load FormMemory AND fetch server profile in parallel
    const [formMemory, profile] = await Promise.all([
      loadFormMemory(host, schemaHash),
      fetchLearningProfile(host, schemaHash)
    ]);

    // Merge server canonical map with local memory
    const serverMap = profile?.canonicalMap || {};
    const localMap = formMemory?.selectorMap || {};
    const effectiveMap = mergeSelectorMaps(serverMap, localMap);

    console.log("[Learning] Effective mapping:");
    console.log("  Server:", Object.keys(serverMap).length, "mappings");
    console.log("  Local:", Object.keys(localMap).length, "mappings");
    console.log("  Merged:", Object.keys(effectiveMap).length, "mappings");

    // Log style hint if available
    if (profile?.styleHint) {
      console.log(`[Learning] Style hint: ${profile.styleHint.genStyleId} (${(profile.styleHint.confidence * 100).toFixed(0)}% confidence)`);
    }

    const data = await fetchFormAnswers(ctx.job, fields);

    // Build suggested map for learning (now incorporating effective mappings)
    suggestedMap = {};
    let learnedMappingCount = 0;
    let heuristicMappingCount = 0;

    for (const ans of (data.answers || [])) {
      const field = fields.find(f => f.field_id === ans.field_id);
      if (field) {
        // Check if we have a learned mapping for this field
        if (effectiveMap[field.selector]) {
          // Use learned mapping
          suggestedMap[field.selector] = effectiveMap[field.selector];
          learnedMappingCount++;
          console.log(`[Learning] ✅ Using learned mapping: ${field.selector} → ${effectiveMap[field.selector]}`);
        } else {
          // Fall back to generated field_id (original heuristic behavior)
          suggestedMap[field.selector] = ans.field_id;
          heuristicMappingCount++;
          console.log(`[Learning] 🔍 Using heuristic: ${field.selector} → ${ans.field_id}`);
        }
      }
    }

    console.log(`[Learning] Mapping summary: ${learnedMappingCount} learned, ${heuristicMappingCount} heuristic`);

    renderAnswers(panel, data.answers || [], fields);

    // Setup learning tracking on Fill All
    const fillAllBtn = panel.querySelector("#al_fill_all");
    const originalFillAll = fillAllBtn.onclick;
    fillAllBtn.onclick = async () => {
      originalFillAll();
      await trackAutofillCompletion(host, schemaHash, fields, body);
    };

    // log application (best-effort)
    try {
      await chrome.runtime?.sendMessage?.({ type: "LOG_APPLICATION", payload: {
        company: ctx.job.company, role: ctx.job.title, job_url: ctx.job.url,
        source: "browser_extension", notes: "Scan & review"
      }});
    } catch {}
  } catch (e) {
    body.innerHTML = `<div class="muted">Error: ${String(e)}</div>`;
  }
}

async function trackAutofillCompletion(host, schemaHash, fields, panelBody) {
  // Check if learning is enabled
  try {
    const settings = await chrome.storage.sync.get(["learningEnabled"]);
    if (settings.learningEnabled === false) {
      console.log("[Learning] Disabled by user settings");
      return;
    }
  } catch (err) {
    console.warn("[Learning] Failed to check settings, skipping:", err);
    return;
  }

  const durationMs = Date.now() - learningStartTime;

  // Build final map and calculate edit stats
  finalMap = {};
  const editStats = {
    totalCharsAdded: 0,
    totalCharsDeleted: 0,
    perField: {}
  };

  for (const field of fields) {
    const textarea = panelBody.querySelector(`textarea[data-field="${encodeURIComponent(field.field_id)}"]`);
    const generatedValue = textarea?.defaultValue || "";
    const finalValue = textarea?.value || "";

    if (finalValue) {
      finalMap[field.selector] = field.field_id;

      // Calculate edit distance
      const distance = editDistance(generatedValue, finalValue);
      const charsAdded = Math.max(0, finalValue.length - generatedValue.length);
      const charsDeleted = Math.max(0, generatedValue.length - finalValue.length);

      editStats.totalCharsAdded += charsAdded;
      editStats.totalCharsDeleted += charsDeleted;
      editStats.perField[field.selector] = {
        added: charsAdded,
        deleted: charsDeleted,
        editDistance: distance
      };
    }
  }

  // Queue learning event
  const event = {
    host,
    schemaHash,
    suggestedMap,
    finalMap,
    editStats,
    durationMs,
    validationErrors: {},
    status: "ok"
  };

  queueLearningEvent(event);
  await flushLearningEvents();

  // Update form memory
  const formMemory = {
    host,
    schemaHash,
    selectorMap: finalMap,
    stats: {
      totalRuns: (await loadFormMemory(host, schemaHash))?.stats?.totalRuns || 0 + 1,
      lastUsedAt: new Date().toISOString()
    }
  };

  await saveFormMemory(formMemory);
  console.log("[Learning] Saved form memory and queued event");
}

// Listen for SW messages and devtools test hook
chrome.runtime?.onMessage?.addListener((msg, _sender, _sendResponse) => {
  if (msg?.type === "SCAN_AND_SUGGEST") runScanAndSuggest();
});

// Simple global for E2E to call directly
window.__APPLYLENS__ = { runScanAndSuggest, scanFields };
