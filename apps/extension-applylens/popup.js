// popup.js
// ApplyLens Companion popup logic (shared theme with sidepanel)

import { APPLYLENS_API_BASE } from "./config.js";

const THEME_KEY = 'applylens_companion_theme';
const VIEW_ATTR = 'view';
const VIEW_CONTAINER_ATTR = 'viewContainer';

function q(sel) {
  return document.querySelector(sel);
}

function qa(sel) {
  return Array.from(document.querySelectorAll(sel));
}

function getApiBase() {
  // Provided by config.js
  const base = window.APPLYLENS_API_BASE || APPLYLENS_API_BASE || 'https://api.applylens.app';
  return base.replace(/\/$/, '');
}

// ---------- Theme Management ----------

function getInitialTheme() {
  const stored = localStorage.getItem(THEME_KEY);
  return stored === 'light' ? 'light' : 'dark';
}

function applyTheme(theme) {
  const root = document.body;
  root.classList.remove('alp-theme-light', 'alp-theme-dark');
  root.classList.add(theme === 'light' ? 'alp-theme-light' : 'alp-theme-dark');

  const isLight = theme === 'light';

  // Toggle Lucide sun/moon icons
  const sunIcons = qa('.alp-popup-theme-icon-sun, #alp-popup-theme-icon-sun');
  const moonIcons = qa('.alp-popup-theme-icon-moon, #alp-popup-theme-icon-moon');

  sunIcons.forEach(icon => icon.classList.toggle('hidden', !isLight));
  moonIcons.forEach(icon => icon.classList.toggle('hidden', isLight));

  // Update theme label in settings
  const label = q('#alp-popup-theme-label');
  if (label) {
    label.textContent = theme === 'light' ? 'Light' : 'Dark';
  }
}

function wireThemeToggle() {
  const toggles = qa('[id^="alp-popup-theme-toggle"]');

  toggles.forEach(toggle => {
    toggle.addEventListener('click', () => {
      const current = document.body.classList.contains('alp-theme-light')
        ? 'light'
        : 'dark';
      const next = current === 'light' ? 'dark' : 'light';
      localStorage.setItem(THEME_KEY, next);
      applyTheme(next);
    });
  });
}
// ---------- Navigation ----------

function setActiveView(view) {
  const containers = qa('[data-view-container]');
  containers.forEach(el => {
    const target = el.dataset[VIEW_CONTAINER_ATTR];
    const isActive = target === view;
    el.classList.toggle('hidden', !isActive);
  });

  const items = qa('.alp-popup-sidebar-item');
  items.forEach(btn => {
    const target = btn.dataset[VIEW_ATTR];
    const isActive = target === view;
    btn.classList.toggle('alp-popup-sidebar-item-active', isActive);
  });

  console.log('[ApplyLens Popup] Switched to view:', view);

  // Refresh auth status when switching to overview
  if (view === 'overview') {
    refreshAuthStatus();
  }
}

function wireSidebarNav() {
  const items = qa('.alp-popup-sidebar-item');
  if (!items.length) return;

  items.forEach(btn => {
    btn.addEventListener('click', () => {
      const view = btn.dataset[VIEW_ATTR] || 'overview';
      setActiveView(view);
    });
  });

  // Set initial view (overview by default)
  setActiveView('overview');
}

// ---------- Content Script Communication ----------

async function getActiveTabId() {
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
          console.warn('[ApplyLens Popup] sendMessage error:', chrome.runtime.lastError);
          return resolve(null);
        }
        resolve(response || null);
      });
    });
  } catch (err) {
    console.warn('[ApplyLens Popup] Could not send message to content:', err);
    return null;
  }
}

// ---------- Timeline Helpers ----------

function formatTimestamp(isoString) {
  if (!isoString) return "recently";
  try {
    const date = new Date(isoString);
    const now = Date.now();
    const diff = now - date.getTime();
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);

    if (minutes < 1) return "just now";
    if (minutes < 60) return `${minutes}m ago`;
    if (hours < 24) return `${hours}h ago`;
    if (days < 7) return `${days}d ago`;
    return date.toLocaleDateString();
  } catch {
    return "recently";
  }
}

function addTimelineItem(text, timestamp = new Date().toISOString()) {
  const container = q('#alp-popup-timeline-content');
  if (!container) return;

  const item = document.createElement('div');
  item.className = 'grid grid-cols-[16px,1fr] gap-x-3';
  item.innerHTML = `
    <div class="mt-1 h-[7px] w-[7px] rounded-full bg-cyan-400 shadow-[0_0_10px_rgba(34,211,238,0.9)]"></div>
    <div>
      <div class="text-[12px]">${text}</div>
      <div class="text-[11px] text-slate-400">${formatTimestamp(timestamp)}</div>
    </div>
  `;

  // Insert at top
  container.insertBefore(item, container.firstChild);

  // Keep max 5 items
  while (container.children.length > 5) {
    container.removeChild(container.lastChild);
  }
}

