# Lauren's Meal Planner: plan

A phone app that knows what food is in the house and which kitchen tools you
own, and suggests meals you can cook now (or nearly can). It also keeps the
shopping list and a full recipe book.

## Platform

**An installable web app (PWA)**, the same approach as the OOW Oral Trainer:
- One version works on **iPhone** (Safari, then "Add to Home Screen") and
  **Android** (Chrome, then "Install app"), and it opens full-screen like a
  normal app.
- It works **offline**, since phones often lose signal in supermarkets.
- No App Store or Play Store needed. It's free to host on GitHub Pages, and
  updates arrive on their own.
- Your data (profile, stock, lists) is saved on the phone (IndexedDB). The
  recipe catalogue comes with the app.

## Features

### 1. Profile
- **Diet**: vegetarian, vegan, pescatarian, gluten-free, dairy-free,
  low-carb, halal and others. Recipes that don't fit are hidden everywhere.
- **Allergies**: the 14 UK allergens (nuts, peanuts, milk, egg, fish,
  shellfish, sesame, soy, celery, mustard, lupin, molluscs, sulphites,
  cereals containing gluten). These are strict filters.
- **Dislikes**: individual ingredients to avoid (e.g. mushrooms, coriander).
- **Kitchen tools** you own: oven, hob, microwave, air fryer, slow cooker,
  pressure cooker / Instant Pot, food processor, blender, stick blender,
  stand mixer, grill, BBQ, wok, griddle pan, steamer, and others. Recipes
  that need a tool you don't have are hidden, or shown with a warning.
- **Household size**: recipes scale their portions to it by default.
- **Calorie goal per meal** (optional): sets the default for the finder.

### 2. Kitchen stock (pantry)
- **Have it / don't have it**, with no quantities to keep up. Add food by
  typing (e.g. "chick..." → chickpeas) or with quick-add buttons for common
  items.
- **"Running low" warning**: any item can be marked low. A low item still
  counts as "have it" for recipes, but it's flagged on the recipe ("you're
  low on rice") and suggested for the shopping list. The app can also guess
  "probably low" (e.g. after cooking 2 recipes that used it). A guess is
  only a suggestion: one tap clears it or turns it into a real "low" mark,
  because guesses will often be wrong.
- Optional **expiry date** on fresh items.
- Grouped as Fridge, Freezer, Cupboard, Fruit & veg, Spices.
- **Staples**: tick the things you always have (salt, pepper, oil, water),
  so they never count as "missing".
- **Delete stock**: swipe or tap to remove an item.
- **Use it up**: items close to expiry are highlighted, and the finder can
  favour recipes that use them.
- **"I cooked this"**: shows that recipe's ingredients, so you can tap the
  ones that are now used up (removed) or running low.

### 3. Meal finder (the main screen)
**"What do you fancy?"** The screen starts with a big, tappable **cuisine**
picker, so Lauren can choose by mood. You can pick one or several:
- Chinese, Italian, Mexican, Indian, Thai, Japanese, Korean, Vietnamese,
  Middle Eastern, Greek, Spanish, French, Turkish, Caribbean,
  North African, American, British, "Anything".

Then narrow down with any of these:
- Time (e.g. under 15 / 30 / 45 / 60 min)
- Calories per portion (range)
- Meal type (breakfast, lunch, dinner, snack, dessert)
- Difficulty, number of ingredients, one-pot only, a specific tool
  (e.g. "air fryer meals")
- Include an ingredient (e.g. "something with the chicken")

Results come in three groups:
1. **Cook now**: you have everything.
2. **Missing 1–2 ingredients**: each one shows what's missing, with a button
   to add those items to the shopping list.
3. **Ideas**: everything else that matches the filters, sorted by how much
   you already have.

Results are sorted by best match (most ingredients in stock, then items that
use up food close to expiry). Recipes that rely on a "running low" item show
a small warning. There's a "surprise me" button for a random pick.

### 4. Shopping list
- Add items by hand, from a recipe's missing ingredients, or with
  "add all ingredients for this recipe".
