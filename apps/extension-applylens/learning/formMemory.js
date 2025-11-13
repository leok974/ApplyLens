// learning/formMemory.js — IndexedDB wrapper for form memory
const DB_NAME = "applylens-companion";
const STORE_NAME = "form-memory";
const DB_VERSION = 1;

function openDb() {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, DB_VERSION);
    req.onerror = () => reject(req.error);
    req.onsuccess = () => resolve(req.result);
    req.onupgradeneeded = (e) => {
      const db = e.target.result;
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        db.createObjectStore(STORE_NAME, { keyPath: "key" });
      }
    };
  });
}

function makeKey(host, schemaHash) {
  return `${host}::${schemaHash}`;
}

export async function loadFormMemory(host, schemaHash) {
  try {
    const db = await openDb();
    const tx = db.transaction(STORE_NAME, "readonly");
    const store = tx.objectStore(STORE_NAME);
    const key = makeKey(host, schemaHash);

    return new Promise((resolve, reject) => {
      const req = store.get(key);
      req.onsuccess = () => resolve(req.result?.entry || null);
      req.onerror = () => reject(req.error);
    });
  } catch (err) {
    console.warn("[FormMemory] Load failed:", err);
    return null;
  }
}

export async function saveFormMemory(entry) {
  try {
    const db = await openDb();
    const tx = db.transaction(STORE_NAME, "readwrite");
    const store = tx.objectStore(STORE_NAME);
    const key = makeKey(entry.host, entry.schemaHash);

    return new Promise((resolve, reject) => {
      const req = store.put({ key, entry });
      req.onsuccess = () => resolve();
      req.onerror = () => reject(req.error);
    });
  } catch (err) {
    console.warn("[FormMemory] Save failed:", err);
  }
}

export async function clearFormMemory() {
  try {
    const db = await openDb();
    const tx = db.transaction(STORE_NAME, "readwrite");
    const store = tx.objectStore(STORE_NAME);

    return new Promise((resolve, reject) => {
      const req = store.clear();
      req.onsuccess = () => resolve();
      req.onerror = () => reject(req.error);
    });
  } catch (err) {
    console.warn("[FormMemory] Clear failed:", err);
  }
}
