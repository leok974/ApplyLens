// sidepanel.js
// ApplyLens Companion sidepanel logic (Tailwind layout)
//
// Responsibilities:
// - Load current state from content script
// - Render metrics + field rows with source badges
// - Auto-check profile/learned rows
// - Trigger scan+suggest & apply-to-page
// - Show scan progress + basic tab switching
// - Theme toggle (light/dark mode)

const MSG = {
  GET_STATE: 'COMPANION_GET_STATE',
  SCAN_AND_SUGGEST: 'SCAN_AND_SUGGEST_V2',
  APPLY_MAPPINGS: 'COMPANION_APPLY_MAPPINGS',
  LOG_APPLICATION: 'LOG_APPLICATION',
  GEN_COVER_LETTER: 'GEN_COVER_LETTER',
};

const THEME_KEY = 'applylens_companion_theme';

const state = {
  tab: 'fields',
  fields: [], // [{ id, label, canonicalType, selector, currentValue, suggestedValue, source }]
  metrics: {
    jobBoard: 'Unknown',
    fieldCount: 0,
    mappedCount: 0,
    profileCount: 0,
    learningLevel: '—',
    status: 'disconnected',
  },
  scanInProgress: false,
};

// ---------- theme helpers ----------

function getInitialTheme() {
  const stored = localStorage.getItem(THEME_KEY);
  return stored === 'light' ? 'light' : 'dark';
}

function applyTheme(theme) {
  const root = document.body;

  root.classList.remove('alp-theme-light', 'alp-theme-dark');
  root.classList.add(theme === 'light' ? 'alp-theme-light' : 'alp-theme-dark');

  const icon = query('#alp-sp-theme-icon');
  if (icon) {
    // In dark mode, show sun (switch to light); in light mode, show moon
    icon.textContent = theme === 'light' ? '🌙' : '☀️';
  }
}

// ---------- helpers ----------

function query(selector) {
  return document.querySelector(selector);
}

function queryAll(selector) {
  return Array.from(document.querySelectorAll(selector));
}

function getActiveTabId() {
  return new Promise((resolve, reject) => {
    chrome.tabs.query({ active: true, currentWindow: true }, tabs => {
      if (!tabs.length) return reject(new Error('No active tab'));
      resolve(tabs[0].id);
    });
  });
}

async function sendToContent(message) {
  try {
    const tabId = await getActiveTabId();
    return await new Promise(resolve => {
      chrome.tabs.sendMessage(tabId, message, response => {
        if (chrome.runtime.lastError) {
          console.warn('[ApplyLens Sidepanel] sendMessage error:', chrome.runtime.lastError);
          return resolve(null);
        }
        resolve(response || null);
      });
    });
  } catch (err) {
    console.warn('[ApplyLens Sidepanel] Could not send message to content:', err);
    return null;
  }
}

// ---------- rendering ----------

function renderStatus() {
  const pill = query('#alp-sp-status-pill');
  if (!pill) return;

  const status = state.metrics.status;
  const dot = pill.querySelector('span:first-child');
  const label = pill.querySelector('span:last-child');

  if (status === 'connected') {
    pill.className =
      'flex items-center gap-1 rounded-full border border-emerald-400/60 bg-emerald-500/10 px-3 py-1 text-[11px] text-emerald-300';
    if (dot) dot.className = 'h-2 w-2 rounded-full bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.8)]';
    if (label) label.textContent = 'Connected';
  } else if (status === 'scanning') {
    pill.className =
      'flex items-center gap-1 rounded-full border border-cyan-400/60 bg-cyan-500/10 px-3 py-1 text-[11px] text-cyan-200';
    if (dot) dot.className = 'h-2 w-2 rounded-full bg-cyan-400 shadow-[0_0_8px_rgba(34,211,238,0.8)] animate-pulse';
    if (label) label.textContent = 'Scanning…';
  } else {
    pill.className =
      'flex items-center gap-1 rounded-full border border-slate-600/60 bg-slate-900/80 px-3 py-1 text-[11px] text-slate-300';
    if (dot) dot.className = 'h-2 w-2 rounded-full bg-slate-500';
    if (label) label.textContent = 'Idle';
  }
}

