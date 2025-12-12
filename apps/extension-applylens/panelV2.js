// panelV2.js — v0.2 Job Form Mode panel with Scan → Generate → Apply flow

import { APPLYLENS_API_BASE } from "./config.js";
import { scanFormFields, collectJobContext } from "./fieldScanner.js";
import { detectATS } from "./atsPresets.js";
import { isProfileField, isSensitiveField } from "./schema.js";
import { summarizeLearningProfile } from "./learning/client.js";

const PANEL_ID = "__applylens_panel_v2__";
const STYLE_ID = "__applylens_panel_style_v2__";

// Source badge configuration
const SOURCE_LABELS = {
  profile: "Profile",
  learned: "Learned",
  ai: "AI",
  scan: "Scan",
};

const SOURCE_TOOLTIPS = {
  profile: "Filled from your ApplyLens profile (name, links, location, etc.)",
  learned: "Filled from previous successful applications on this site",
  ai: "Filled by AI using your profile + job description",
  scan: "Field detected by scanner, no suggestion yet",
};

function createSourceBadge(source) {
  const type = source || "scan";
  const label = SOURCE_LABELS[type] || "Scan";
  const tooltip = SOURCE_TOOLTIPS[type] || "Detected field";

  const badge = document.createElement("span");
  badge.className =
    "ml-2 inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-medium";
  badge.textContent = label;
  badge.title = tooltip;

  // Apply color classes based on source
  if (type === "profile") {
    badge.classList.add("border-indigo-500/25", "bg-indigo-500/10", "text-indigo-300");
  } else if (type === "learned") {
    badge.classList.add("border-emerald-500/25", "bg-emerald-500/10", "text-emerald-300");
  } else if (type === "ai") {
    badge.classList.add("border-sky-500/25", "bg-sky-500/10", "text-sky-300");
  } else {
    badge.classList.add("border-slate-500/25", "bg-slate-500/10", "text-slate-200");
  }

  return badge;
}

// Panel state for selection tracking
const panelState = {
  selectionByRowId: {}, // rowId -> boolean
};

let applyButtonRef = null;

// --- Helpers: copy + modal ----------------------------------------

async function copyTextToClipboard(text) {
  try {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      await navigator.clipboard.writeText(text);
    } else {
      const ta = document.createElement("textarea");
      ta.value = text;
      ta.style.position = "fixed";
      ta.style.left = "-9999px";
      document.body.appendChild(ta);
      ta.select();
      document.execCommand("copy");
      document.body.removeChild(ta);
    }
    console.info("[panelV2] Copied suggestion to clipboard");
    return true;
  } catch (err) {
    console.warn("[panelV2] Failed to copy suggestion:", err);
    return false;
  }
}

function openSuggestionModal(opts) {
  const { label, suggestion, sourceLabel } = opts;

  const overlay = document.createElement("div");
  Object.assign(overlay.style, {
    position: "fixed",
    inset: "0",
    background: "rgba(15,23,42,0.85)",
    zIndex: "2147483647",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
  });

  const dialog = document.createElement("div");
  Object.assign(dialog.style, {
    width: "min(640px, 90vw)",
    maxHeight: "80vh",
    background: "#020617",
    borderRadius: "18px",
    padding: "20px 24px",
    boxShadow: "0 24px 80px rgba(15,23,42,0.9)",
    border: "1px solid rgba(148,163,184,0.5)",
    display: "flex",
    flexDirection: "column",
    gap: "12px",
    color: "#e5e7eb",
    fontFamily: "system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
  });

  const header = document.createElement("div");
  Object.assign(header.style, {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    gap: "8px",
  });

  const title = document.createElement("div");
  title.textContent = label;
  Object.assign(title.style, {
    fontSize: "14px",
    fontWeight: "600",
    color: "#f9fafb",
  });

  const meta = document.createElement("div");
  meta.textContent = sourceLabel || "";
  Object.assign(meta.style, {
    fontSize: "11px",
    color: "#9ca3af",
  });

  const closeBtn = document.createElement("button");
  closeBtn.type = "button";
  closeBtn.textContent = "✕";
  Object.assign(closeBtn.style, {
    marginLeft: "8px",
    border: "none",
    background: "transparent",
    color: "#9ca3af",
    cursor: "pointer",
    fontSize: "14px",
  });

  closeBtn.addEventListener("click", () => {
    document.body.removeChild(overlay);
  });

  header.appendChild(title);
  header.appendChild(meta);
  header.appendChild(closeBtn);

  const body = document.createElement("div");
  body.textContent = suggestion;
  Object.assign(body.style, {
    fontSize: "13px",
    lineHeight: "1.5",
    color: "#e5e7eb",
    whiteSpace: "pre-wrap",
    overflowY: "auto",
    padding: "8px 0",
    borderTop: "1px solid rgba(31,41,55,0.9)",
    borderBottom: "1px solid rgba(31,41,55,0.9)",
    maxHeight: "55vh",
  });

  const footer = document.createElement("div");
  Object.assign(footer.style, {
    display: "flex",
    justifyContent: "flex-end",
    gap: "8px",
    marginTop: "4px",
  });

  const copyBtn = document.createElement("button");
  copyBtn.type = "button";
  copyBtn.textContent = "Copy";
  Object.assign(copyBtn.style, {
    borderRadius: "999px",
    border: "1px solid rgba(148,163,184,0.6)",
    background: "rgba(15,23,42,0.9)",
    padding: "6px 10px",
    fontSize: "12px",
    color: "#e5e7eb",
    cursor: "pointer",
  });

  copyBtn.addEventListener("click", async (ev) => {
    ev.stopPropagation();
    const ok = await copyTextToClipboard(suggestion);
    if (ok) {
      const prev = copyBtn.textContent;
      copyBtn.textContent = "Copied";
      setTimeout(() => { copyBtn.textContent = prev; }, 900);
    }
  });

  const closeFooterBtn = document.createElement("button");
  closeFooterBtn.type = "button";
  closeFooterBtn.textContent = "Close";
  Object.assign(closeFooterBtn.style, {
    borderRadius: "999px",
    border: "none",
    background: "rgba(15,23,42,0.9)",
    padding: "6px 12px",
    fontSize: "12px",
    color: "#9ca3af",
    cursor: "pointer",
  });
  closeFooterBtn.addEventListener("click", () => {
    document.body.removeChild(overlay);
  });

  footer.appendChild(copyBtn);
  footer.appendChild(closeFooterBtn);

  dialog.appendChild(header);
  dialog.appendChild(body);
  dialog.appendChild(footer);

  overlay.appendChild(dialog);

  overlay.addEventListener("click", (ev) => {
    if (ev.target === overlay) {
      document.body.removeChild(overlay);
    }
  });

  document.body.appendChild(overlay);
}

/**
 * Compute a stable row ID for selection tracking
 */
function getRowId(row, index) {
  if (row._alp_rowId) return row._alp_rowId;
  const base =
    row.selector ||
    row.idAttr ||
    row.nameAttr ||
    `${row.canonical || "unknown"}:${row.labelText || ""}`;
  const id = `${base}::${index}`;
  row._alp_rowId = id;
  return id;
}

/**
 * Determine if a field should be auto-checked
 */
function shouldAutoCheck(field, suggestions) {
  const hints = field._alp_learning || {};
  const canonical = field.canonical;

  // Auto-check if from local memory
  if (hints.hasLocalPref) return true;

  // Auto-check if learned on this site
  if (hints.learnedOnSite) return true;

  // Auto-check if we have a suggestion from profile
  if (canonical && suggestions[canonical]?.source === 'memory') return true;

  // Never auto-check cover letters or large text fields
  if (canonical === 'cover_letter' || field.tagName === 'TEXTAREA') return false;

  // For AI suggestions, be conservative
  if (canonical && suggestions[canonical]?.source === 'ai') return false;

  return false;
}

// ---------- Source helpers (Profile / Learned / AI / Scan) ----------

/**
 * Try to infer a simple source tag from the field data
 */
function inferRowSource(field, suggestions) {
  const canonical = field.canonical;
  const hints = field._alp_learning || {};
  const suggestionData = suggestions[canonical] || suggestions[field.selector];
  const source = suggestionData?.source;

  // Check explicit source from suggestion
  if (source === 'ai') return 'ai';
  if (source === 'memory') return 'learned';
  if (source === 'profile') return 'profile';

  // Anything that came from learning profile or local memory
  if (hints.learnedOnSite || hints.hasLocalPref) return 'learned';

  // From ApplyLens profile
  if (hints.isProfileField) return 'profile';

  // Fallback: we only know it was scanned from the page
  return 'scan';
}

/**
 * Which canonicals should we *not* auto-overwrite from AI
 */
function isIdentityCanonical(canonical) {
  return [
    'first_name',
    'last_name',
    'email',
    'phone',
    'linkedin',
    'linkedin_url',
    'github',
    'github_url',
    'portfolio_url',
    'location',
    'years_experience',  // Profile fact, not AI-generated
  ].includes(canonical);
}

/**
 * Compute source summary with counts for the "Using:" display
 */
function computeSourceSummary(fields, suggestions) {
  const summary = {
    // counts by source
    profileCount: 0,
    learnedCount: 0,
    aiCount: 0,
    scanOnlyCount: 0,

    // overall stats
    totalFields: fields.length,
    totalSuggested: 0,
    requiredCount: 0,
    optionalCount: 0,
  };

  for (const field of fields) {
    if (field.required) summary.requiredCount++;
    else summary.optionalCount++;

    const canonical = field.canonical;
    const suggestionData = suggestions[canonical] || suggestions[field.selector];
    const suggestionValue = typeof suggestionData === 'object' ? suggestionData.value : (suggestionData || '');
    const hasSuggestion = suggestionValue && String(suggestionValue).trim() !== '';

    if (!hasSuggestion) {
      summary.scanOnlyCount++;
      continue;
    }

    summary.totalSuggested++;

    const source = suggestionData?.source;
    if (source === 'profile') {
      summary.profileCount++;
    } else if (source === 'learned' || source === 'memory') {
      summary.learnedCount++;
    } else if (source === 'ai') {
      summary.aiCount++;
    }
  }

  return summary;
}

/**
 * Render style preferences tag
 */