- **Running low** items are suggested at the top ("You're low on: rice,
  olive oil. Add?").
- The same item from several recipes is combined (e.g. 2 onions + 1 onion =
  3 onions).
- Sorted by **supermarket aisle** (fruit & veg, meat & fish, dairy,
  bakery, tins & dry goods, frozen, household).
- Tick items off as you shop. **"Done shopping"** moves the ticked items
  into kitchen stock and clears their "low" marks.

### 5. Recipe book
- Browse by cuisine, meal type, diet, tool, or collection.
- Search by name or ingredient.
- **Favourites**, star ratings, private notes ("add more chilli"), and a
  "last cooked" date.
- **Collections**, e.g. "Weeknight", "Batch cook", "Date night".
- **Add your own recipes** with the same details as the built-in ones.
- **Save recipes found online** (e.g. BBC Good Food) into your own book:
  paste the recipe in, and the app sorts it into ingredients and steps for
  you to check. "Save from a link" will be tried too: many recipe sites
  include machine-readable recipe data, but browsers block one site from
  reading another directly, so this needs working out. Saved recipes stay on
  your phone only and are never published with the app.
- **Recipe page**: photo, the details below, ingredients (each ticked if in
  stock), numbered steps, servings that scale up or down, and a **cooking
  mode** that keeps the screen awake and shows one step at a time in large
  text.

### 6. Weekly planner (later phase)
- Drag recipes onto days of the week.
- "Shop for this week" builds one shopping list from the plan, minus what's
  already in stock.

## Recipe details

Each recipe stores:

| Detail | Example |
|---|---|
| Name, short description, photo | "Chickpea & spinach curry" |
| Ingredients (each with quantity, unit, optional/required) | 400 g chickpeas, 1 onion … |
| Number of ingredients (worked out, not counting staples) | 8 |
| Prep time / cook time / total time | 10 / 25 / 35 min |
| Kitchen tools needed | hob, stick blender |
| Calories per portion | 420 kcal |
| Protein / carbs / fat / fibre per portion | 15 g / 52 g / 14 g / 11 g |
| Servings | 4 |
| Cuisine | Indian |
| Meal type | dinner |
| Diet tags (worked out from ingredients) | vegan, gluten-free |
| Allergens (worked out from ingredients) | mustard |
| Difficulty | easy |
| Spice level | 2 / 3 |
| Cost estimate | £ (cheap) / ££ / £££ |
| One-pot, batch-cook, freezer-friendly, good for leftovers / lunchbox | yes / yes / yes / yes |
| Season | all year |
| Steps | numbered method |
| Tags | "comfort food", "quick" |

Diet tags, allergens and the ingredient count are **worked out from the
ingredients** rather than typed in. That keeps them accurate, so a recipe
can never say "vegan" while containing honey.

## How it works

- **Ingredient list**: one master list of foods (e.g. "chickpeas (tinned)"),
  each recording its diet facts (vegan? contains gluten?), allergens,
  supermarket aisle, where it's stored, and nutrition per 100 g. Recipes,
  stock and the shopping list all use this list, which is what makes
  "what can I cook?" matching reliable.
- **Similar items**: e.g. "any pasta" is met by spaghetti or penne, and
  "cheddar" by "cheese". This avoids "missing ingredient" results that
  aren't really missing.
- **Calories**: worked out from the ingredient list's nutrition figures,
  using the UK's public nutrition data (CoFID) or USDA FoodData Central, so
  your own recipes get calories automatically.
- **Units**: metric, UK-style (g, ml, tsp, tbsp, "1 onion"). Recipes keep
  quantities (for cooking and the shopping list), but stock doesn't.
- **One phone for now**: everything is saved on that phone only. The data
  is kept so that sharing between phones can be added later without
  starting again.

## Build phases

1. **Foundations**: app shell (installable, offline), ingredient list,
   starter recipe catalogue, recipe book (browse, search, recipe page),
   profile (diet, allergies, tools).
2. **Kitchen stock**: add and delete stock, "running low" marks, staples,
   expiry dates.
3. **Meal finder**: filters, the cook now / missing 1–2 / ideas groups.
4. **Shopping list**: add from recipes, combined items, aisles,
   "done shopping" → stock.
5. **Extras**: own recipes, saving recipes found online, favourites,
   collections, cooking mode, "I cooked this".
6. **Later**: weekly planner, sharing stock and the list between two
   phones, backup and restore.

## Decisions

- **Recipes**: an original starter catalogue (growing to about 150–200 recipes with
  full details, spread across all the cuisines), plus Lauren's own recipes
  and ones she saves from sites like BBC Good Food. Saved recipes stay on
  her phone only; the app is published on a public website, so it can't
  include copied recipes.
- **One phone for now**: no accounts and no online database. Sharing
  between phones may come later.
- **Stock**: have it / don't have it, plus a "running low" mark that can
  always be changed by hand.
- **Lauren's diet comes first**: she has coeliac disease and a peanut
  allergy, and avoids all nuts. At least three-quarters of the catalogue is
  gluten-free and nut-free (38 of the first 40).
  - Gluten is strict: no wheat, barley, rye, spelt, malt, couscous, ordinary
    soy sauce or ordinary oats. Gluten-free versions are separate
    ingredients (tamari, GF pasta, GF stock, GF oats).
  - Ingredients that vary by brand or are often contaminated (stock, sauces,
    spice blends, tortillas, oats) show "check labels". With "Strict
    (coeliac)" on, this becomes a warning banner.
  - Nut-free excludes peanuts, all tree nuts and pine nuts. **Coconut is
    allowed.**
  - The Profile has a one-tap "Coeliac + nut-free" preset.
  - When "similar items" matching is built (phase 3), wheat pasta must never
    count as gluten-free pasta, nor soy sauce as tamari.
- **Catalogue size**: grows in batches (`data/recipes/batch-NN.json`) to
  about 150–200 original recipes.

## Open questions

1. **Photos.** Built-in recipes could have no photos, simple illustrations,
   or free stock photos. Your own recipes can use a photo from the phone's
   camera.
2. **Calorie accuracy.** Worked-out estimates are fine for planning, but they
   aren't exact.