function renderMetrics() {
  const m = state.metrics;

  const setText = (id, value) => {
    const el = query(id);
    if (el) el.textContent = value;
  };

  setText('#alp-sp-job-board', m.jobBoard || 'Unknown');
  setText('#alp-sp-metric-fields', m.fieldCount ?? 0);
  setText('#alp-sp-metric-mapped', m.mappedCount ?? 0);
  setText('#alp-sp-metric-profile', m.profileCount ?? 0);
  setText('#alp-sp-metric-learning', m.learningLevel || '—');

  renderStatus();
}

function renderScanIndicator() {
  const bar = query('#alp-sp-scan-progress');
  const label = query('#alp-sp-scan-label');
  if (!bar || !label) return;

  if (state.scanInProgress) {
    bar.classList.remove('hidden');
    bar.classList.add('block');
    label.textContent = 'Scanning form and generating suggestions…';
  } else {
    bar.classList.add('hidden');
    bar.classList.remove('block');
    label.textContent = '';
  }
}

function badgeForSource(source) {
  switch (source) {
    case 'profile':
      return {
        text: 'From profile',
        classes:
          'inline-flex w-fit items-center gap-1 rounded-full bg-emerald-500/15 px-2 py-0.5 text-[10px] text-emerald-300',
        dot: 'h-1.5 w-1.5 rounded-full bg-emerald-400',
      };
    case 'learned':
      return {
        text: 'Learned',
        classes:
          'inline-flex w-fit items-center gap-1 rounded-full bg-cyan-500/15 px-2 py-0.5 text-[10px] text-cyan-300',
        dot: 'h-1.5 w-1.5 rounded-full bg-cyan-400',
      };
    case 'ai':
      return {
        text: 'AI suggestion',
        classes:
          'inline-flex w-fit items-center gap-1 rounded-full bg-indigo-500/15 px-2 py-0.5 text-[10px] text-indigo-200',
        dot: 'h-1.5 w-1.5 rounded-full bg-indigo-400',
      };
    default:
      return null;
  }
}

function renderFieldRows() {
  const container = query('#alp-sp-field-rows');
  if (!container) return;

  container.innerHTML = '';

  if (!state.fields.length) {
    const empty = document.createElement('div');
    empty.className = 'flex h-full items-center justify-center text-[12px] text-slate-400';
    empty.textContent = 'No fields detected yet. Click "Generate suggestions" to scan the form.';
    container.appendChild(empty);
    updateApplyButtonState();
    return;
  }

  for (const field of state.fields) {
    const row = document.createElement('div');
    row.className = 'alp-sp-row alp-field-row';
    row.dataset.fieldId = field.id || '';
    row.dataset.selector = field.selector || '';
    row.dataset.canonical = field.canonicalType || '';
    row.dataset.source = field.source || 'ai';
    row.dataset.suggestedValue = field.suggestedValue ?? '';

    const isTrustedSource =
      field.source === 'profile' || field.source === 'learned';
    const isCheckedByDefault = Boolean(field.suggestedValue) && isTrustedSource;

    // checkbox
    const checkboxCell = document.createElement('div');
    checkboxCell.className = 'flex justify-center';
    const checkbox = document.createElement('input');
    checkbox.type = 'checkbox';
    checkbox.className = 'alp-field-checkbox h-3.5 w-3.5 accent-cyan-400 cursor-pointer';
    checkbox.checked = isCheckedByDefault;
    checkbox.addEventListener('change', updateApplyButtonState);
    checkboxCell.appendChild(checkbox);

    // label + badge
    const labelCell = document.createElement('div');
    labelCell.className = 'flex flex-col gap-0.5';
    const labelSpan = document.createElement('span');
    labelSpan.textContent = field.label || '(unnamed field)';
    labelCell.appendChild(labelSpan);

    const badgeInfo = badgeForSource(field.source);
    if (badgeInfo) {
      const badge = document.createElement('span');
      badge.className = badgeInfo.classes;
      const dot = document.createElement('span');
      dot.className = badgeInfo.dot;
      const text = document.createElement('span');
      text.textContent = badgeInfo.text;
      badge.appendChild(dot);
      badge.appendChild(text);
      labelCell.appendChild(badge);
    }

    // type pill
    const typeCell = document.createElement('div');
    const typePill = document.createElement('span');
    typePill.className =
      'inline-flex items-center rounded-full border border-slate-600/80 bg-slate-900/80 px-2 py-0.5 text-[10px] text-slate-300';
    typePill.textContent = field.canonicalType || 'unknown';
    typeCell.appendChild(typePill);

    // current value
    const currentCell = document.createElement('div');
    currentCell.className = 'truncate text-[11px] text-slate-300';
    currentCell.title = field.currentValue || '';
    currentCell.textContent = field.currentValue || '—';

    // suggestion
    const suggestionCell = document.createElement('div');
    suggestionCell.className = 'truncate text-[11px] text-cyan-300';
    suggestionCell.title = field.suggestedValue || '';
    suggestionCell.textContent = field.suggestedValue || '—';

    row.appendChild(checkboxCell);
    row.appendChild(labelCell);
    row.appendChild(typeCell);
    row.appendChild(currentCell);
    row.appendChild(suggestionCell);

    container.appendChild(row);
  }

  updateApplyButtonState();
}

