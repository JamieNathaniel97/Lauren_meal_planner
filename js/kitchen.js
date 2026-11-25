// Kitchen stock and shopping list: the data side (no screens here).
//
// Stock records (store "stock"):
//   { id, ingId|null, name, storage, aisle, low, lowSource, expiry, addedAt, updatedAt }
//   - Foods from the ingredient list use the ingredient id as the record id,
//     so each food is in stock at most once. Custom foods get "custom-…" ids
//     and never count for recipe matching.
//   - Have it / don't have it only: no quantities.
//   - low: "running low" mark. lowSource is "user" now; "guess" is kept free
//     for a later "probably low" suggestion after cooking.
//   - expiry: "YYYY-MM-DD" or null.
// Shopping records (store "shopping"):
//   { id, ingId|null, name, aisle, parts: [{ qty, unit, recipe }], ticked, addedAt, updatedAt }
//   - The same food added from several recipes is one record with several parts.
// Staples (store "meta", id "staples"): { id, ids: [ingredient ids] }.
//   Staples always count as in stock.
//
// Matching is on exact ingredient ids only, so wheat pasta never stands in
// for gluten-free pasta (similar-item matching comes later, with GF rules).

import * as db from "./db.js";
import { makeStockIndex } from "./match.js";
import { SUGGESTED_STAPLES, STORAGE_FOR_AISLE, EXPIRY_SOON_DAYS } from "./stock-data.js";

const state = { stock: new Map(), shopping: new Map(), staples: new Set(), ingById: {}, loaded: false };

export async function loadKitchen(ingById) {
  state.ingById = ingById;
  const [stock, shopping, staples] = await Promise.all([db.all("stock"), db.all("shopping"), db.get("meta", "staples")]);
  state.stock = new Map(stock.map((r) => [r.id, r]));
  state.shopping = new Map(shopping.map((r) => [r.id, r]));
  const defaults = [...SUGGESTED_STAPLES, ...Object.values(ingById).filter((i) => i.staple).map((i) => i.id)];
  state.staples = new Set((staples?.ids || defaults).filter((id) => ingById[id]));
  state.loaded = true;
}

const uid = (prefix) => `${prefix}-${Date.now().toString(36)}${Math.random().toString(36).slice(2, 7)}`;
const ing = (id) => state.ingById[id];
/** The ingredient-list entry for an id (or undefined). */
export const ingredient = ing;

// ---------------------------------------------------------------- staples

export const staples = () => [...state.staples];
export const isStaple = (ingId) => state.staples.has(ingId);

export async function setStaple(ingId, on) {
  if (on) state.staples.add(ingId); else state.staples.delete(ingId);
  await db.put("meta", { id: "staples", ids: [...state.staples] });
}

// ---------------------------------------------------------------- stock

export const stockList = () => [...state.stock.values()];
export const stockItem = (id) => state.stock.get(id);

/** "in" | "low" | "missing" for an ingredient id. Staples are always "in". */
export function stockStatus(ingId) {
  if (state.staples.has(ingId)) return "in";
  const r = state.stock.get(ingId);
  if (!r) return "missing";
  return r.low ? "low" : "in";
}

async function saveStock(rec) {
  const saved = await db.put("stock", rec);
  state.stock.set(saved.id, saved);
  return saved;
}

/** Add a food from the ingredient list (or clear its low mark if already there). */
export async function addStock(ingId, extra = {}) {
  const i = ing(ingId);
  if (!i) throw new Error(`Unknown ingredient ${ingId}`);
  const existing = state.stock.get(ingId);
  if (existing) return saveStock({ ...existing, low: false, lowSource: null, ...extra });
  return saveStock({
    id: ingId, ingId, name: i.name, storage: i.storage || STORAGE_FOR_AISLE[i.aisle] || "cupboard",
    aisle: i.aisle || "other", low: false, lowSource: null, expiry: null, addedAt: new Date().toISOString(), ...extra,
  });
}

/** Add a food that isn't in the ingredient list. */
export async function addCustomStock(name, { storage = "cupboard", aisle = "other" } = {}) {
  const clean = name.trim();
  const same = stockList().find((r) => !r.ingId && r.name.toLowerCase() === clean.toLowerCase());
  if (same) return same;
  return saveStock({ id: uid("custom"), ingId: null, name: clean, storage, aisle, low: false, lowSource: null,
    expiry: null, addedAt: new Date().toISOString() });
}