function renderStylePrefsTag(stylePrefs) {
  if (!stylePrefs) return "";

  const tone = stylePrefs.tone || "concise";
  const length = stylePrefs.length || "medium";

  const toneLabel =
    tone === "confident"
      ? "Confident"
      : tone === "friendly"
      ? "Friendly"
      : tone === "detailed"
      ? "Detailed"
      : "Concise";

  const lengthLabel =
    length === "short"
      ? "Short"
      : length === "long"
      ? "Long"
      : "Medium";

  const chipText = `${toneLabel} · ${lengthLabel}`;
  const title = `Answers for this run will follow: ${toneLabel} tone, ${lengthLabel} length. Change this in the ApplyLens popup.`;

  return `
    <div
      class="mt-1 inline-flex items-center gap-1 rounded-full bg-slate-900/80 px-2 py-0.5 text-[10px] text-slate-200 ring-1 ring-slate-700/70"
      title="${title}"
    >
      <svg class="h-3 w-3" data-lucide="SlidersHorizontal"></svg>
      <span>${chipText}</span>
    </div>
  `;
}

/**
 * Build HTML for source summary bar showing counts
 */
function buildSourceSummaryBar(summary) {
  const items = [];

  if (summary.profileCount > 0) {
    items.push({
      label: 'Profile',
      count: summary.profileCount,
      color: '#a78bfa',  // indigo
      tooltip: `Using your ApplyLens profile for ${summary.profileCount} field(s)`
    });
  }

  if (summary.learnedCount > 0) {
    items.push({
      label: 'Learned',
      count: summary.learnedCount,
      color: '#34d399',  // emerald
      tooltip: `Using learned mappings from previous applications for ${summary.learnedCount} field(s)`
    });
  }

  if (summary.aiCount > 0) {
    items.push({
      label: 'AI',
      count: summary.aiCount,
      color: '#7dd3fc',  // sky
      tooltip: `Using AI (job posting + profile) for ${summary.aiCount} field(s)`
    });
  }

  if (items.length === 0) {
    return '';
  }

  const totalText = summary.totalSuggested > 0
    ? `Filled ${summary.totalSuggested} of ${summary.totalFields} fields`
    : `Found ${summary.totalFields} fields`;

  const chipsHtml = items.map(item => `
    <span
      class="inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] font-medium shadow-sm"
      style="border-color: ${item.color}40; background-color: ${item.color}15; color: ${item.color};"
      title="${item.tooltip}"
    >
      <span>${item.label}</span>
      <span class="ml-0.5 tabular-nums font-semibold">${item.count}</span>
    </span>
  `).join('');

  return `
    <div class="mt-2 flex flex-col gap-1.5 text-[11px] text-slate-400">
      <div class="flex items-center gap-2">
        <span class="uppercase tracking-wide text-[10px] text-slate-500">Using:</span>
        <span class="rounded-full bg-slate-900/70 px-2 py-0.5 text-[10px] text-slate-200">${totalText}</span>
      </div>
      <div class="flex flex-wrap items-center gap-1.5">
        ${chipsHtml}
      </div>
    </div>
  `;
}

/**
 * Get reason chip data for a field
 */
function getReasonChip(field, suggestions) {
  const canonical = field.canonical;
  const hints = field._alp_learning || {};

  let label = 'Manual';
  let classes = 'alp-field-chip-reason border-slate-600/80 text-slate-300 bg-slate-900/80';

  if (hints.hasLocalPref) {
    label = 'Profile';
    classes = 'alp-field-chip-reason border-emerald-500/80 text-emerald-300 bg-emerald-900/10';
  } else if (hints.learnedOnSite) {
    label = 'Learned';
    classes = 'alp-field-chip-reason border-sky-500/80 text-sky-300 bg-sky-900/10';
  } else if (canonical && suggestions[canonical]?.source === 'ai') {
    label = 'AI';
    classes = 'alp-field-chip-reason border-fuchsia-500/80 text-fuchsia-300 bg-fuchsia-900/10';
  }

  return { label, classes };
}

/**
 * Metadata for the little pill next to the field label
 */
function getRowSourceMeta(field, suggestions) {
  const source = inferRowSource(field, suggestions);
  const label = SOURCE_LABELS[source] || 'Scan';
  const tooltip = SOURCE_TOOLTIPS[source] || 'Detected field';

  if (source === 'ai') {
    return {
      label,
      className:
        'ml-2 inline-flex items-center rounded-full border border-sky-500/25 bg-sky-500/10 px-2 py-0.5 text-[10px] font-medium text-sky-300',
      tooltip,
    };
  }

  if (source === 'learned') {
    return {
      label,
      className:
        'ml-2 inline-flex items-center rounded-full border border-emerald-500/25 bg-emerald-500/10 px-2 py-0.5 text-[10px] font-medium text-emerald-300',
      tooltip,
    };
  }

  if (source === 'profile') {
    return {
      label,
      className:
        'ml-2 inline-flex items-center rounded-full border border-indigo-500/25 bg-indigo-500/10 px-2 py-0.5 text-[10px] font-medium text-indigo-300',
      tooltip,
    };
  }

  // "scan" / unknown
  return {
    label,
    className:
      'ml-2 inline-flex items-center rounded-full border border-slate-500/25 bg-slate-500/10 px-2 py-0.5 text-[10px] font-medium text-slate-200',
    tooltip,
  };
}

/**
 * Determine if a field is optional (for grouping)
 */
// Core profile fields that should always be in "Key fields" section
// even if the site doesn't mark them as required
const CORE_CANONICAL = new Set([
  "first_name",
  "last_name",
  "email",
  "phone",
  "linkedin",
]);

// Contact/link fields that respect the auto-apply toggle
const AUTO_CHECK_CANONICALS = new Set([
  "first_name",
  "last_name",
  "email",
  "phone",
  "linkedin",
  "linkedin_url",
  "github",
  "github_url",
  "portfolio",
  "portfolio_url",
  "website",
  "website_url",
  "location",
]);

function isOptionalField(field) {
  // Required fields are always key fields
  if (field.required) return false;
  // Core canonical fields are always key fields
  if (field.canonical && CORE_CANONICAL.has(field.canonical)) return false;
  // Everything else is optional
  return true;
}

/**
 * Classify a field and explain why it's key or optional
 */
function classifyField(field) {
  const canonical = field.canonical || "";
  const labelText = (field.labelText || "").toLowerCase();

  const hasRequiredAttr = !!field.required;
  const isCoreProfile = CORE_CANONICAL.has(canonical);
  const isExplicitlyOptional = labelText.includes('optional');

  let bucket = "optional";
  let importanceReason = "No required marker detected; treated as optional.";

  // Explicitly optional always wins
  if (isExplicitlyOptional) {
    bucket = "optional";
    importanceReason = "Label contains '(optional)' - always treated as optional.";
  } else if (hasRequiredAttr && isCoreProfile) {
    bucket = "key";
    importanceReason = "Marked as required on the page and matches a core profile field.";
  } else if (hasRequiredAttr) {
    bucket = "key";
    importanceReason = "Detected HTML required attribute or aria-required=true or * in label.";
  } else if (isCoreProfile) {
    bucket = "key";
    importanceReason = "Even if not strictly required, this is a core profile field (e.g., name/email/phone/linkedin).";
  }

  return { ...field, bucket, importanceReason };
}

/**
 * Score a row for auto-apply confidence based on learning hints
 */
function computeAutoApplyScore(row, learningProfile) {
  let score = 0;
  const hints = row._alp_learning || {};
  const canonical = row.canonical;

  // 1) Strongest signal: local memory hit
  if (hints.hasLocalPref) {
    score += 2;
  }

  // 2) Server profile knows this canonical type on this site
  if (canonical && learningProfile?.canonical_map && learningProfile.canonical_map[canonical]) {
    score += 2;
  }

  // 3) Required fields get a small bump
  if (row.required) {
    score += 1;
  }

  // 4) Identity-ish fields get a bump (name, email, phone, LinkedIn)
  const strongCanonicals = ["first_name", "last_name", "preferred_name", "email", "phone", "linkedin_url"];
  if (canonical && strongCanonicals.includes(canonical)) {
    score += 1;
  }

  return score;
}

/**
 * Determine if a row should be auto-selected for apply
 */
function shouldAutoApply(row, learningProfile, suggestions, settings = {}) {
  // Don't auto-apply if there is no suggestion yet
  const suggestionData = suggestions[row.canonical] || suggestions[row.selector];
  const suggestion = typeof suggestionData === 'object' ? suggestionData.value : (suggestionData || "");
  if (!suggestion || !String(suggestion).trim()) {
    return false;
  }

  const source = inferRowSource(row, suggestions);
  const autoApplyLinks = settings.autoApplyContactLinks !== false; // default true

  // 1) Always auto-select required core fields if we have a suggestion
  if (row.required) return true;

  // 2) For profile/learned fields, respect the toggle setting
  if (source === 'profile' || source === 'learned') {
    // Always auto-select name fields even if toggle is off
    if (row.canonical === 'first_name' || row.canonical === 'last_name') {
      return true;
    }

    // For contact links, only auto-select if toggle is enabled
    if (AUTO_CHECK_CANONICALS.has(row.canonical)) {
      return autoApplyLinks;
    }

    // Other profile/learned fields auto-select by default
    return true;
  }

  // 3) For pure AI answers, only auto-select if it's NOT an identity field
  if (source === 'ai' && !isIdentityCanonical(row.canonical)) {
    return true;
  }

  // 4) Everything else stays unchecked by default
  return false;
}

/**
 * Initialize selection state based on learning hints and settings
 */
function initializeSelectionState(fields, learningProfile, suggestions, settings = {}) {
  const map = {};
  fields.forEach((row, index) => {
    const rowId = getRowId(row, index);
    map[rowId] = shouldAutoApply(row, learningProfile, suggestions, settings);
  });
  panelState.selectionByRowId = map;
  console.log("[panelV2] Initialized selection state:",
    Object.values(map).filter(Boolean).length,
    "of", fields.length, "rows pre-selected",
    "(autoApplyContactLinks:", settings.autoApplyContactLinks !== false, ")");
}

/**
 * Check if any rows are selected
 */
function anyRowsSelected() {
  const sel = panelState.selectionByRowId || {};
  return Object.values(sel).some(Boolean);
}

