// contentV2.js — v0.2 Job Form Mode main orchestration
// v0.3 enhancements: memory integration, cover letter generation, UX polish
// Learning v1: Server-side learning loop integration

console.log("[Companion v0.2] contentV2 script loaded on", location.hostname, location.href);

import { APPLYLENS_API_BASE } from "./config.js";
import { scanFormFields, collectJobContext } from "./fieldScanner.js";
import { collectJobDescription } from "./jobExtractor.js";
import { buildMemoryKey, loadPreferences, saveFieldPreference } from "./memoryV3Clean.js";
import { queueLearningEvent, flushLearningEvents, fetchLearningProfile } from "./learning/client.js";
import { simpleHash, editDistance } from "./learning/utils.js";
import {
  createPanel,
  renderFields,
  applySuggestionsToPage,
  showStatus,
  showCoverLetterModal,
  showBanner,
} from "./panelV2.js";

// ============================================================================
// API Helper Functions
// ============================================================================

/**
 * Get ApplyLens Extension ID
 * Reads from meta tag set by content-loader.js (CSP-safe)
 * Or from chrome.runtime.id if in extension context
 */
function getApplyLensExtensionId() {
  // Try chrome.runtime.id first (works in extension context)
  if (typeof chrome !== "undefined" && chrome.runtime?.id) {
    console.log("[ContentV2] Using extension ID from chrome.runtime:", chrome.runtime.id);
    return chrome.runtime.id;
  }

  // Try window global (set by extension-id.js)
  if (typeof window !== "undefined" && window.__APPLYLENS_EXTENSION_ID__) {
    console.log("[ContentV2] Using extension ID from window global:", window.__APPLYLENS_EXTENSION_ID__);
    return window.__APPLYLENS_EXTENSION_ID__;
  }

  // Try reading from meta tag (set by content-loader.js)
  const meta = document.querySelector('meta[name="applylens-extension-id"]');
  if (meta && meta.content) {
    console.log("[ContentV2] Using extension ID from meta tag:", meta.content);
    return meta.content;
  }

  // Try reading from script data attribute
  const idScript = document.getElementById('applylens-extension-id-script');
  if (idScript && idScript.dataset.extensionId) {
    console.log("[ContentV2] Using extension ID from script data attribute:", idScript.dataset.extensionId);
    return idScript.dataset.extensionId;
  }

  console.error("[ContentV2] Extension ID not available.");
  console.error("[ContentV2] chrome.runtime.id:", typeof chrome !== "undefined" && chrome.runtime ? chrome.runtime.id : "chrome.runtime not available");
  console.error("[ContentV2] window.__APPLYLENS_EXTENSION_ID__:", typeof window !== "undefined" ? window.__APPLYLENS_EXTENSION_ID__ : "window undefined");
  console.error("[ContentV2] meta tag:", meta ? meta.content : "not found");
  console.error("[ContentV2] id script:", idScript ? idScript.dataset.extensionId : "not found");
  return null;
}

/**
 * Send message to extension background/service worker
 * Handles both direct chrome.runtime calls and bridged calls from page context
 */
async function sendExtensionMessage(message) {
  const extensionId = getApplyLensExtensionId();

  if (!extensionId) {
    throw new Error("ApplyLens extension ID not available");
  }

  // Check if we're in page context (no chrome.runtime access)
  const hasDirectAccess = typeof chrome !== "undefined" && chrome.runtime && typeof chrome.runtime.sendMessage === "function";

  if (hasDirectAccess) {
    // Direct access - we're in extension context
    console.log("[ContentV2] Using direct chrome.runtime.sendMessage");
    return chrome.runtime.sendMessage(extensionId, message);
  } else {
    // Page context - use postMessage bridge
    console.log("[ContentV2] Using postMessage bridge to extension");
    return new Promise((resolve, reject) => {
      const requestId = `req_${Date.now()}_${Math.random()}`;

      const listener = (event) => {
        if (event.source !== window) return;
        if (event.data?.type === 'APPLYLENS_FROM_EXTENSION' && event.data.requestId === requestId) {
          window.removeEventListener('message', listener);
          resolve(event.data.response);
        }
      };

      window.addEventListener('message', listener);

      // Send via bridge
      window.postMessage({
        type: 'APPLYLENS_TO_EXTENSION',
        action: 'SEND_TO_BACKGROUND',
        payload: message,
        requestId
      }, '*');

      // Timeout after 30 seconds
      setTimeout(() => {
        window.removeEventListener('message', listener);
        reject(new Error('Extension message timeout'));
      }, 30000);
    });
  }
}

