# Lauren's Meal Planner

An installable, offline web app (PWA) for meal ideas, recipes, kitchen stock
and shopping. It works on iPhone and Android. The full brief is in
[PLAN.md](PLAN.md).

**Status: phase 1 (foundations).** Done: the recipe book, recipe pages, the
profile, and the cuisine picker on Find. Stock, Shopping and the full finder
are placeholders for later phases.

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
css/app.css              main styles; light and dark mode
css/kitchen.css          stock and shopping styles
js/app.js                start-up, routing (#/find, #/recipes, #/recipe/<id>, #/profile …)
js/constants.js          cuisines, meal types, diets, 14 UK allergens, tools, presets, default profile
js/derive.js             works out diet tags, allergens, label warnings, ingredient count, nutrition
js/data.js               loads ingredients + all recipe batches, runs derive.js on each
js/db.js                 IndexedDB storage (profile, stock, shopping; own recipes later)
js/ui.js                 HTML escaping, quantity and time formatting
js/views/*.js            one file per screen
data/ingredients.json    master ingredient list
data/recipes/index.json  list of recipe batch files to load
data/recipes/batch-01.json  the first 40 recipes
icons/                   app icons (made by tools/make_icons.py)
tools/validate.py        checks all recipe data (see below)
tools/validate.html      the check itself (runs the app's own derive.js)
tools/make_icons.py      redraws the icons (needs Pillow)
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
allowed but flagged ("Contains coconut") until someone decides on it.

### Adding a batch of recipes

1. Write `data/recipes/batch-02.json` (a JSON array of recipes). Add any new
   ingredients to `data/ingredients.json`.
2. Add `"batch-02.json"` to `data/recipes/index.json`.
3. Run `python tools/validate.py` and fix anything it reports.
4. Bump `CACHE` in `sw.js`.

Recipe ids must be unique across all batches. All recipes must be original:
don't copy them from websites or books.

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

## Kitchen stock and shopping list

Added in phases 2 and 4. All of it is saved on the phone (IndexedDB stores
`stock`, `shopping` and `meta`/`staples`; every record has `id` + `updatedAt`).

- **Stock tab**: have it / don't have it, no quantities. Search to add (name,
  synonyms, small typos are fine) or tap a quick-add button. Your own items
  can be added too, but they aren't used to match recipes. Each item can be
  marked **Low** and given an optional use-by date. Anything due within 3 days
  shows in **Use it up**. Swipe left (or tap ✕) to remove, with Undo.
  **Staples** (salt, pepper, oil, water by default) always count as in stock.
- **Shopping tab**: grouped by supermarket aisle. The same food from several
  recipes is combined into one line (amounts added up, converted between
  units where the ingredient list gives weights). Running-low stock is
  suggested at the top. Tick items as you shop. **Done shopping** puts the
  ticked foods into stock (clearing their Low mark) and removes them from
  the list. Share sends the list as text.
- **Recipe page**: each ingredient shows Have / Low / Need (tap to change your
  stock), plus **Add missing to shopping list** and **Add all ingredients**,
  scaled to the chosen servings and labelled with the recipe name.
- Matching is on exact ingredient ids only, so wheat pasta never counts as
  gluten-free pasta. Similar-item matching (phase 3) must keep that rule.

Files: `js/kitchen.js` (data and logic), `js/stock-data.js` (storage places,
aisle order, default staples, quick-add list), `js/views/stock.js`,
`js/views/shopping.js`, `js/views/recipe-kitchen.js` (recipe page block),
`js/views/food-search.js`, `js/views/kitchen-ui.js` (Undo toast, swipe),
`css/kitchen.css`. Run `tools/kitchen-test.html` in a browser (served
locally) to exercise the stock and shopping flows.