// ---------- Job Board Detection ----------

async function detectJobBoard() {
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tab?.url) return '–';

    const hostname = new URL(tab.url).hostname;
    if (hostname.includes('greenhouse')) return 'Greenhouse';
    if (hostname.includes('lever')) return 'Lever';
    if (hostname.includes('workday')) return 'Workday';
    if (hostname.includes('smartrecruiters')) return 'SmartRecruiters';
    if (hostname.includes('ashby')) return 'Ashby';
    if (hostname.includes('linkedin')) return 'LinkedIn';

    return hostname;
  } catch (err) {
    console.warn('[ApplyLens Popup] Job board detection error:', err);
    return '–';
  }
}

// ---------- Authentication Status ----------

async function fetchProfile() {
  const base = getApiBase();
  const url = `${base}/api/profile/me`;

  console.log('[ApplyLens Popup] Fetching profile from:', url);

  try {
    const res = await fetch(url, {
      method: 'GET',
      credentials: 'include',
      headers: { Accept: 'application/json' },
    });

    console.log('[ApplyLens Popup] Profile response status:', res.status);

    if (!res.ok) {
      console.warn('[ApplyLens Popup] /profile/me failed:', res.status, res.statusText);
      return null;
    }

    const data = await res.json();
    console.log('[ApplyLens Popup] Profile data:', data);
    return data;
  } catch (err) {
    console.warn('[ApplyLens Popup] /profile/me error:', err);
    return null;
  }
}

function renderAuthPill({ status, email } = {}) {
  const pill = q('#alp-popup-auth-pill');
  const valueEl = q('#alp-popup-auth-value');
  const emailEl = q('#alp-popup-auth-email');
  if (!pill || !valueEl) return;

  // Reset classes
  pill.classList.remove(
    'border-slate-700/80',
    'border-emerald-500/80',
    'border-amber-500/80'
  );
  valueEl.classList.remove('text-emerald-300', 'text-amber-300', 'text-slate-300');

  let label = 'No';
  let pillBorder = 'border-slate-700/80';
  let tone = 'text-amber-300';

  if (status === 'loading') {
    label = '…';
    tone = 'text-slate-300';
  } else if (status === 'signed_in') {
    label = 'Yes';
    pillBorder = 'border-emerald-500/80';
    tone = 'text-emerald-300';
  } else if (status === 'error') {
    label = 'Unknown';
    pillBorder = 'border-amber-500/80';
    tone = 'text-amber-300';
  } else {
    // signed_out or default
    label = 'No';
    pillBorder = 'border-slate-700/80';
    tone = 'text-amber-300';
  }

  valueEl.textContent = label;
  pill.classList.add(pillBorder);
  valueEl.classList.add(tone);

  if (emailEl) {
    if (status === 'signed_in' && email) {
      emailEl.textContent = email;
      emailEl.classList.remove('hidden');
    } else {
      emailEl.textContent = '';
      emailEl.classList.add('hidden');
    }
  }
}

async function refreshAuthStatus() {
  renderAuthPill({ status: 'loading' });

  const profile = await fetchProfile();

  console.log('[ApplyLens Popup] Profile result:', JSON.stringify(profile, null, 2));

  if (!profile || !profile.name) {
    const status = profile === null ? 'error' : 'signed_out';
    renderAuthPill({ status });
    console.log('[ApplyLens Popup] Auth status:', status, '- Missing name field. Profile keys:', profile ? Object.keys(profile) : 'null');
    return;
  }

  renderAuthPill({ status: 'signed_in', email: profile.name });
  console.log('[ApplyLens Popup] Auth status: signed_in as', profile.name);
}

// ---------- API Health Check ----------

async function checkAPIHealth() {
  const statusEl = q('#alp-popup-api-status');
  const signedInEl = q('#alp-popup-signed-in');
  const settingsStatusEl = q('#alp-popup-settings-api-status');

  try {
    const response = await fetch(`${APPLYLENS_API_BASE}/api/profile/me`, {
      credentials: 'include',
    });

    const updateStatus = (el, text, className) => {
      if (el) {
        el.textContent = text;
        if (className) el.className = className;
      }
    };

    if (response.ok) {
      updateStatus(statusEl, 'Online', 'mt-0.5 text-[13px] font-semibold text-emerald-400');
      updateStatus(settingsStatusEl, 'Online', 'text-cyan-400');

      const data = await response.json();
      updateStatus(signedInEl, data.email ? 'Yes' : 'No', 'mt-0.5 text-[13px] font-semibold');
    } else {
      updateStatus(statusEl, 'Error', 'mt-0.5 text-[13px] font-semibold text-red-400');
      updateStatus(settingsStatusEl, 'Error', 'text-red-400');

      if (response.status === 401 || response.status === 403) {
        updateStatus(signedInEl, 'No', 'mt-0.5 text-[13px] font-semibold');
      } else {
        updateStatus(signedInEl, '?', 'mt-0.5 text-[13px] font-semibold');
      }
    }
  } catch (err) {
    console.warn('[ApplyLens Popup] API health check failed:', err);
    const updateStatus = (el, text, className) => {
      if (el) {
        el.textContent = text;
        if (className) el.className = className;
      }
    };
    updateStatus(statusEl, 'Offline', 'mt-0.5 text-[13px] font-semibold text-red-400');
    updateStatus(settingsStatusEl, 'Offline', 'text-red-400');
  }
}

