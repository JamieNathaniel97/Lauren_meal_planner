// Shopping list: grouped by supermarket aisle, duplicates combined, tick
// off as you shop, then "Done shopping" moves ticked foods into stock.

import { esc, $, formatQty } from "../ui.js";
import * as k from "../kitchen.js";
import { AISLES, AISLE_BY_ID, aisleOf } from "../stock-data.js";
import { mountFoodSearch } from "./food-search.js";
import { undoToast, enableSwipe } from "./kitchen-ui.js";

// Units you can only buy whole of: combined amounts are rounded up.
const WHOLE_UNITS = new Set(["each", "tin", "bunch", "block", "nest"]);

/** "3", "400 g", "2 tins + 1 tbsp" for a shopping item. */
export function amountText(item) {
  if (!item.ingId) return "";
  return k.combineParts(item.parts, item.ingId)
    .map(({ qty, unit }) => formatQty(WHOLE_UNITS.has(unit) ? Math.ceil(qty - 0.05) || 1 : qty, unit))
    .join(" + ");
}

export function renderShopping({ app, view }) {
  app.setTitle("Shopping list");
  const { ingredients, ingById } = app.catalogue;

  view.innerHTML = `
    <div class="screen">
      <div id="fs"></div>
      <div id="low"></div>
      <div id="body"></div>
    </div>`;
  const root = $(".screen", view);

  mountFoodSearch($("#fs", view), {
    placeholder: "Add to list, e.g. milk",
    ingredients,
    status: (i) => (k.onShoppingList(i.id) ? "On list ✓" : k.stockStatus(i.id) === "in" ? "In stock" : k.stockStatus(i.id) === "low" ? "Running low" : ""),
    onPick: async (i) => {
      const was = k.onShoppingList(i.id);
      const rec = await k.addToShopping(i.id);
      if (was) app.toast(`${i.name} is already on the list`);
      else undoToast(`Added ${i.name}`, async () => { await k.removeShopping(rec.id); draw(); });
      draw();
    },
    onCustom: async (text) => {
      const rec = await k.addFreeText(text);
      undoToast(`Added ${text}`, async () => { await k.removeShopping(rec.id); draw(); });
      draw();
    },
    customLabel: (text) => `Add “${text}” to the list`,
  });

  function drawLow() {
    const low = k.lowNotOnList().sort((a, b) => a.name.localeCompare(b.name));
    $("#low", view).innerHTML = low.length ? `
      <section class="lowbox" aria-label="Running low">
        <div class="row"><b>You're running low on:</b>${low.length > 1 ? `<button type="button" class="btn small-btn" data-addlow="all">Add all</button>` : ""}</div>
        <div class="taglist">${low.map((r) => `<button type="button" class="chip" data-addlow="${esc(r.id)}">+ ${esc(r.name)}</button>`).join("")}</div>
      </section>` : "";
  }

  function itemRow(r) {
    const amount = amountText(r);
    const recipes = k.recipesFor(r);
    return `
      <li class="shrow${r.ticked ? " ticked" : ""}" data-id="${esc(r.id)}">
        <div class="swipe-bg" aria-hidden="true">Delete</div>
        <div class="swipe-inner">
          <button type="button" class="tick" data-tick role="checkbox" aria-checked="${!!r.ticked}">
            <span class="box" aria-hidden="true">${r.ticked ? "✓" : ""}</span>
            <span class="shname"><b>${esc(r.name)}</b>${amount ? ` <span class="amt">${esc(amount)}</span>` : ""}
              ${recipes.length ? `<small class="for">For: ${esc(recipes.join(", "))}</small>` : ""}</span>
          </button>
          <button type="button" class="del" data-del aria-label="Remove ${esc(r.name)}">✕</button>
        </div>
      </li>`;
  }

  function drawBody() {
    const body = $("#body", view);
    const items = k.shoppingList();
    const ticked = items.filter((r) => r.ticked).length;
    if (!items.length) {
      body.innerHTML = `<div class="empty"><div style="font-size:2.4rem">🛒</div>Your list is empty.<br>Add items above, or use “Add missing to shopping list” on a recipe.</div>`;
      return;
    }
    const known = AISLES.map((a) => a.id);
    const extra = [...new Set(items.map((r) => r.aisle || "other"))].filter((a) => !AISLE_BY_ID[a]);
    const order = [...known.slice(0, -1), ...extra, "other"];
    let html = `<p class="count">${items.length} item${items.length === 1 ? "" : "s"}${ticked ? ` · ${ticked} in the trolley` : ""}</p>`;
    for (const aisle of order) {
      const group = items.filter((r) => (r.aisle || "other") === aisle)
        .sort((a, b) => (a.ticked - b.ticked) || a.name.localeCompare(b.name));
      if (!group.length) continue;
      const a = aisleOf(aisle);
      html += `<h3 class="group-h">${a.emoji} ${esc(a.label)}</h3><ul class="shlist">${group.map(itemRow).join("")}</ul>`;
    }
    html += `
      <div class="shop-actions">
        <button type="button" class="btn block" data-done ${ticked ? "" : "disabled"}>Done shopping${ticked ? ` (${ticked})` : ""}</button>
        <p class="small muted center">Ticked foods are added to your kitchen stock.</p>
        <div class="row">
          <button type="button" class="btn secondary" data-share>Share list</button>
          <button type="button" class="btn secondary danger-text" data-clear>Clear list</button>
        </div>
      </div>`;
    body.innerHTML = html;
  }

  function draw() { drawLow(); drawBody(); }

  function listText() {
    const items = k.shoppingList().filter((r) => !r.ticked);
    const lines = ["Shopping list"];
    for (const a of new Set([...AISLES.map((x) => x.id), ...items.map((r) => r.aisle || "other")])) {
      const group = items.filter((r) => (r.aisle || "other") === a);
      if (!group.length) continue;
      lines.push(`\n${aisleOf(a).label}`);
      group.sort((x, y) => x.name.localeCompare(y.name)).forEach((r) => {
        const amt = amountText(r);
        lines.push(`- ${r.name}${amt ? ` (${amt})` : ""}`);
      });
    }
    return lines.join("\n");
  }

  root.addEventListener("click", async (e) => {
    const t = e.target;
    const low = t.closest("[data-addlow]");
    if (low) {
      const list = low.dataset.addlow === "all" ? k.lowNotOnList() : [k.stockItem(low.dataset.addlow)].filter(Boolean);
      for (const r of list) await k.addLowToShopping(r);
      app.toast(list.length === 1 ? `Added ${list[0].name}` : `Added ${list.length} items`);
      return draw();
    }
    if (t.closest("[data-done]")) {
      const res = await k.doneShopping();
      const bits = [];
      if (res.added) bits.push(`${res.added} added to stock`);
      if (res.restocked) bits.push(`${res.restocked} restocked`);
      if (res.removed) bits.push(`${res.removed} other item${res.removed === 1 ? "" : "s"} cleared`);
      app.toast(bits.length ? `Done! ${bits.join(", ")}.` : "Done!");
      return draw();
    }
    if (t.closest("[data-clear]")) {
      if (!confirm("Clear the whole shopping list?")) return;
      await k.clearShopping();
      app.toast("List cleared");
      return draw();
    }
    if (t.closest("[data-share]")) {
      const text = listText();
      try {
        if (navigator.share) await navigator.share({ title: "Shopping list", text });
        else { await navigator.clipboard.writeText(text); app.toast("List copied"); }
      } catch (err) {
        if (err?.name !== "AbortError") {
          try { await navigator.clipboard.writeText(text); app.toast("List copied"); } catch { app.toast("Couldn't share the list"); }
        }
      }
      return;
    }
    const row = t.closest(".shrow");
    if (!row) return;
    if (t.closest("[data-del]")) return deleteRow(row.dataset.id);
    if (t.closest("[data-tick]")) { await k.toggleTicked(row.dataset.id); drawBody(); }
  });
  enableSwipe(root, ".shrow", (row) => deleteRow(row.dataset.id));

  async function deleteRow(id) {
    const rec = await k.removeShopping(id);
    if (!rec) return;
    undoToast(`Removed ${rec.name}`, async () => { await k.restoreShopping(rec); draw(); });
    draw();
  }

  draw();
}
