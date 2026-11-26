// Loads the ingredient list and every recipe batch, and derives each
// recipe's facts. Used by the app and by tools/validate.html.
//
// Recipes live in data/recipes/*.json, listed in data/recipes/index.json
// (a static site can't list a folder). Our own batches (batch-NN.json) keep
// their method steps inline. Imported batches (unitools-NN, fork-NN) keep
// them in data/steps/<same name>.json, loaded when a recipe is opened, so
// the recipe list starts quickly. Adding a batch means: write the file, add
// its name to index.json, bump CACHE in sw.js.

import { deriveRecipe } from "./derive.js";

async function getJSON(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`${url}: HTTP ${res.status}`);
  return res.json();
}

/** base: URL of the app folder, e.g. new URL("./", location.href). */
export async function loadCatalogue(base) {
  const at = (p) => new URL(p, base).href;
  const ingredients = await getJSON(at("data/ingredients.json"));
  const ingById = Object.fromEntries(ingredients.map((i) => [i.id, i]));
  const index = await getJSON(at("data/recipes/index.json"));
  const batches = await Promise.all(
    index.batches.map(async (file) => ({ file, recipes: await getJSON(at(`data/recipes/${file}`)) }))
  );

  const problems = [];
  const seen = new Map();
  const recipes = [];
  for (const { file, recipes: list } of batches) {
    for (const r of list) {
      if (seen.has(r.id)) {
        problems.push(`${file}: duplicate recipe id "${r.id}" (also in ${seen.get(r.id)})`);
        continue;
      }
      seen.set(r.id, file);
      const d = deriveRecipe(r, ingById);
      d.problems.forEach((p) => problems.push(`${file}: ${r.id}: ${p}`));
      const rec = { ...r, batch: file, d };
      if (!r.steps) rec.stepsUrl = at(`data/steps/${file}`);
      recipes.push(rec);
    }
  }
  const stepsFiles = [...new Set(recipes.map((r) => r.stepsUrl).filter(Boolean))];
  return { ingredients, ingById, recipes, problems, stepsFiles };
}

const stepCache = new Map();   // steps file URL -> Promise of { id: [steps] }

/** The method steps for a recipe, fetching its steps file if needed. */
export async function stepsFor(recipe) {
  if (recipe.steps) return recipe.steps;
  if (!stepCache.has(recipe.stepsUrl)) {
    stepCache.set(recipe.stepsUrl, getJSON(recipe.stepsUrl).catch((e) => {
      stepCache.delete(recipe.stepsUrl);
      throw e;
    }));
  }
  const all = await stepCache.get(recipe.stepsUrl);
  return all[recipe.id] || [];
}
