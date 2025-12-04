// content.js — adds a lightweight review panel for form answers with learning
import { APPLYLENS_API_BASE } from "./config.js";
import { loadFormMemory, saveFormMemory } from "./learning/formMemory.js";
import { queueLearningEvent, flushLearningEvents } from "./learning/client.js";
import { computeSchemaHash, editDistance } from "./learning/utils.js";
import { fetchLearningProfile } from "./learning.profileClient.js";
import { mergeSelectorMaps } from "./learning.mergeMaps.js";
import { sanitizeGeneratedContent } from "./guardrails.js"; // Phase 3.1

const PANEL_ID = "__applylens_panel__";
const STYLE_ID = "__applylens_panel_style__";

// Learning state
let learningStartTime = null;
let suggestedMap = {};
let finalMap = {};
let currentProfile = null; // Phase 5.0: Store current profile for style tracking

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

// Phase 5.4 — epsilon-greedy bandit
const BANDIT_EPSILON_DEFAULT = 0.15; // 15% explore

function resolveBanditEpsilon() {
  try {
    if (
      typeof window !== "undefined" &&
      typeof window.__APPLYLENS_BANDIT_EPSILON === "number"
    ) {
      return window.__APPLYLENS_BANDIT_EPSILON;
    }
  } catch (e) {
    // ignore
  }
  return BANDIT_EPSILON_DEFAULT;
}

/**
 * Check if bandit exploration is enabled.
 * Reads from window.__APPLYLENS_BANDIT_ENABLED (set by settings or test).
 * Defaults to true if not explicitly set to false.
 */
function isBanditEnabled() {
  try {
    if (
      typeof window !== "undefined" &&
      typeof window.__APPLYLENS_BANDIT_ENABLED === "boolean"
    ) {
      return window.__APPLYLENS_BANDIT_ENABLED;
    }
  } catch (e) {
    // ignore
  }
  return true; // Default: bandit enabled
}

/**
 * styleHint is the normalized object from profileClient:
 * {
 *   preferredStyleId?: string;
 *   styleStats?: {
 *     chosen?: { styleId: string; helpfulRatio?: number; totalRuns?: number; ... };
 *     competitors?: Array<{ styleId: string; helpfulRatio?: number; totalRuns?: number; ... }>;
 *   }
 * }
 */
function pickStyleForBandit(styleHint) {
  if (!styleHint || !styleHint.preferredStyleId) {
    console.log("[Bandit] fallback: no preferredStyleId");
    return { styleId: null, policy: "fallback" };
  }

  const best = styleHint.preferredStyleId;
  const competitors =
    (styleHint.styleStats && styleHint.styleStats.competitors) || [];

  // No competitors → always exploit
  if (!competitors.length) {
    console.log("[Bandit] exploit (no competitors)", best);
    return { styleId: best, policy: "exploit" };
  }

  const epsilon = resolveBanditEpsilon();
  const r = Math.random();

  if (r < epsilon) {
    const idx = Math.floor(Math.random() * competitors.length);
    const candidate = competitors[idx] && competitors[idx].styleId;
    const chosen = candidate || best;
    console.log(
      "[Bandit] explore",
      chosen,
      "ε=" + epsilon,
      "vs best=" + best
    );
    return { styleId: chosen, policy: "explore" };
  }

  console.log("[Bandit] exploit", best, "ε=" + epsilon);
  return { styleId: best, policy: "exploit" };
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

async function fetchFormAnswers(job, fields, styleHint = null) {
  const payload = { job, fields };
  if (styleHint) {
    payload.style_hint = styleHint;
  }

  // Dogfood v0.1: Better error handling with specific messages
  try {
    const res = await fetch(`${APPLYLENS_API_BASE}/api/extension/generate-form-answers`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(payload),
      credentials: "omit",
    });

    if (!res.ok) {
      if (res.status === 401 || res.status === 403) {
        throw new Error("NOT_LOGGED_IN");
      } else if (res.status >= 500) {
        throw new Error("SERVER_ERROR");
      } else {
        throw new Error(`HTTP_${res.status}`);
      }
    }

    return res.json(); // { job, answers: [ { field_id, answer } ] }
  } catch (err) {
    if (err.message.startsWith("HTTP_") || err.message === "NOT_LOGGED_IN" || err.message === "SERVER_ERROR") {
      throw err; // Re-throw known errors
    }
    throw new Error("NETWORK_ERROR"); // Network/fetch failures
  }
}