/**
 * Update Apply button enabled/disabled state
 */
function updateApplyButtonState() {
  if (!applyButtonRef) return;
  const hasSelections = anyRowsSelected();
  applyButtonRef.disabled = !hasSelections;
  console.log("[panelV2] Apply button", hasSelections ? "enabled" : "disabled");
}


/**
 * Inject panel styles (legacy - now using panel.css)
 */
function injectStyles() {
  // Styles now loaded via panel.css in manifest.json
  // Keep this function for backward compatibility
  if (document.getElementById(STYLE_ID)) return;

  const css = `
  #${PANEL_ID} {
    position: fixed;
    top: 16px;
    right: 16px;
    z-index: 2147483646;
    width: 520px;
    max-width: 540px;
    max-height: 80vh;
    overflow: hidden;
    background: #0f172a;
    color: #e2e8f0;
    border: 1px solid #334155;
    border-radius: 12px;
    box-shadow: 0 10px 40px rgba(0,0,0,.4);
    font: 13px/1.45 system-ui, -apple-system, Segoe UI, Roboto, Inter, sans-serif;
    display: flex;
    flex-direction: column;
    padding: 0;
  }

  #${PANEL_ID} .alp-panel-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 12px 16px;
    border-bottom: 1px solid #334155;
    background: #0a0f1c;
    flex-shrink: 0;
  }

  #${PANEL_ID} .alp-panel-header-title {
    font-size: 14px;
    font-weight: 600;
    margin: 0;
    color: #e2e8f0;
  }

  #${PANEL_ID} .alp-panel-header-sub {
    margin-top: 4px;
    font-size: 11px;
    color: #94a3b8;
    font-weight: 400;
  }

  #${PANEL_ID} .alp-pill {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 4px 10px;
    border-radius: 999px;
    border: 1px solid rgba(52,211,153,0.6);
    background: rgba(16,185,129,0.1);
    font-size: 11px;
    color: #6ee7b7;
  }

  #${PANEL_ID} .alp-pill-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #10b981;
    box-shadow: 0 0 8px rgba(16,185,129,0.8);
  }

  #${PANEL_ID} .alp-panel-body {
    flex: 1;
    overflow-y: auto;
    padding: 12px 16px;
  }

  #${PANEL_ID} .alp-panel-footer {
    display: flex;
    gap: 8px;
    padding: 12px 16px;
    border-top: 1px solid #334155;
    background: #0a0f1c;
    flex-shrink: 0;
  }

  #${PANEL_ID} .alp-btn-primary {
    flex: 1;
    padding: 10px 14px;
    border-radius: 10px;
    background: linear-gradient(135deg, #22d3ee 0%, #2563eb 100%);
    border: none;
    color: #020617;
    cursor: pointer;
    font-size: 13px;
    font-weight: 600;
    box-shadow: 0 0 28px rgba(56,189,248,0.55);
    transition: all 0.15s;
  }

  #${PANEL_ID} .alp-btn-primary:hover:not(:disabled) {
    filter: brightness(1.1);
  }

  #${PANEL_ID} .alp-btn-primary:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  #${PANEL_ID} .alp-btn-secondary {
    flex: 1;
    padding: 8px 14px;
    border-radius: 10px;
    border: 1px solid rgba(71,85,105,0.8);
    background: rgba(15,23,42,0.9);
    color: #e2e8f0;
    cursor: pointer;
    font-size: 13px;
    font-weight: 500;
    transition: all 0.15s;
  }

  #${PANEL_ID} .alp-btn-secondary:hover:not(:disabled) {
    border-color: rgba(34,211,238,0.6);
    color: #7dd3fc;
  }

  #${PANEL_ID} #al_close {
    background: none;
    border: none;
    color: #94a3b8;
    font-size: 20px;
    cursor: pointer;
    padding: 0;
    width: 24px;
    height: 24px;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: color 0.15s;
  }

  #${PANEL_ID} #al_close:hover {
    color: #e2e8f0;
  }

  #${PANEL_ID} .flex {
    display: flex;
  }

  #${PANEL_ID} .items-center {
    align-items: center;
  }

  #${PANEL_ID} .gap-2 {
    gap: 8px;
  }

  #${PANEL_ID} header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 12px 16px;
    border-bottom: 1px solid #334155;
    background: #0a0f1c;
    flex-shrink: 0;
  }

  #${PANEL_ID} header h3 {
    margin: 0;
    font-size: 14px;
    font-weight: 600;
  }

  #${PANEL_ID} .status-subheader {
    margin-top: 4px;
    font-size: 11px;
    color: #94a3b8;
    font-weight: 400;
  }

  #${PANEL_ID} .ats-badge {
    display: inline-block;
    padding: 2px 8px;
    background: #1e293b;
    border: 1px solid #334155;
    border-radius: 4px;
    font-size: 11px;
    color: #94a3b8;
    margin-left: 8px;
  }

  #${PANEL_ID} .close-btn {
    background: none;
    border: none;
    color: #94a3b8;
    font-size: 20px;
    cursor: pointer;
    padding: 0;
    width: 24px;
    height: 24px;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  #${PANEL_ID} .close-btn:hover {
    color: #e2e8f0;
  }

  #${PANEL_ID} .body {
    flex: 1;
    overflow-y: auto;
    padding: 12px 16px;
  }

  #${PANEL_ID} .profile-snapshot {
    background: #1e293b;
    border: 1px solid #334155;
    border-radius: 8px;
    padding: 10px 12px;
    margin-bottom: 12px;
    font-size: 12px;
  }

  #${PANEL_ID} .profile-snapshot .label {
    color: #94a3b8;
    font-weight: 500;
  }

  #${PANEL_ID} .profile-snapshot .value {
    color: #e2e8f0;
  }

  #${PANEL_ID} .fields-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 12px;
    margin: 12px 0;
  }

  #${PANEL_ID} .fields-table th {
    text-align: left;
    padding: 8px 6px;
    background: #1e293b;
    color: #94a3b8;
    font-weight: 600;
    border-bottom: 1px solid #334155;
  }

  #${PANEL_ID} .fields-table td {
    padding: 8px 6px;
    border-bottom: 1px solid #334155;
    vertical-align: top;
  }

  #${PANEL_ID} .fields-table tr:last-child td {
    border-bottom: none;
  }

  #${PANEL_ID} .field-label {
    color: #e2e8f0;
    font-weight: 500;
    max-width: 120px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  #${PANEL_ID} .canonical-badge {
    display: inline-block;
    padding: 2px 6px;
    background: #1e40af;
    border-radius: 3px;
    font-size: 10px;
    color: #bfdbfe;
    font-family: monospace;
  }

  #${PANEL_ID} .canonical-badge.profile {
    background: #065f46;
    color: #6ee7b7;
  }

  #${PANEL_ID} .canonical-badge.sensitive {
    background: #7c2d12;
    color: #fca5a5;
  }

  #${PANEL_ID} .req-badge {
    display: inline-block;
    padding: 2px 5px;
    background: #7f1d1d;
    border-radius: 3px;
    font-size: 9px;
    color: #fca5a5;
    font-weight: 600;
    margin-left: 4px;
  }

  #${PANEL_ID} .opt-badge {
    display: inline-block;
    padding: 2px 5px;
    background: #1e293b;
    border-radius: 3px;
    font-size: 9px;
    color: #64748b;
    margin-left: 4px;
  }

  #${PANEL_ID} .source-badge {
    display: inline-block;
    padding: 2px 5px;
    border-radius: 3px;
    font-size: 9px;
    margin-left: 4px;
  }

  #${PANEL_ID} .source-badge.profile {
    background: #065f46;
    color: #6ee7b7;
  }

  #${PANEL_ID} .source-badge.memory {
    background: #0c4a6e;
    color: #7dd3fc;
  }

  #${PANEL_ID} .source-badge.ai {
    background: #3730a3;
    color: #c4b5fd;
  }

  #${PANEL_ID} .alp-row-has-suggestion {
    background: #0f172a;
  }

  #${PANEL_ID} .field-value {
    color: #94a3b8;
    font-size: 11px;
    max-width: 100px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  #${PANEL_ID} .field-value.empty-placeholder {
    color: #475569;
    font-style: italic;
  }

  #${PANEL_ID} .suggestion-pending {
    color: #64748b;
    font-size: 11px;
    font-style: italic;
  }

  #${PANEL_ID} .matches-current {
    color: #10b981;
    font-size: 10px;
    margin-left: 6px;
  }

  #${PANEL_ID} .suggestion-input {
    width: 100%;
    padding: 6px 8px;
    background: #0a0f1c;
    border: 1px solid #334155;
    border-radius: 4px;
    color: #e2e8f0;
    font-size: 13px;
    line-height: 1.4;
    font-family: inherit;
    resize: vertical;
    min-height: 36px;
    white-space: normal;
    overflow: visible;
    max-height: 8em;
  }

  #${PANEL_ID} .suggestion-input:focus {
    outline: none;
    border-color: #3b82f6;
  }

  #${PANEL_ID} .suggestion-loading {
    color: #94a3b8;
    font-style: italic;
  }

  #${PANEL_ID} .footer {
    display: flex;
    gap: 8px;
    padding: 12px 16px;
    border-top: 1px solid #334155;
    background: #0a0f1c;
    flex-shrink: 0;
  }

  #${PANEL_ID} button {
    padding: 8px 14px;
    border-radius: 6px;
    border: 1px solid #334155;
    background: #1e293b;
    color: #e2e8f0;
    cursor: pointer;
    font-size: 13px;
    font-weight: 500;
    transition: all 0.15s;
  }

  #${PANEL_ID} button:hover:not(:disabled) {
    background: #334155;
  }

  #${PANEL_ID} button:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  #${PANEL_ID} button.primary {
    background: #2563eb;
    border-color: #1d4ed8;
    color: white;
  }

  #${PANEL_ID} button.primary:hover:not(:disabled) {
    background: #1d4ed8;
  }

  #${PANEL_ID} .alp-btn-copy,
  #${PANEL_ID} .alp-btn-expand {
    transition: all 0.15s;
  }

  #${PANEL_ID} .alp-btn-copy:hover {
    background: rgba(15,23,42,1) !important;
    border-color: rgba(148,163,184,0.7) !important;
  }

  #${PANEL_ID} .alp-btn-expand:hover {
    background: rgba(30,41,55,1) !important;
    color: #cbd5e1 !important;
  }

  #${PANEL_ID} button.secondary {
    background: #059669;
    border-color: #047857;
    color: white;
  }

  #${PANEL_ID} button.secondary:hover:not(:disabled) {
    background: #047857;
  }

  #${PANEL_ID} .status-message {
    padding: 10px 12px;
    border-radius: 6px;
    margin: 8px 0;
    font-size: 12px;
  }

  #${PANEL_ID} .status-success {
    background: #064e3b;
    border: 1px solid #065f46;
    color: #6ee7b7;
  }

  #${PANEL_ID} .status-error {
    background: #7f1d1d;
    border: 1px solid #991b1b;
    color: #fca5a5;
  }

  #${PANEL_ID} .status-warning {
    background: #78350f;
    border: 1px solid #92400e;
    color: #fcd34d;
  }

  #${PANEL_ID} .banner {
    padding: 6px 10px;
    border-radius: 6px;
    margin-bottom: 10px;
    font-size: 11px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    line-height: 1.3;
  }

  #${PANEL_ID} .banner.info {
    background: #0c4a6e;
    border: 1px solid #075985;
    color: #7dd3fc;
  }

  #${PANEL_ID} .banner.success {
    background: #064e3b;
    border: 1px solid #065f46;
    color: #6ee7b7;
  }

  #${PANEL_ID} .banner button {
    padding: 2px 6px;
    font-size: 10px;
    background: transparent;
    border: 1px solid currentColor;
    color: inherit;
    white-space: nowrap;
    flex-shrink: 0;
  }

  #${PANEL_ID} .banner-text {
    flex: 1;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  #${PANEL_ID} .muted {
    color: #94a3b8;
    font-size: 12px;
  }

  #${PANEL_ID} .stats {
    display: flex;
    gap: 16px;
    padding: 8px 0;
    font-size: 12px;
    color: #94a3b8;
  }

  #${PANEL_ID} .stats strong {
    color: #e2e8f0;
  }

  #${PANEL_ID} .alp-learning-summary {
    margin: 8px 0 4px;
    padding: 6px 10px;
    border-radius: 6px;
    font-size: 11px;
    display: flex;
    gap: 6px;
    align-items: center;
  }

  #${PANEL_ID} .alp-learning-summary-label {
    text-transform: uppercase;
    font-weight: 600;
    letter-spacing: 0.04em;
    opacity: 0.8;
    font-size: 10px;
  }

  #${PANEL_ID} .alp-learning-summary-text {
    opacity: 0.9;
    flex: 1;
  }

  #${PANEL_ID} .alp-learning-summary--none {
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid rgba(255, 255, 255, 0.05);
  }

  #${PANEL_ID} .alp-learning-summary--low {
    background: rgba(122, 162, 247, 0.08);
    border: 1px solid rgba(122, 162, 247, 0.15);
  }

  #${PANEL_ID} .alp-learning-summary--medium {
    background: rgba(168, 162, 247, 0.08);
    border: 1px solid rgba(168, 162, 247, 0.15);
  }

  #${PANEL_ID} .alp-learning-summary--high {
    background: rgba(74, 222, 128, 0.08);
    border: 1px solid rgba(74, 222, 128, 0.15);
  }

  #${PANEL_ID} .alp-learning-badges {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
    margin-top: 4px;
  }

  #${PANEL_ID} .alp-pill-learning-local {
    display: inline-block;
    padding: 2px 6px;
    border-radius: 999px;
    font-size: 9px;
    line-height: 1.3;
    background: rgba(56, 189, 248, 0.16);
    color: #7dd3fc;
    font-weight: 500;
  }

  #${PANEL_ID} .alp-pill-learning-site {
    display: inline-block;
    padding: 2px 6px;
    border-radius: 999px;
    font-size: 9px;
    line-height: 1.3;
    background: rgba(52, 211, 153, 0.16);
    color: #6ee7b7;
    font-weight: 500;
  }
  `;

  const style = document.createElement("style");
  style.id = STYLE_ID;
  style.textContent = css;
  document.documentElement.appendChild(style);
}

