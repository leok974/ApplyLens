/* memoryV3Clean.js v0.3 - Client-side field memory with per-site defaults.
 * Regex-free implementation using character code checking instead of pattern matching. */

console.log(">>> MEMORYV3CLEAN.JS LOADING AT: " + new Date().toISOString() + " <<<");
console.log(">>> THIS FILE HAS ZERO REGEX PATTERNS - IT IS 100% REGEX-FREE <<<");
console.log(">>> FILE SIZE: " + document.currentScript?.src?.length + " chars <<<");

console.log("[ApplyLens] memoryV3Clean.js LOADED - regex-free, pure ASCII version");

const DB_NAME = "applylens-companion-v3";
const STORE_NAME = "field-preferences";
const DB_VERSION = 1;

/**
 * Open IndexedDB for field preferences
 */
function openDb() {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, DB_VERSION);
    req.onerror = () => reject(req.error);
    req.onsuccess = () => resolve(req.result);
    req.onupgradeneeded = (e) => {
      const db = e.target.result;
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        const store = db.createObjectStore(STORE_NAME, { keyPath: "id" });
        store.createIndex("memoryKey", "memoryKey", { unique: false });
      }
    };
  });
}

/**
 * Helpers for pathname normalization - implemented WITHOUT regex
 */

function isDigitsOnly(str) {
  if (!str) return false;
  for (let i = 0; i < str.length; i++) {
    const c = str.charCodeAt(i);
    if (c < 48 || c > 57) return false; /* digit check 0 to 9 */
  }
  return true;
}

function isAlnumDash(str) {
  if (!str) return false;
  for (let i = 0; i < str.length; i++) {
    const c = str.charCodeAt(i);
    const isDigit = c >= 48 && c <= 57;
    const isUpper = c >= 65 && c <= 90;
    const isLower = c >= 97 && c <= 122;
    const isDashOrUnderscore = str[i] === "-" || str[i] === "_";
    if (!(isDigit || isUpper || isLower || isDashOrUnderscore)) {
      return false;
    }
  }
  return true;
}

/**
 * Normalize pathname by replacing numeric or UUID-ish segments with asterisk.
 * Examples: jobs with IDs become jobs with asterisk, positions with IDs become positions with asterisk.
 */
function normalizePathname(pathname) {
  const raw = (pathname || "/").split("/");
  const segments = [];

  for (const seg of raw) {
    if (!seg) continue; /* skip empty segments */
    if (isDigitsOnly(seg)) {
      segments.push("*");
    } else if (seg.length >= 8 && isAlnumDash(seg)) {
      segments.push("*");
    } else {
      segments.push(seg);
    }
  }

  return "/" + segments.join("/");
}

/**
 * Build memory key from location object.
 * Returns a string like "jobs.lever.co" followed by normalized path pattern.
 */
export function buildMemoryKey(location) {
  const host = location.hostname;
  const pathPattern = normalizePathname(location.pathname);
  return `${host}${pathPattern}`;
}

/**
 * Save a field preference for a specific site/canonical field
 */
export async function saveFieldPreference({ memoryKey, canonicalField, value, pageUrl = "" }) {
  try {
    const db = await openDb();
    const tx = db.transaction(STORE_NAME, "readwrite");
    const store = tx.objectStore(STORE_NAME);

    const id = `${memoryKey}::${canonicalField}`;
    const record = {
      id,
      memoryKey,
      canonicalField,
      value,
      pageUrl,
      updatedAt: Date.now(),
    };

    return new Promise((resolve, reject) => {
      const req = store.put(record);
      req.onsuccess = () => {
        console.log(`[MemoryV3] Saved preference: ${canonicalField} = "${String(value).slice(0, 50)}..."`);
        resolve();
      };
      req.onerror = () => reject(req.error);
    });
  } catch (err) {
    console.warn("[MemoryV3] Save failed:", err);
  }
}

/**
 * Load all field preferences for a memory key
 */
export async function loadPreferences(memoryKey) {
  try {
    const db = await openDb();
    const tx = db.transaction(STORE_NAME, "readonly");
    const store = tx.objectStore(STORE_NAME);
    const index = store.index("memoryKey");

    return new Promise((resolve, reject) => {
      const req = index.getAll(memoryKey);
      req.onsuccess = () => {
        const records = req.result || [];
        const prefs = {};
        for (const record of records) {
          prefs[record.canonicalField] = record.value;
        }
        console.log(`[MemoryV3] Loaded ${Object.keys(prefs).length} preferences for ${memoryKey}`);
        resolve(prefs);
      };
      req.onerror = () => reject(req.error);
    });
  } catch (err) {
    console.warn("[MemoryV3] Load failed:", err);
    return {};
  }
}

/**
 * Get a single field preference
 */
export async function getFieldPreference(memoryKey, canonicalField) {
  try {
    const db = await openDb();
    const tx = db.transaction(STORE_NAME, "readonly");
    const store = tx.objectStore(STORE_NAME);

    const id = `${memoryKey}::${canonicalField}`;

    return new Promise((resolve, reject) => {
      const req = store.get(id);
      req.onsuccess = () => resolve(req.result?.value || null);
      req.onerror = () => reject(req.error);
    });
  } catch (err) {
    console.warn("[MemoryV3] Get failed:", err);
    return null;
  }
}

/**
 * Clear all preferences for a memory key
 */
export async function clearPreferencesForKey(memoryKey) {
  try {
    const db = await openDb();
    const tx = db.transaction(STORE_NAME, "readwrite");
    const store = tx.objectStore(STORE_NAME);
    const index = store.index("memoryKey");

    return new Promise((resolve, reject) => {
      const req = index.openCursor(memoryKey);
      req.onsuccess = (e) => {
        const cursor = e.target.result;
        if (cursor) {
          cursor.delete();
          cursor.continue();
        } else {
          console.log(`[MemoryV3] Cleared preferences for ${memoryKey}`);
          resolve();
        }
      };
      req.onerror = () => reject(req.error);
    });
  } catch (err) {
    console.warn("[MemoryV3] Clear failed:", err);
  }
}

/**
 * Clear ALL preferences (for reset or debugging purposes).
 */
export async function clearAllPreferences() {
  try {
    const db = await openDb();
    const tx = db.transaction(STORE_NAME, "readwrite");
    const store = tx.objectStore(STORE_NAME);

    return new Promise((resolve, reject) => {
      const req = store.clear();
      req.onsuccess = () => {
        console.log("[MemoryV3] Cleared all preferences");
        resolve();
      };
      req.onerror = () => reject(req.error);
    });
  } catch (err) {
    console.warn("[MemoryV3] Clear all failed:", err);
  }
}

/**
 * Get statistics about stored preferences
 */
export async function getPreferenceStats() {
  try {
    const db = await openDb();
    const tx = db.transaction(STORE_NAME, "readonly");
    const store = tx.objectStore(STORE_NAME);

    return new Promise((resolve, reject) => {
      const req = store.getAll();
      req.onsuccess = () => {
        const records = req.result || [];
        const byKey = {};
        for (const record of records) {
          byKey[record.memoryKey] = (byKey[record.memoryKey] || 0) + 1;
        }
        resolve({
          total: records.length,
          byKey,
        });
      };
      req.onerror = () => reject(req.error);
    });
  } catch (err) {
    console.warn("[MemoryV3] Stats failed:", err);
    return { total: 0, byKey: {} };
  }
}
