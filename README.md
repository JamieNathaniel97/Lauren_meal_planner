# Lauren's Meal Planner

An installable, offline web app (PWA) for meal ideas, recipes, kitchen stock
and shopping. It works on iPhone and Android. The full brief is in
[PLAN.md](PLAN.md).

**Status: phase 1 (foundations).** Done: the recipe book, recipe pages, the
profile, and the cuisine picker on Find. Stock, Shopping and the full finder
are placeholders for later phases.

**Recipes:** about 1,400. 42 were written for this app; the rest are adapted
from two open recipe collections (CC BY-SA 4.0), plus gluten-free and
nut-free versions made from them. See [Imported recipes](#imported-recipes)
and [DATA_LICENSE.md](DATA_LICENSE.md).

## Run it locally

It needs a web server, because ES modules don't load from `file://`:

```
cd C:\Documents\Claude\Lauren_meal_planner
python -m http.server 8000
```

Then open http://localhost:8000. To try it on a phone on the same Wi-Fi, use
the computer's IP address instead of localhost. Installing it ("Add to Home
Screen") and offline use need HTTPS, so test those on GitHub Pages.

**Caching while developing:** the service worker serves files from its
cache, so after editing anything either bump `CACHE` in `sw.js`, or in Chrome
DevTools → Application → Service workers tick "Update on reload".

## Deploy (GitHub Pages)

Everything is static, with no build step. Push the repo and turn on Pages
(Settings → Pages → deploy from the `main` branch, root folder). All paths
are relative, so it works under `/<repo-name>/`.

**Before every deploy that changes any file, bump `CACHE` in `sw.js`**
(e.g. `meal-planner-v2`). If you don't, installed phones keep the old version.

## Files

```
index.html               app page (tabs: Find, Recipes, Stock, Shopping, Profile)
manifest.webmanifest     install info (name, icons, colours)
sw.js                    service worker: offline cache (bump CACHE on changes)
css/app.css              all styles; light and dark mode
js/app.js                start-up, routing (#/find, #/recipes, #/recipe/<id>, #/profile …)
js/constants.js          cuisines, meal types, diets, 14 UK allergens, tools, presets, default profile
js/derive.js             works out diet tags, allergens, label warnings, ingredient count, nutrition
js/data.js               loads ingredients + all recipe batches, runs derive.js on each
js/db.js                 IndexedDB storage (profile now; stock, shopping, own recipes later)
js/ui.js                 HTML escaping, quantity and time formatting
js/views/*.js            one file per screen
data/ingredients.json    master ingredient list (written by tools/import_all.py; see below)
data/recipes/index.json  list of recipe batch files to load
data/recipes/batch-01.json  our own recipes (steps inline)
data/recipes/unitools-NN.json, fork-NN.json  imported recipes, without steps
data/steps/unitools-NN.json, fork-NN.json    their method steps, loaded when a recipe opens
DATA_LICENSE.md          licence and credits for the imported recipe data
icons/                   app icons (made by tools/make_icons.py)
tools/validate.py        checks all recipe data (see below)
tools/validate.html      the check itself (runs the app's own derive.js)
tools/make_icons.py      redraws the icons (needs Pillow)
tools/import_all.py      rebuilds the imported batches (see Imported recipes)
tools/safety_scan.py     coeliac/nut check of recipe WORDS (run by validate.py; --test runs its tests)
tools/text_safety.py     rewrites words to match safe ingredients (soy sauce -> tamari, etc.); used by the importer
tools/recipe_fixes.json  hand-reviewed per-recipe fixes and allowed phrases
tools/import_unitools.py, import_forkrecipe.py   read each source into a common format
tools/import_common.py   ingredient matching, safety checks, units, GF/NF versions
tools/jslit.py           reads ForkRecipe's .js files as plain data (never runs them)
tools/ingnorm.py         cleans ingredient names for matching
tools/ingredient_master_new.txt   ingredients added for the imports (flags, allergens, nutrition, match phrases)
tools/ingredient_map_existing.txt match phrases for the original ingredients
tools/import_report.md   what the last import took, converted and rejected, and why
tools/debug_recipe.py    prints a recipe's grams and kcal line by line
```

## Recipe data

### Ingredients (`data/ingredients.json`)

One entry per food. Recipes, and later stock and the shopping list, all
refer to these ids.

| Field | Meaning |
|---|---|
| `id`, `name`, `synonyms` | `synonyms` help search and "foods you don't like" |
| `group` | interchangeable foods share a group, e.g. `any-pasta`, `rice`, `stock` (used by the phase 3 matching; that matching must respect diet, so wheat pasta must never stand in for gluten-free pasta) |
| `flags` | diet facts: `meat`, `pork`, `fish`, `shellfish`, `dairy`, `egg`, `honey`, `gluten`, `alcohol`, `animal-rennet`, `gelatin`, `coconut`, `pine-nut` |
| `allergens` | from the 14 UK allergens: `gluten`, `peanuts`, `nuts` (tree nuts), `milk`, `eggs`, `fish`, `crustaceans`, `molluscs`, `sesame`, `soya`, `celery`, `mustard`, `lupin`, `sulphites` |
| `checkLabel` | text shown when an item often contains gluten or nuts depending on the brand (stock, sauces, oats, spice blends, processed meat …) |
| `aisle`, `storage` | for the shopping list and stock screens |
| `per100g` | kcal, protein, carbs, fat, fibre (approximate UK/USDA figures) |
| `units` | grams per unit, e.g. `{"each": 150}` for an onion or `{"tin": 240}` for drained chickpeas. `tsp`/`tbsp`/`pinch`/`ml` fall back to 5 g / 15 g / 0.5 g / 1 g |
| `staple` | salt, pepper, oil, water: never "missing" and not counted as ingredients |

Gluten-free versions are **separate ingredients** (`tamari` vs `soy-sauce`,
`gf-pasta` vs `spaghetti`, `gf-oats` vs `porridge-oats`, `gf-*-stock`), so a
recipe is only tagged gluten-free if it really uses the GF version. A
`gluten` flag must always match a `gluten` allergen (the validator checks
this).

### Recipes (`data/recipes/batch-NN.json`)

Each recipe has `id`, `name`, `description`, `cuisine`, `mealTypes`,
`servings`, `prepMins`, `cookMins`, `difficulty` (easy/medium/hard),
`spice` (0–3), `cost` (1–3), `tools`, `onePot`, `batchCook`,
`freezerFriendly`, `goodForLeftovers`, `lunchbox`, `season`, `tags`,
`ingredients` and `steps`. Each ingredient line is
`{"id", "qty", "unit", "note", "optional"}`. Leave out `qty` for "to taste".

Optional `variants` links versions of the same dish, e.g. a gluten-free
version and the original:
`"variants": [{"id": "gf-fluffy-pancakes", "label": "Gluten-free version"}]`.
The recipe page shows each one as a link. Links must point both ways; the
validator checks this.

**Not stored, but worked out** by `js/derive.js`: diet tags (gluten-free,
nut-free, vegetarian, vegan, pescatarian, dairy-free, halal-friendly,
low-carb), allergens, "check labels" warnings, ingredient count, total time,
and nutrition per portion. Optional ingredients don't count towards the
tags, the ingredient count or the calories. If they clash with the profile,
the recipe page warns about them.

**Nut-free** means no peanuts, no tree nuts and no pine nuts. Coconut is
allowed (decided), and shown as "Contains coconut".

Extra optional recipe fields: `origin` (country or region), `nativeName`,
`photo` (`url`, `credit`, `licence`, `via`), `source` (`name`, `url`,
`licence`, `author`) for adapted recipes, `quantitiesEstimated` (amounts were
worked out from ratios; the page says so) and, on an ingredient line,
`absorb` (the share of deep-frying oil that ends up in the food, used for
calories).

### Adding a batch of recipes

1. Write `data/recipes/batch-02.json` (a JSON array of recipes). Add any new
   ingredients to `data/ingredients.json`.
2. Add `"batch-02.json"` to `data/recipes/index.json`.
3. Run `python tools/validate.py` and fix anything it reports.
4. Bump `CACHE` in `sw.js`.

Recipe ids must be unique across all batches. Recipes in our own batches must
be original: don't copy them from websites or books. Openly licensed
collections go through the importer below instead.

### Imported recipes

Two open collections, both **CC BY-SA 4.0** (licence confirmed from each
source's own LICENSE file):

- **UniTools World Recipes** (theunitools.com/en/data): 501 home-cooking
  recipes from 127 countries, with real quantities and Wikimedia Commons
  photos (each with its own licence and author).
- **ForkRecipe** (github.com/futurechef/forkrecipe-recipes): 963 recipe files.
  Only dishes are imported (proteins, seafood, grains, vegetables, eggs,
  desserts); sauces, stocks, condiments, ferments, drinks and breads are
  skipped as components. Many give **ratios ("parts") instead of amounts**;
  those are scaled to a sensible size (or to a weight stated in the recipe,
  like "pork shoulder, 2 kg") and the recipe page says the amounts were
  worked out.

To rebuild (safe to rerun; our own `batch-NN.json` files are never touched):

```
git clone --depth 1 https://github.com/futurechef/forkrecipe-recipes raw/forkrecipe/repo
git clone --depth 1 https://github.com/farcrak/unitools-recipes raw/unitools/repo
python tools/import_all.py raw/forkrecipe/repo raw/unitools/repo/unitools-recipes-v1.json
python tools/validate.py
```

**Words must match the safe ingredients.** For every recipe that is
gluten-free or nut-free by its ingredients, the importer runs
`tools/text_safety.py`: optional unsafe extras ("naan, to serve") are swapped
for safe ones, and the name, description, notes and steps are rewritten
("soy sauce" -> "tamari", "lightly floured surface" -> "surface dusted with
gluten-free flour", "serve with crusty bread" -> "serve with gluten-free
bread", "walnuts" -> the seeds used). Hand fixes go in
`tools/recipe_fixes.json`. `tools/validate.py` then runs
`tools/safety_scan.py` and fails if any gluten word is left in a gluten-free
recipe or any nut word in a nut-free one. Our own batch isn't rebuilt by
the importer, so after editing it, check it with `python tools/safety_scan.py`.

`raw/` is git-ignored. Downloaded files are treated as data only: the
ForkRecipe `.js` files are parsed by `tools/jslit.py`, which accepts plain
literals and rejects anything else; nothing from the sources is executed.

What the importer does, per recipe:

1. **Matches every ingredient** to `data/ingredients.json` using the phrase
   lists in `tools/ingredient_map_existing.txt` and
   `tools/ingredient_master_new.txt` (longest phrase wins; "x or y" uses the
   first option, "x and y" becomes both). The source's wording is kept as
   the line's note. A recipe with any unmatched ingredient is left out.
2. **Safety check:** if the source text mentions nuts, peanuts, pine nuts, a
   gluten source, fish or meat that the matched ingredient doesn't carry,
   the recipe is left out, so a loose match can't hide an allergen.
   Alternatives the cook chooses between ("sunflower or peanut oil") use the
   first option, and the note says the source also suggests a nut or gluten
   option.
3. **Converts amounts** (cups, lb, cans, pieces, ratios) to the app's units.
   Liquid stock becomes gluten-free stock cubes ("made up to 500 ml").
   Deep-frying oil counts at 15 % for calories.
4. **Works out** tools from the method, spice, cost and meal type; servings
   are adjusted only if calories per portion would otherwise be implausible.
5. **Skips duplicates** of dishes we already have (ours win, then UniTools).
6. **Makes gluten-free / nut-free versions** where the swap is standard
   (tamari for soy sauce, GF pasta, GF flour, GF stock, corn tortillas, rice
   noodles, quinoa for couscous, seeds for garnish nuts …), linked to the
   original with `variants`. Kneaded yeast doughs and dishes built on nuts
   aren't converted.

Diet tags, allergens and nutrition are still worked out by `derive.js`.
`tools/import_report.md` lists everything rejected with the reason, the
recipes whose calories differ a lot from the source's own figure (the
app's figure is used), and diet-tag disagreements with UniTools (all
checked: either the source was loose, e.g. "vegetarian" jollof made with
chicken stock, or UK rules are stricter, e.g. Parmesan uses animal rennet).

**Credits:** Profile → Credits names both sources and the licence; every
imported recipe page links to its source and says it was adapted; photos are
credited on the recipe page. Under CC BY-SA, the adapted recipe data must
stay under the same licence (see DATA_LICENSE.md). Don't call the app
"ForkRecipe" (their trademark).

### Checking the data

```
python tools/validate.py
```

This serves the repo, runs `tools/validate.html` in headless Chrome or Edge
(so it uses exactly the app's own `derive.js`), and prints a table of every
recipe (kcal, protein, carbs, fat, GF, NF, number of label warnings) with
totals. It reports **problems** (unknown ingredients or units, duplicate ids,
unknown cuisines/tools, missing fields) and exits with 1 if there are any.
It also reports **warnings** (kcal per portion out of the normal range for
the meal type, cuisines with no recipes). You can also open
http://localhost:8000/tools/validate.html while serving the repo.

## Profile and allergies

- The profile starts empty. **"Coeliac + nut-free"** at the top of Profile
  sets it all in one tap: gluten-free and nut-free diets, the gluten,
  peanut and tree-nut allergens, and **Strict (coeliac)**.
- With Strict (coeliac) on, any recipe that has a "check labels" ingredient
  shows a red warning listing what to check. The recipe book chip
  **"Gluten-free & nut-free"** filters to those recipes for anyone.
- Nutrition and allergen information is worked out from the ingredient list
  and is only a guide. Always check the packaging.
