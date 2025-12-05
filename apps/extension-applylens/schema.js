// schema.js — Canonical field types and schema for v0.2 Job Form Mode
// Single source of truth for field detection and mapping

/**
 * @typedef {"full_name"|"first_name"|"last_name"|"email"|"phone"|"location"|"linkedin"|"github"|"portfolio"|"website"|"headline"|"summary"|"cover_letter"|"salary_expectation"|"visa_status"|"relocation"|"remote_preference"|"years_experience"|"work_authorization"|"notice_period"|"pronouns"|"diversity_gender"|"diversity_race"|"diversity_veteran"|"diversity_disability"|"referral_source"|"how_hear"} CanonicalField
 */

/**
 * @typedef {Object} FieldInfo
 * @property {CanonicalField|null} canonical - Best guess at canonical field type
 * @property {string} labelText - Human-readable label from page
 * @property {string} nameAttr - Element name attribute
 * @property {string} idAttr - Element id attribute
 * @property {"text"|"textarea"|"select"|"checkbox"|"radio"|"email"|"tel"|"url"|"file"|"number"} type - Input type
 * @property {string} selector - CSS selector to re-find the element
 * @property {string} value - Current value in the field
 * @property {string} placeholder - Placeholder text if any
 */

/**
 * Infer canonical field from various text sources (label, name, id, placeholder)
 * @param {string} labelText
 * @param {string} nameAttr
 * @param {string} idAttr
 * @param {string} placeholder
 * @param {string} inputType
 * @returns {CanonicalField|null}
 */
export function inferCanonicalField(labelText, nameAttr, idAttr, placeholder, inputType) {
  const combined = `${labelText} ${nameAttr} ${idAttr} ${placeholder}`.toLowerCase();

  // Email (high confidence)
  if (inputType === "email" || /\b(email|e-mail|email.?address)\b/.test(combined)) {
    return "email";
  }

  // Phone (high confidence)
  if (inputType === "tel" || /\b(phone|telephone|mobile|cell)\b/.test(combined)) {
    return "phone";
  }

  // URL fields - check specific types before generic website
  // LinkedIn (specific) - must come before generic website
  if (/\b(linkedin|linked-in)\b/.test(combined)) {
    return "linkedin";
  }

  // GitHub (specific) - must come before generic website
  if (/\bgithub\b/.test(combined)) {
    return "github";
  }

  // Portfolio (specific) - must come before generic website
  if (/\b(portfolio|personal.?site)\b/.test(combined)) {
    return "portfolio";
  }

  // Generic URL/website (comes after specific URL types)
  if (inputType === "url" || /\b(website|url|homepage)\b/.test(combined)) {
    return "website";
  }

  // Name fields (order matters - check full_name before first/last)
  if (/\b(full.?name|your.?name|applicant.?name|legal.?name)\b/.test(combined)) {
    return "full_name";
  }
  if (/\b(first.?name|given.?name|fname)\b/.test(combined)) {
    return "first_name";
  }
  if (/\b(last.?name|family.?name|surname|lname)\b/.test(combined)) {
    return "last_name";
  }

  // Location
  if (/\b(location|city|address|current.?location|where.*located)\b/.test(combined)) {
    return "location";
  }

  // Cover letter / motivation
  if (/\b(cover.?letter|motivation|why.*(join|apply|interested)|tell.*us.*about)\b/.test(combined)) {
    return "cover_letter";
  }

  // Summary / headline
  if (/\b(headline|tagline|professional.?summary)\b/.test(combined)) {
    return "headline";
  }
  if (/\b(summary|bio|about.*(you|yourself)|profile)\b/.test(combined)) {
    return "summary";
  }

  // Salary
  if (/\b(salary|compensation|expected.?salary|salary.?expectation)\b/.test(combined)) {
    return "salary_expectation";
  }

  // Work authorization / visa
  if (/\b(visa|work.?authorization|sponsorship|authorized.*work|require.*sponsorship)\b/.test(combined)) {
    return "visa_status";
  }

  // Years of experience
  if (/\b(years?.*(of.?)?experience|experience.?level)\b/.test(combined)) {
    return "years_experience";
  }

  // Notice period / availability
  if (/\b(notice.?period|availability|start.?date|when.*available)\b/.test(combined)) {
    return "notice_period";
  }

  // Remote preference / relocation
  if (/\b(relocate|relocation)\b/.test(combined)) {
    return "relocation";
  }
  if (/\b(remote|work.*from.*home|location.?preference|willing.*relocate)\b/.test(combined)) {
    return "remote_preference";
  }

  // Diversity fields (optional, many companies ask)
  if (/\b(pronouns?|preferred.?pronouns?)\b/.test(combined)) {
    return "pronouns";
  }
  if (/\b(gender|gender.?identity)\b/.test(combined)) {
    return "diversity_gender";
  }
  if (/\b(race|ethnicity|racial)\b/.test(combined)) {
    return "diversity_race";
  }
  if (/\bveteran\b/.test(combined)) {
    return "diversity_veteran";
  }
  if (/\bdisability\b/.test(combined)) {
    return "diversity_disability";
  }

  // Referral / how did you hear
  if (/\b(referral|referred.*by|reference)\b/.test(combined)) {
    return "referral_source";
  }
  if (/\b(how.*(did.*you.?)?(hear|find|learn)|where.*did.*you.*hear|where.*did.*you.*find)\b/.test(combined)) {
    return "how_hear";
  }

  return null; // Unknown field
}

/**
 * Check if a field is likely a "profile" field (safe to autofill from profile)
 * vs. job-specific (needs generation) or sensitive (diversity, etc.)
 * @param {CanonicalField|null} canonical
 * @returns {boolean}
 */
export function isProfileField(canonical) {
  if (!canonical) return false;
  const profileFields = [
    "full_name", "first_name", "last_name", "email", "phone",
    "location", "linkedin", "github", "portfolio", "website",
    "headline", "summary"
  ];
  return profileFields.includes(canonical);
}

/**
 * Check if a field is sensitive (diversity, etc.) - should not autofill by default
 * @param {CanonicalField|null} canonical
 * @returns {boolean}
 */
export function isSensitiveField(canonical) {
  if (!canonical) return false;
  const sensitiveFields = [
    "diversity_gender", "diversity_race", "diversity_veteran",
    "diversity_disability", "pronouns", "salary_expectation"
  ];
  return sensitiveFields.includes(canonical);
}