/**
 * Create and mount the panel
 */
export function createPanel() {
  injectStyles();

  // Remove old panel if exists
  const existing = document.getElementById(PANEL_ID);
  if (existing) existing.remove();

  const panel = document.createElement("aside");
  panel.id = PANEL_ID;
  panel.className = "alp-panel";

  const atsName = detectATS(location.hostname) || "Generic";

  panel.innerHTML = `
    <div class="alp-panel-header">
      <div style="display: flex; flex-direction: column; gap: 2px; min-width: 0;">
        <div class="alp-panel-header-title">ApplyLens Companion</div>
        <div id="al_status_subheader" class="alp-panel-header-sub">
          Job board: <span style="color:#7dd3fc;font-weight:500;">${atsName}</span>
        </div>
      </div>
      <div class="flex items-center gap-2" style="display: flex; align-items: center; gap: 8px;">
        <div id="al_status_pill" class="alp-pill">
          <span class="alp-pill-dot"></span>
          <span>Ready</span>
        </div>
        <button id="al_close" title="Close" style="background: none; border: none; color: #94a3b8; cursor: pointer; font-size: 18px; padding: 4px 8px;">✕</button>
      </div>
    </div>

    <div class="alp-panel-body" id="al_body">
      <div style="font-size:11px;color:rgba(148,163,184,0.9);">Loading...</div>
    </div>

    <div class="alp-panel-footer" id="al_footer">
      <button id="al_generate" class="alp-btn-secondary">Generate</button>
      <button id="al_apply" class="alp-btn-primary" disabled>Apply</button>
    </div>
  `;

  document.documentElement.appendChild(panel);

  // Capture button reference for state management
  applyButtonRef = panel.querySelector("#al_apply");

  // Wire up close button
  panel.querySelector("#al_close").addEventListener("click", () => {
    panel.remove();
    applyButtonRef = null; // Clear reference on close
  });

  return panel;
}

/**
 * Render profile snapshot in panel
 */
function renderProfileSnapshot(panel, profile) {
  const body = panel.querySelector("#al_body");

  const snapshot = document.createElement("div");
  snapshot.className = "profile-snapshot";
  snapshot.innerHTML = `
    <div><span class="label">Name:</span> <span class="value">${profile.name || "—"}</span></div>
    <div><span class="label">Email:</span> <span class="value">${profile.email || "—"}</span></div>
    <div><span class="label">Location:</span> <span class="value">${profile.location || "—"}</span></div>
  `;

  body.insertBefore(snapshot, body.firstChild);
}

/**
 * Render learning summary banner
 */
function renderLearningSummary(body, learningProfile) {
  const { summary, level } = summarizeLearningProfile(learningProfile);

  const bar = document.createElement("div");
  bar.className = `alp-learning-summary alp-learning-summary--${level}`;

  const label = document.createElement("span");
  label.className = "alp-learning-summary-label";
  label.textContent = "Learning";

  const text = document.createElement("span");
  text.className = "alp-learning-summary-text";
  text.textContent = summary;

  bar.appendChild(label);
  bar.appendChild(text);

  body.appendChild(bar);
}

/**
 * Render a single field row (new card-based layout)
 */
function renderFieldRow(field, index, suggestions, learningProfile) {
  const rowId = getRowId(field, index);
  const isSelected = panelState.selectionByRowId[rowId] || false;
  const canonical = field.canonical;
  const hints = field._alp_learning || {};

  const suggestionData = suggestions[canonical] || suggestions[field.selector];
  const suggestionValue = typeof suggestionData === 'object' ? suggestionData.value : (suggestionData || "");
  const hasSuggestions = Object.keys(suggestions).length > 0;

  const reason = getReasonChip(field, suggestions);
  const sourceMeta = getRowSourceMeta(field, suggestions);
  const displayLabel = field.labelText || field.nameAttr || field.idAttr || "?";
  const fieldType = canonical || field.tagName?.toLowerCase() || "text";

  // Current value
  const currentValue = field.value && field.value.trim()
    ? `<div class="alp-field-value" title="${field.value}">${field.value}</div>`
    : `<div class="alp-field-value-empty">— empty —</div>`;

  // Suggestion value with actions
  let suggestionHtml;
  if (!hasSuggestions) {
    suggestionHtml = `<div class="alp-field-value-empty">Pending</div>`;
  } else if (!suggestionValue || suggestionValue.trim() === "") {
    suggestionHtml = `<div class="alp-field-value-empty">— none —</div>`;
  } else {
    // Truncate for display but keep full value in data attribute
    const displayValue = suggestionValue.length > 60
      ? suggestionValue.slice(0, 60) + '...'
      : suggestionValue;

    suggestionHtml = `
      <div class="alp-field-suggestion-wrapper" style="display:flex;align-items:center;gap:8px;justify-content:space-between;">
        <div class="alp-field-suggestion"
             title="${suggestionValue.replace(/"/g, '&quot;')}"
             style="flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">
          ${displayValue}
        </div>
        <div class="alp-field-actions" style="display:flex;gap:4px;flex-shrink:0;">
          <button type="button"
                  class="alp-btn-copy"
                  data-suggestion="${suggestionValue.replace(/"/g, '&quot;')}"
                  data-row-id="${rowId}"
                  style="border-radius:999px;border:1px solid rgba(148,163,184,0.4);background:rgba(15,23,42,0.8);padding:2px 8px;fontSize:10px;color:#e5e7eb;cursor:pointer;">
            Copy
          </button>
          <button type="button"
                  class="alp-btn-expand"
                  data-suggestion="${suggestionValue.replace(/"/g, '&quot;')}"
                  data-label="${displayLabel.replace(/"/g, '&quot;')}"
                  data-source="${sourceMeta.label}"
                  data-row-id="${rowId}"
                  style="border-radius:999px;border:none;background:rgba(15,23,42,0.9);padding:2px 8px;fontSize:10px;color:#9ca3af;cursor:pointer;">
            Expand
          </button>
        </div>
      </div>
    `;
  }

  // Status
  const matchesCurrent = field.value && field.value.trim() === suggestionValue.trim();
  const status = matchesCurrent
    ? `<span class="text-emerald-300">Applied</span>`
    : `<span class="text-slate-400">Pending</span>`;

  const isOptional = isOptionalField(field);

  return `
    <div class="alp-field-row ${isOptional ? 'alp-field-row-muted' : ''}"
         data-row-id="${rowId}"
         data-selector="${field.selector}"
         data-canonical="${canonical || ''}"
         title="${field.importanceReason || ''}">
      <div class="alp-field-left">
        <input
          type="checkbox"
          class="field-toggle"
          data-field="${field.selector}"
          data-row-id="${rowId}"
          ${isSelected ? 'checked' : ''}
        />
        <div>
          <div class="alp-field-label">
            ${displayLabel}
            <span class="${sourceMeta.className}" title="${sourceMeta.tooltip}">${sourceMeta.label}</span>
          </div>
          <div class="alp-field-type-chip">${fieldType}</div>
        </div>
      </div>

      <div>
        ${currentValue}
      </div>

      <div>
        ${suggestionHtml}
        <div class="${reason.classes}">
          <span class="alp-field-reason-dot"></span>
          <span>${reason.label}</span>
        </div>
      </div>

      <div class="alp-field-status">${status}</div>
    </div>
  `;
}

