// atsPresets.js — ATS-specific field detection helpers
// Tweaks for Lever, Greenhouse, Workday, Ashby, etc.

import { inferCanonicalField } from "./schema.js";

/**
 * Apply Lever-specific field detection improvements
 * @param {import('./schema.js').FieldInfo[]} fields
 * @returns {import('./schema.js').FieldInfo[]}
 */
function patchLeverFields(fields) {
  // Lever uses consistent naming patterns
  // e.g., name="cards[***][field0]" with labels in divs
  return fields.map(field => {
    const { nameAttr, labelText, canonical } = field;

    // Lever cover letter is often in a section called "Additional Information"
    if (!canonical && /additional.?information|comments/.test(labelText.toLowerCase())) {
      return { ...field, canonical: "cover_letter" };
    }

    // Lever often has "Full name" as first field
    if (!canonical && nameAttr?.includes("field0") && /name/.test(labelText.toLowerCase())) {
      return { ...field, canonical: "full_name" };
    }

    return field;
  });
}

/**
 * Apply Greenhouse-specific field detection improvements
 * @param {import('./schema.js').FieldInfo[]} fields
 * @returns {import('./schema.js').FieldInfo[]}
 */
function patchGreenhouseFields(fields) {
  // Greenhouse uses IDs like "first_name", "last_name", "email", "phone"
  // BUT: Phone is a split widget (country dropdown + tel input)

  let phoneFieldFound = false;

  // First, ensure the phone input is correctly mapped
  fields = fields.map(field => {
    const { idAttr, nameAttr, labelText, canonical, selector, type } = field;

    // Cover Letter handling
    if (!canonical && (idAttr === "cover_letter" || nameAttr === "cover_letter")) {
      return { ...field, canonical: "cover_letter" };
    }

    // Resume upload field (file input) - mark as special
    if (type === "file" && /resume|cv/.test(labelText.toLowerCase())) {
      return { ...field, canonical: null }; // Don't autofill file inputs
    }

    // Phone input: Ensure we're targeting the actual tel input, not wrapper
    if (type === "tel" || idAttr === "phone" || nameAttr === "phone") {
      phoneFieldFound = true;
      console.log('[ATS] Greenhouse phone field detected:', { selector, type, idAttr, nameAttr, canonical });
      // If the scanner picked up a phone field, ensure it's canonical
      if (!canonical || canonical !== "phone") {
        return { ...field, canonical: "phone" };
      }
    }

    // Country code dropdown (part of phone widget)
    if (type === "select" && (idAttr === "country" || nameAttr?.includes("country") || labelText.toLowerCase().includes("country"))) {
      // Only map to 'country' if it's NOT the dial code dropdown
      // Greenhouse phone widgets have a separate country dropdown for dial codes
      // We want location_country for actual country of residence
      const isDialCodeDropdown = selector?.includes("phone") || labelText.toLowerCase().includes("code");
      if (!isDialCodeDropdown && !canonical) {
        return { ...field, canonical: "country" };
      }
    }

    return field;
  });

  if (phoneFieldFound) {
    console.log('[ATS] Greenhouse phone field mapping complete');
  }

  return fields;
}

/**
 * Apply Workday-specific field detection improvements
 * @param {import('./schema.js').FieldInfo[]} fields
 * @returns {import('./schema.js').FieldInfo[]}
 */
function patchWorkdayFields(fields) {
  // Workday is notorious for cryptic IDs like "input-1", "input-2"
  // Must rely heavily on label text and nearby context
  return fields.map(field => {
    const { labelText, canonical, nameAttr, idAttr } = field;

    // Workday often nests labels weirdly - try harder to find canonical match
    if (!canonical) {
      // Re-run inference with just label text (might be cleaner than combined)
      const cleanLabel = labelText.trim().toLowerCase();

      // Common Workday patterns
      if (cleanLabel.includes("legal name") || cleanLabel === "name") {
        return { ...field, canonical: "full_name" };
      }
      if (cleanLabel.includes("email address")) {
        return { ...field, canonical: "email" };
      }
      if (cleanLabel.includes("phone number") || cleanLabel.includes("mobile number")) {
        return { ...field, canonical: "phone" };
      }
      if (cleanLabel.includes("city") || cleanLabel.includes("current location")) {
        return { ...field, canonical: "location" };
      }
      if (cleanLabel.includes("linkedin") && cleanLabel.includes("profile")) {
        return { ...field, canonical: "linkedin" };
      }
    }

    // Workday has multi-part forms - sometimes "Address" fields appear
    // Mark them clearly so we can decide to skip or fill
    if (/\b(street|address.?line|apartment|apt|zip|postal.?code|state|province)\b/.test(labelText.toLowerCase())) {
      return { ...field, canonical: null }; // Skip complex address fields for now
    }

    return field;
  });
}