function updateApplyButtonState() {
  const applyBtn = query('#alp-sp-apply');
  if (!applyBtn) return;

  const checkboxes = queryAll('.alp-field-checkbox');
  const anyChecked = checkboxes.some(cb => cb.checked);

  applyBtn.disabled = !anyChecked;
  if (anyChecked) {
    applyBtn.classList.remove('opacity-50', 'cursor-not-allowed');
  } else {
    applyBtn.classList.add('opacity-50', 'cursor-not-allowed');
  }
}

// ---------- tabs & animations ----------

function switchTab(tab) {
  state.tab = tab;

  // update tab buttons
  queryAll('.alp-sp-tab').forEach(btn => {
    const isActive = btn.dataset.tab === tab;
    btn.classList.toggle('alp-tab-active', isActive);
  });

  // toggle view visibility
  queryAll('.alp-sp-view').forEach(viewEl => {
    const viewId = viewEl.id.replace('view-', '');
    const isActive = viewId === tab;

    if (isActive) {
      viewEl.classList.remove('hidden');
      setTimeout(() => {
        viewEl.classList.add('opacity-100', 'translate-y-0');
        viewEl.classList.remove('opacity-0', 'translate-y-1');
      }, 10);
    } else {
      viewEl.classList.add('opacity-0', 'translate-y-1');
      viewEl.classList.remove('opacity-100', 'translate-y-0');
      setTimeout(() => {
        viewEl.classList.add('hidden');
      }, 150);
    }
  });
}

// ---------- actions ----------

async function handleScanAndSuggest() {
  console.log('[ApplyLens Sidepanel] Generate suggestions clicked');

  state.scanInProgress = true;
  state.metrics.status = 'scanning';
  renderStatus();
  renderScanIndicator();

  const response = await sendToContent({
    type: MSG.SCAN_AND_SUGGEST,
  });

  state.scanInProgress = false;
  state.metrics.status = 'connected';

  if (!response) {
    console.warn('[ApplyLens Sidepanel] No response from scan');
    renderStatus();
    renderScanIndicator();
    return;
  }

  // expected shape from content:
  // {
  //   jobBoard: string,
  //   fields: [...],
  //   metrics: { fieldCount, mappedCount, profileCount, learningLevel }
  // }
  if (response.metrics) {
    state.metrics = {
      ...state.metrics,
      ...response.metrics,
      jobBoard: response.jobBoard || state.metrics.jobBoard,
      status: 'connected',
    };
  }
  if (Array.isArray(response.fields)) {
    state.fields = response.fields;
  }

  renderMetrics();
  renderFieldRows();
  renderScanIndicator();
}