/**
 * Render scanned fields in a cleaner card-based layout
 */
export function renderFields(panel, fields, suggestions = {}, learningProfile = null, settings = {}) {
  const body = panel.querySelector("#al_body");
  body.innerHTML = "";

  if (fields.length === 0) {
    body.innerHTML = '<div class="text-[11px] text-slate-400/90">No form fields detected on this page.</div>';
    return;
  }

  // Calculate stats
  const totalFields = fields.length;
  const mappedCount = fields.filter(f => f.canonical).length;
  const profileFieldCount = fields.filter(f => isProfileField(f.canonical)).length;
  const requiredCount = fields.filter(f => f.required).length;
  const suggestionCount = Object.keys(suggestions).length;

  // Compute source summary with counts
  const sourceSummary = computeSourceSummary(fields, suggestions);

  console.log(`[panelV2] Rendering ${totalFields} fields: ${mappedCount} mapped, ${profileFieldCount} from profile, ${requiredCount} required`);
  console.log(
    `[panelV2] Source summary: ${sourceSummary.totalSuggested} suggestions | Profile: ${sourceSummary.profileCount}, Learned: ${sourceSummary.learnedCount}, AI: ${sourceSummary.aiCount}, Scan-only: ${sourceSummary.scanOnlyCount}`
  );

  // Update status subheader
  const subheader = panel.querySelector("#al_status_subheader");
  if (subheader) {
    const atsName = detectATS(location.hostname) || "Generic";
    const sourceSummaryHtml = buildSourceSummaryBar(sourceSummary);
    const stylePrefs = panel.__stylePrefs;
    const stylePrefsHtml = renderStylePrefsTag(stylePrefs);
    console.log("[panelV2] Style prefs for this run:", stylePrefs);
    subheader.innerHTML = `
      <div>Job board: <span style="color:#7dd3fc;font-weight:500;">${atsName}</span> · <span style="color:#cbd5e1;">${totalFields} fields</span> · <span style="color:#6ee7b7;">${mappedCount} mapped</span></div>
      ${sourceSummaryHtml}
      ${stylePrefsHtml}
    `;
  }

  // Classify fields with importance reasoning
  const classifiedFields = fields.map(classifyField);

  // Sort: required/profile first, then optional
  const sortedFields = [...classifiedFields].sort((a, b) => {
    const aOpt = a.bucket === "optional" ? 1 : 0;
    const bOpt = b.bucket === "optional" ? 1 : 0;
    return aOpt - bOpt;
  });

  console.log(`[panelV2] Sorted ${sortedFields.length} rows`);

  // Initialize selection state
  initializeSelectionState(sortedFields, learningProfile, suggestions, settings);

  // Group fields
  const keyFields = sortedFields.filter(f => f.bucket === "key");
  const optionalFields = sortedFields.filter(f => f.bucket === "optional");

  // Render key fields
  if (keyFields.length > 0) {
    const keySection = document.createElement("div");
    keySection.innerHTML = `
      <div class="alp-section-header">
        <div class="alp-section-title">Key fields (${keyFields.length})</div>
        <div class="alp-section-subtitle">
          Required or core profile fields (name, email, phone, LinkedIn)
        </div>
      </div>
      <div>
        ${keyFields.map((f, i) => renderFieldRow(f, i, suggestions, learningProfile)).join('')}
      </div>
    `;
    body.appendChild(keySection);
  }

  // Render optional fields (collapsed)
  if (optionalFields.length > 0) {
    const optSection = document.createElement("div");
    optSection.className = "mt-3";
    optSection.innerHTML = `
      <details class="group">
        <summary class="flex items-center justify-between">
          <div class="alp-section-header" style="margin-bottom:0;">
            <div class="alp-section-title">Optional fields (${optionalFields.length})</div>
            <div class="alp-section-subtitle">
              Nice-to-have questions (usually no red * or required marker)
            </div>
          </div>
          <span class="group-open:rotate-90">›</span>
        </summary>
        <div class="mt-2">
          ${optionalFields.map((f, i) => renderFieldRow(f, keyFields.length + i, suggestions, learningProfile)).join('')}
        </div>
      </details>
    `;
    body.appendChild(optSection);
  }

  // Wire up checkbox change events
  const checkboxes = body.querySelectorAll('.field-toggle');
  checkboxes.forEach(cb => {
    cb.addEventListener('change', () => {
      const rowId = cb.dataset.rowId;
      panelState.selectionByRowId[rowId] = cb.checked;
      updateApplyButtonState();
    });
  });

  // Wire up Copy button events
  const copyButtons = body.querySelectorAll('.alp-btn-copy');
  copyButtons.forEach(btn => {
    btn.addEventListener('click', async (ev) => {
      ev.stopPropagation();
      const suggestionValue = btn.dataset.suggestion;
      if (!suggestionValue) return;

      const ok = await copyTextToClipboard(suggestionValue);
      if (ok) {
        const prev = btn.textContent;
        btn.textContent = "Copied";
        setTimeout(() => { btn.textContent = prev; }, 900);
      }
    });
  });

  // Wire up Expand button events
  const expandButtons = body.querySelectorAll('.alp-btn-expand');
  expandButtons.forEach(btn => {
    btn.addEventListener('click', (ev) => {
      ev.stopPropagation();
      const suggestionValue = btn.dataset.suggestion;
      const label = btn.dataset.label;
      const sourceLabel = btn.dataset.source;

      if (!suggestionValue) return;

      openSuggestionModal({
        label: label || "Field",
        suggestion: suggestionValue,
        sourceLabel: sourceLabel || "Suggestion",
      });
    });
  });

  // Store fields on panel for later use
  panel.__fields = sortedFields;

  // Update apply button state
  updateApplyButtonState();
}

/**
 * Render scanned fields in a table (DEPRECATED - keep for compatibility)
 */