function mountPanel() {
  injectStyles();
  let panel = document.getElementById(PANEL_ID);
  if (panel) panel.remove();

  panel = document.createElement("aside");
  panel.id = PANEL_ID;
  panel.setAttribute("data-testid", "al-panel"); // Phase 3.0: test attribute
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
    <div style="padding: 12px; border-top: 1px solid #334155; display: flex; align-items: center; gap: 12px; background: #0a0f1c;">
      <span style="font-size: 12px; color: #94a3b8;">How was this?</span>
      <button id="al_feedback_up" data-testid="al-feedback-up" aria-pressed="false" style="background: none; border: 1px solid #334155; border-radius: 4px; padding: 6px 12px; cursor: pointer; color: #94a3b8; font-size: 16px;" title="Helpful">👍</button>
      <button id="al_feedback_down" data-testid="al-feedback-down" aria-pressed="false" style="background: none; border: 1px solid #334155; border-radius: 4px; padding: 6px 12px; cursor: pointer; color: #94a3b8; font-size: 16px;" title="Not helpful">👎</button>
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

  // Phase 3.0: Track row state for UX controls
  const rows = [];

  for (const f of fields) {
    const current = map.get(f.field_id) || "";
    const row = document.createElement("div");
    row.className = "row";
    row.setAttribute("data-testid", "al-answer-row"); // Phase 3.0
    row.setAttribute("data-selector", f.selector); // Phase 3.0

    // Phase 3.0: Row state
    const rowState = {
      selector: f.selector,
      fieldId: f.field_id,
      text: current,
      accepted: true,
      source: "generated"
    };
    rows.push(rowState);

    // Phase 3.0: Build row with checkbox + textarea
    row.innerHTML = `
      <div class="label">
        <input type="checkbox" checked data-testid="al-answer-checkbox" style="margin-right: 6px;">
        ${f.label}
      </div>
      <textarea data-field="${encodeURIComponent(f.field_id)}" data-testid="al-answer-textarea" rows="3">${current}</textarea>
      <div class="actions">
        <button data-act="apply" data-field="${encodeURIComponent(f.field_id)}">Apply</button>
        <button data-act="skip" data-field="${encodeURIComponent(f.field_id)}">Skip</button>
      </div>
    `;
    body.appendChild(row);

    // Store original generated value for edit tracking
    const textarea = row.querySelector("textarea");
    const checkbox = row.querySelector('input[type="checkbox"]');

    if (textarea) {
      textarea.defaultValue = current;
      // Phase 3.0: Track text edits
      textarea.addEventListener("input", () => {
        rowState.text = textarea.value;
        rowState.source = "manual";
      });
    }

    if (checkbox) {
      // Phase 3.0: Track acceptance state
      checkbox.addEventListener("change", () => {
        rowState.accepted = checkbox.checked;
      });
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

  // Phase 3.0: Update Fill All to respect row state
  panel.querySelector("#al_fill_all").onclick = async () => {
    for (const row of rows) {
      if (!row.accepted) continue; // Phase 3.0: Skip unchecked rows

      const el = document.querySelector(row.selector);
      if (!el) continue;

      // Phase 3.0: Use current textarea value (may be edited)
      const val = row.text;
      if ("value" in el) {
        el.focus();
        el.value = val;
        el.dispatchEvent(new Event("input", { bubbles: true }));
        el.dispatchEvent(new Event("change", { bubbles: true }));
      }
    }

    // Track learning event with final state (Phase 5.4: includes ctx with bandit policy)
    await trackAutofillCompletion(location.host, computeSchemaHash(fields), rows, panel.__ctx);
  };

  // Store rows for learning
  panel.__rowsState = rows;

  // Phase 4.0: Wire feedback buttons
  const feedbackUp = panel.querySelector("#al_feedback_up");
  const feedbackDown = panel.querySelector("#al_feedback_down");

  const sendFeedback = async (status) => {
    try {
      await fetch(`${APPLYLENS_API_BASE}/api/extension/feedback/autofill`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          host: location.host,
          schema_hash: panel.__schemaHash || "unknown",
          status: status
        }),
        credentials: "omit",
      });
    } catch (e) {
      console.error("[Feedback] Error sending feedback:", e);
    }
  };

  if (feedbackUp && feedbackDown) {
    feedbackUp.onclick = async () => {
      feedbackUp.setAttribute("aria-pressed", "true");
      feedbackDown.setAttribute("aria-pressed", "false");
      feedbackUp.style.color = "#10b981";
      feedbackDown.style.color = "#94a3b8";
      await sendFeedback("helpful");
    };

    feedbackDown.onclick = async () => {
      feedbackDown.setAttribute("aria-pressed", "true");
      feedbackUp.setAttribute("aria-pressed", "false");
      feedbackDown.style.color = "#ef4444";
      feedbackUp.style.color = "#94a3b8";
      await sendFeedback("unhelpful");
    };
  }
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

    // Phase 5.0: Store profile for learning event
    currentProfile = profile;

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
      const styleId = profile.styleHint.preferredStyleId || profile.styleHint.genStyleId;
      const confidence = profile.styleHint.confidence;
      if (styleId && confidence !== undefined) {
        console.log(`[Learning] Style hint: ${styleId} (${(confidence * 100).toFixed(0)}% confidence)`);
      }
      // Phase 5.0: Log preferred style from aggregator
      if (profile.styleHint.preferredStyleId && profile.styleHint.styleStats) {
        const stats = profile.styleHint.styleStats[profile.styleHint.preferredStyleId];
        if (stats) {
          console.log(
            `📊 Using tuned style: ${profile.styleHint.preferredStyleId} ` +
            `(${stats.helpful}/${stats.total_runs} helpful, avg ${Math.round(stats.avg_edit_chars)} chars edited)`
          );
        }
      }
    }

    // Phase 5.4 — epsilon-greedy bandit
    const styleHint = profile?.styleHint || null;

    let chosenStyleId = null;
    let banditPolicy = "fallback";

    if (isBanditEnabled() && styleHint && styleHint.preferredStyleId) {
      // Bandit is enabled - use normal exploration logic
      const banditResult = pickStyleForBandit(styleHint);
      chosenStyleId = banditResult.styleId;
      banditPolicy = banditResult.policy;
    } else {
      // Bandit disabled globally or no style hint available - fallback
      chosenStyleId = styleHint ? styleHint.preferredStyleId : null;
      banditPolicy = "fallback";
      if (!isBanditEnabled()) {
        console.log("[Bandit] DISABLED via kill switch - using fallback policy");
      }
    }

    // If bandit couldn't choose, fall back to preferred
    const styleIdToSend =
      chosenStyleId ||
      (styleHint && styleHint.preferredStyleId) ||
      null;

    // Build style_hint object for backend (snake_case)
    let styleHintForRequest = null;
    if (styleIdToSend) {
      styleHintForRequest = {
        ...(styleHint || {}),
        style_id: styleIdToSend,
      };
      // Don't send preferredStyleId back, API expects style_id
      delete styleHintForRequest.preferredStyleId;
    }

    // Remember for learning sync
    ctx.genStyleId = styleIdToSend;
    ctx.banditPolicy = banditPolicy;

    // Phase 4.1: Pass style hint to generation endpoint
    const data = await fetchFormAnswers(ctx.job, fields, styleHintForRequest);

    // Phase 3.1: Apply guardrails to sanitize generated content
    if (data.answers) {
      data.answers = data.answers.map(ans => ({
        ...ans,
        answer: sanitizeGeneratedContent(ans.answer)
      }));
    }

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

    // Store context for feedback and learning (Phase 5.4: includes bandit policy)
    panel.__schemaHash = schemaHash;
    panel.__ctx = ctx;

    renderAnswers(panel, data.answers || [], fields);

    // log application (best-effort)
    try {
      await chrome.runtime?.sendMessage?.({ type: "LOG_APPLICATION", payload: {
        company: ctx.job.company, role: ctx.job.title, job_url: ctx.job.url,
        source: "browser_extension", notes: "Scan & review"
      }});
    } catch {}
  } catch (e) {
    // Dogfood v0.1: Show user-friendly error messages
    let errorMsg = "Something went wrong";
    let helpMsg = "";

    if (e.message === "NOT_LOGGED_IN") {
      errorMsg = "Not logged in to ApplyLens";
      helpMsg = `Please visit <a href="${APPLYLENS_API_BASE.replace('/api', '')}" target="_blank">applylens.app</a> and sign in first.`;
    } else if (e.message === "NETWORK_ERROR") {
      errorMsg = "Cannot reach ApplyLens backend";
      helpMsg = "Check your internet connection and try again.";
    } else if (e.message === "SERVER_ERROR") {
      errorMsg = "ApplyLens server error";
      helpMsg = "Our servers are experiencing issues. Please try again in a few minutes.";
    } else if (e.message.startsWith("HTTP_")) {
      errorMsg = `Backend error (${e.message.replace('HTTP_', '')})`;
      helpMsg = "An unexpected error occurred. Please try again.";
    } else {
      errorMsg = String(e);
    }

    body.innerHTML = `
      <div style="padding: 12px; background: #fef2f2; border-left: 3px solid #ef4444; margin: 8px 0;">
        <div style="font-weight: 600; color: #991b1b; margin-bottom: 4px;">⚠️ ${errorMsg}</div>
        ${helpMsg ? `<div style="color: #7f1d1d; font-size: 13px;">${helpMsg}</div>` : ''}
      </div>
      <div class="muted" style="margin-top: 8px;">Form scanning still works locally, but autofill generation requires backend access.</div>
    `;
  }
}