async function handleApplyToPage() {
  console.log('[ApplyLens Sidepanel] Apply to page clicked');

  const rows = queryAll('.alp-sp-row');
  if (!rows.length) return;

  const selected = rows.filter(row => {
    const cb = row.querySelector('input[type="checkbox"]');
    return cb && cb.checked;
  });

  if (!selected.length) {
    console.warn('[ApplyLens Sidepanel] No fields selected');
    return;
  }

  const mappings = selected.map(row => ({
    fieldId: row.dataset.fieldId || null,
    selector: row.dataset.selector || null,
    canonicalType: row.dataset.canonical || null,
    value: row.dataset.suggestedValue || '',
  }));

  console.log('[ApplyLens Sidepanel] Applying mappings:', mappings);

  await sendToContent({
    type: MSG.APPLY_MAPPINGS,
    mappings,
  });

  // Flash success state
  const applyBtn = query('#alp-sp-apply');
  if (applyBtn) {
    const originalText = applyBtn.textContent;
    applyBtn.textContent = '✓ Applied';
    setTimeout(() => {
      applyBtn.textContent = originalText;
    }, 2000);
  }
}

async function handleCoverLetter() {
  console.log('[ApplyLens Sidepanel] Cover letter clicked');

  await sendToContent({
    type: MSG.GEN_COVER_LETTER,
  });
}

async function handleLogApplication() {
  console.log('[ApplyLens Sidepanel] Log application clicked');

  await sendToContent({
    type: MSG.LOG_APPLICATION,
    payload: {
      source: 'companion_sidepanel',
    },
  });

  // Flash success state
  const logBtn = query('#alp-sp-log');
  if (logBtn) {
    const originalText = logBtn.textContent;
    logBtn.textContent = '✓ Logged';
    setTimeout(() => {
      logBtn.textContent = originalText;
    }, 2000);
  }
}

// ---------- init ----------

async function loadInitialState() {
  console.log('[ApplyLens Sidepanel] Loading initial state...');

  // Detect job board from URL
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (tab?.url) {
      const hostname = new URL(tab.url).hostname;
      if (hostname.includes('greenhouse')) {
        state.metrics.jobBoard = 'Greenhouse';
      } else if (hostname.includes('lever')) {
        state.metrics.jobBoard = 'Lever';
      } else if (hostname.includes('workday')) {
        state.metrics.jobBoard = 'Workday';
      } else if (hostname.includes('smartrecruiters')) {
        state.metrics.jobBoard = 'SmartRecruiters';
      } else if (hostname.includes('ashby')) {
        state.metrics.jobBoard = 'Ashby';
      } else {
        state.metrics.jobBoard = hostname;
      }
    }
  } catch (err) {
    console.warn('[ApplyLens Sidepanel] Could not detect job board:', err);
  }

  const response = await sendToContent({
    type: MSG.GET_STATE,
  });

  if (!response) {
    console.warn('[ApplyLens Sidepanel] No initial state from content script');
    state.metrics.status = 'disconnected';
    renderMetrics();
    renderFieldRows();
    renderScanIndicator();
    return;
  }

  state.metrics = {
    ...state.metrics,
    jobBoard: response.jobBoard || state.metrics.jobBoard,
    fieldCount: response.metrics?.fieldCount ?? state.metrics.fieldCount,
    mappedCount: response.metrics?.mappedCount ?? state.metrics.mappedCount,
    profileCount: response.metrics?.profileCount ?? state.metrics.profileCount,
    learningLevel: response.metrics?.learningLevel || state.metrics.learningLevel,
    status: 'connected',
  };

  if (Array.isArray(response.fields)) {
    state.fields = response.fields;
  }

  console.log('[ApplyLens Sidepanel] Initial state loaded:', state);

  renderMetrics();
  renderFieldRows();
  renderScanIndicator();
}