export function renderFieldsOld(panel, fields, suggestions = {}, learningProfile = null, settings = {}) {
  const body = panel.querySelector("#al_body");
  body.innerHTML = "";

  if (fields.length === 0) {
    body.innerHTML = '<div class="muted">No form fields detected on this page.</div>';
    return;
  }

  // Calculate stats
  const totalFields = fields.length;
  const mappedCount = fields.filter(f => f.canonical).length;
  const profileFieldCount = fields.filter(f => isProfileField(f.canonical)).length;
  const sensitiveCount = fields.filter(f => isSensitiveField(f.canonical)).length;
  const requiredCount = fields.filter(f => f.required).length;
  const suggestionCount = Object.keys(suggestions).length;

  console.log(`[panelV2] Rendering ${totalFields} fields: ${mappedCount} mapped, ${profileFieldCount} from profile, ${requiredCount} required`);

  // Update status subheader
  const subheader = panel.querySelector("#al_status_subheader");
  if (subheader) {
    if (suggestionCount > 0) {
      subheader.textContent = `Step 2 of 3 — Review suggestions · ${totalFields} fields · ${mappedCount} mapped · ${suggestionCount} suggestions`;
    } else {
      subheader.textContent = `Step 1 of 3 — Review fields · ${totalFields} fields · ${mappedCount} mapped · ${profileFieldCount} from profile`;
    }
  }

  // Sort rows: required + mapped first, then required + unmapped, then optional
  const sortedFields = [...fields].sort((a, b) => {
    const aReq = a.required ? 1 : 0;
    const bReq = b.required ? 1 : 0;
    const aMapped = a.canonical ? 1 : 0;
    const bMapped = b.canonical ? 1 : 0;

    // Required + mapped first
    if (aReq && aMapped && !(bReq && bMapped)) return -1;
    if (bReq && bMapped && !(aReq && aMapped)) return 1;

    // Then required + unmapped
    if (aReq && !aMapped && !(bReq && !bMapped)) return -1;
    if (bReq && !bMapped && !(aReq && !aMapped)) return 1;

    // Required fields come before optional
    if (aReq && !bReq) return -1;
    if (bReq && !aReq) return 1;

    return 0;
  });

  console.log(`[panelV2] Sorted ${sortedFields.length} rows`);

  // Initialize selection state based on learning hints
  initializeSelectionState(sortedFields, learningProfile, suggestions, settings);

  // Learning summary
  renderLearningSummary(body, learningProfile);

  // Stats
  const stats = document.createElement("div");
  stats.className = "stats";
  stats.innerHTML = `
    <div><strong>${totalFields}</strong> fields</div>
    <div><strong>${mappedCount}</strong> mapped</div>
    <div><strong>${profileFieldCount}</strong> profile</div>
    ${requiredCount > 0 ? `<div><strong>${requiredCount}</strong> required</div>` : ''}
    ${sensitiveCount > 0 ? `<div><strong>${sensitiveCount}</strong> sensitive</div>` : ''}
  `;
  body.appendChild(stats);

  // Table
  const table = document.createElement("table");
  table.className = "fields-table";
  table.innerHTML = `
    <thead>
      <tr>
        <th style="width: 30px;" title="Rows are pre-selected when ApplyLens has learned good defaults from your previous applications on this site">✓</th>
        <th>Field</th>
        <th>Type</th>
        <th>Current</th>
        <th>Suggestion</th>
      </tr>
    </thead>
    <tbody id="al_fields_tbody"></tbody>
  `;
  body.appendChild(table);

  const tbody = table.querySelector("#al_fields_tbody");

  sortedFields.forEach((field, index) => {
    const tr = document.createElement("tr");
    tr.dataset.selector = field.selector;
    tr.dataset.canonical = field.canonical || "";

    const rowId = getRowId(field, index);
    const isSelected = panelState.selectionByRowId[rowId] || false;

    // v0.3: Checkbox for toggle - now uses selection state
    const tdCheck = document.createElement("td");
    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.className = "field-toggle";
    checkbox.dataset.field = field.selector;
    checkbox.checked = isSelected;
    checkbox.addEventListener("change", () => {
      panelState.selectionByRowId[rowId] = checkbox.checked;
      updateApplyButtonState();
    });
    tdCheck.appendChild(checkbox);
    tr.appendChild(tdCheck);

    // Field label
    const tdLabel = document.createElement("td");
    const displayLabel = field.labelText || field.nameAttr || field.idAttr || "?";
    tdLabel.innerHTML = `<div class="field-label" title="${displayLabel}">${displayLabel}</div>`;
    tr.appendChild(tdLabel);

    // Canonical type with badges
    const tdType = document.createElement("td");
    if (field.canonical) {
      let badgeClass = "canonical-badge";
      if (isProfileField(field.canonical)) badgeClass += " profile";
      if (isSensitiveField(field.canonical)) badgeClass += " sensitive";

      const reqBadge = field.required ? '<span class="req-badge">REQ</span>' : '<span class="opt-badge">opt</span>';

      tdType.innerHTML = `<span class="${badgeClass}">${field.canonical}</span>${reqBadge}`;

      // Learning badges
      const hints = field._alp_learning || {};
      if (hints.hasLocalPref || hints.learnedOnSite) {
        const badges = document.createElement("div");
        badges.className = "alp-learning-badges";

        if (hints.hasLocalPref) {
          const pill = document.createElement("span");
          pill.className = "alp-pill-learning-local";
          pill.textContent = "from last app";
          pill.title = hints.localValuePreview || "Value from your previous application on this site";
          badges.appendChild(pill);
        }

        if (hints.learnedOnSite && learningProfile?.canonical_map?.[field.canonical]) {
          const pill = document.createElement("span");
          pill.className = "alp-pill-learning-site";
          pill.textContent = "learned on site";
          pill.title = "Based on previous ApplyLens uses on this site";
          badges.appendChild(pill);
        }

        tdType.appendChild(badges);
      }
    } else {
      const reqBadge = field.required ? '<span class="req-badge">REQ</span>' : '<span class="opt-badge">opt</span>';
      tdType.innerHTML = `<span class="muted">—</span>${reqBadge}`;
    }
    tr.appendChild(tdType);

    // Current value with empty placeholder
    const tdCurrent = document.createElement("td");
    if (field.value && field.value.trim()) {
      const truncated = field.value.length > 25 ? field.value.slice(0, 25) + '...' : field.value;
      tdCurrent.innerHTML = `<div class="field-value" title="${field.value}">${truncated}</div>`;
    } else {
      tdCurrent.innerHTML = '<span class="field-value empty-placeholder">— empty —</span>';
    }
    tr.appendChild(tdCurrent);

    // Suggestion (editable) with source indicator and state
    const tdSuggestion = document.createElement("td");
    const suggestionData = suggestions[field.canonical] || suggestions[field.selector];
    const suggestion = typeof suggestionData === 'object' ? suggestionData.value : (suggestionData || "");
    const source = typeof suggestionData === 'object' ? suggestionData.source : null;

    // Determine if we have suggestions yet
    const hasSuggestions = Object.keys(suggestions).length > 0;

    if (!hasSuggestions) {
      // Before generating suggestions
      tdSuggestion.innerHTML = '<span class="suggestion-pending">Pending</span>';
    } else if (!suggestion || suggestion.trim() === "") {
      // No suggestion for this field
      tdSuggestion.innerHTML = '<span class="muted">—</span>';
    } else {
      // We have a suggestion
      tr.classList.add("alp-row-has-suggestion");

      let sourceLabel = "";
      if (source === "memory") {
        sourceLabel = `<span class="source-badge memory">💾 saved</span>`;
      } else if (source === "ai") {
        sourceLabel = `<span class="source-badge ai">🤖 AI</span>`;
      } else if (source === "profile") {
        sourceLabel = `<span class="source-badge profile">👤 profile</span>`;
      }

      // Check if suggestion matches current value
      const matchesCurrent = field.value && field.value.trim() === suggestion.trim();
      const matchesBadge = matchesCurrent ? '<span class="matches-current">✓ matches</span>' : '';

      if (field.type === "textarea" || suggestion.length > 50) {
        tdSuggestion.innerHTML = `<textarea class="suggestion-input" data-field="${field.selector}" rows="3">${suggestion}</textarea><div>${sourceLabel}${matchesBadge}</div>`;
      } else {
        tdSuggestion.innerHTML = `<input type="text" class="suggestion-input" data-field="${field.selector}" value="${suggestion}"><div>${sourceLabel}${matchesBadge}</div>`;
      }
    }

    tr.appendChild(tdSuggestion);
    tbody.appendChild(tr);
  }); // end forEach

  // Store fields on panel for later use
  panel.__fields = sortedFields;

  // Update apply button state based on initial selection
  updateApplyButtonState();
}

/**
 * Fetch profile from backend
 */
export async function fetchProfile() {
  try {
    const res = await fetch(`${APPLYLENS_API_BASE}/api/profile/me`, {
      credentials: "include",
    });

    if (!res.ok) {
      if (res.status === 401 || res.status === 403) {
        throw new Error("NOT_LOGGED_IN");
      }
      throw new Error(`HTTP_${res.status}`);
    }

    return res.json();
  } catch (err) {
    if (err.message === "NOT_LOGGED_IN" || err.message.startsWith("HTTP_")) {
      throw err;
    }
    throw new Error("NETWORK_ERROR");
  }
}

/**
 * Generate suggestions from backend
 */
export async function generateSuggestions(fields, jobContext) {
  try {
    const res = await fetch(`${APPLYLENS_API_BASE}/api/extension/form/suggestions`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({
        url: jobContext.url,
        title: jobContext.title,
        company: jobContext.company,
        fields: fields.map(f => ({
          canonical: f.canonical,
          label: f.labelText,
          type: f.type,
          current_value: f.value,
        })),
      }),
    });

    if (!res.ok) {
      if (res.status === 401 || res.status === 403) {
        throw new Error("NOT_LOGGED_IN");
      } else if (res.status >= 500) {
        throw new Error("SERVER_ERROR");
      }
      throw new Error(`HTTP_${res.status}`);
    }

    const data = await res.json();
    return data.suggestions || {}; // { canonical_field: value, ... }
  } catch (err) {
    if (err.message.startsWith("HTTP_") || err.message === "NOT_LOGGED_IN" || err.message === "SERVER_ERROR") {
      throw err;
    }
    throw new Error("NETWORK_ERROR");
  }
}

/**
 * Find phone widget elements (split country + number)
 * @param {HTMLElement} anchor - Starting element (wrapper or input)
 * @returns {{phoneInput: HTMLElement|null, countrySelect: HTMLElement|null}}
 */
function findPhoneElements(anchor) {
  if (!anchor) return { phoneInput: null, countrySelect: null };

  console.log('[panelV2] findPhoneElements starting from:', {
    tag: anchor.tagName,
    id: anchor.id,
    type: anchor.type,
    className: anchor.className
  });

  // If anchor itself is the phone input, use it directly
  if (anchor.tagName === 'INPUT' && anchor.type === 'tel') {
    console.log('[panelV2] Anchor itself is tel input!');
    return { phoneInput: anchor, countrySelect: null };
  }

  // Try nearest "phone" wrapper
  const wrapper =
    anchor.closest('div[class*="phone"], div[data-testid*="phone"], .phone-number-input') ||
    anchor.closest('div, fieldset, section') ||
    anchor;

  console.log('[panelV2] Using wrapper:', {
    tag: wrapper.tagName,
    id: wrapper.id,
    className: wrapper.className
  });

  const phoneInput =
    wrapper.querySelector('input[type="tel"]') ||
    wrapper.querySelector('input[name*="phone"], input[aria-label*="Phone"]') ||
    (anchor.tagName === 'INPUT' && anchor.type === 'tel' ? anchor : null);

  const countrySelect =
    wrapper.querySelector('select') ||
    wrapper.querySelector('select[name*="country"], select[aria-label*="Country"]');

  console.log('[panelV2] findPhoneElements result:', {
    phoneInput: phoneInput ? `${phoneInput.tagName}#${phoneInput.id}` : 'null',
    countrySelect: countrySelect ? `${countrySelect.tagName}` : 'null'
  });

  return { phoneInput, countrySelect };
}

/**
 * Wait for phone country widget to initialize, then auto-select country
 * Retries multiple times to handle async intlTelInput initialization
 * @param {HTMLElement} widgetRoot - Phone widget container or input
 * @param {string} countryCode - ISO country code (default: "us")
 * @param {number} attempt - Current attempt number (default: 1)
 */
function waitForPhoneCountryWidget(widgetRoot, countryCode = "us", attempt = 1) {
  const MAX_ATTEMPTS = 10;      // ~10 * 300ms = 3 seconds max
  const DELAY_MS = 300;

  if (!widgetRoot) {
    console.warn("[panelV2] No widgetRoot passed to waitForPhoneCountryWidget");
    return;
  }

  // Try once using existing logic
  const ok = autoSelectPhoneCountry(widgetRoot, countryCode);
  if (ok) {
    console.log(
      "[panelV2] ✓ Phone country auto-selected on attempt",
      attempt,
      "for",
      countryCode
    );
    return;
  }

  if (attempt >= MAX_ATTEMPTS) {
    console.warn(
      "[panelV2] Phone country auto-select timed out after",
      attempt,
      "attempts for",
      countryCode
    );
    return;
  }

  // Retry later – give intlTelInput time to initialize
  setTimeout(() => {
    waitForPhoneCountryWidget(widgetRoot, countryCode, attempt + 1);
  }, DELAY_MS);
}