/**
 * Fetch profile from backend
 */
async function fetchProfile() {
  try {
    const response = await sendExtensionMessage({
      type: "API_PROXY",
      payload: {
        url: "/api/profile/me",
        method: "GET",
      }
    });

    if (!response.ok) {
      if (response.status === 401 || response.status === 403) {
        throw new Error("NOT_LOGGED_IN");
      }
      throw new Error(`HTTP_${response.status}`);
    }

    return response.data;
  } catch (err) {
    if (err.message === "NOT_LOGGED_IN" || err.message.startsWith("HTTP_")) {
      throw err;
    }
    throw new Error("NETWORK_ERROR");
  }
}

/**
 * Normalize answer text to remove placeholder/debug patterns
 * Safety guard against LLM returning "Answer for..." instead of actual values
 */
function normalizeAnswerText(label, raw) {
  if (!raw) return '';

  let text = String(raw).trim();

  // Kill generic "Answer for 'Field' ..." style placeholders
  const placeholderPatterns = [
    /^answer for ['"].+['"]/i,
    /^write an answer for ['"].+['"]/i,
    /based on .*my projects/i,
    /based on ai engineer/i,
    /answer the question .* based on/i,
    /\(e\.g\.,/i,
  ];

  if (placeholderPatterns.some(re => re.test(text))) {
    console.log(
      `[v0.3] Filtered placeholder text for "${label}":`,
      JSON.stringify(text)
    );
    return '';
  }

  return text;
}

/**
 * Build safe profile context for LLM (excludes PII like email/phone)
 */
function buildLLMProfileContext(profile) {
  if (!profile) return null;

  // Convert work_setup array to string if needed
  let workSetup = profile.work_setup;
  if (Array.isArray(workSetup)) {
    workSetup = workSetup.join(', ');
  }

  // Get contact and links objects
  const contact = profile.contact || {};
  const links = profile.links || {};

  return {
    name: profile.name || null,
    headline: profile.headline || null,
    experience_years: profile.experience_years || null,
    target_roles: profile.target_roles || [],
    tech_stack: profile.tech_stack || [],
    domains: profile.domains || [],  // from flattened preferences
    work_setup: workSetup || null,  // from flattened preferences (converted to string)
    locations: profile.locations || [],
    note: profile.note || null,  // from flattened preferences
    // Include social/professional links for AI to use (not PII)
    linkedin: links.linkedin || profile.linkedin || profile.linkedinUrl || null,
    github: links.github || profile.github || profile.githubUrl || null,
    portfolio: links.portfolio || profile.portfolio || profile.portfolioUrl || null,
    website: links.website || profile.website || profile.websiteUrl || null,
  };
}

/**
 * Get style preferences from extension storage via message passing
 */
async function getStylePrefs() {
  try {
    const response = await sendExtensionMessage({
      type: "GET_STORAGE",
      payload: {
        keys: ['companionTone', 'companionLength'],
        storageType: 'sync'
      }
    });

    if (response && response.data) {
      const tone = response.data.companionTone || 'confident';
      const length = response.data.companionLength || 'medium';
      return { tone, length };
    }

    return { tone: 'confident', length: 'medium' };
  } catch (err) {
    console.warn('[v0.3] Failed to load style prefs:', err);
    return { tone: 'confident', length: 'medium' };
  }
}

/**
 * Generate suggestions from backend
 */
async function generateSuggestions(fields, jobContext, userProfile = null) {
  try {
    const profileContext = buildLLMProfileContext(userProfile);
    const stylePrefs = await getStylePrefs();

    if (profileContext) {
      const skillCount = (profileContext.tech_stack || []).length;
      const roleCount = (profileContext.target_roles || []).length;
      console.log(`[v0.3] Sending profile context to LLM: ${profileContext.name}, ${profileContext.experience_years} years, ${skillCount} skills, ${roleCount} roles`);
      console.log(`[v0.3] Profile links: LinkedIn=${profileContext.linkedin}, GitHub=${profileContext.github}, Portfolio=${profileContext.portfolio}`);
    } else {
      console.log("[v0.3] No profile context available for LLM");
    }

    if (stylePrefs) {
      console.log(`[v0.3] Using style: ${stylePrefs.tone} tone, ${stylePrefs.length} length`);
    }

    // Build request body
    const requestBody = {
      job: {
        url: jobContext.url,
        title: jobContext.title,
        company: jobContext.company,
      },
      fields: fields.map(f => ({
        field_id: f.canonical || f.selector,  // Use selector as fallback for non-canonical fields
        label: f.labelText,
        type: f.type,
      })),
    };

    // Add optional fields
    if (profileContext) {
      requestBody.profile_context = profileContext;
    }

    // Backend supports style_prefs as of v0.8.8-style-prefs
    if (stylePrefs) {
      requestBody.style_prefs = stylePrefs;
    }

    console.log('[v0.3] Sending request to API:', {
      url: '/api/extension/generate-form-answers',
      fieldCount: requestBody.fields.length,
      hasProfileContext: !!requestBody.profile_context,
      hasStylePrefs: !!requestBody.style_prefs,
      stylePrefs: requestBody.style_prefs
    });

    const response = await sendExtensionMessage({
      type: "API_PROXY",
      payload: {
        url: "/api/extension/generate-form-answers",
        method: "POST",
        body: requestBody,
      }
    });

    if (!response.ok) {
      // Log the full error response for debugging
      console.error('[v0.3] API error response:', {
        status: response.status,
        error: response.error,
        data: response.data
      });

      // Log validation details if available
      if (response.data?.detail) {
        console.error('[v0.3] Validation error details:', JSON.stringify(response.data.detail, null, 2));
      }

      // Log the full request that failed
      console.error('[v0.3] Failed request body:', JSON.stringify(requestBody, null, 2));

      if (response.status === 401 || response.status === 403) {
        throw new Error("NOT_LOGGED_IN");
      } else if (response.status >= 500) {
        throw new Error("SERVER_ERROR");
      }
      throw new Error(`HTTP_${response.status}`);
    }

    const data = response.data;
    const suggestions = {};

    // Normalize answers to filter out placeholder/debug text
    for (const ans of (data.answers || [])) {
      const normalized = normalizeAnswerText(ans.label || ans.field_id, ans.answer);
      if (normalized) {
        suggestions[ans.field_id] = normalized;
      }
    }

    return suggestions;
  } catch (err) {
    if (err.message.startsWith("HTTP_") || err.message === "NOT_LOGGED_IN" || err.message === "SERVER_ERROR") {
      throw err;
    }
    throw new Error("NETWORK_ERROR");
  }
}

/**
 * Log application to backend
 */
async function logApplication(jobContext) {
  try {
    const response = await sendExtensionMessage({
      type: "API_PROXY",
      payload: {
        url: "/api/extension/log-application",
        method: "POST",
        body: {
          url: jobContext.url,
          title: jobContext.title,
          company: jobContext.company,
          source: "extension",
          notes: "Logged from Companion v0.2",
        },
      }
    });

    if (!response.ok) {
      if (response.status === 401 || response.status === 403) {
        throw new Error("NOT_LOGGED_IN");
      }
      throw new Error(`HTTP_${response.status}`);
    }

    return response.data;
  } catch (err) {
    if (err.message === "NOT_LOGGED_IN" || err.message.startsWith("HTTP_")) {
      throw err;
    }
    throw new Error("NETWORK_ERROR");
  }
}

/**
 * Generate cover letter from backend
 */
async function generateCoverLetter(jobContext, jobDescription) {
  try {
    const response = await sendExtensionMessage({
      type: "API_PROXY",
      payload: {
        url: "/api/extension/cover-letter",
        method: "POST",
        body: {
          job_title: jobContext.title,
          company: jobContext.company,
          job_url: jobContext.url,
          job_description: jobDescription,
        },
      }
    });

    if (!response.ok) {
      if (response.status === 401 || response.status === 403) {
        throw new Error("NOT_LOGGED_IN");
      } else if (response.status >= 500) {
        throw new Error("SERVER_ERROR");
      }
      throw new Error(`HTTP_${response.status}`);
    }

    const data = response.data;
    return data.text || data.cover_letter || "";
  } catch (err) {
    if (err.message.startsWith("HTTP_") || err.message === "NOT_LOGGED_IN" || err.message === "SERVER_ERROR") {
      throw err;
    }
    throw new Error("NETWORK_ERROR");
  }
}

// ============================================================================
// Main Orchestration
// ============================================================================

/**
 * Main entry point: Scan form and show panel
 */
export async function runScanAndSuggestV2() {
  const panel = createPanel();
  const body = panel.querySelector("#al_body");
  const generateBtn = panel.querySelector("#al_generate");
  const applyBtn = panel.querySelector("#al_apply");
  const logBtn = panel.querySelector("#al_log"); // May be null in new layout

  // v0.3: Build memory key for this page
  const memoryKey = buildMemoryKey(location);
  console.log("[v0.3] Memory key:", memoryKey);

  // v0.3: Fetch style prefs once per run
  const stylePrefs = await getStylePrefs();
  console.log("[v0.3] Style prefs for this run:", stylePrefs);
  panel.__stylePrefs = stylePrefs;

  // Learning v1: Track timing and mappings for learning events
  const autofillStartTime = Date.now();
  let suggestedMap = {}; // canonical -> selector mappings from AI/memory
  let finalMap = {}; // canonical -> selector mappings after user edits

  try {
    // Step 1: Scan fields - show scanning banner
    showBanner(panel, "Scanning page…", "info");
    const fields = scanFormFields();

    if (fields.length === 0) {
      showBanner(panel, "Scan complete · No form fields detected on this page", "info");
      generateBtn.disabled = true;
      return;
    }

    // Learning v1: Compute schema hash for form structure
    const schemaHash = simpleHash(fields.map(f => f.selector).join("|"));
    panel.__schemaHash = schemaHash;

    // Step 2: Collect job context
    const jobContext = collectJobContext();
    panel.__jobContext = jobContext;

    console.log("[v0.3] Job context:", jobContext);
    console.log("[v0.3] Scanned fields:", fields);
    console.log("[Learning v1] Schema hash:", schemaHash);

    // Step 3: Load memory preferences
    const memoryPrefs = await loadPreferences(memoryKey);
    console.log("[v0.3] Loaded memory:", memoryPrefs);

    // Step 3.5: Fetch user profile for identity fields
    let userProfile = null;
    try {
      userProfile = await fetchProfile();
      console.log("[v0.3] Loaded user profile from API:", userProfile ? "yes" : "no");
      if (userProfile) {
        console.log("[v0.3] API profile links:", userProfile.links);
      }

      // Flatten preferences into profile for easier access
      if (userProfile?.preferences) {
        userProfile = { ...userProfile, ...userProfile.preferences };
      }

      // Merge local chrome.storage links (from popup settings) into API profile
      try {
        const response = await sendExtensionMessage({
          type: "GET_STORAGE",
          payload: {
            keys: ['userProfile'],
            storageType: 'sync'
          }
        });

        console.log("[v0.3] Local storage response:", response);

        const localProfile = response?.data?.userProfile;
        console.log("[v0.3] Local userProfile:", localProfile);

        if (localProfile?.links) {
          console.log("[v0.3] ✓ Merging local Professional Links into profile:", localProfile.links);
          userProfile.links = { ...userProfile.links, ...localProfile.links };
          console.log("[v0.3] ✓ Final merged links:", userProfile.links);
        } else {
          console.log("[v0.3] No local Professional Links found in storage");
        }
      } catch (storageErr) {
        console.warn("[v0.3] Could not load local Professional Links:", storageErr);
      }
    } catch (err) {
      console.warn("[v0.3] Could not fetch profile:", err.message);
    }

    // Step 3.6: Fetch learning profile from server
    const learningProfile = await fetchLearningProfile({
      host: location.hostname,
      schemaHash,
    });
    console.log("[Learning v1] Learning profile:", learningProfile);

    // Step 4: Build initial suggestions from memory, profile, and annotate fields with learning hints
    const suggestions = {};

    // Identity/profile fields that should NEVER go to LLM
    const PROFILE_CANONICAL = new Set([
      "first_name", "last_name", "email", "phone", "linkedin",
      "github", "portfolio", "website", "location", "country", "headline",
      "years_experience", "linkedin_url", "github_url", "portfolio_url"
    ]);

    // Map canonical names to profile keys and handle special cases
    const getProfileValue = (canonical, profile) => {
      if (!profile) return null;

      // Get contact and links objects (with fallbacks)
      const contact = profile.contact || {};
      const links = profile.links || {};

      // Handle name splitting
      if (canonical === 'first_name' && profile.name) {
        const parts = profile.name.trim().split(/\s+/);
        return parts[0] || null;
      }
      if (canonical === 'last_name' && profile.name) {
        const parts = profile.name.trim().split(/\s+/);
        return parts.length > 1 ? parts.slice(1).join(' ') : null;
      }

      // Handle location (convert array to string or use contact fields)
      if (canonical === 'location') {
        const locCity = contact.location_city;
        const locCountry = contact.location_country;
        const locStr =
          profile.location ||
          (locCity && locCountry ? `${locCity}, ${locCountry}` : locCity || locCountry);
        return locStr || (profile.locations && profile.locations.length > 0 ? profile.locations[0] : null);
      }

      // Handle country
      if (canonical === 'country') {
        return contact.location_country || null;
      }

      // Handle years of experience (convert number to string)
      if (canonical === 'years_experience' && typeof profile.experience_years === 'number') {
        return String(profile.experience_years);
      }

      // Direct mappings with new contact/links structure
      const directMap = {
        headline: profile.headline,
        // Contact info (prioritize nested contact object)
        email: contact.email || profile.email,
        phone: contact.phone || profile.phone,
        // Links (prioritize nested links object, extract username from URL if needed)
        linkedin: links.linkedin || profile.linkedin || profile.linkedinUrl,
        linkedin_url: links.linkedin || profile.linkedin || profile.linkedinUrl,
        github: links.github || profile.github || profile.githubUrl,
        github_url: links.github || profile.github || profile.githubUrl,
        portfolio: links.portfolio || profile.portfolio || profile.portfolioUrl,
        portfolio_url: links.portfolio || profile.portfolio || profile.portfolioUrl,
        website: links.website || profile.website || profile.websiteUrl,
      };

      let value = directMap[canonical];

      // If linkedin field and value is a full URL, check if we should extract username
      if (canonical === 'linkedin' && value && value.includes('linkedin.com/in/')) {
        // Keep full URL - some forms want the full URL, some want just username
        // The form scanner should have already determined which format is needed
        // For now, always use full URL format
        if (!value.startsWith('http')) {
          value = 'https://' + value;
        }
      }

      return value || null;
    };

    const annotatedFields = fields.map(field => {
      const hasLocalPref = !!(field.canonical && memoryPrefs[field.canonical]);
      const learnedOnSite = !!(learningProfile?.canonical_map?.[field.canonical]);
      const isProfileField = !!(field.canonical && PROFILE_CANONICAL.has(field.canonical));

      // Priority: memory > profile > nothing
      if (hasLocalPref) {
        suggestions[field.canonical] = {
          value: memoryPrefs[field.canonical],
          source: "memory",
        };
        suggestedMap[field.canonical] = field.selector;
      } else if (isProfileField && userProfile) {
        // Use profile data for identity fields
        const profileValue = getProfileValue(field.canonical, userProfile);

        if (profileValue) {
          suggestions[field.canonical] = {
            value: profileValue,
            source: "profile",
          };
          suggestedMap[field.canonical] = field.selector;
        }
      }

      // Annotate field with learning metadata
      return {
        ...field,
        _alp_learning: {
          memoryKey,
          schemaHash,
          hasLocalPref,
          learnedOnSite,
          isProfileField,
          localValuePreview: hasLocalPref ? String(memoryPrefs[field.canonical]).slice(0, 80) : null,
        },
      };
    });

    console.log("[Learning v1] Annotated fields with learning hints:", annotatedFields.filter(f => f._alp_learning?.hasLocalPref || f._alp_learning?.learnedOnSite).length, "have hints");
    console.log("[v0.3] Initial suggestions built:", Object.keys(suggestions).length, "fields have values -", suggestions);

    // Learning v1: Store suggested map on panel for later comparison
    panel.__suggestedMap = suggestedMap;
    panel.__fields = annotatedFields;
    panel.__learningProfile = learningProfile;
    panel.__suggestions = suggestions;  // Store for Apply

    // Step 5: Render fields with memory-based suggestions
    renderFields(panel, annotatedFields, suggestions, learningProfile);

    // Update banner with scan results
    const mappedCount = fields.filter(f => f.canonical).length;
    showBanner(panel, `✓ Scan complete · ${fields.length} fields · ${mappedCount} mapped`, "info");

    // Store scan summary for popup (using localStorage since we're in page context)
    try {
      localStorage.setItem(`applylens_lastScan_${location.hostname}`, JSON.stringify({
        host: location.hostname,
        totalFields: fields.length,
        mappedCount,
        timestamp: Date.now()
      }));
      console.log("[v0.2] Stored last scan summary");
    } catch (err) {
      console.warn("[v0.2] Failed to store scan summary:", err);
    }

    // Enable or disable apply button based on suggestions
    if (applyBtn) {
      if (Object.keys(suggestions).length > 0) {
        applyBtn.disabled = false;
        console.log(`[panelV2] Apply button enabled (${Object.keys(suggestions).length} suggestions available)`);
      } else {
        applyBtn.disabled = true;
        console.log("[panelV2] Apply button disabled (no suggestions yet)");
      }
    }

    // Enable log button immediately (if it exists)
    if (logBtn) {
      logBtn.disabled = false;
    }

    // Wire up Generate button
    generateBtn.addEventListener("click", async () => {
      generateBtn.disabled = true;
      generateBtn.textContent = "Generating...";

      try {
        // Canonical types we NEVER ask the LLM for – they come from profile/memory
        const NON_AI_CANONICAL = new Set([
          "first_name", "last_name", "email", "phone", "linkedin",
          "github", "portfolio", "website", "location", "years_experience"
        ]);

        // Only send real "question" fields to the LLM
        const fieldsNeedingAI = annotatedFields.filter((field) => {
          const c = field.canonical;

          // Include non-canonical fields (questions without standard mappings)
          if (!c) return true;

          // Exclude profile/identity fields
          if (NON_AI_CANONICAL.has(c)) return false;

          // Skip if we already have from profile/memory, EXCEPT for cover_letter
          if (c === "cover_letter") return true;  // Always allow regenerating
          if (suggestions[c]?.source === "profile") return false;
          if (suggestions[c]?.source === "memory") return false;

          return true;  // Include all other canonical fields
        });

        console.log(
          `[v0.3] Requesting AI for ${fieldsNeedingAI.length} fields (question/summary only)`
        );

        const aiSuggestions = await generateSuggestions(fieldsNeedingAI, jobContext, userProfile);
        console.log("[v0.3] Generated AI suggestions:", aiSuggestions);

        // Merge: memory takes precedence, AI fills gaps
        const mergedSuggestions = { ...suggestions }; // Start with memory

        for (const [fieldId, value] of Object.entries(aiSuggestions)) {
          if (!mergedSuggestions[fieldId]) {
            mergedSuggestions[fieldId] = {
              value,
              source: "ai",
            };

            // Learning v1: Track AI-sourced mappings
            // fieldId can be either canonical or selector
            const field = annotatedFields.find(f =>
              f.canonical === fieldId || f.selector === fieldId
            );
            if (field) {
              panel.__suggestedMap[fieldId] = field.selector;
            }
          }
        }

        // Re-render with merged suggestions
        panel.__suggestions = mergedSuggestions;  // Update for Apply
        renderFields(panel, annotatedFields, mergedSuggestions, learningProfile);

        showStatus(panel, "Suggestions generated! Review and edit before applying.", "success");

        // Enable apply button (now we have suggestions)
        applyBtn.disabled = false;
        console.log(`[panelV2] Apply button enabled (${Object.keys(mergedSuggestions).length} suggestions available)`);

        generateBtn.textContent = "Re-generate";
        generateBtn.disabled = false;
      } catch (err) {
        console.error("[v0.3] Generation failed:", err);

        let errorMsg = "Could not generate suggestions";
        if (err.message === "NOT_LOGGED_IN") {
          errorMsg = "Not logged in. Please visit applylens.app to sign in.";
        } else if (err.message === "NETWORK_ERROR") {
          errorMsg = "Network error. Check your connection.";
        } else if (err.message === "SERVER_ERROR") {
          errorMsg = "Server error. Please try again in a moment.";
        }

        showStatus(panel, errorMsg, "error");
        generateBtn.textContent = "Generate Suggestions";
        generateBtn.disabled = false;
      }
    });

    // Wire up Apply button
    applyBtn.addEventListener("click", async () => {
      const count = applySuggestionsToPage(panel);

      if (count > 0) {
        showStatus(panel, `Applied ${count} field${count > 1 ? 's' : ''} to the page! ✓`, "success");

        // Learning v1: Build final map and emit learning event
        const finalMap = {};
        const inputs = panel.querySelectorAll(".suggestion-input");
        let totalCharsAdded = 0;
        let totalCharsDeleted = 0;

        for (const input of inputs) {
          const selector = input.dataset.field;
          const finalValue = input.value.trim();

          if (!finalValue) continue;

          // Find the field to get its canonical type
          const field = annotatedFields.find(f => f.selector === selector);
          if (field && field.canonical) {
            // Track final mapping
            finalMap[field.canonical] = selector;

            // v0.3: Save to client-side memory
            await saveFieldPreference({
              memoryKey,
              canonicalField: field.canonical,
              value: finalValue,
              pageUrl: location.href,
            });

            // Learning v1: Compute edit distance
            const originalValue = suggestions[field.canonical]?.value || "";
            const editDist = editDistance(originalValue, finalValue);
            totalCharsAdded += Math.max(0, finalValue.length - originalValue.length);
            totalCharsDeleted += Math.max(0, originalValue.length - finalValue.length);
          }
        }

        // Learning v1: Queue learning event for server sync
        const autofillDuration = Date.now() - autofillStartTime;

        queueLearningEvent({
          host: location.hostname,
          schemaHash,
          suggestedMap: panel.__suggestedMap || {},
          finalMap,
          genStyleId: null, // v0.3 doesn't use style variants yet
          editStats: {
            totalCharsAdded,
            totalCharsDeleted,
            perField: {}, // Could add per-field breakdown in future
          },
          durationMs: autofillDuration,
          validationErrors: {},
          status: "ok",
          policy: "exploit", // v0.3 always uses memory/AI exploit, no exploration
        });

        // Learning v1: Flush events to backend
        await flushLearningEvents();

        console.log("[v0.3] Saved applied values to memory");
        console.log("[Learning v1] Queued learning event (schema:", schemaHash, ")");
      } else {
        showStatus(panel, "No suggestions to apply. Generate suggestions first.", "warning");
      }
    });

    // v0.3: Wire up Cover Letter button
    const coverLetterBtn = panel.querySelector("#al_cover_letter");
    coverLetterBtn?.addEventListener("click", async () => {
      coverLetterBtn.disabled = true;
      coverLetterBtn.textContent = "Generating...";

      try {
        // Extract job description from page
        const jobDesc = collectJobDescription();

        if (!jobDesc || jobDesc.trim().length < 50) {
          showStatus(panel, "Could not extract job description from this page", "warning");
          coverLetterBtn.disabled = false;
          coverLetterBtn.textContent = "📝 Cover Letter";
          return;
        }

        console.log("[v0.3] Extracted job description:", jobDesc.substring(0, 200) + "...");

        // Call API to generate cover letter
        const coverLetterText = await generateCoverLetter(jobContext, jobDesc);

        // Find cover letter field on page
        const coverLetterField = annotatedFields.find(f => f.canonical === "cover_letter");

        // Show cover letter in panel (expand section or modal)
        showCoverLetterModal(panel, coverLetterText, coverLetterField);

        showStatus(panel, "Cover letter generated! Review and apply below.", "success");
        coverLetterBtn.textContent = "📝 Regenerate";
      } catch (err) {
        console.error("[v0.3] Cover letter generation failed:", err);

        let errorMsg = "Could not generate cover letter";
        if (err.message === "NOT_LOGGED_IN") {
          errorMsg = "Not logged in. Visit applylens.app to sign in.";
        } else if (err.message && err.message.includes("network")) {
          errorMsg = "Network error. Check your connection.";
        }

        showStatus(panel, errorMsg, "error");
      } finally {
        coverLetterBtn.disabled = false;
        if (coverLetterBtn.textContent === "Generating...") {
          coverLetterBtn.textContent = "📝 Cover Letter";
        }
      }
    });

    // Wire up Log button (if it exists in layout)
    if (logBtn) {
      logBtn.addEventListener("click", async () => {
        logBtn.disabled = true;
        logBtn.textContent = "Logging...";

        try {
          await logApplication(jobContext);
          showStatus(panel, "Application logged to ApplyLens Tracker ✓", "success");
          logBtn.textContent = "Logged ✓";
        } catch (err) {
          console.error("[v0.2] Log failed:", err);

          let errorMsg = "Could not log application";
          if (err.message === "NOT_LOGGED_IN") {
            errorMsg = "Not logged in. Visit applylens.app to sign in.";
          } else if (err.message === "NETWORK_ERROR") {
            errorMsg = "Network error. Check your connection.";
          }

          showStatus(panel, errorMsg, "error");
          logBtn.textContent = "Log Application";
          logBtn.disabled = false;
        }
      });
    }

  } catch (err) {
    console.error("[v0.2] Fatal error:", err);
    body.innerHTML = `<div class="status-message status-error">Fatal error: ${err.message}</div>`;
  }
}

// Listen for messages from extension via window.postMessage bridge
// (content-loader.js forwards chrome.runtime messages to us)
window.addEventListener('message', (event) => {
  // Only accept messages from same window
  if (event.source !== window) return;

  const { type, message } = event.data;

  if (type === 'APPLYLENS_EXTENSION_MESSAGE') {
    const msg = message;

    if (msg?.type === "SCAN_AND_SUGGEST_V2") {
      console.log("[Companion v0.2] Received SCAN_AND_SUGGEST_V2 in content script on", location.href);
      // Fire and forget - don't wait for completion since panel is shown on page
      runScanAndSuggestV2().catch(err => console.error("[Companion v0.2] Error in runScanAndSuggestV2:", err));
    }

    if (msg?.type === "COMPANION_GET_STATE") {
      console.log("[Companion v0.2] Received COMPANION_GET_STATE request");
      // TODO: Send current state back via postMessage
    }

    if (msg?.type === "COMPANION_APPLY_MAPPINGS") {
      console.log("[Companion v0.2] Received COMPANION_APPLY_MAPPINGS request");
      // TODO: Apply field mappings
    }
  }
});