function wireEvents() {
  // tabs
  queryAll('.alp-sp-tab').forEach(btn => {
    btn.addEventListener('click', () => {
      switchTab(btn.dataset.tab || 'fields');
    });
  });

  const genBtn = query('#alp-sp-generate');
  if (genBtn) genBtn.addEventListener('click', handleScanAndSuggest);

  const coverLetterBtn = query('#alp-sp-coverletter');
  if (coverLetterBtn) coverLetterBtn.addEventListener('click', handleCoverLetter);

  const applyBtn = query('#alp-sp-apply');
  if (applyBtn) applyBtn.addEventListener('click', handleApplyToPage);

  const logBtn = query('#alp-sp-log');
  if (logBtn) logBtn.addEventListener('click', handleLogApplication);

  // theme toggle
  const themeToggle = query('#alp-sp-theme-toggle');
  if (themeToggle) {
    themeToggle.addEventListener('click', () => {
      const current = document.body.classList.contains('alp-theme-light')
        ? 'light'
        : 'dark';
      const next = current === 'light' ? 'dark' : 'light';
      localStorage.setItem(THEME_KEY, next);
      applyTheme(next);
    });
  }

  // default tab
  switchTab('fields');
}

document.addEventListener('DOMContentLoaded', async () => {
  console.log('[ApplyLens Sidepanel] DOMContentLoaded');

  // Apply initial theme
  const initialTheme = getInitialTheme();
  applyTheme(initialTheme);

  wireEvents();
  await loadInitialState();
});
const jobBoardEl = document.getElementById("alp-sp-job-board");
const metricFields = document.getElementById("alp-sp-metric-fields");
const metricMapped = document.getElementById("alp-sp-metric-mapped");
const metricProfile = document.getElementById("alp-sp-metric-profile");
const metricLearning = document.getElementById("alp-sp-metric-learning");
const fieldRows = document.getElementById("alp-sp-field-rows");

// Tab navigation
const tabs = document.querySelectorAll(".alp-sp-tab");
const views = document.querySelectorAll(".alp-sp-view");

tabs.forEach(tab => {
  tab.addEventListener("click", () => {
    const targetView = tab.dataset.tab;

    // Update tab active state
    tabs.forEach(t => {
      t.classList.remove("alp-sp-tab--active", "bg-cyan-500/20", "border", "border-cyan-400/60", "text-cyan-300", "shadow-[0_0_8px_rgba(56,189,248,0.4)]");
      t.classList.add("text-slate-300");
    });
    tab.classList.remove("text-slate-300");
    tab.classList.add("alp-sp-tab--active", "bg-cyan-500/20", "border", "border-cyan-400/60", "text-cyan-300", "shadow-[0_0_8px_rgba(56,189,248,0.4)]");

    // Update view visibility
    views.forEach(view => {
      view.classList.add("hidden");
    });
    document.getElementById(`view-${targetView}`).classList.remove("hidden");
  });
});

// Button handlers
const generateBtn = document.getElementById("alp-sp-generate");
const coverLetterBtn = document.getElementById("alp-sp-coverletter");
const applyBtn = document.getElementById("alp-sp-apply");
const logBtn = document.getElementById("alp-sp-log");

generateBtn?.addEventListener("click", async () => {
  console.log("[Sidepanel] Generate suggestions clicked");
  // TODO: Wire to scan and generate logic
  alert("Generate suggestions - to be implemented");
});

coverLetterBtn?.addEventListener("click", async () => {
  console.log("[Sidepanel] Cover letter clicked");
  // TODO: Wire to cover letter generation
  alert("Cover letter generation - to be implemented");
});

applyBtn?.addEventListener("click", async () => {
  console.log("[Sidepanel] Apply to page clicked");
  // TODO: Wire to apply logic
  alert("Apply to page - to be implemented");
});