/**
 * Auto-select phone country in dropdown (for intl phone widgets)
 * @param {HTMLElement} phoneInput - The phone input element (may have intlTelInput instance)
 * @param {string} countryCode - ISO country code (default: "us")
 * @returns {boolean} - True if country was selected
 */
function autoSelectPhoneCountry(phoneInput, countryCode = "us") {
  if (!phoneInput) return false;

  try {
    // Method 1: Check for intlTelInput via global object
    if (window.intlTelInputGlobals && typeof window.intlTelInputGlobals.getInstance === 'function') {
      const itiInstance = window.intlTelInputGlobals.getInstance(phoneInput);

      if (itiInstance && typeof itiInstance.setCountry === 'function') {
        console.log("[panelV2] Found intlTelInput instance via globals, setting country to:", countryCode);
        itiInstance.setCountry(countryCode.toLowerCase());
        console.log("[panelV2] ✓ Auto-selected phone country via intlTelInput:", countryCode);
        return true;
      }
    }

    // Method 2: Check for jQuery intlTelInput plugin
    if (window.$ && phoneInput.id) {
      const $input = window.$('#' + phoneInput.id);
      if ($input.length && typeof $input.intlTelInput === 'function') {
        try {
          $input.intlTelInput("setCountry", countryCode.toLowerCase());
          console.log("[panelV2] ✓ Auto-selected phone country via jQuery intlTelInput:", countryCode);
          return true;
        } catch (e) {
          console.warn("[panelV2] jQuery intlTelInput setCountry failed:", e.message);
        }
      }
    }

    // Method 3: Try clicking the flag dropdown and selecting country
    // Search in multiple parent levels for intlTelInput container
    let flagContainer = null;
    let currentElement = phoneInput;
    for (let i = 0; i < 5; i++) {
      if (!currentElement) break;
      flagContainer = currentElement.querySelector('.iti__flag-container, .iti__selected-flag');
      if (flagContainer) break;
      currentElement = currentElement.parentElement;
    }

    if (flagContainer) {
      console.log("[panelV2] Found intlTelInput flag container, attempting manual country selection");

      // Click to open dropdown
      flagContainer.click();

      // Wait a bit for dropdown to open, then select US
      setTimeout(() => {
        const countryList = document.querySelector('.iti__country-list');
        if (countryList) {
          const usOption = countryList.querySelector('[data-country-code="us"], .iti__united-states, [data-dial-code="1"]');
          if (usOption) {
            usOption.click();
            console.log("[panelV2] ✓ Auto-selected phone country via flag dropdown click");
          } else {
            console.warn("[panelV2] Found country list but no US option");
          }
        } else {
          console.warn("[panelV2] Clicked flag but no country list appeared");
        }
      }, 100);

      return true; // Optimistically return true
    } else {
      console.log("[panelV2] No intlTelInput flag container found (searched 5 parent levels)");
    }

    // Fallback: Try to find a native <select> in parent wrapper
    const wrapper = phoneInput.closest('div, fieldset') || phoneInput.parentElement;
    if (!wrapper) {
      console.warn("[panelV2] No wrapper found for phone country select");
      return false;
    }

    const select =
      wrapper.querySelector("select") ||
      wrapper.querySelector('select[name*="country"], select[aria-label*="Country"]');

    if (!select) {
      console.warn("[panelV2] No intlTelInput instance and no <select> found");
      return false;
    }

    const target = String(countryCode || "us").toLowerCase().trim();
    const candidates = [
      target,
      "united states",
      "united states of america",
      "usa",
      "us",
      "+1",
      "1",
    ];

    let matched = false;

    for (const opt of select.options) {
      const text = (opt.textContent || "").toLowerCase().trim();
      const val = String(opt.value || "").toLowerCase().trim();

      if (candidates.some((c) => text === c || val === c || text.includes(c))) {
        select.value = opt.value;
        select.dispatchEvent(
          new Event("change", { bubbles: true, cancelable: true })
        );
        matched = true;
        console.log("[panelV2] Auto-selected phone country option:", opt.textContent);
        break;
      }
    }

    if (!matched) {
      console.warn("[panelV2] Could not match phone country option for", countryCode);
    }

    return matched;
  } catch (err) {
    console.error("[panelV2] Error setting phone country:", err);
    return false;
  }
}

/**
 * Set React input value (bypasses React property descriptor)
 * @param {HTMLInputElement|HTMLTextAreaElement} element
 * @param {string} value
 */
function setReactInputValue(element, value) {
  if (!element) return false;

  try {
    console.log('[panelV2] setReactInputValue - BEFORE:', {
      element: element.tagName,
      id: element.id,
      currentValue: element.value,
      newValue: value
    });

    // Use React's internal setter if available (for React-controlled inputs)
    const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
      window.HTMLInputElement.prototype,
      "value"
    )?.set;
    const nativeTextAreaValueSetter = Object.getOwnPropertyDescriptor(
      window.HTMLTextAreaElement.prototype,
      "value"
    )?.set;

    const setter = element.tagName === "TEXTAREA" ? nativeTextAreaValueSetter : nativeInputValueSetter;

    if (setter) {
      setter.call(element, value);
      console.log('[panelV2] Used native setter');
    } else {
      element.value = value;
      console.log('[panelV2] Used direct assignment');
    }

    console.log('[panelV2] setReactInputValue - AFTER setter:', {
      valueNow: element.value,
      valueMatches: element.value === value
    });

    // Dispatch React-compatible events
    element.dispatchEvent(new Event("input", { bubbles: true, cancelable: true }));
    element.dispatchEvent(new Event("change", { bubbles: true, cancelable: true }));

    console.log('[panelV2] setReactInputValue - Dispatched events');

    // PERSISTENCE STRATEGY: Re-apply value if React/plugins clear it
    setTimeout(() => {
      if (element.value !== value) {
        console.log('[panelV2] Value was cleared by React/plugin, re-applying:', {
          id: element.id,
          expected: value,
          actual: element.value
        });

        // Re-apply using setter
        if (setter) {
          setter.call(element, value);
        } else {
          element.value = value;
        }

        // Re-dispatch events
        element.dispatchEvent(new Event("input", { bubbles: true, cancelable: true }));
        element.dispatchEvent(new Event("change", { bubbles: true, cancelable: true }));

        // Final persistence attempt
        setTimeout(() => {
          if (element.value !== value) {
            console.warn('[panelV2] Value still not persisting for:', element.id);
            if (setter) {
              setter.call(element, value);
            }
          } else {
            console.log('[panelV2] ✓ Value persisted after re-apply:', element.id);
          }
        }, 50);
      } else {
        console.log('[panelV2] ✓ Value persisted naturally:', element.id);
      }
    }, 150);

    // Focus WITHOUT triggering other extension conflicts
    setTimeout(() => {
      try {
        element.focus();
        element.blur();
      } catch (e) {
        // Silently ignore focus errors from other extensions
      }
    }, 0);

    return true;
  } catch (error) {
    console.warn('[panelV2] Error setting React input value:', error.message);
    return false;
  }
}

/**
 * Apply suggestions to page
 */
export function applySuggestionsToPage(panel) {
  const fields = panel.__fields || [];

  // Collect checked rows with suggestions
  const toApply = [];
  const fieldsWithoutSuggestions = [];

  for (const field of fields) {
    // Check if checkbox is checked
    const checkbox = panel.querySelector(`.field-toggle[data-field="${CSS.escape(field.selector)}"]`);
    const isChecked = checkbox && checkbox.checked;

    // Get suggestion value (from either canonical or selector key)
    const suggestionData = panel.__suggestions?.[field.canonical] || panel.__suggestions?.[field.selector];
    const suggestionValue = typeof suggestionData === 'object' ? suggestionData.value : (suggestionData || "");

    if (!suggestionValue || !suggestionValue.trim()) {
      if (isChecked) {
        fieldsWithoutSuggestions.push({
          canonical: field.canonical,
          selector: field.selector,
          label: field.labelText
        });
      }
      continue;
    }

    if (!isChecked) {
      continue; // User unchecked it
    }

    toApply.push({
      selector: field.selector,
      value: suggestionValue,
      canonical: field.canonical,
      element: field.element
    });
  }

  if (fieldsWithoutSuggestions.length > 0) {
    console.log('[panelV2] Fields checked but no suggestion:', fieldsWithoutSuggestions);
  }

  console.log(`[panelV2] Applying ${toApply.length} of ${fields.length} fields`);

  let appliedCount = 0;
  let skippedCount = 0;

  for (const item of toApply) {
    console.log('[panelV2] Applying field:', {
      selector: item.selector,
      canonical: item.canonical,
      hasValue: !!item.value,
      valueLength: item.value?.length || 0,
      hasElement: !!item.element
    });

    // Use the element reference from scan, or fallback to querySelector
    const anchor = item.element || document.querySelector(item.selector);

    if (!anchor) {
      console.warn('[panelV2] No DOM element for field:', item.selector, item.canonical);
      skippedCount++;
      continue;
    }

    try {
      // 🔹 Special case: split phone widget (country + number)
      if (item.canonical === "phone") {
        console.log('[panelV2] Phone field detected, finding phone input...', {
          anchor: anchor.tagName,
          anchorId: anchor.id,
          anchorType: anchor.type
        });

        const { phoneInput, countrySelect } = findPhoneElements(anchor);

        console.log('[panelV2] Phone input search result:', {
          found: !!phoneInput,
          element: phoneInput?.tagName,
          elementId: phoneInput?.id,
          elementType: phoneInput?.type,
          hasCountrySelect: !!countrySelect
        });

        if (!phoneInput) {
          console.warn('[panelV2] No phone input found for selector', item.selector);
          skippedCount++;
          continue;
        }

        if (setReactInputValue(phoneInput, item.value)) {
          appliedCount++;
          console.log('[panelV2] ✓ Applied phone value to input:', item.value);

          // 🔁 NEW: Retry country selection over ~3s while intlTelInput initializes
          waitForPhoneCountryWidget(phoneInput.closest('div') || phoneInput.parentElement || phoneInput, "us");
        } else {
          skippedCount++;
        }
        continue; // skip generic logic
      }

      // 🔹 Special case: country dropdown (may be part of phone widget or standalone)
      if (item.canonical === "country") {
        // First check if this is a standalone country select or part of phone widget
        let countryElement = null;

        // Check if anchor is a standard SELECT element
        if (anchor.tagName === 'SELECT') {
          countryElement = anchor;
        }
        // Check if it's a React/custom select component (INPUT with select class)
        else if (anchor.tagName === 'INPUT' &&
                 (anchor.className.includes('select') || anchor.getAttribute('role') === 'combobox')) {
          // For custom select components, just fill the input directly
          if (setReactInputValue(anchor, item.value)) {
            appliedCount++;
            console.log('[panelV2] ✓ Applied country value to custom select input:', item.value);
          } else {
            skippedCount++;
          }
          continue;
        }
        // Fallback: look for select in phone widget
        else {
          const { countrySelect: phoneWidgetCountry } = findPhoneElements(anchor);
          countryElement = phoneWidgetCountry;
        }

        if (!countryElement) {
          console.warn('[panelV2] No country select found for selector', item.selector);
          skippedCount++;
          continue;
        }

        // Standard SELECT handling
        // Try to match by option text or value (very forgiving)
        const target = String(item.value || "").toLowerCase().trim();
        let matched = false;

        for (const opt of countryElement.options) {
          const text = opt.textContent.toLowerCase().trim();
          const val = String(opt.value || "").toLowerCase().trim();

          if (text === target || val === target || text.includes(target) || val.includes(target)) {
            countryElement.value = opt.value;
            countryElement.dispatchEvent(
              new Event("change", { bubbles: true, cancelable: true })
            );
            matched = true;
            appliedCount++;
            console.log('[panelV2] Applied country value:', opt.value);
            break;
          }
        }

        if (!matched) {
          console.warn('[panelV2] Could not match country option for', item.value);
          skippedCount++;
        }
        continue; // skip generic logic
      }

      // 🔹 Fallback: generic fields (name, email, Q&A, etc.)
      const element = anchor;

      if (element.tagName === "INPUT" || element.tagName === "TEXTAREA") {
        if (setReactInputValue(element, item.value)) {
          appliedCount++;
        } else {
          skippedCount++;
        }
      } else if (element.tagName === "SELECT") {
        element.value = item.value;
        element.dispatchEvent(new Event("change", { bubbles: true, cancelable: true }));
        appliedCount++;
      } else {
        // Fallback: try textContent
        element.textContent = item.value;
        element.dispatchEvent?.(new Event("change", { bubbles: true, cancelable: true }));
        appliedCount++;
      }
    } catch (error) {
      console.warn('[panelV2] Error applying field (likely extension conflict):', item.selector, error.message);
      skippedCount++;
    }
  }

  console.log(`[panelV2] Applied ${appliedCount} suggestions to page (${skippedCount} skipped, no element found)`);

  // Show success banner
  if (appliedCount > 0) {
    showBanner(panel, `✓ Applied ${appliedCount} fields to this page. You can tweak them manually before submitting.`, "success");

    // Update status subheader
    const subheader = panel.querySelector("#al_status_subheader");
    if (subheader) {
      subheader.textContent = `Step 3 of 3 — Applied to page · ${appliedCount} fields filled`;
    }
  }

  return appliedCount;
}

