// learning/utils.js — Learning utilities

/**
 * Simple hash function for form schema fingerprinting
 * @param {string} str - String to hash
 * @returns {string} Hex hash
 */
export function simpleHash(str) {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    const chr = str.charCodeAt(i);
    hash = ((hash << 5) - hash) + chr;
    hash |= 0; // Convert to 32bit integer
  }
  return Math.abs(hash).toString(16);
}

/**
 * Generate schema hash from form fields
 * @param {Array} fields - Array of field objects with selector and type
 * @returns {string} Schema hash
 */
export function computeSchemaHash(fields) {
  const signature = fields
    .map(f => `${f.selector}:${f.type}`)
    .sort()
    .join("|");
  return simpleHash(signature);
}

/**
 * Calculate edit distance (Levenshtein distance) between two strings
 * @param {string} str1 - First string
 * @param {string} str2 - Second string
 * @returns {number} Edit distance
 */
export function editDistance(str1, str2) {
  const len1 = str1.length;
  const len2 = str2.length;
  const dp = Array(len1 + 1).fill(null).map(() => Array(len2 + 1).fill(0));

  for (let i = 0; i <= len1; i++) dp[i][0] = i;
  for (let j = 0; j <= len2; j++) dp[0][j] = j;

  for (let i = 1; i <= len1; i++) {
    for (let j = 1; j <= len2; j++) {
      if (str1[i - 1] === str2[j - 1]) {
        dp[i][j] = dp[i - 1][j - 1];
      } else {
        dp[i][j] = 1 + Math.min(
          dp[i - 1][j],     // deletion
          dp[i][j - 1],     // insertion
          dp[i - 1][j - 1]  // substitution
        );
      }
    }
  }

  return dp[len1][len2];
}
