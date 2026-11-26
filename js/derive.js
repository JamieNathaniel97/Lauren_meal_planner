// Works out a recipe's facts from its ingredients, so they can't be typed
// in wrong: diet tags, allergens, "check the label" notes, ingredient count,
// and nutrition per portion. Pure functions, no browser APIs, so the same
// code runs in the app and in tools/validate.html.

// Grams per unit when an ingredient doesn't give its own figure.
// Keep in step with DEFAULT_UNIT_GRAMS in tools/import_common.py.
const DEFAULT_UNIT_GRAMS = { tsp: 5, tbsp: 15, pinch: 0.5, ml: 1, g: 1, kg: 1000, l: 1000,
  sprig: 1, leaf: 0.3, slice: 25, bunch: 25, handful: 30, clove: 4, cm: 5, stick: 40, tin: 400 };

const MEAT_LIKE = ["meat", "pork", "fish", "shellfish", "animal-rennet", "gelatin"];

/** Grams for one recipe line, 0 for "to taste", or null if the unit is unknown. */
export function gramsFor(line, ing) {
  if (line.qty == null) return 0;
  const unit = line.unit || "each";
  const perUnit = (ing.units && ing.units[unit]) ?? DEFAULT_UNIT_GRAMS[unit];
  return perUnit == null ? null : line.qty * perUnit;
}

/** Derive everything for one recipe. ingById maps ingredient id -> ingredient. */
export function deriveRecipe(recipe, ingById) {
  const problems = [];
  const flags = new Set();
  const allergens = new Set();
  const optionalAllergens = new Set();
  const optionalFlags = new Set();
  const checkLabels = [];
  const totals = { kcal: 0, protein: 0, carbs: 0, fat: 0, fibre: 0 };
  let ingredientCount = 0;

  for (const line of recipe.ingredients) {
    const ing = ingById[line.id];
    if (!ing) {
      problems.push(`unknown ingredient "${line.id}"`);
      continue;
    }
    if (ing.checkLabel && !checkLabels.some((c) => c.id === ing.id)) {
      checkLabels.push({ id: ing.id, name: ing.name, reason: ing.checkLabel, optional: !!line.optional });
    }
    if (line.optional) {
      ing.flags.forEach((f) => optionalFlags.add(f));
      ing.allergens.forEach((a) => optionalAllergens.add(a));
      continue; // optional extras don't count towards tags, count or calories
    }
    ing.flags.forEach((f) => flags.add(f));
    ing.allergens.forEach((a) => allergens.add(a));
    if (!ing.staple) ingredientCount++;
    const grams = gramsFor(line, ing);
    if (grams == null) {
      problems.push(`no weight for unit "${line.unit}" of "${line.id}"`);
      continue;
    }
    // absorb: the share that ends up in the food (e.g. 0.15 of deep-frying oil).
    const eaten = grams * (line.absorb ?? 1);
    for (const k of Object.keys(totals)) totals[k] += (ing.per100g[k] || 0) * eaten / 100;
  }
  allergens.forEach((a) => optionalAllergens.delete(a));

  const servings = recipe.servings || 1;
  const perPortion = {};
  for (const [k, v] of Object.entries(totals)) perPortion[k] = Math.round(v / servings * (k === "kcal" ? 1 : 10)) / (k === "kcal" ? 1 : 10);
  perPortion.kcal = Math.round(perPortion.kcal / 5) * 5;

  const has = (f) => flags.has(f);
  const vegetarian = !MEAT_LIKE.some(has);
  const diets = [];
  if (!has("gluten") && !allergens.has("gluten")) diets.push("gluten-free");
  // Nut-free also excludes pine nuts (not a legal tree-nut allergen, but
  // avoided by people who avoid all nuts). Coconut is allowed; see containsCoconut.
  if (!allergens.has("peanuts") && !allergens.has("nuts") && !has("pine-nut")) diets.push("nut-free");
  if (vegetarian) diets.push("vegetarian");
  if (vegetarian && !has("dairy") && !has("egg") && !has("honey")) diets.push("vegan");
  if (!has("meat") && !has("pork") && !has("animal-rennet") && !has("gelatin")) diets.push("pescatarian");
  if (!has("dairy")) diets.push("dairy-free");
  if (!has("pork") && !has("alcohol") && !has("gelatin")) diets.push("halal");
  if (perPortion.carbs <= 20) diets.push("low-carb");

  return {
    diets,
    allergens: [...allergens].sort(),
    optionalAllergens: [...optionalAllergens].sort(),
    optionalFlags: [...optionalFlags].sort(),
    containsCoconut: has("coconut"),
    checkLabels,
    ingredientCount,
    totalMins: (recipe.prepMins || 0) + (recipe.cookMins || 0),
    perPortion,
    problems,
  };
}

/** Does a recipe suit the profile? Returns { ok, reasons }. */
export function fitsProfile(recipe, derived, profile, ingById) {
  const reasons = [];
  if (!profile) return { ok: true, reasons };
  for (const d of profile.diets || []) {
    if (!derived.diets.includes(d)) reasons.push(`not ${d.replace("-", " ")}`);
  }
  for (const a of profile.allergens || []) {
    if (derived.allergens.includes(a)) reasons.push(`contains ${a}`);
  }
  const dislikes = new Set(profile.dislikes || []);
  for (const line of recipe.ingredients) {
    if (!line.optional && dislikes.has(line.id)) reasons.push(`has ${ingById[line.id]?.name || line.id}`);
  }
  if (Array.isArray(profile.tools)) {
    const owned = new Set(profile.tools);
    for (const t of recipe.tools) if (!owned.has(t)) reasons.push(`needs ${t.replace("-", " ")}`);
  }
  return { ok: reasons.length === 0, reasons };
}

/** Optional extras in a recipe that clash with the profile (to warn about). */
export function optionalClashes(recipe, profile, ingById) {
  if (!profile) return [];
  const bad = new Set(profile.allergens || []);
  const diets = new Set(profile.diets || []);
  const out = [];
  for (const line of recipe.ingredients) {
    if (!line.optional) continue;
    const ing = ingById[line.id];
    if (!ing) continue;
    const hit = ing.allergens.some((a) => bad.has(a))
      || (diets.has("gluten-free") && ing.flags.includes("gluten"))
      || (diets.has("nut-free") && (ing.allergens.some((a) => a === "peanuts" || a === "nuts") || ing.flags.includes("pine-nut")))
      || ((diets.has("vegetarian") || diets.has("vegan")) && ing.flags.some((f) => MEAT_LIKE.includes(f)))
      || (diets.has("vegan") && ing.flags.some((f) => ["dairy", "egg", "honey"].includes(f)))
      || (diets.has("dairy-free") && ing.flags.includes("dairy"))
      || (profile.dislikes || []).includes(ing.id);
    if (hit) out.push(ing.name);
  }
  return out;
}