export async function updateStock(id, changes) {
  const r = state.stock.get(id);
  if (!r) return null;
  return saveStock({ ...r, ...changes });
}

export async function toggleLow(id) {
  const r = state.stock.get(id);
  if (!r) return null;
  return saveStock({ ...r, low: !r.low, lowSource: r.low ? null : "user" });
}

/** Remove from stock. Returns the removed record so it can be restored (Undo). */
export async function removeStock(id) {
  const r = state.stock.get(id);
  if (!r) return null;
  state.stock.delete(id);
  await db.remove("stock", id);
  return r;
}

export async function restoreStock(rec) {
  return saveStock(rec);
}

/** Whole days from today until a "YYYY-MM-DD" date (negative = past). */
export function daysUntil(date) {
  if (!date) return null;
  const [y, m, d] = date.split("-").map(Number);
  const target = new Date(y, m - 1, d);
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  return Math.round((target - today) / 86400000);
}

/** Items expiring within EXPIRY_SOON_DAYS (not already expired), soonest first. */
export function useItUp() {
  return stockList()
    .filter((r) => r.expiry && daysUntil(r.expiry) >= 0 && daysUntil(r.expiry) <= EXPIRY_SOON_DAYS)
    .sort((a, b) => a.expiry.localeCompare(b.expiry));
}

// Expired items are never removed automatically. The Stock tab shows a
// banner until each one is removed or dismissed ("keep it"). A dismissal is
// stored against the expiry date it was for (expiredDismissedFor), so it
// only comes back if that date changes. Dismissed items stay in stock.

export const isExpired = (r) => !!r.expiry && daysUntil(r.expiry) < 0;

/** Expired items whose warning hasn't been dismissed, oldest first. */
export function expiredToReview() {
  return stockList().filter((r) => isExpired(r) && r.expiredDismissedFor !== r.expiry)
    .sort((a, b) => a.expiry.localeCompare(b.expiry));
}

/** Keep these expired items without being warned again (until the date changes). */
export async function dismissExpired(ids) {
  const at = new Date().toISOString();
  for (const id of ids) {
    const r = state.stock.get(id);
    if (r && r.expiry) await saveStock({ ...r, expiredDismissedFor: r.expiry, expiredDismissedAt: at });
  }
}

export function expiryText(date) {
  const n = daysUntil(date);
  if (n == null) return "";
  if (n < 0) return n === -1 ? "Expired yesterday" : `Expired ${-n} days ago`;
  if (n === 0) return "Use today";
  if (n === 1) return "Use by tomorrow";
  if (n <= 6) return `Use within ${n} days`;
  const [y, m, d] = date.split("-").map(Number);
  return `Use by ${new Date(y, m - 1, d).toLocaleDateString("en-GB", { day: "numeric", month: "short" })}`;
}

// ---------------------------------------------------------------- shopping

export const shoppingList = () => [...state.shopping.values()];
export const onShoppingList = (ingId) => state.shopping.has(ingId);

async function saveShop(rec) {
  const saved = await db.put("shopping", rec);
  state.shopping.set(saved.id, saved);
  return saved;
}

/** Add an ingredient-list food. qty/unit/recipe are optional; repeats merge into one item. */
export async function addToShopping(ingId, { qty = null, unit = null, recipe = null } = {}) {
  const i = ing(ingId);
  if (!i) throw new Error(`Unknown ingredient ${ingId}`);
  const existing = state.shopping.get(ingId);
  const part = { qty, unit, recipe };
  if (existing) {
    // The same recipe added twice replaces its own part rather than doubling it.
    const parts = existing.parts.filter((p) => !(recipe && p.recipe === recipe));
    const hasPlain = parts.some((p) => !p.recipe && p.qty == null);
    if (!recipe && qty == null && hasPlain) return existing;
    return saveShop({ ...existing, parts: [...parts, part], ticked: false });
  }
  return saveShop({ id: ingId, ingId, name: i.name, aisle: i.aisle || "other", parts: [part], ticked: false,
    addedAt: new Date().toISOString() });
}

/** Add a free-text item (not in the ingredient list). */
export async function addFreeText(name, aisle = "other") {
  const clean = name.trim();
  if (!clean) return null;
  const same = shoppingList().find((r) => !r.ingId && r.name.toLowerCase() === clean.toLowerCase());
  if (same) return same;
  return saveShop({ id: uid("item"), ingId: null, name: clean, aisle, parts: [], ticked: false,
    addedAt: new Date().toISOString() });
}