// ---------- Actions ----------

function wireActions() {
  // Overview buttons
  const scanBtn = q('#alp-popup-scan');
  const applyBtn = q('#alp-popup-apply');

  // Form view buttons
  const scanFormBtn = q('#alp-popup-form-scan');
  const applyFormBtn = q('#alp-popup-form-apply');

  // DM view button
  const dmDraftBtn = q('#alp-popup-dm-draft');

  // Shared scan handler
  const scanClick = async () => {
    console.log('[ApplyLens Popup] Scan requested');

    const response = await sendToContent({ type: 'SCAN_AND_SUGGEST_V2' });

    console.log('[ApplyLens Popup] Scan response:', response);

    if (response && response.received) {
      addTimelineItem('Scan initiated - check page for panel', new Date().toISOString());

      // Update last scan metric
      const lastScanEl = q('#alp-popup-last-scan');
      if (lastScanEl) {
        lastScanEl.textContent = formatTimestamp(new Date().toISOString());
      }

      // Store scan time
      try {
        await chrome.storage.local.set({ lastScanTime: new Date().toISOString() });
      } catch (err) {
        console.warn('[ApplyLens Popup] Failed to store scan time:', err);
      }
    } else {
      addTimelineItem('Scan failed - reload page and try again', new Date().toISOString());
    }
  };

  // Shared apply handler
  const applyClick = async () => {
    console.log('[ApplyLens Popup] Apply-to-page requested');

    const response = await sendToContent({ type: 'COMPANION_APPLY_MAPPINGS' });

    if (response) {
      addTimelineItem('Fields applied to page', new Date().toISOString());
    } else {
      addTimelineItem('Apply failed - open sidepanel to select fields', new Date().toISOString());
    }
  };

  // Wire scan buttons
  if (scanBtn) scanBtn.addEventListener('click', scanClick);
  if (scanFormBtn) scanFormBtn.addEventListener('click', scanClick);

  // Wire apply buttons
  if (applyBtn) applyBtn.addEventListener('click', applyClick);
  if (applyFormBtn) applyFormBtn.addEventListener('click', applyClick);

  // Wire DM button
  if (dmDraftBtn) {
    dmDraftBtn.addEventListener('click', async () => {
      console.log('[ApplyLens Popup] DM draft requested');
      await sendToContent({ type: 'APPLYLENS_COMPANION_DRAFT_DM' });
      addTimelineItem('Opening DM composer in ApplyLens', new Date().toISOString());
    });
  }
}

// ---------- Initialization ----------

async function init() {
  console.log('[ApplyLens Popup] Initializing...');

  // Apply theme first (before any rendering)
  const initialTheme = getInitialTheme();
  applyTheme(initialTheme);

  // Wire up UI
  wireThemeToggle();
  wireSidebarNav();
  wireActions();

  // Load auth status
  refreshAuthStatus();

  // Load initial data
  const jobBoard = await detectJobBoard();
  const jobBoardEl = q('#alp-popup-job-board');
  if (jobBoardEl) {
    jobBoardEl.textContent = jobBoard;
  }

  // Check API health
  await checkAPIHealth();

  // Load stored metrics from chrome.storage
  try {
    const stored = await chrome.storage.local.get([
      'lastScanTime',
      'learningEnabled',
    ]);

    if (stored.lastScanTime) {
      const lastScanEl = q('#alp-popup-last-scan');
      if (lastScanEl) {
        lastScanEl.textContent = formatTimestamp(stored.lastScanTime);
      }
    }

    if (stored.learningEnabled !== undefined) {
      const learningEl = q('#alp-popup-learning');
      const learningStatusEl = q('#alp-popup-learning-status');
      const status = stored.learningEnabled ? 'On' : 'Off';

      if (learningEl) {
        learningEl.textContent = status;
      }
      if (learningStatusEl) {
        learningStatusEl.textContent = status;
      }
    }
  } catch (err) {
    console.warn('[ApplyLens Popup] Failed to load stored metrics:', err);
  }

  console.log('[ApplyLens Popup] Ready');
}

document.addEventListener('DOMContentLoaded', init);
