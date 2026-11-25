// Profile: diet, allergens, coeliac strictness, dislikes, tools, household.
// Starts empty; "Coeliac + nut-free" sets Lauren's needs in one tap.

import { DIETS, ALLERGENS, TOOLS, COELIAC_NF_PRESET, DEFAULT_PROFILE } from "../constants.js";
import { esc, $, $$ } from "../ui.js";
import { isPersistent } from "../db.js";

const COMMON_TOOLS = ["hob", "oven", "microwave", "grill"];

export function renderProfile(ctx) {
  const { app, view } = ctx;
  app.setTitle("Profile");
  const p = app.profile;
  const { ingredients, ingById } = app.catalogue;
  const presetOn = COELIAC_NF_PRESET.diets.every((d) => p.diets.includes(d))
    && COELIAC_NF_PRESET.allergens.every((a) => p.allergens.includes(a)) && p.coeliac;
  const tools = Array.isArray(p.tools) ? p.tools : [];

  view.innerHTML = `
    <button class="preset" id="preset" aria-pressed="${presetOn}">
      <span class="emoji" aria-hidden="true">${presetOn ? "✅" : "🌾"}</span>
      <span><b>${presetOn ? "Coeliac + nut-free is on" : "Coeliac + nut-free"}</b>
      <span class="small muted">${presetOn ? "Tap to turn off." : "One tap: strict gluten-free, no peanuts and no tree nuts (including pine nuts)."}</span></span>
    </button>

    <h2>Diet</h2>
    <div class="panel checks">${DIETS.map((d) => `
      <label class="toggle"><input type="checkbox" data-diet="${d.id}"${p.diets.includes(d.id) ? " checked" : ""}> ${esc(d.label)}</label>`).join("")}
    </div>
    <div class="panel">
      <label class="toggle"><input type="checkbox" id="coeliac"${p.coeliac ? " checked" : ""}>
        <span><b>Strict (coeliac)</b><br><span class="small muted">Recipes with ingredients that are often cross-contaminated (stock, sauces, oats, spice blends) get a clear warning to check the labels.</span></span></label>
    </div>

    <h2>Allergies</h2>
    <p class="small muted" style="margin-top:-4px">Recipes containing these are hidden.</p>
    <div class="panel checks">${ALLERGENS.map((a) => `
      <label class="toggle"><input type="checkbox" data-allergen="${a.id}"${p.allergens.includes(a.id) ? " checked" : ""}> ${esc(a.label)}</label>`).join("")}
    </div>

    <h2>Foods you don't like</h2>
    <div class="panel">
      <div class="taglist" id="dislikes">${p.dislikes.map((id) => `
        <span class="tag">${esc(ingById[id]?.name || id)}<button data-remove="${id}" aria-label="Remove ${esc(ingById[id]?.name || id)}">✕</button></span>`).join("") || `<span class="small muted">None yet</span>`}
      </div>
      <input class="search" id="dislike" list="ing-list" placeholder="Add a food, e.g. mushrooms" autocomplete="off">
      <datalist id="ing-list">${ingredients.filter((i) => !i.staple).map((i) => `<option value="${esc(i.name)}">`).join("")}</datalist>
    </div>

    <h2>Kitchen tools</h2>
    <p class="small muted" style="margin-top:-4px">${Array.isArray(p.tools) ? "Recipes that need a tool you haven't ticked are hidden." : "Not set yet, so all recipes are shown. Tick what you have."}</p>
    <div class="panel checks">${TOOLS.map((t) => `
      <label class="toggle"><input type="checkbox" data-tool="${t.id}"${tools.includes(t.id) ? " checked" : ""}> ${esc(t.label)}</label>`).join("")}
    </div>
    ${Array.isArray(p.tools) ? `<button class="btn secondary block" id="tools-clear">Don't filter by tools</button>` : `<button class="btn secondary block" id="tools-basic">Start with hob, oven, microwave and grill</button>`}

    <h2>Household</h2>
    <div class="panel row" style="padding:10px 14px">
      <span>Portions to cook by default</span>
      <div class="stepper"><button id="hh-less" aria-label="Fewer">−</button><output id="hh">${p.household}</output><button id="hh-more" aria-label="More">+</button></div>
    </div>

    <h2>Reset</h2>
    <button class="btn secondary block" id="reset">Clear my profile</button>
    <p class="small muted">${isPersistent() ? "Saved on this phone only." : "This browser isn't allowing storage, so changes last until you close the app."}</p>`;

  const save = async (changes, msg) => {
    await app.saveProfile(changes);
    if (msg) app.toast(msg);
    renderProfile(ctx);
  };
  const toggleIn = (list, id, on) => (on ? [...new Set([...list, id])] : list.filter((x) => x !== id));

  $("#preset", view).addEventListener("click", () => {
    if (presetOn) {
      save({
        diets: p.diets.filter((d) => !COELIAC_NF_PRESET.diets.includes(d)),
        allergens: p.allergens.filter((a) => !COELIAC_NF_PRESET.allergens.includes(a)),
        coeliac: false,
      }, "Coeliac + nut-free turned off");
    } else {
      save({
        diets: [...new Set([...p.diets, ...COELIAC_NF_PRESET.diets])],
        allergens: [...new Set([...p.allergens, ...COELIAC_NF_PRESET.allergens])],
        coeliac: true,
      }, "Coeliac + nut-free is on");
    }
  });
  $$("[data-diet]", view).forEach((el) => el.addEventListener("change", () => {
    const changes = { diets: toggleIn(p.diets, el.dataset.diet, el.checked) };
    if (el.dataset.diet === "gluten-free" && !el.checked) changes.coeliac = false;
    save(changes);
  }));
  $("#coeliac", view).addEventListener("change", (e) => {
    const changes = { coeliac: e.target.checked };
    if (e.target.checked) {
      changes.diets = toggleIn(p.diets, "gluten-free", true);
      changes.allergens = toggleIn(p.allergens, "gluten", true);
    }
    save(changes);
  });
  $$("[data-allergen]", view).forEach((el) => el.addEventListener("change", () =>
    save({ allergens: toggleIn(p.allergens, el.dataset.allergen, el.checked) })));
  $$("[data-tool]", view).forEach((el) => el.addEventListener("change", () =>
    save({ tools: toggleIn(tools, el.dataset.tool, el.checked) })));
  $("#tools-clear", view)?.addEventListener("click", () => save({ tools: null }));
  $("#tools-basic", view)?.addEventListener("click", () => save({ tools: COMMON_TOOLS }));

  const dislike = $("#dislike", view);
  const addDislike = () => {
    const name = dislike.value.trim().toLowerCase();
    if (!name) return;
    const ing = ingredients.find((i) => i.name.toLowerCase() === name || (i.synonyms || []).includes(name));
    if (!ing) { app.toast("Pick a food from the list"); return; }
    save({ dislikes: toggleIn(p.dislikes, ing.id, true) });
  };
  dislike.addEventListener("change", addDislike);
  dislike.addEventListener("keydown", (e) => { if (e.key === "Enter") addDislike(); });
  $$("[data-remove]", view).forEach((b) => b.addEventListener("click", () =>
    save({ dislikes: p.dislikes.filter((x) => x !== b.dataset.remove) })));

  const setHousehold = (n) => save({ household: Math.min(12, Math.max(1, n)) });
  $("#hh-less", view).addEventListener("click", () => setHousehold(p.household - 1));
  $("#hh-more", view).addEventListener("click", () => setHousehold(p.household + 1));
  $("#reset", view).addEventListener("click", () => {
    if (confirm("Clear all profile settings?")) save({ ...DEFAULT_PROFILE }, "Profile cleared");
  });
}
