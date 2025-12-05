// fieldScanner.js — Robust field detection for v0.2 Job Form Mode

import { inferCanonicalField } from "./schema.js";
import { applyATSPreset, detectATS } from "./atsPresets.js";

/**
 * Generate a unique CSS selector for an element
 * @param {HTMLElement} el
 * @returns {string|null}
 */
function uniqueSelector(el) {
  if (!el || !el.tagName) return null;

  // Prefer ID if available
  if (el.id) {
    return `#${CSS.escape(el.id)}`;
  }

  // Use name attribute if available
  const name = el.getAttribute?.("name");
  if (name) {
    return `${el.tagName.toLowerCase()}[name="${CSS.escape(name)}"]`;
  }

  // Fallback to path with nth-of-type
  const parts = [];
  let n = el;
  while (n && n.nodeType === 1 && parts.length < 5) {
    let seg = n.tagName.toLowerCase();
    if (n.id) {
      seg += `#${CSS.escape(n.id)}`;
      parts.unshift(seg);
      break;
    }
    const sibs = Array.from(n.parentElement?.children || []).filter(e => e.tagName === n.tagName);
    if (sibs.length > 1) {
      seg += `:nth-of-type(${sibs.indexOf(n) + 1})`;
    }
    parts.unshift(seg);
    n = n.parentElement;
  }
  return parts.join(" > ");
}

/**
 * Find the label text for an input element
 * Tries multiple strategies: <label for>, parent <label>, nearby text
 * @param {HTMLElement} el
 * @returns {string}
 */
function findLabelText(el) {
  // Strategy 1: <label for="id">
  const id = el.getAttribute("id");
  if (id) {
    const label = document.querySelector(`label[for="${CSS.escape(id)}"]`);
    if (label) return label.textContent.trim();
  }

  // Strategy 2: Parent <label>
  const parentLabel = el.closest("label");
  if (parentLabel) {
    // Remove the input's own value from the label text
    const clone = parentLabel.cloneNode(true);
    const inputs = clone.querySelectorAll("input, textarea, select");
    inputs.forEach(inp => inp.remove());
    return clone.textContent.trim();
  }

  // Strategy 3: Previous sibling label or span
  let prev = el.previousElementSibling;
  while (prev) {
    if (prev.tagName === "LABEL" || prev.tagName === "SPAN" || prev.tagName === "DIV") {
      const text = prev.textContent.trim();
      if (text && text.length < 200) return text; // Reasonable length
    }
    prev = prev.previousElementSibling;
  }

  // Strategy 4: Parent's previous sibling (for some ATS layouts)
  const parent = el.parentElement;
  if (parent) {
    let parentPrev = parent.previousElementSibling;
    if (parentPrev && (parentPrev.tagName === "LABEL" || parentPrev.tagName === "DIV")) {
      const text = parentPrev.textContent.trim();
      if (text && text.length < 200) return text;
    }
  }

  // Strategy 5: Look for aria-label or aria-labelledby
  const ariaLabel = el.getAttribute("aria-label");
  if (ariaLabel) return ariaLabel.trim();

  const ariaLabelledBy = el.getAttribute("aria-labelledby");
  if (ariaLabelledBy) {
    const labelEl = document.getElementById(ariaLabelledBy);
    if (labelEl) return labelEl.textContent.trim();
  }

  return "";
}

/**
 * Detect if a field is required based on multiple signals
 * @param {HTMLElement} inputEl
 * @param {string} labelText
 * @returns {boolean}
 */
function detectRequired(inputEl, labelText = "") {
  const text = (labelText || "").toLowerCase();

  return Boolean(
    inputEl.required ||
    inputEl.getAttribute("aria-required") === "true" ||
    text.includes("(required") ||
    text.includes("required:") ||
    /[*]\s*$/.test(labelText || "")   // label ends with *
  );
}

/**
 * Determine if an element is visible and interactable
 * @param {HTMLElement} el
 * @returns {boolean}
 */
function isVisible(el) {
  if (!el) return false;

  // Check display/visibility
  const style = window.getComputedStyle(el);
  if (style.display === "none" || style.visibility === "hidden") return false;

  // Check opacity
  if (parseFloat(style.opacity) === 0) return false;

  // Check if element has dimensions
  const rect = el.getBoundingClientRect();
  if (rect.width === 0 && rect.height === 0) return false;

  return true;
}

/**
 * Get the input type category
 * @param {HTMLElement} el
 * @returns {"text"|"textarea"|"select"|"checkbox"|"radio"|"email"|"tel"|"url"|"file"|"number"}
 */