async function trackAutofillCompletion(host, schemaHash, rows, ctx = {}) {
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

  // Build final map and calculate edit stats from row state
  finalMap = {};
  const editStats = {
    totalCharsAdded: 0,
    totalCharsDeleted: 0,
    perField: {}
  };

  for (const row of rows) {
    if (!row.accepted) continue; // Only track accepted rows

    // Get suggested value (generated answer)
    const panel = document.getElementById(PANEL_ID);
    const textarea = panel?.querySelector(`textarea[data-field="${encodeURIComponent(row.fieldId)}"]`);
    const generatedValue = textarea?.defaultValue || "";
    const finalValue = row.text; // Current value from row state

    if (finalValue) {
      finalMap[row.selector] = row.fieldId;

      // Calculate edit distance
      const distance = editDistance(generatedValue, finalValue);
      const charsAdded = Math.max(0, finalValue.length - generatedValue.length);
      const charsDeleted = Math.max(0, generatedValue.length - finalValue.length);

      editStats.totalCharsAdded += charsAdded;
      editStats.totalCharsDeleted += charsDeleted;
      editStats.perField[row.selector] = {
        added: charsAdded,
        deleted: charsDeleted,
        editDistance: distance
      };
    }
  }

  // Queue learning event (Phase 5.4: includes bandit policy)
  const event = {
    host,
    schemaHash,
    suggestedMap,
    finalMap,
    genStyleId: ctx.genStyleId || null,
    policy: ctx.banditPolicy || "exploit", // Phase 5.4: bandit policy
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

// ======= Phase 3.2: Recruiter DM Panel =======

const DM_PANEL_ID = "__applylens_dm_panel__";

function mountDMPanel() {
  injectStyles();
  let panel = document.getElementById(DM_PANEL_ID);
  if (panel) panel.remove();

  panel = document.createElement("aside");
  panel.id = DM_PANEL_ID;
  panel.setAttribute("data-testid", "al-dm-panel");
  panel.style.cssText = `
    position: fixed;
    top: 80px;
    right: 20px;
    width: 420px;
    max-height: 80vh;
    background: white;
    border: 1px solid #ccc;
    border-radius: 8px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    z-index: 999999;
    font-family: system-ui, -apple-system, sans-serif;
    display: flex;
    flex-direction: column;
  `;

  panel.innerHTML = `
    <header style="padding: 16px; border-bottom: 1px solid #eee; display: flex; justify-content: space-between; align-items: center;">
      <div style="font-weight: 600; font-size: 15px;">ApplyLens — Recruiter DM</div>
      <button id="al_dm_close" title="Close" style="background: none; border: none; font-size: 20px; cursor: pointer; color: #666;">✕</button>
    </header>
    <div class="body" id="al_dm_body" style="flex: 1; overflow-y: auto; padding: 16px;">
      <div style="color: #999; text-align: center;">Generating DM...</div>
    </div>
    <div style="padding: 16px; border-top: 1px solid #eee; display: flex; gap: 8px;">
      <button id="al_dm_insert" style="flex: 1; padding: 10px; background: #0066cc; color: white; border: none; border-radius: 4px; cursor: pointer; font-weight: 500;">Insert DM</button>
      <button id="al_dm_cancel" style="padding: 10px 20px; background: #f5f5f5; border: 1px solid #ddd; border-radius: 4px; cursor: pointer;">Cancel</button>
    </div>
  `;

  document.documentElement.appendChild(panel);
  panel.querySelector("#al_dm_close").onclick = () => panel.remove();
  panel.querySelector("#al_dm_cancel").onclick = () => panel.remove();
  return panel;
}

function renderDMLines(panel, lines) {
  const body = panel.querySelector("#al_dm_body");
  body.innerHTML = "";

  // Phase 3.2: Track row state for DM lines
  const rows = [];

  for (const line of lines) {
    const row = document.createElement("div");
    row.style.cssText = "margin-bottom: 16px; padding-bottom: 16px; border-bottom: 1px solid #f0f0f0;";
    row.setAttribute("data-testid", "al-dm-row");

    const rowState = {
      text: line,
      accepted: true
    };
    rows.push(rowState);

    row.innerHTML = `
      <div style="margin-bottom: 8px;">
        <label style="display: flex; align-items: center; gap: 8px; cursor: pointer;">
          <input type="checkbox" checked data-testid="al-dm-checkbox" style="cursor: pointer;">
          <span style="font-size: 13px; color: #666;">Include this line</span>
        </label>
      </div>
      <textarea data-testid="al-dm-textarea" rows="2" style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px; font-family: inherit; font-size: 14px; resize: vertical;">${line}</textarea>
    `;

    body.appendChild(row);

    const checkbox = row.querySelector('input[type="checkbox"]');
    const textarea = row.querySelector("textarea");

    if (checkbox) {
      checkbox.addEventListener("change", () => {
        rowState.accepted = checkbox.checked;
      });
    }

    if (textarea) {
      textarea.addEventListener("input", () => {
        rowState.text = textarea.value;
      });
    }
  }

  // Wire Insert DM button
  panel.querySelector("#al_dm_insert").onclick = () => {
    const acceptedLines = rows
      .filter(r => r.accepted)
      .map(r => r.text)
      .filter(t => t.trim());

    const finalDM = acceptedLines.join("\n\n");

    // Find message field on page
    const messageField = document.querySelector('textarea[name="recruiter_message"]')
      || document.querySelector('[contenteditable="true"]');

    if (messageField) {
      if (messageField.tagName.toLowerCase() === "textarea") {
        messageField.focus();
        messageField.value = finalDM;
        messageField.dispatchEvent(new Event("input", { bubbles: true }));
        messageField.dispatchEvent(new Event("change", { bubbles: true }));
      } else {
        // contenteditable
        messageField.focus();
        messageField.textContent = finalDM;
        messageField.dispatchEvent(new Event("input", { bubbles: true }));
      }
    }

    panel.remove();
  };

  panel.__dmRowsState = rows;
}

async function generateRecruiterDM() {
  const panel = mountDMPanel();
  const body = panel.querySelector("#al_dm_body");

  try {
    const ctx = getPageContext();

    // Call DM generation endpoint
    const res = await fetch(`${APPLYLENS_API_BASE}/api/extension/generate-recruiter-dm`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        job: ctx.job,
        recruiter: {
          name: "Recruiter",
          company: ctx.job.company
        }
      }),
      credentials: "omit",
    });

    if (!res.ok) throw new Error(`DM generation failed: ${res.status}`);

    const data = await res.json();
    let lines = data.dm || [];

    // Phase 3.1: Apply guardrails to each line
    lines = lines.map(line => sanitizeGeneratedContent(line));

    renderDMLines(panel, lines);

  } catch (e) {
    body.innerHTML = `<div style="color: #d32f2f; text-align: center;">Error: ${String(e)}</div>`;
  }
}

// Listen for SW messages and devtools test hook
chrome.runtime?.onMessage?.addListener((msg, _sender, _sendResponse) => {
  if (msg?.type === "SCAN_AND_SUGGEST") runScanAndSuggest();
});

// Simple global for E2E to call directly
window.__APPLYLENS__ = { runScanAndSuggest, scanFields, generateRecruiterDM };
