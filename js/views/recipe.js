// One recipe: details, label warnings, scalable ingredients, steps.

import { CUISINE_BY_ID, DIET_BY_ID, ALLERGEN_BY_ID, TOOL_BY_ID, DIFFICULTY, COST } from "../constants.js";
import { fitsProfile, optionalClashes } from "../derive.js";
import { esc, $, formatQty, minutes } from "../ui.js";

const SPICE = ["Not spicy", "Mild", "Medium", "Hot"];

export function renderRecipe({ app, view, route }) {
  const { recipes, ingById } = app.catalogue;
  const r = recipes.find((x) => x.id === route.param);
  if (!r) {
    app.setTitle("Recipe", { back: true });
    view.innerHTML = `<p class="empty">That recipe wasn't found. <a href="#/recipes">Back to the recipe book</a></p>`;
    return;
  }
  app.setTitle(r.name, { back: true });
  const c = CUISINE_BY_ID[r.cuisine];
  const d = r.d;
  const profile = app.profile;
  const fit = fitsProfile(r, d, profile, ingById);
  const clashes = optionalClashes(r, profile, ingById);
  let servings = profile.household > 0 ? profile.household : r.servings;

  const dietBadges = d.diets
    // Halal isn't shown as a badge: "no pork or alcohol" doesn't make the meat halal.
    .filter((x) => x !== "halal"
      && !(x === "pescatarian" && d.diets.includes("vegetarian"))
      && !(x === "vegetarian" && d.diets.includes("vegan")))
    .map((x) => `<span class="badge">${esc(DIET_BY_ID[x].label.replace(/ \(.*\)/, ""))}</span>`).join("");

  const labelList = d.checkLabels.map((l) => `<li><b>${esc(l.name)}</b>${l.optional ? " (optional)" : ""}: ${esc(l.reason)}</li>`).join("");
  let labelBanner = "";
  if (d.checkLabels.length && profile.coeliac) {
    labelBanner = `<div class="banner danger" role="alert"><strong>⚠ Coeliac check: read these labels before cooking</strong>
      These ingredients often contain gluten or are cross-contaminated, depending on the brand. Only use ones labelled gluten-free.<ul>${labelList}</ul></div>`;
  } else if (d.checkLabels.length) {
    labelBanner = `<div class="banner"><strong>Check labels</strong>These can vary by brand:<ul>${labelList}</ul></div>`;
  }
  const fitBanner = fit.ok ? "" : `<div class="banner danger"><strong>Doesn't suit your profile</strong>${esc(fit.reasons.join(", "))}.</div>`;
  const clashBanner = clashes.length ? `<div class="banner">Leave out the optional ${esc(clashes.join(", "))}, as ${clashes.length > 1 ? "they don't" : "it doesn't"} suit your profile.</div>` : "";

  // Linked versions of this recipe, e.g. the gluten-free one and the original.
  const variantLinks = (r.variants || [])
    .filter((v) => recipes.some((x) => x.id === v.id))
    .map((v) => `<a class="variant-link" href="#/recipe/${encodeURIComponent(v.id)}">${esc(v.label)} →</a>`).join("");

  const allergenText = d.allergens.length ? d.allergens.map((a) => ALLERGEN_BY_ID[a]?.label || a).join(", ") : "None of the 14 major allergens";
  const optionalAllergenText = d.optionalAllergens.length ? ` (optional extras add: ${d.optionalAllergens.map((a) => ALLERGEN_BY_ID[a]?.label || a).join(", ")})` : "";
  const extras = [r.onePot && "One-pot", r.batchCook && "Batch cook", r.freezerFriendly && "Freezes well",
    r.goodForLeftovers && "Good leftovers", r.lunchbox && "Lunchbox"].filter(Boolean);

  view.innerHTML = `
    <section class="hero" style="--c:${c.color}">
      <div class="emoji" aria-hidden="true">${c.emoji}</div>
      <h2>${esc(r.name)}</h2>
      <p>${esc(r.description)}</p>
      <div class="badges">${dietBadges}</div>
    </section>
    ${variantLinks ? `<div class="variants">${variantLinks}</div>` : ""}
    ${fitBanner}${labelBanner}${clashBanner}
    <div class="facts">
      <div class="fact"><b>${minutes(d.totalMins)}</b><span>${r.prepMins} prep · ${r.cookMins} cook</span></div>
      <div class="fact"><b>≈${d.perPortion.kcal}</b><span>kcal per portion</span></div>
      <div class="fact"><b>${d.ingredientCount}</b><span>ingredients</span></div>
    </div>

    <div class="row"><h2>Ingredients</h2>
      <div class="stepper" aria-label="Servings">
        <button type="button" id="less" aria-label="Fewer servings">−</button>
        <output id="servings" aria-live="polite"></output>
        <button type="button" id="more" aria-label="More servings">+</button>
      </div>
    </div>
    <ul class="ingredients" id="ings"></ul>
    <p class="small muted">Salt, pepper, oil and water count as staples, so they aren't included in the ingredient count.</p>

    <h2>Method</h2>
    <ol class="steps">${r.steps.map((s) => `<li>${esc(s)}</li>`).join("")}</ol>

    <h2>Details</h2>
    <dl class="kv">
      <dt>Cuisine</dt><dd>${esc(c.label)}</dd>
      <dt>Meal</dt><dd>${r.mealTypes.map((m) => m[0].toUpperCase() + m.slice(1)).join(", ")}</dd>
      <dt>Kitchen tools</dt><dd>${r.tools.length ? r.tools.map((t) => TOOL_BY_ID[t]?.label || t).join(", ") : "None"}</dd>
      <dt>Difficulty</dt><dd>${DIFFICULTY[r.difficulty]}</dd>
      <dt>Spice</dt><dd>${SPICE[r.spice] || "–"}</dd>
      <dt>Cost</dt><dd>${COST[r.cost]}</dd>
      <dt>Season</dt><dd>${esc(r.season[0].toUpperCase() + r.season.slice(1))}</dd>
      ${extras.length ? `<dt>Good for</dt><dd>${extras.join(", ")}</dd>` : ""}
      <dt>Allergens</dt><dd>${esc(allergenText + optionalAllergenText)}</dd>
      ${d.containsCoconut ? `<dt>Coconut</dt><dd>Contains coconut</dd>` : ""}
      <dt>Per portion</dt><dd>≈${d.perPortion.kcal} kcal · ${d.perPortion.protein} g protein · ${d.perPortion.carbs} g carbs · ${d.perPortion.fat} g fat · ${d.perPortion.fibre} g fibre</dd>
    </dl>
    <p class="small muted">Nutrition is an estimate worked out from the ingredients (optional extras not included). Always check packaging for allergens.</p>`;

  function drawIngredients() {
    const scale = servings / r.servings;
    $("#servings", view).textContent = `${servings} serving${servings === 1 ? "" : "s"}`;
    $("#ings", view).innerHTML = r.ingredients.map((l) => {
      const ing = ingById[l.id];
      const qty = l.qty == null ? (ing?.staple ? "to taste" : "") : formatQty(l.qty * scale, l.unit);
      return `<li><span class="qty">${esc(qty)}</span><span>${esc(ing?.name || l.id)}${l.optional ? `<span class="opt">optional</span>` : ""}${l.note ? `<br><span class="note">${esc(l.note)}</span>` : ""}</span></li>`;
    }).join("");
  }
  $("#less", view).addEventListener("click", () => { if (servings > 1) { servings--; drawIngredients(); } });
  $("#more", view).addEventListener("click", () => { if (servings < 20) { servings++; drawIngredients(); } });
  drawIngredients();
}