logBtn?.addEventListener("click", async () => {
  console.log("[Sidepanel] Log application clicked");
  // TODO: Wire to log application logic
  alert("Log application - to be implemented");
});

/**
 * Render field rows into the table
 * @param {Array} fields - Array of field objects with { label, type, current, suggestion, source }
 */
function renderFieldRows(fields) {
  if (!fields || fields.length === 0) {
    fieldRows.innerHTML = `
      <div class="flex h-full items-center justify-center text-[12px] text-slate-400">
        No fields scanned yet. Click "Generate suggestions" to start.
      </div>
    `;
    return;
  }

  fieldRows.innerHTML = "";

  for (const field of fields) {
    const row = document.createElement("div");
    row.className = "alp-sp-row grid grid-cols-[20px,1.2fr,0.9fr,1fr,1fr] items-center gap-2 rounded-lg px-1.5 py-1.5 text-slate-100 hover:bg-slate-800/80 transition";
    row.dataset.source = field.source || "manual";

    // Auto-check if source is profile or learned
    const autoCheck = field.source === "profile" || field.source === "learned";

    // Badge colors based on source
    const badgeConfig = {
      profile: { bg: "bg-emerald-500/15", text: "text-emerald-300", dot: "bg-emerald-400", label: "From profile" },
      learned: { bg: "bg-cyan-500/15", text: "text-cyan-300", dot: "bg-cyan-400", label: "Learned" },
      ai: { bg: "bg-purple-500/15", text: "text-purple-300", dot: "bg-purple-400", label: "AI suggested" },
      manual: { bg: "bg-slate-600/15", text: "text-slate-400", dot: "bg-slate-500", label: "Manual" }
    };
    const badge = badgeConfig[field.source] || badgeConfig.manual;

    row.innerHTML = `
      <!-- checkbox -->
      <div class="flex justify-center">
        <input type="checkbox" class="alp-field-checkbox h-3.5 w-3.5 accent-cyan-400 cursor-pointer" ${autoCheck ? "checked" : ""} />
      </div>

      <!-- label + badge -->
      <div class="flex flex-col gap-0.5">
        <span class="text-[12px]">${field.label || "Unknown"}</span>
        <span class="inline-flex w-fit items-center gap-1 rounded-full ${badge.bg} px-2 py-0.5 text-[10px] ${badge.text}">
          <span class="h-1.5 w-1.5 rounded-full ${badge.dot}"></span>
          ${badge.label}
        </span>
      </div>

      <!-- type pill -->
      <div>
        <span class="inline-flex items-center rounded-full border border-slate-600/80 bg-slate-900/80 px-2 py-0.5 text-[10px] text-slate-300">
          ${field.type || "text"}
        </span>
      </div>

      <!-- current -->
      <div class="truncate text-[11px] text-slate-300" title="${field.current || ""}">
        ${field.current || "—"}
      </div>

      <!-- suggestion -->
      <div class="truncate text-[11px] text-cyan-300" title="${field.suggestion || ""}">
        ${field.suggestion || "—"}
      </div>
    `;

    fieldRows.appendChild(row);
  }

  // Update metrics
  metricFields.textContent = fields.length;
  const mappedCount = fields.filter(f => f.suggestion).length;
  metricMapped.textContent = mappedCount;
  const profileCount = fields.filter(f => f.source === "profile").length;
  metricProfile.textContent = profileCount;

  // Update apply button state
  updateApplyButtonState();
}

/**
 * Update apply button state based on checked fields
 */
function updateApplyButtonState() {
  const checkboxes = document.querySelectorAll(".alp-field-checkbox");
  const anyChecked = Array.from(checkboxes).some(cb => cb.checked);

  if (applyBtn) {
    applyBtn.disabled = !anyChecked;
    if (anyChecked) {
      applyBtn.classList.remove("opacity-50", "cursor-not-allowed");
    } else {
      applyBtn.classList.add("opacity-50", "cursor-not-allowed");
    }
  }
}

