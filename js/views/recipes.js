// Recipe book: search, quick chips and filters, recipe cards.

import { CUISINES, CUISINE_BY_ID, MEAL_TYPES, DIETS, TOOLS } from "../constants.js";
import { fitsProfile } from "../derive.js";
import { esc, $, minutes } from "../ui.js";

// Remembered while the app is open, so going back keeps your filters.
const state = { q: "", cuisine: "", meal: "", diet: "", tool: "", gfnf: false, showAll: false, scrollY: 0 };

function searchText(r, ingById) {
  return [r.name, r.description, ...(r.tags || []), CUISINE_BY_ID[r.cuisine]?.label,
    ...r.ingredients.flatMap((l) => [ingById[l.id]?.name, ...(ingById[l.id]?.synonyms || [])])]
    .join(" ").toLowerCase();
}

export function card(r, { unfit = false } = {}) {
  const c = CUISINE_BY_ID[r.cuisine];
  const gf = r.d.diets.includes("gluten-free"), nf = r.d.diets.includes("nut-free");
  const badges = [];
  if (gf && nf) badges.push(`<span class="badge gfnf">GF · NF</span>`);
  else {
    if (gf) badges.push(`<span class="badge">GF</span>`);
    if (nf) badges.push(`<span class="badge">NF</span>`);
  }
  if (r.d.diets.includes("vegan")) badges.push(`<span class="badge">Vegan</span>`);
  else if (r.d.diets.includes("vegetarian")) badges.push(`<span class="badge">Veggie</span>`);
  return `
    <a class="card${unfit ? " unfit" : ""}" href="#/recipe/${encodeURIComponent(r.id)}">
      <div class="card-art" style="--c:${c.color}"><span aria-hidden="true">${c.emoji}</span><span class="cuisine-label">${esc(c.label)}</span></div>
      <div class="card-body">
        <div class="card-title">${esc(r.name)}</div>
        <div class="card-meta">${minutes(r.d.totalMins)} · ≈${r.d.perPortion.kcal} kcal</div>
        <div class="badges">${badges.join("")}</div>
      </div>
    </a>`;
}

function options(list, selected, any) {
  return `<option value="">${any}</option>` + list.map((o) =>
    `<option value="${o.id}"${o.id === selected ? " selected" : ""}>${esc(o.label)}</option>`).join("");
}

export function renderRecipes({ app, view, route }) {
  app.setTitle("Recipe book");
  if (route.query.has("cuisine")) state.cuisine = route.query.get("cuisine");
  const { recipes, ingById } = app.catalogue;
  const profileSet = app.profile.diets.length || app.profile.allergens.length || app.profile.dislikes.length || Array.isArray(app.profile.tools);
  const usedTools = TOOLS.filter((t) => recipes.some((r) => r.tools.includes(t.id)));

  view.innerHTML = `
    <input class="search" type="search" id="q" placeholder="Search recipes or ingredients" value="${esc(state.q)}" autocomplete="off">
    <div class="chips" role="group" aria-label="Quick filters">
      <button class="chip big" id="gfnf" aria-pressed="${state.gfnf}">✓ Gluten-free &amp; nut-free</button>
      ${MEAL_TYPES.map((m) => `<button class="chip" data-meal="${m.id}" aria-pressed="${state.meal === m.id}">${m.label}</button>`).join("")}
    </div>
    <div class="filters">
      <select id="cuisine" aria-label="Cuisine">${options(CUISINES, state.cuisine, "All cuisines")}</select>
      <select id="diet" aria-label="Diet">${options(DIETS.map((d) => ({ id: d.id, label: d.label.replace(/ \(.*\)/, "") })), state.diet, "Any diet")}</select>
      <select id="tool" aria-label="Kitchen tool">${options(usedTools, state.tool, "Any kitchen tool")}</select>
      <select id="meal" aria-label="Meal type">${options(MEAL_TYPES, state.meal, "Any meal")}</select>
    </div>
    ${profileSet ? `<label class="toggle small"><input type="checkbox" id="showAll"${state.showAll ? " checked" : ""}> Also show recipes that don't suit my profile</label>` : ""}
    <div class="count" id="count"></div>
    <div class="grid" id="list"></div>`;

  const list = $("#list", view), countEl = $("#count", view);
  const texts = new Map(recipes.map((r) => [r.id, searchText(r, ingById)]));

  function update() {
    const words = state.q.toLowerCase().split(/\s+/).filter(Boolean);
    let hidden = 0;
    const shown = [];
    for (const r of recipes) {
      if (state.cuisine && r.cuisine !== state.cuisine) continue;
      if (state.meal && !r.mealTypes.includes(state.meal)) continue;
      if (state.diet && !r.d.diets.includes(state.diet)) continue;
      if (state.tool && !r.tools.includes(state.tool)) continue;
      if (state.gfnf && !(r.d.diets.includes("gluten-free") && r.d.diets.includes("nut-free"))) continue;
      if (words.length && !words.every((w) => texts.get(r.id).includes(w))) continue;
      const fit = fitsProfile(r, r.d, app.profile, ingById).ok;
      if (!fit && !state.showAll) { hidden++; continue; }
      shown.push({ r, fit });
    }
    shown.sort((a, b) => (b.fit - a.fit) || a.r.name.localeCompare(b.r.name));
    list.innerHTML = shown.map(({ r, fit }) => card(r, { unfit: !fit })).join("")
      || `<p class="empty" style="grid-column:1/-1">No recipes match. Try removing a filter.</p>`;
    countEl.textContent = `${shown.length} recipe${shown.length === 1 ? "" : "s"}` +
      (hidden ? ` · ${hidden} hidden because they don't suit your profile` : "");
  }

  $("#q", view).addEventListener("input", (e) => { state.q = e.target.value; update(); });
  $("#gfnf", view).addEventListener("click", (e) => {
    state.gfnf = !state.gfnf;
    e.currentTarget.setAttribute("aria-pressed", state.gfnf);
    update();
  });
  view.querySelectorAll("[data-meal]").forEach((b) => b.addEventListener("click", () => {
    state.meal = state.meal === b.dataset.meal ? "" : b.dataset.meal;
    view.querySelectorAll("[data-meal]").forEach((x) => x.setAttribute("aria-pressed", x.dataset.meal === state.meal));
    $("#meal", view).value = state.meal;
    update();
  }));
  for (const key of ["cuisine", "diet", "tool", "meal"]) {
    $(`#${key}`, view).addEventListener("change", (e) => {
      state[key] = e.target.value;
      if (key === "meal") view.querySelectorAll("[data-meal]").forEach((x) => x.setAttribute("aria-pressed", x.dataset.meal === state.meal));
      if (key === "cuisine" && route.query.has("cuisine")) history.replaceState(null, "", "#/recipes");
      update();
    });
  }
  $("#showAll", view)?.addEventListener("change", (e) => { state.showAll = e.target.checked; update(); });
  list.addEventListener("click", () => { state.scrollY = window.scrollY; });

  update();
  window.scrollTo(0, state.scrollY);
  state.scrollY = 0;
}

