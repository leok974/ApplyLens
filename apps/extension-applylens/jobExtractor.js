// jobExtractor.js — Extract job description from ATS pages

/**
 * Extract job description text from the current page
 * Tries multiple strategies to find the main job description content
 * @returns {string} Job description text (up to 4000 chars)
 */
export function collectJobDescription() {
  // Strategy 1: Try Open Graph description
  const ogDesc = document.querySelector('meta[property="og:description"]');
  if (ogDesc) {
    const content = ogDesc.getAttribute("content");
    if (content && content.length > 100) {
      console.log("[JobExtractor] Using og:description");
      return truncate(content, 4000);
    }
  }

  // Strategy 2: Look for common job description containers
  const commonSelectors = [
    // Generic
    ".job-description",
    "#job-description",
    ".description",
    "#description",
    ".job-details",
    "#job-details",
    ".jd-contents",

    // Lever
    ".section-wrapper .section",
    ".posting-description",

    // Greenhouse
    "#content .application",
    ".body-text",

    // Workday
    ".job-description-card",
    "[data-automation-id='jobPostingDescription']",

    // Ashby
    ".job-description-content",
    "[class*='JobDescription']",

    // SmartRecruiters
    ".job-description-content",
    ".st-text-block",
  ];

  for (const selector of commonSelectors) {
    const el = document.querySelector(selector);
    if (el) {
      const text = extractTextFromElement(el);
      if (text.length > 200) {
        console.log(`[JobExtractor] Using selector: ${selector}`);
        return truncate(text, 4000);
      }
    }
  }

  // Strategy 3: Find largest content block
  // Look for sections/divs with substantial text content
  const candidates = document.querySelectorAll("section, div.content, div.main, article, main");
  let bestCandidate = null;
  let maxLength = 0;

  for (const el of candidates) {
    // Skip if too high in the DOM (likely header/nav)
    if (el.matches("header, nav, footer, aside")) continue;

    const text = extractTextFromElement(el);

    // Must have reasonable length
    if (text.length > maxLength && text.length > 200) {
      maxLength = text.length;
      bestCandidate = el;
    }
  }

  if (bestCandidate) {
    const text = extractTextFromElement(bestCandidate);
    console.log(`[JobExtractor] Using largest content block (${text.length} chars)`);
    return truncate(text, 4000);
  }

  // Strategy 4: Fallback to body text (last resort)
  console.log("[JobExtractor] Fallback to body text");
  const bodyText = document.body.textContent || "";
  return truncate(bodyText.trim(), 4000);
}

/**
 * Extract clean text from an element
 * Removes script/style tags, normalizes whitespace
 * @param {HTMLElement} el
 * @returns {string}
 */
function extractTextFromElement(el) {
  if (!el) return "";

  // Clone to avoid modifying the DOM
  const clone = el.cloneNode(true);

  // Remove script, style, and other unwanted elements
  const unwanted = clone.querySelectorAll("script, style, nav, header, footer, aside, button, input, select, textarea");
  unwanted.forEach(node => node.remove());

  // Get text content
  let text = clone.textContent || "";

  // Normalize whitespace
  text = text
    .replace(/\s+/g, " ") // Multiple spaces/newlines -> single space
    .trim();

  return text;
}

/**
 * Truncate text to max length, trying to break at sentence boundaries
 * @param {string} text
 * @param {number} maxLength
 * @returns {string}
 */
function truncate(text, maxLength) {
  if (text.length <= maxLength) return text;

  // Try to break at sentence boundary
  const truncated = text.slice(0, maxLength);
  const lastPeriod = truncated.lastIndexOf(". ");
  const lastNewline = truncated.lastIndexOf("\n");

  const breakPoint = Math.max(lastPeriod, lastNewline);

  if (breakPoint > maxLength * 0.8) {
    // Good break point found (at least 80% of max length)
    return truncated.slice(0, breakPoint + 1).trim();
  }

  // Just hard truncate
  return truncated.trim() + "...";
}

/**
 * Extract job requirements/qualifications specifically
 * @returns {string}
 */
export function extractRequirements() {
  const selectors = [
    ".requirements",
    "#requirements",
    ".qualifications",
    "#qualifications",
    "[class*='requirement']",
    "[class*='qualification']",
  ];

  for (const selector of selectors) {
    const el = document.querySelector(selector);
    if (el) {
      const text = extractTextFromElement(el);
      if (text.length > 50) {
        return truncate(text, 2000);
      }
    }
  }

  return "";
}

/**
 * Extract benefits/perks section
 * @returns {string}
 */
export function extractBenefits() {
  const selectors = [
    ".benefits",
    "#benefits",
    ".perks",
    "#perks",
    "[class*='benefit']",
    "[class*='perk']",
  ];

  for (const selector of selectors) {
    const el = document.querySelector(selector);
    if (el) {
      const text = extractTextFromElement(el);
      if (text.length > 50) {
        return truncate(text, 1000);
      }
    }
  }

  return "";
}