/**
 * Apply Ashby-specific field detection improvements
 * @param {import('./schema.js').FieldInfo[]} fields
 * @returns {import('./schema.js').FieldInfo[]}
 */
function patchAshbyFields(fields) {
  // Ashby is relatively modern - uses clean HTML
  // Similar to Greenhouse in structure
  return fields.map(field => {
    const { labelText, canonical } = field;

    // Ashby often has "Tell us about yourself" or "Why [Company]?" questions
    if (!canonical && /why.?(are.?you|do.?you|this.?role|our.?company)/.test(labelText.toLowerCase())) {
      return { ...field, canonical: "cover_letter" };
    }

    return field;
  });
}

/**
 * Apply SmartRecruiters-specific field detection improvements
 * @param {import('./schema.js').FieldInfo[]} fields
 * @returns {import('./schema.js').FieldInfo[]}
 */
function patchSmartRecruitersFields(fields) {
  // SmartRecruiters uses data-test-id attributes heavily
  return fields.map(field => {
    const { labelText, canonical, nameAttr } = field;

    // SmartRecruiters has specific field patterns
    if (!canonical && nameAttr?.includes("firstName")) {
      return { ...field, canonical: "first_name" };
    }
    if (!canonical && nameAttr?.includes("lastName")) {
      return { ...field, canonical: "last_name" };
    }

    return field;
  });
}

/**
 * ATS preset registry - maps hostname patterns to patch functions
 */
export const ATS_PRESETS = {
  "jobs.lever.co": patchLeverFields,
  "boards.greenhouse.io": patchGreenhouseFields,
  "greenhouse.io": patchGreenhouseFields, // Some companies use custom domains
  "myworkdayjobs.com": patchWorkdayFields,
  "wd1.myworkdayjobs.com": patchWorkdayFields,
  "wd5.myworkdayjobs.com": patchWorkdayFields,
  "jobs.ashbyhq.com": patchAshbyFields,
  "ashbyhq.com": patchAshbyFields,
  "jobs.smartrecruiters.com": patchSmartRecruitersFields,
  "smartrecruiters.com": patchSmartRecruitersFields,
};

/**
 * Detect ATS platform from hostname
 * @param {string} hostname
 * @returns {string|null} ATS name or null if unknown
 */
export function detectATS(hostname) {
  if (hostname.includes("lever.co")) return "Lever";
  if (hostname.includes("greenhouse.io")) return "Greenhouse";
  if (hostname.includes("myworkdayjobs.com")) return "Workday";
  if (hostname.includes("ashbyhq.com")) return "Ashby";
  if (hostname.includes("smartrecruiters.com")) return "SmartRecruiters";
  return null;
}

/**
 * Apply ATS-specific patches to fields based on current hostname
 * @param {import('./schema.js').FieldInfo[]} fields
 * @param {string} hostname
 * @returns {import('./schema.js').FieldInfo[]}
 */
export function applyATSPreset(fields, hostname) {
  // Try exact match first
  if (ATS_PRESETS[hostname]) {
    console.log(`[ATS] Applying preset for: ${hostname}`);
    return ATS_PRESETS[hostname](fields);
  }

  // Try partial match (for custom domains hosting Greenhouse, etc.)
  for (const [pattern, patchFn] of Object.entries(ATS_PRESETS)) {
    if (hostname.includes(pattern) || pattern.includes(hostname)) {
      console.log(`[ATS] Applying preset for: ${pattern} (matched ${hostname})`);
      return patchFn(fields);
    }
  }

  console.log(`[ATS] No preset for ${hostname} - using generic detection`);
  return fields;
}