// Listen for checkbox changes
document.addEventListener("change", (e) => {
  if (e.target.classList.contains("alp-field-checkbox")) {
    updateApplyButtonState();
  }
});

// Initialize
(async () => {
  console.log("[Sidepanel] Initializing with API:", APPLYLENS_API_BASE);

  // Detect job board from current page
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (tab?.url) {
      const hostname = new URL(tab.url).hostname;
      if (hostname.includes("greenhouse")) {
        jobBoardEl.textContent = "Greenhouse";
      } else if (hostname.includes("lever")) {
        jobBoardEl.textContent = "Lever";
      } else if (hostname.includes("workday")) {
        jobBoardEl.textContent = "Workday";
      } else if (hostname.includes("smartrecruiters")) {
        jobBoardEl.textContent = "SmartRecruiters";
      } else if (hostname.includes("ashby")) {
        jobBoardEl.textContent = "Ashby";
      } else {
        jobBoardEl.textContent = hostname;
      }
    }
  } catch (err) {
    console.warn("[Sidepanel] Could not detect job board:", err);
  }

  // Check backend health
  try {
    const r = await fetch(`${APPLYLENS_API_BASE}/api/profile/me`, { credentials: "include" });
    if (r.ok) {
      statusPill.innerHTML = `
        <span class="h-2 w-2 rounded-full bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.8)]"></span>
        <span>Connected</span>
      `;
      statusPill.className = "flex items-center gap-1 rounded-full border border-emerald-400/60 bg-emerald-500/10 px-3 py-1 text-[11px] text-emerald-300";

      // Load profile data
      const profile = await r.json();
      document.getElementById("alp-sp-profile-name").textContent = profile.name || profile.email || "—";
      document.getElementById("alp-sp-profile-email").textContent = profile.email || "—";
      document.getElementById("alp-sp-profile-headline").textContent = profile.headline || "—";

      // Render tech stack
      const stackEl = document.getElementById("alp-sp-profile-stack");
      if (profile.tech_stack && profile.tech_stack.length > 0) {
        stackEl.innerHTML = profile.tech_stack.map(tech =>
          `<span class="inline-flex items-center rounded-full border border-cyan-400/60 bg-cyan-500/10 px-2 py-0.5 text-[10px] text-cyan-300">${tech}</span>`
        ).join("");
      } else {
        stackEl.innerHTML = `<span class="text-[11px] text-slate-400">No tech stack defined</span>`;
      }
    } else {
      statusPill.innerHTML = `
        <span class="h-2 w-2 rounded-full bg-red-400 shadow-[0_0_8px_rgba(248,113,113,0.8)]"></span>
        <span>Disconnected</span>
      `;
      statusPill.className = "flex items-center gap-1 rounded-full border border-red-400/60 bg-red-500/10 px-3 py-1 text-[11px] text-red-300";
    }
  } catch (e) {
    console.warn("[Sidepanel] Health check failed:", e);
    statusPill.innerHTML = `
      <span class="h-2 w-2 rounded-full bg-red-400 shadow-[0_0_8px_rgba(248,113,113,0.8)]"></span>
      <span>Offline</span>
    `;
    statusPill.className = "flex items-center gap-1 rounded-full border border-red-400/60 bg-red-500/10 px-3 py-1 text-[11px] text-red-300";
  }

  // Example: Render demo fields (remove this when you wire to real data)
  const demoFields = [
    { label: "First Name", type: "first_name", current: "Leo", suggestion: "Leo", source: "profile" },
    { label: "Last Name", type: "last_name", current: "K", suggestion: "K", source: "profile" },
    { label: "Email", type: "email", current: "leo@example.com", suggestion: "leo@example.com", source: "profile" },
    { label: "Phone", type: "phone", current: "", suggestion: "+1 555-0100", source: "ai" },
    { label: "LinkedIn", type: "linkedin_url", current: "", suggestion: "linkedin.com/in/leok", source: "learned" },
  ];

  // Uncomment to test with demo data
  // renderFieldRows(demoFields);
})();
