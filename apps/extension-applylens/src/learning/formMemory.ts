/** IndexedDB wrapper for FormMemory - stores learned field mappings per host+schema. */

import { FormMemoryEntry } from "./types";

const DB_NAME = "applylens-companion";
const STORE_NAME = "form-memory";
const DB_VERSION = 1;

function openDb(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);

    request.onupgradeneeded = () => {
      const db = request.result;
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        db.createObjectStore(STORE_NAME, { keyPath: "key" });
      }
    };

    request.onerror = () => reject(request.error);
    request.onsuccess = () => resolve(request.result);
  });
}

function makeKey(host: string, schemaHash: string): string {
  return `${host}::${schemaHash}`;
}

export async function loadFormMemory(host: string, schemaHash: string): Promise<FormMemoryEntry | null> {
  const db = await openDb();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, "readonly");
    const store = tx.objectStore(STORE_NAME);
    const req = store.get(makeKey(host, schemaHash));

    req.onerror = () => reject(req.error);
    req.onsuccess = () => {
      const value = req.result;
      resolve(value ? (value.entry as FormMemoryEntry) : null);
    };
  });
}

export async function saveFormMemory(entry: FormMemoryEntry): Promise<void> {
  const db = await openDb();
  const key = makeKey(entry.host, entry.schemaHash);

  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, "readwrite");
    const store = tx.objectStore(STORE_NAME);
    const req = store.put({ key, entry });

    req.onerror = () => reject(req.error);
    req.onsuccess = () => resolve();
  });
}

export async function clearFormMemory(): Promise<void> {
  const db = await openDb();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, "readwrite");
    const store = tx.objectStore(STORE_NAME);
    const req = store.clear();

    req.onerror = () => reject(req.error);
    req.onsuccess = () => resolve();
  });
}
