// Kitchen stock on the recipe page: marks each ingredient as in stock,
// running low or missing; a tap toggles it in or out of stock; buttons add
// the missing (or all) ingredients to the shopping list, scaled to the
// chosen servings. Matching uses js/match.js (shared with the meal finder):
// exact ids, plus safe similar items ("using: gluten-free pasta").

import { $, $$, esc } from "../ui.js";
import * as k from "../kitchen.js";
import { matchLine } from "../match.js";
import { undoToast } from "./kitchen-ui.js";

const LABEL = { in: "✓ Have", low: "Low", missing: "Need" };

export function mountRecipeKitchen({ app, view, recipe, getServings }) {
  const { ingById } = app.catalogue;
  const list = $("#ings", view);
  if (!list) return;
  const actions = document.createElement("div");
  actions.className = "kitchen-actions";
  list.after(actions);

  const lines = recipe.ingredients;
  let idx = k.stockIndex();
  const matchOf = (l) => matchLine(l, idx, ingById, app.profile);
  // "staple" counts as in stock; needed() leaves staples out of the buttons.
  const statusOf = (l) => { const s = matchOf(l).status; return s === "staple" ? "in" : s; };
  const needed = (l) => !l.optional && ingById[l.id] && matchOf(l).status !== "staple";

  function decorate() {
    idx = k.stockIndex();
    $$(":scope > li", list).forEach((li, n) => {
      const l = lines[n];
      if (!l || !ingById[l.id]) return;
      const m = matchOf(l);
      const st = statusOf(l);
      li.classList.remove("st-in", "st-low", "st-missing");
      li.classList.add(`st-${st}`, "tappable");
      li.dataset.ing = l.id;
      li.tabIndex = 0;
      li.setAttribute("role", "button");
      const staple = m.status === "staple";
      const sub = m.using && m.using !== l.id ? ingById[m.using] : null;
      let using = li.querySelector(".ing-using");
      if (sub) {
        if (!using) { using = document.createElement("span"); using.className = "ing-using"; li.children[1]?.append(using); }
        using.textContent = `using: ${sub.name.toLowerCase()}`;
      } else if (using) using.outerHTML = "";
      li.setAttribute("aria-label", `${ingById[l.id].name}: ${staple ? "staple, always in stock" : sub ? `in stock as ${sub.name}` : st === "in" ? "in stock" : st === "low" ? "in stock, running low" : "not in stock"}. Tap to ${st === "missing" ? "add to" : "remove from"} stock.`);
      let pill = li.querySelector(".ing-st");
      if (!pill) { pill = document.createElement("span"); pill.className = "ing-st"; li.append(pill); }
      pill.textContent = staple ? "Staple" : LABEL[st];
    });
    drawActions();
  }

  function drawActions() {
    const missing = lines.filter((l) => needed(l) && statusOf(l) === "missing");
    const low = lines.filter((l) => needed(l) && statusOf(l) === "low");
    const all = lines.filter(needed);
    actions.innerHTML = `
      ${low.length ? `<p class="small low-note">Running low: ${esc(low.map((l) => ingById[l.id].name).join(", "))}</p>` : ""}
      ${missing.length
        ? `<button type="button" class="btn block" data-addmissing>🛒 Add missing to shopping list (${missing.length})</button>`
        : `<p class="have-all">✓ You have everything for this recipe</p>`}
      <button type="button" class="btn secondary block" data-addall>Add all ingredients (${all.length})</button>
      <p class="small muted">Tap an ingredient to mark it in or out of your stock.</p>`;
  }

  async function addLines(chosen) {
    const scale = getServings() / recipe.servings;
    const before = chosen.map((l) => [l.id, k.shoppingList().find((r) => r.id === l.id) || null]);
    for (const l of chosen) {
      await k.addToShopping(l.id, { qty: l.qty == null ? null : l.qty * scale, unit: l.unit || null, recipe: recipe.name });
    }
    undoToast(`Added ${chosen.length} item${chosen.length === 1 ? "" : "s"} to your shopping list`, async () => {
      for (const [id, prev] of before) {
        if (prev) await k.restoreShopping(prev); else await k.removeShopping(id);
      }
      app.toast("Undone");
    });
  }

  async function toggle(li) {
    const id = li.dataset.ing;
    const name = ingById[id].name;
    if (k.isStaple(id)) { app.toast(`${name} is a staple, so it always counts as in stock`); return; }
    if (!k.stockItem(id)) {
      // Missing, or covered by a similar item: add this exact ingredient.
      await k.addStock(id);
      undoToast(`${name} added to stock`, async () => { await k.removeStock(id); decorate(); });
    } else {
      const rec = await k.removeStock(id);
      undoToast(`${name} removed from stock`, async () => { await k.restoreStock(rec); decorate(); });
    }
    decorate();
  }

  list.addEventListener("click", (e) => { const li = e.target.closest("li[data-ing]"); if (li) toggle(li); });
  list.addEventListener("keydown", (e) => {
    const li = e.target.closest("li[data-ing]");
    if (li && (e.key === "Enter" || e.key === " ")) { e.preventDefault(); toggle(li); }
  });
  actions.addEventListener("click", async (e) => {
    if (e.target.closest("[data-addmissing]")) await addLines(lines.filter((l) => needed(l) && statusOf(l) === "missing"));
    else if (e.target.closest("[data-addall]")) await addLines(lines.filter(needed));
  });

  // The recipe page redraws the list when servings change: re-mark it.
  new MutationObserver(decorate).observe(list, { childList: true });
  decorate();
}