/**
 * Log application to backend
 */
export async function logApplication(jobContext) {
  try {
    const res = await fetch(`${APPLYLENS_API_BASE}/api/extension/log-application`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({
        url: jobContext.url,
        title: jobContext.title,
        company: jobContext.company,
        source: "extension",
        notes: "Logged from Companion v0.2",
      }),
    });

    if (!res.ok) {
      if (res.status === 401 || res.status === 403) {
        throw new Error("NOT_LOGGED_IN");
      }
      throw new Error(`HTTP_${res.status}`);
    }

    return res.json();
  } catch (err) {
    if (err.message === "NOT_LOGGED_IN" || err.message.startsWith("HTTP_")) {
      throw err;
    }
    throw new Error("NETWORK_ERROR");
  }
}

/**
 * Generate cover letter from backend
 * @param {Object} jobContext - Job context from collectJobContext()
 * @param {string} jobDescription - Job description text
 * @returns {Promise<string>} Generated cover letter text
 */
export async function generateCoverLetter(jobContext, jobDescription) {
  try {
    const res = await fetch(`${APPLYLENS_API_BASE}/api/extension/cover-letter`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({
        job_title: jobContext.title,
        company: jobContext.company,
        job_url: jobContext.url,
        job_description: jobDescription,
      }),
    });

    if (!res.ok) {
      if (res.status === 401 || res.status === 403) {
        throw new Error("NOT_LOGGED_IN");
      } else if (res.status >= 500) {
        throw new Error("SERVER_ERROR");
      }
      throw new Error(`HTTP_${res.status}`);
    }

    const data = await res.json();
    return data.text || data.cover_letter || "";
  } catch (err) {
    if (err.message.startsWith("HTTP_") || err.message === "NOT_LOGGED_IN" || err.message === "SERVER_ERROR") {
      throw err;
    }
    console.error("[panelV2] Cover letter generation error:", err);
    throw new Error("NETWORK_ERROR");
  }
}

export function showBanner(panel, message, type = "info") {
  const body = panel.querySelector("#al_body");

  // Remove existing banners
  const existingBanners = body.querySelectorAll(".alp-scan-banner");
  existingBanners.forEach(b => b.remove());

  // Parse message for structured banner (e.g., "✓ Scan complete · 11 fields · 7 mapped")
  const parts = message.split('·').map(p => p.trim());
  const mainText = parts[0] || message;
  const meta = parts.slice(1).join(' · ');

  const banner = document.createElement("div");
  banner.className = `alp-scan-banner alp-scan-banner--${type}`;
  banner.innerHTML = `
    <div class="alp-scan-banner-text">
      <span class="alp-scan-banner-icon">✓</span>
      <span>${mainText.replace('✓', '').trim()}</span>
      ${meta ? `<span class="alp-scan-banner-meta">${meta}</span>` : ''}
    </div>
  `;

  body.insertBefore(banner, body.firstChild);

  console.log(`[panelV2] Showed ${type} banner: ${message}`);

  return banner;
}

/**
 * Show status message in panel
 */
export function showStatus(panel, message, type = "success") {
  const body = panel.querySelector("#al_body");

  const existing = body.querySelector(".status-message");
  if (existing) existing.remove();

  const statusDiv = document.createElement("div");
  statusDiv.className = `status-message status-${type}`;
  statusDiv.textContent = message;

  body.insertBefore(statusDiv, body.firstChild);

  // Auto-remove after 5 seconds
  if (type === "success") {
    setTimeout(() => statusDiv.remove(), 5000);
  }
}

/**
 * v0.3: Show cover letter modal with editable textarea
 */
export function showCoverLetterModal(panel, coverLetterText, coverLetterField) {
  const body = panel.querySelector("#al_body");

  // Remove existing cover letter section
  const existing = body.querySelector(".cover-letter-section");
  if (existing) existing.remove();

  const section = document.createElement("div");
  section.className = "cover-letter-section";
  section.style.cssText = `
    padding: 16px;
    margin: 12px 0;
    background: #1e293b;
    border: 1px solid #334155;
    border-radius: 8px;
  `;

  section.innerHTML = `
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
      <h3 style="margin: 0; font-size: 14px; font-weight: 600; color: #e2e8f0;">
        📝 Generated Cover Letter
      </h3>
      <button class="close-cover-letter" style="
        background: transparent;
        border: none;
        color: #94a3b8;
        font-size: 18px;
        cursor: pointer;
        padding: 0 4px;
      ">×</button>
    </div>

    <textarea class="cover-letter-text" style="
      width: 100%;
      min-height: 300px;
      padding: 12px;
      background: #0f172a;
      border: 1px solid #334155;
      border-radius: 6px;
      color: #e2e8f0;
      font-family: inherit;
      font-size: 13px;
      line-height: 1.6;
      resize: vertical;
    ">${coverLetterText}</textarea>

    <div style="display: flex; gap: 8px; margin-top: 12px;">
      ${coverLetterField ? `
        <button class="apply-cover-letter" style="
          flex: 1;
          padding: 8px 16px;
          background: #10b981;
          color: white;
          border: 1px solid #059669;
          border-radius: 6px;
          cursor: pointer;
          font-size: 13px;
          font-weight: 500;
        ">Apply to Page</button>
      ` : ''}
      <button class="copy-cover-letter" style="
        flex: 1;
        padding: 8px 16px;
        background: #3b82f6;
        color: white;
        border: 1px solid #2563eb;
        border-radius: 6px;
        cursor: pointer;
        font-size: 13px;
        font-weight: 500;
      ">Copy to Clipboard</button>
    </div>
  `;

  // Insert at top of body
  body.insertBefore(section, body.firstChild);

  // Wire up buttons
  const textarea = section.querySelector(".cover-letter-text");
  const closeBtn = section.querySelector(".close-cover-letter");
  const applyBtn = section.querySelector(".apply-cover-letter");
  const copyBtn = section.querySelector(".copy-cover-letter");

  closeBtn.addEventListener("click", () => section.remove());

  if (applyBtn && coverLetterField) {
    applyBtn.addEventListener("click", () => {
      const text = textarea.value.trim();
      if (!text) return;

      // Find the cover letter field on page and fill it
      const element = document.querySelector(coverLetterField.selector);
      if (element) {
        element.value = text;
        element.dispatchEvent(new Event("input", { bubbles: true }));
        element.dispatchEvent(new Event("change", { bubbles: true }));

        showStatus(panel, "Cover letter applied to page! ✓", "success");

        // Update the suggestion input in the panel
        const input = panel.querySelector(`.suggestion-input[data-field="${coverLetterField.selector}"]`);
        if (input) {
          input.value = text;
        }
      } else {
        showStatus(panel, "Could not find cover letter field on page", "warning");
      }
    });
  }

  copyBtn.addEventListener("click", async () => {
    const text = textarea.value.trim();
    if (!text) return;

    try {
      await navigator.clipboard.writeText(text);
      copyBtn.textContent = "Copied ✓";
      setTimeout(() => {
        copyBtn.textContent = "Copy to Clipboard";
      }, 2000);
    } catch (err) {
      console.error("[v0.3] Copy failed:", err);
      showStatus(panel, "Could not copy to clipboard", "error");
    }
  });
}
