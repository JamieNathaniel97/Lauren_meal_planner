// Loads the ingredient list and every recipe batch, and derives each
// recipe's facts. Used by the app and by tools/validate.html.
//
// Recipes live in data/recipes/batch-NN.json. data/recipes/index.json lists
// the batch files (a static site can't list a folder), so adding a batch
// means: write the file, add its name to index.json, bump CACHE in sw.js.

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
      recipes.push({ ...r, batch: file, d });
    }
  }
  return { ingredients, ingById, recipes, problems };
}
