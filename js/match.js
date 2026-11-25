// What can I cook? Matches recipe ingredients against kitchen stock.
// Used by the meal finder AND the recipe page, so they always agree.
//
// A recipe ingredient counts as "have" when:
//  - it's a staple (salt, oil …), or
//  - that exact ingredient is in stock, or
//  - a SIMILAR item is in stock: same "group" in data/ingredients.json
//    (e.g. "any-pasta", "cheese") AND at least as safe: its diet flags and
//    allergens are a subset of the recipe ingredient's. So:
//      stock GF pasta    -> recipe "spaghetti"   ✓ (shown as "using: gluten-free pasta")
//      stock spaghetti   -> recipe "GF pasta"    ✗ (would add gluten)
//      stock soy sauce   -> recipe "tamari"      ✗
//    A substitute must also suit the profile (allergens, diets, dislikes).
// Optional ingredients never count as missing.
//
// Pure functions: pass in the stock (via makeStockIndex) so this runs in
// tests without the app.

const MEAT_LIKE = ["meat", "pork", "fish", "shellfish", "animal-rennet", "gelatin"];

/**
 * Build a quick-lookup index of what's in stock.
 *   stock:   [{ ingId, low, expiry }]   (custom items have ingId null and are ignored)
 *   staples: iterable of ingredient ids
 *   daysUntil: fn("YYYY-MM-DD") -> whole days (optional)
 */
export function makeStockIndex(stock, staples, ingById, { daysUntil = null, soonDays = 3 } = {}) {
  const byId = new Map();     // ingId -> { low, days }
  const byGroup = new Map();  // group -> [ingId]
  for (const r of stock) {
    if (!r.ingId || !ingById[r.ingId]) continue;
    const days = r.expiry && daysUntil ? daysUntil(r.expiry) : null;
    byId.set(r.ingId, { low: !!r.low, days });
    const g = ingById[r.ingId].group;
    if (g) (byGroup.get(g) || byGroup.set(g, []).get(g)).push(r.ingId);
  }
  return { byId, byGroup, staples: new Set(staples), soonDays };
}

const subset = (a = [], b = []) => a.every((x) => b.includes(x));

/** Is `sub` at least as safe as `wanted` (no new diet flags or allergens)? */
export function safeSubstitute(sub, wanted) {
  return subset(sub.flags, wanted.flags) && subset(sub.allergens, wanted.allergens);
}

/** Does a single ingredient suit the profile? (for substitutes) */
export function ingredientSuits(ing, profile) {
  if (!profile) return true;
  if ((profile.dislikes || []).includes(ing.id)) return false;
  if ((profile.allergens || []).some((a) => ing.allergens.includes(a))) return false;
  const diets = new Set(profile.diets || []);
  const f = (x) => ing.flags.includes(x);
  if (diets.has("gluten-free") && (f("gluten") || ing.allergens.includes("gluten"))) return false;
  if (diets.has("nut-free") && (ing.allergens.includes("peanuts") || ing.allergens.includes("nuts") || f("pine-nut"))) return false;
  if ((diets.has("vegetarian") || diets.has("vegan")) && MEAT_LIKE.some(f)) return false;
  if (diets.has("vegan") && (f("dairy") || f("egg") || f("honey"))) return false;
  if (diets.has("pescatarian") && (f("meat") || f("pork") || f("animal-rennet") || f("gelatin"))) return false;
  if (diets.has("dairy-free") && f("dairy")) return false;
  if (diets.has("halal") && (f("pork") || f("alcohol") || f("gelatin"))) return false;
  return true;
}

/**
 * Status of one recipe line.
 * Returns { status, using, days }:
 *   status: "staple" | "in" | "low" | "missing" | "unknown"
 *   using:  ingredient id actually used from stock (differs from line.id for a substitute)
 *   days:   days until that stock item expires (or null)
 */
export function matchLine(line, idx, ingById, profile) {
  const wanted = ingById[line.id];
  if (!wanted) return { status: "unknown", using: null, days: null };
  if (idx.staples.has(line.id)) return { status: "staple", using: line.id, days: null };
  const exact = idx.byId.get(line.id);
  if (exact && !exact.low) return { status: "in", using: line.id, days: exact.days };
  // Look for a safe similar item (prefer one that isn't running low).
  let best = null;
  if (wanted.group) {
    for (const id of idx.byGroup.get(wanted.group) || []) {
      if (id === line.id) continue;
      const sub = ingById[id];
      if (!safeSubstitute(sub, wanted) || !ingredientSuits(sub, profile)) continue;
      const s = idx.byId.get(id);
      if (!best || (best.low && !s.low)) best = { id, ...s };
      if (!s.low) break;
    }
  }
  if (exact) {
    // Exact item is low; a non-low substitute is better if there is one.
    if (best && !best.low) return { status: "in", using: best.id, days: best.days };
    return { status: "low", using: line.id, days: exact.days };
  }
  if (best) return { status: best.low ? "low" : "in", using: best.id, days: best.days };
  // A staple can stand in too (e.g. a recipe's olive oil when vegetable oil is a staple).
  if (wanted.group) {
    for (const id of idx.staples) {
      const sub = ingById[id];
      if (sub && sub.group === wanted.group && safeSubstitute(sub, wanted) && ingredientSuits(sub, profile)) {
        return { status: "staple", using: id, days: null };
      }
    }
  }
  return { status: "missing", using: null, days: null };
}

/**
 * Summary for a whole recipe.
 * Returns { needed, have, pct, missing:[line], low:[ingId], subs:[{line, using}], usesUp:[ingId], lines:[{line, m}] }
 * "needed" counts non-optional, non-staple ingredients; staples are free.
 */
export function matchRecipe(recipe, idx, ingById, profile) {
  let needed = 0, have = 0;
  const missing = [], low = [], subs = [], usesUp = [], lines = [];
  for (const line of recipe.ingredients) {
    const m = matchLine(line, idx, ingById, profile);
    lines.push({ line, m });
    if (line.optional || m.status === "unknown") continue;
    if (m.status === "staple") continue;
    needed++;
    if (m.status === "missing") { missing.push(line); continue; }
    have++;
    if (m.status === "low") low.push(m.using);
    if (m.using !== line.id) subs.push({ line, using: m.using });
    // "Uses up" food expiring soon; already-expired food isn't something to rank on.
    if (m.days != null && m.days >= 0 && m.days <= idx.soonDays && !usesUp.includes(m.using)) usesUp.push(m.using);
  }
  return { needed, have, pct: needed ? have / needed : 1, missing, low, subs, usesUp, lines };
}

/** Which result group a recipe falls in. */
export function groupOf(match) {
  if (match.missing.length === 0) return "now";
  if (match.missing.length <= 2) return "nearly";
  return "ideas";
}

/** Does the recipe use this ingredient (exactly or via a safe similar item)? */
export function recipeUses(recipe, ingId, ingById) {
  const have = ingById[ingId];
  if (!have) return false;
  return recipe.ingredients.some((l) => {
    if (l.id === ingId) return true;
    const w = ingById[l.id];
    return w && have.group && w.group === have.group && safeSubstitute(have, w);
  });
}
