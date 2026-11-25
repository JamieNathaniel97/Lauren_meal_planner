// Small IndexedDB wrapper. Everything the user creates is stored on this
// phone only. Every record has an `id` and an `updatedAt` timestamp, so a
// sync between phones can be added later by merging on updatedAt.
//
// Stores: profile (one record, id "me"), stock, shopping, userRecipes, meta.
// If IndexedDB is unavailable (some private-browsing modes), it falls back
// to memory so the app still works for that visit.

const DB_NAME = "lauren-meal-planner";
const DB_VERSION = 1;
const STORES = ["profile", "stock", "shopping", "userRecipes", "meta"];

let dbPromise = null;
const memory = Object.fromEntries(STORES.map((s) => [s, new Map()]));
let useMemory = false;

function open() {
  if (dbPromise) return dbPromise;
  dbPromise = new Promise((resolve) => {
    try {
      const req = indexedDB.open(DB_NAME, DB_VERSION);
      req.onupgradeneeded = () => {
        const db = req.result;
        for (const s of STORES) if (!db.objectStoreNames.contains(s)) db.createObjectStore(s, { keyPath: "id" });
      };
      req.onsuccess = () => resolve(req.result);
      req.onerror = () => { useMemory = true; resolve(null); };
      req.onblocked = () => { useMemory = true; resolve(null); };
    } catch {
      useMemory = true;
      resolve(null);
    }
  });
  return dbPromise;
}

function run(store, mode, fn) {
  return open().then((db) => {
    if (useMemory || !db) return fn(null);
    return new Promise((resolve, reject) => {
      const tx = db.transaction(store, mode);
      const req = fn(tx.objectStore(store));
      tx.oncomplete = () => resolve(req && req.result);
      tx.onerror = () => reject(tx.error);
    });
  });
}

export async function get(store, id) {
  if (useMemory) return memory[store].get(id);
  const r = await run(store, "readonly", (s) => (s ? s.get(id) : null));
  return useMemory ? memory[store].get(id) : r;
}

export async function all(store) {
  if (useMemory) return [...memory[store].values()];
  const r = await run(store, "readonly", (s) => (s ? s.getAll() : null));
  return useMemory ? [...memory[store].values()] : r || [];
}

export async function put(store, record) {
  const rec = { ...record, updatedAt: new Date().toISOString() };
  await run(store, "readwrite", (s) => (s ? s.put(rec) : null));
  if (useMemory) memory[store].set(rec.id, rec);
  return rec;
}

export async function remove(store, id) {
  await run(store, "readwrite", (s) => (s ? s.delete(id) : null));
  if (useMemory) memory[store].delete(id);
}

export function isPersistent() {
  return !useMemory;
}