function getInputType(el) {
  const tagName = el.tagName.toLowerCase();

  if (tagName === "textarea") return "textarea";
  if (tagName === "select") return "select";

  if (tagName === "input") {
    const type = (el.getAttribute("type") || "text").toLowerCase();

    // Map HTML5 input types to our canonical types
    if (type === "email") return "email";
    if (type === "tel") return "tel";
    if (type === "url") return "url";
    if (type === "file") return "file";
    if (type === "number") return "number";
    if (type === "checkbox") return "checkbox";
    if (type === "radio") return "radio";

    // Everything else is treated as text
    return "text";
  }

  return "text";
}

/**
 * Scan page for form fields and infer canonical field types
 * @returns {import('./schema.js').FieldInfo[]}
 */
export function scanFormFields() {
  const fields = [];

  // Find all potential form inputs
  const selectors = [
    "input[type='text']",
    "input[type='email']",
    "input[type='tel']",
    "input[type='url']",
    "input[type='number']",
    "input:not([type])", // Inputs without type attribute default to text
    "textarea",
    "select",
    // Don't include checkbox/radio/file for now - they need special handling
  ];

  const candidates = document.querySelectorAll(selectors.join(", "));

  for (const el of candidates) {
    // Skip invisible elements
    if (!isVisible(el)) continue;

    // Skip disabled or readonly fields
    if (el.disabled || el.readOnly) continue;

    // Get element attributes
    const idAttr = el.getAttribute("id") || "";
    const nameAttr = el.getAttribute("name") || "";
    const placeholder = el.getAttribute("placeholder") || "";
    const value = el.value || "";

    // Get selector
    const selector = uniqueSelector(el);
    if (!selector) continue; // Skip if we can't generate a selector

    // Get label
    const labelText = findLabelText(el);

    // Get type
    const type = getInputType(el);

    // Infer canonical field
    const canonical = inferCanonicalField(labelText, nameAttr, idAttr, placeholder, type);

    // Detect if required
    const required = detectRequired(el, labelText);

    fields.push({
      canonical,
      labelText,
      nameAttr,
      idAttr,
      type,
      selector,
      value,
      placeholder,
      required,
    });
  }

  // Apply ATS-specific patches
  const hostname = location.hostname;
  const patchedFields = applyATSPreset(fields, hostname);

  console.log(`[Scanner] Found ${patchedFields.length} fields on ${hostname}`);
  console.log(`[Scanner] Canonical mappings:`, patchedFields.filter(f => f.canonical).map(f => ({
    label: f.labelText.slice(0, 30),
    canonical: f.canonical
  })));

  return patchedFields;
}

/**
 * Collect job context from page metadata
 * @returns {{url: string, title: string, company: string}}
 */
export function collectJobContext() {
  const url = window.location.href;

  // Try to get job title from various sources
  let title = "";

  // 1. Open Graph meta tag
  const ogTitle = document.querySelector('meta[property="og:title"]');
  if (ogTitle) {
    title = ogTitle.getAttribute("content") || "";
  }

  // 2. Page title
  if (!title) {
    title = document.title;
  }

  // 3. H1 fallback
  if (!title) {
    const h1 = document.querySelector("h1");
    if (h1) title = h1.textContent.trim();
  }

  // Clean up title (remove " - Company Name" suffix, etc.)
  title = title.replace(/\s*[-|–]\s*.+$/, "").trim();

  // Try to get company name
  let company = "";

  // 1. Open Graph site name
  const ogSiteName = document.querySelector('meta[property="og:site_name"]');
  if (ogSiteName) {
    company = ogSiteName.getAttribute("content") || "";
  }

  // 2. ATS-specific selectors
  const hostname = location.hostname;
  if (!company) {
    if (hostname.includes("lever.co")) {
      const leverCompany = document.querySelector(".main-header-text a, .company-name");
      if (leverCompany) company = leverCompany.textContent.trim();
    } else if (hostname.includes("greenhouse.io")) {
      const ghCompany = document.querySelector("#header .company-name, [data-test='company-name']");
      if (ghCompany) company = ghCompany.textContent.trim();
    } else if (hostname.includes("ashbyhq.com")) {
      const ashbyCompany = document.querySelector("[class*='company'], [class*='CompanyName']");
      if (ashbyCompany) company = ashbyCompany.textContent.trim();
    }
  }

  // 3. Extract from URL (last resort)
  if (!company && hostname.includes("myworkdayjobs.com")) {
    // Workday URLs like https://company.wd1.myworkdayjobs.com/...
    const match = hostname.match(/^([^.]+)\./);
    if (match) company = match[1];
  }

  return { url, title, company };
}
