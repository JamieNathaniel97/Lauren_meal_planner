// Meal finder (Find tab), PLAN.md section 3.
//   1. "How long have you got?"  time buttons (single choice)
//   2. "What do you fancy?"      cuisine tiles (several, or Anything)
//   3. More filters               calories, meal, difficulty, ingredients, one-pot, tool, "use this"
//   4. Results in three groups:   Cook now / Missing 1–2 / Ideas
// The profile is always applied. Matching against stock is in js/match.js,
// shared with the recipe page so both say the same thing.

import { CUISINES, MEAL_TYPES, TOOLS, DIFFICULTY, DIET_BY_ID } from "../constants.js";
import { fitsProfile } from "../derive.js";
import { matchRecipe, groupOf, recipeUses } from "../match.js";
import * as k from "../kitchen.js";
import { card } from "./recipes.js";
import { undoToast } from "./kitchen-ui.js";
import { esc, $, $$ } from "../ui.js";

export const TIMES = [
  { id: "speedy", emoji: "⚡", label: "Speedy", hint: "15 min or less", test: (r) => r.d.totalMins <= 15 },
  { id: "quick", emoji: "🏃", label: "Quick", hint: "30 min or less", test: (r) => r.d.totalMins <= 30 },
  { id: "normal", emoji: "🍳", label: "Normal", hint: "45 min or less", test: (r) => r.d.totalMins <= 45 },
  { id: "long", emoji: "🕰️", label: "Take my time", hint: "over 45 min", test: (r) => r.d.totalMins > 45 },
  { id: "slow", emoji: "🐢", label: "Slow cook", hint: "leave it to cook", test: (r) => isSlowCook(r) },
];
const TIME_BY_ID = Object.fromEntries(TIMES.map((t) => [t.id, t]));

/** Long but mostly hands-off: slow cooker, or a long cook with little prep (oven braise). */
export function isSlowCook(r) {
  return r.tools.includes("slow-cooker") || ((r.cookMins || 0) >= 60 && (r.prepMins || 0) <= 20);
}

const KCAL = [
  { id: "lt400", label: "Under 400 kcal", test: (n) => n < 400 },
  { id: "400-600", label: "400–600 kcal", test: (n) => n >= 400 && n <= 600 },
  { id: "gt600", label: "Over 600 kcal", test: (n) => n > 600 },
];
const MAX_ING = [5, 8, 10, 12];
const PAGE = 30;
const GROUPS = [
  { id: "now", title: "Cook now", icon: "✅", blurb: "You have everything." },
  { id: "nearly", title: "Missing 1–2 ingredients", icon: "🛒", blurb: "Nearly there: add what's missing to your list." },
  { id: "ideas", title: "Ideas", icon: "💡", blurb: "Everything else that matches, most in stock first." },
];

const STORE_KEY = "mp-finder-v1";
const BLANK = { time: "", cuisines: [], kcal: "", meal: "", difficulty: "", maxIng: "", onePot: false, tool: "", use: "", more: false };

function loadFilters() {
  try { return { ...BLANK, ...JSON.parse(localStorage.getItem(STORE_KEY) || "{}") }; } catch { return { ...BLANK }; }
}
function saveFilters(f) {
  try { localStorage.setItem(STORE_KEY, JSON.stringify(f)); } catch { /* private mode: fine */ }
}

function options(list, selected, any) {
  return `<option value="">${any}</option>` + list.map((o) =>
    `<option value="${esc(o.id)}"${String(o.id) === String(selected) ? " selected" : ""}>${esc(o.label)}</option>`).join("");
}

function profileSummary(p) {
  const bits = [...(p.diets || []).map((d) => DIET_BY_ID[d]?.label.replace(/ \(.*\)/, "") || d)];
  if ((p.allergens || []).length && !(p.diets || []).length) bits.push(`${p.allergens.length} allerg${p.allergens.length > 1 ? "ies" : "y"}`);
  if ((p.dislikes || []).length) bits.push(`no ${p.dislikes.length} disliked food${p.dislikes.length > 1 ? "s" : ""}`);
  if (Array.isArray(p.tools)) bits.push("your kitchen tools");
  return bits;
}