export async function toggleTicked(id) {
  const r = state.shopping.get(id);
  if (!r) return null;
  return saveShop({ ...r, ticked: !r.ticked });
}

export async function removeShopping(id) {
  const r = state.shopping.get(id);
  if (!r) return null;
  state.shopping.delete(id);
  await db.remove("shopping", id);
  return r;
}

export async function restoreShopping(rec) {
  return saveShop(rec);
}

export async function clearShopping() {
  const ids = [...state.shopping.keys()];
  await Promise.all(ids.map((id) => db.remove("shopping", id)));
  state.shopping.clear();
}

/** Ticked foods go into stock (or lose their low mark); ticked items leave the list. */
export async function doneShopping() {
  const ticked = shoppingList().filter((r) => r.ticked);
  let added = 0, restocked = 0, removed = 0;
  for (const r of ticked) {
    if (r.ingId && ing(r.ingId)) {
      const before = state.stock.get(r.ingId);
      await addStock(r.ingId);
      if (before) restocked++; else added++;
    } else removed++;
    await removeShopping(r.id);
  }
  return { added, restocked, removed, total: ticked.length };
}

/** Stock items marked low that aren't on the shopping list yet. */
export function lowNotOnList() {
  return stockList().filter((r) => r.low && !(r.ingId ? state.shopping.has(r.ingId)
    : shoppingList().some((s) => !s.ingId && s.name.toLowerCase() === r.name.toLowerCase())));
}

/** Put a low stock item on the list (custom items become free-text items). */
export async function addLowToShopping(stockRec) {
  if (stockRec.ingId) return addToShopping(stockRec.ingId);
  return addFreeText(stockRec.name, stockRec.aisle || "other");
}

// ---------------------------------------------------------------- quantities

const COUNTABLE_FIRST = ["each", "tin", "bunch", "block", "nest", "stick", "slice", "clove", "handful"];

/** Weight of one unit of an ingredient in grams, or null if unknown. */
function gramsPer(i, unit) {
  if (unit === "g") return 1;
  if (unit === "ml") return i?.units?.ml ?? 1; // close enough for shopping
  const w = i?.units?.[unit];
  return typeof w === "number" ? w : null;
}

/**
 * Combine an item's parts into shopping amounts, e.g.
 * [{2 each},{1 each}] -> [{3 each}];  [{2 each},{100 g}] (onion 150 g each) -> [{2.67 each}]
 * Units that can't be converted stay separate: [{2 each},{1 tbsp}] -> both.
 * Returns [{ qty, unit }]; empty if no part has a quantity.
 */
export function combineParts(parts, ingId) {
  const i = ing(ingId);
  const byUnit = new Map();
  for (const p of parts) {
    if (p.qty == null) continue;
    const u = p.unit || "each";
    byUnit.set(u, (byUnit.get(u) || 0) + p.qty);
  }
  if (byUnit.size <= 1) return [...byUnit].map(([unit, qty]) => ({ qty, unit }));
  // Pick the unit you'd shop in: a countable one if present, else grams/ml.
  const units = [...byUnit.keys()];
  const target = COUNTABLE_FIRST.find((u) => byUnit.has(u)) || (byUnit.has("g") ? "g" : byUnit.has("ml") ? "ml" : units[0]);
  const tg = gramsPer(i, target);
  const out = new Map([[target, byUnit.get(target)]]);
  for (const [u, q] of byUnit) {
    if (u === target) continue;
    const g = gramsPer(i, u);
    // Spoons and pinches of something bought by the each (e.g. 1 tbsp of a
    // lemon's juice) are only converted when the data gives a weight.
    if (tg && g && !(["tsp", "tbsp", "pinch"].includes(u) && !i?.units?.[u])) {
      out.set(target, out.get(target) + (q * g) / tg);
    } else out.set(u, (out.get(u) || 0) + q);
  }
  return [...out].map(([unit, qty]) => ({ qty, unit }));
}

export function recipesFor(item) {
  return [...new Set(item.parts.map((p) => p.recipe).filter(Boolean))];
}

// ---------------------------------------------------------------- matching

/** Quick-lookup index of current stock for js/match.js (finder & recipe page). */
export function stockIndex() {
  return makeStockIndex(stockList(), state.staples, state.ingById, { daysUntil, soonDays: EXPIRY_SOON_DAYS });
}
