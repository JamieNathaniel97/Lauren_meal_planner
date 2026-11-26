# Recipe data licence and credits

## Imported recipes

These files contain recipes adapted from openly licensed collections:

- `data/recipes/unitools-*.json` and `data/steps/unitools-*.json`:
  adapted from **UniTools World Recipes** by UniTools — theunitools.com
  (https://theunitools.com/en/data), licensed CC BY-SA 4.0.
- `data/recipes/fork-*.json` and `data/steps/fork-*.json`: adapted from the
  **ForkRecipe open recipe dataset**, © 2026 FoodML and the ForkRecipe
  contributors (https://github.com/futurechef/forkrecipe-recipes), licensed
  CC BY-SA 4.0. "ForkRecipe" and "FoodML" are trademarks of FoodML; this app
  is not ForkRecipe and is not endorsed by FoodML.

**Changes made:** ingredients were matched to this app's ingredient list and
renamed; amounts were converted (ForkRecipe ratios were scaled to real
quantities); serving counts were adjusted in some recipes; kitchen tools,
spice level, cost and meal type were worked out; and gluten-free and
nut-free versions (recipe ids ending `-gf`, `-nf` or `-gfnf`) were created
by ingredient swaps with matching changes to the method text. Diet tags,
allergens and nutrition are calculated by the app, not taken from the
sources.

These adapted recipes, and the matching entries in `data/ingredients.json`,
are shared under the same licence: **Creative Commons
Attribution-ShareAlike 4.0 International**
(https://creativecommons.org/licenses/by-sa/4.0/).

## Photos

Recipe photos are linked from UniTools, which takes them from Wikimedia
Commons. Each photo's author and licence are stored with the recipe (`photo`
field) and shown on its recipe page. Photos without a stated open licence
were left out.

## Our own recipes

`data/recipes/batch-*.json` were written for this app.