export function renderFind({ app, view }) {
  app.setTitle("Find a meal");
  const { recipes, ingById } = app.catalogue;
  const profile = app.profile;
  const f = loadFilters();
  const shown = { now: PAGE, nearly: PAGE, ideas: PAGE };
  const added = new Set(); // recipes whose missing items were just added

  // The profile doesn't change on this screen: work out what fits once.
  const fitting = recipes.filter((r) => fitsProfile(r, r.d, profile, ingById).ok);
  const hiddenByProfile = recipes.length - fitting.length;
  const ownedTools = Array.isArray(profile.tools) ? new Set(profile.tools) : null;
  const tools = TOOLS.filter((t) => fitting.some((r) => r.tools.includes(t.id)) && (!ownedTools || ownedTools.has(t.id)));
  const usedCuisines = CUISINES.filter((c) => fitting.some((r) => r.cuisine === c.id));
  if (f.tool && !tools.some((t) => t.id === f.tool)) f.tool = "";
  f.cuisines = f.cuisines.filter((id) => usedCuisines.some((c) => c.id === id));
  const summary = profileSummary(profile);

  view.innerHTML = `
    <p class="small muted profile-note">${summary.length
      ? `Showing recipes for your profile (${esc(summary.join(", "))}). <a href="#/profile">Change</a>`
      : `<a href="#/profile">Set up your profile</a> to hide recipes that don't suit you.`}</p>

    <h2 class="find-h">How long have you got?</h2>
    <div class="times" role="group" aria-label="Cooking time" id="times">
      ${TIMES.map((t) => `<button type="button" class="time" data-time="${t.id}" aria-pressed="${f.time === t.id}">
        <span class="t-emoji" aria-hidden="true">${t.emoji}</span><b>${t.label}</b><small>${t.hint}</small></button>`).join("")}
      <button type="button" class="time any" data-time="" aria-pressed="${!f.time}"><span class="t-emoji" aria-hidden="true">⏱️</span><b>Any time</b><small>no limit</small></button>
    </div>

    <h2 class="find-h">What do you fancy?</h2>
    <p class="small muted pick-hint">Pick one or more.</p>
    <div class="cuisines picker" role="group" aria-label="Cuisines" id="cuisines"></div>

    <details class="more-filters panel" id="more"${f.more ? " open" : ""}>
      <summary>More filters <span class="small muted" id="moreCount"></span></summary>
      <div class="filters">
        <select id="kcal" aria-label="Calories">${options(KCAL, f.kcal, "Any calories")}</select>
        <select id="meal" aria-label="Meal">${options(MEAL_TYPES, f.meal, "Any meal")}</select>
        <select id="difficulty" aria-label="Difficulty">${options(Object.entries(DIFFICULTY).map(([id, label]) => ({ id, label })), f.difficulty, "Any difficulty")}</select>
        <select id="maxIng" aria-label="Number of ingredients">${options(MAX_ING.map((n) => ({ id: n, label: `${n} ingredients or fewer` })), f.maxIng, "Any no. of ingredients")}</select>
        <select id="tool" aria-label="Kitchen tool">${options(tools.map((t) => ({ id: t.id, label: `${t.label} meals` })), f.tool, "Any kitchen tool")}</select>
        <select id="use" aria-label="Use this ingredient"></select>
      </div>
      <label class="toggle"><input type="checkbox" id="onePot"${f.onePot ? " checked" : ""}> One-pot meals only</label>
      <button type="button" class="btn secondary small-btn" id="reset">Clear all filters</button>
    </details>

    <div class="find-bar">
      <div class="count" id="count" aria-live="polite"></div>
      <button type="button" class="btn small-btn" id="surprise">🎲 Surprise me</button>
    </div>
    <div id="hint"></div>
    <div id="results"></div>`;

  const results = $("#results", view);

  // "Use this ingredient": foods in stock (from the ingredient list), expiring first.
  function drawUseOptions() {
    const items = k.stockList().filter((r) => r.ingId && ingById[r.ingId])
      .sort((a, b) => (a.expiry || "9").localeCompare(b.expiry || "9") || a.name.localeCompare(b.name));
    if (f.use && !items.some((r) => r.ingId === f.use)) f.use = "";
    $("#use", view).innerHTML = options(items.map((r) => ({ id: r.ingId, label: `Use: ${r.name}` })), f.use,
      items.length ? "Use any ingredient" : "Use an ingredient (add stock first)");
  }

  function passes(r, { skipCuisine = false } = {}) {
    if (f.time && !TIME_BY_ID[f.time]?.test(r)) return false;
    if (!skipCuisine && f.cuisines.length && !f.cuisines.includes(r.cuisine)) return false;
    if (f.kcal && !KCAL.find((x) => x.id === f.kcal)?.test(r.d.perPortion.kcal)) return false;
    if (f.meal && !r.mealTypes.includes(f.meal)) return false;
    if (f.difficulty && r.difficulty !== f.difficulty) return false;
    if (f.maxIng && r.d.ingredientCount > Number(f.maxIng)) return false;
    if (f.onePot && !r.onePot) return false;
    if (f.tool && !r.tools.includes(f.tool)) return false;
    if (f.use && !recipeUses(r, f.use, ingById)) return false;
    return true;
  }

  function drawCuisines() {
    const pool = fitting.filter((r) => passes(r, { skipCuisine: true }));
    const count = (id) => pool.filter((r) => r.cuisine === id).length;
    $("#cuisines", view).innerHTML = `
      <button type="button" class="cuisine any" data-cuisine="" aria-pressed="${!f.cuisines.length}"><span aria-hidden="true">🎲</span>Anything<small>${pool.length} recipe${pool.length === 1 ? "" : "s"}</small></button>
      ${usedCuisines.map((c) => {
        const n = count(c.id);
        return `<button type="button" class="cuisine${n ? "" : " none"}" style="--c:${c.color}" data-cuisine="${c.id}" aria-pressed="${f.cuisines.includes(c.id)}">
          <span aria-hidden="true">${c.emoji}</span>${esc(c.label)}<small>${n} recipe${n === 1 ? "" : "s"}</small></button>`;
      }).join("")}`;
  }

  let groups = { now: [], nearly: [], ideas: [] };

  function compute() {
    const idx = k.stockIndex();
    groups = { now: [], nearly: [], ideas: [] };
    for (const r of fitting) {
      if (!passes(r)) continue;
      const m = matchRecipe(r, idx, ingById, profile);
      groups[groupOf(m)].push({ r, m });
    }
    const sort = (a, b) => (b.m.pct - a.m.pct) || (b.m.usesUp.length - a.m.usesUp.length)
      || (a.r.d.totalMins - b.r.d.totalMins) || a.r.name.localeCompare(b.r.name);
    Object.values(groups).forEach((g) => g.sort(sort));
  }

  // Short names for tags: "Tamari (gluten-free soy sauce)" -> "tamari".
  const short = (id) => (ingById[id]?.name || id).replace(/\s*\(.*\)/, "").toLowerCase();
  const names = (ids) => ids.map(short);

  function item({ r, m }, group) {
    const tags = [];
    if (m.needed) tags.push(`<span class="frac${m.pct === 1 ? " full" : ""}">${m.have} of ${m.needed} in stock</span>`);
    if (m.usesUp.length) tags.push(`<span class="tag-use">Uses up ${esc(names(m.usesUp).join(", "))}</span>`);
    if (m.low.length) tags.push(`<span class="tag-low">⚠ Low on ${esc(names(m.low).join(", "))}</span>`);
    const extra = tags.length ? `<div class="fx">${tags.join("")}</div>` : "";
    const html = card(r).replace(/<\/a>\s*$/, `${extra}</a>`);
    let miss = "";
    if (group === "nearly") {
      const list = m.missing.map((l) => short(l.id)).join(", ");
      miss = `<div class="fmiss"><span>Need: <b>${esc(list)}</b></span>${added.has(r.id)
        ? `<span class="on-list">✓ On your list</span>`
        : `<button type="button" class="btn small-btn" data-add="${esc(r.id)}">+ Add ${m.missing.length} to list</button>`}</div>`;
    }
    return `<div class="fitem">${html}${miss}</div>`;
  }

  function drawResults() {
    const total = groups.now.length + groups.nearly.length + groups.ideas.length;
    $("#count", view).textContent = `${total} recipe${total === 1 ? "" : "s"} match` +
      (groups.now.length ? ` · ${groups.now.length} to cook now` : "") +
      (hiddenByProfile && summary.length ? ` · ${hiddenByProfile} hidden by your profile` : "");
    $("#surprise", view).disabled = total === 0;
    const stockEmpty = !k.stockList().some((r) => r.ingId);
    $("#hint", view).innerHTML = stockEmpty
      ? `<div class="banner"><strong>Tell the app what's in your kitchen</strong>Add food on the <a href="#/stock">Stock</a> tab to see what you can cook right now.</div>` : "";
    if (!total) {
      results.innerHTML = `<p class="empty">No recipes match. Try a different time or cuisine, or clear some filters.</p>`;
      return;
    }
    results.innerHTML = GROUPS.filter((g) => groups[g.id].length).map((g) => {
      const list = groups[g.id];
      const more = list.length - shown[g.id];
      return `<section class="fgroup g-${g.id}">
        <h2 class="group-h"><span aria-hidden="true">${g.icon}</span> ${g.title} <small class="muted">${list.length}</small></h2>
        <p class="small muted gblurb">${g.blurb}</p>
        <div class="grid">${list.slice(0, shown[g.id]).map((x) => item(x, g.id)).join("")}</div>
        ${more > 0 ? `<button type="button" class="btn secondary block more-btn" data-more="${g.id}">Show ${Math.min(more, PAGE)} more (${more} left)</button>` : ""}
      </section>`;
    }).join("");
  }

  function drawMoreCount() {
    const n = ["kcal", "meal", "difficulty", "maxIng", "tool", "use"].filter((x) => f[x]).length + (f.onePot ? 1 : 0);
    $("#moreCount", view).textContent = n ? `(${n} on)` : "";
  }

  let timer = null;
  function update({ now = false } = {}) {
    saveFilters(f);
    clearTimeout(timer);
    const run = () => {
      shown.now = shown.nearly = shown.ideas = PAGE;
      drawCuisines(); drawMoreCount(); compute(); drawResults();
    };
    if (now) run(); else timer = setTimeout(run, 60);
  }

  // ---- events
  $("#times", view).addEventListener("click", (e) => {
    const b = e.target.closest("[data-time]");
    if (!b) return;
    f.time = f.time === b.dataset.time ? "" : b.dataset.time;
    $$("[data-time]", view).forEach((x) => x.setAttribute("aria-pressed", x.dataset.time === f.time));
    update();
  });
  $("#cuisines", view).addEventListener("click", (e) => {
    const b = e.target.closest("[data-cuisine]");
    if (!b) return;
    const id = b.dataset.cuisine;
    if (!id) f.cuisines = [];
    else f.cuisines = f.cuisines.includes(id) ? f.cuisines.filter((x) => x !== id) : [...f.cuisines, id];
    update();
  });
  for (const key of ["kcal", "meal", "difficulty", "maxIng", "tool", "use"]) {
    $(`#${key}`, view).addEventListener("change", (e) => { f[key] = e.target.value; update(); });
  }
  $("#onePot", view).addEventListener("change", (e) => { f.onePot = e.target.checked; update(); });
  $("#more", view).addEventListener("toggle", (e) => { f.more = e.target.open; saveFilters(f); });
  $("#reset", view).addEventListener("click", () => {
    Object.assign(f, { ...BLANK, more: true });
    saveFilters(f);
    renderFind({ app, view });
  });
  $("#surprise", view).addEventListener("click", () => {
    const pool = groups.now.length ? groups.now : groups.nearly.length ? groups.nearly : groups.ideas;
    if (!pool.length) return;
    const pick = pool[Math.floor(Math.random() * pool.length)].r;
    app.go(`#/recipe/${encodeURIComponent(pick.id)}`);
  });
  results.addEventListener("click", async (e) => {
    const more = e.target.closest("[data-more]");
    if (more) { shown[more.dataset.more] += PAGE; drawResults(); return; }
    const add = e.target.closest("[data-add]");
    if (!add) return;
    const entry = groups.nearly.find((x) => x.r.id === add.dataset.add);
    if (!entry) return;
    const { r, m } = entry;
    const scale = (profile.household > 0 ? profile.household : r.servings) / r.servings;
    const before = m.missing.map((l) => [l.id, k.shoppingList().find((s) => s.id === l.id) || null]);
    for (const l of m.missing) {
      await k.addToShopping(l.id, { qty: l.qty == null ? null : l.qty * scale, unit: l.unit || null, recipe: r.name });
    }
    added.add(r.id);
    drawResults();
    undoToast(`Added ${m.missing.length} item${m.missing.length === 1 ? "" : "s"} for ${r.name}`, async () => {
      for (const [id, prev] of before) {
        if (prev) await k.restoreShopping(prev); else await k.removeShopping(id);
      }
      added.delete(r.id);
      drawResults();
      app.toast("Undone");
    });
  });

  drawUseOptions();
  update({ now: true });
}
