// Kitchen stock: what's in the house. Have it / don't have it, with a
// "running low" mark, optional expiry dates, staples, swipe to delete.

import { esc, $, $$ } from "../ui.js";
import * as k from "../kitchen.js";
import { STORAGE, STORAGE_BY_ID, AISLES, QUICK_ADD } from "../stock-data.js";
import { mountFoodSearch } from "./food-search.js";
import { undoToast, enableSwipe } from "./kitchen-ui.js";

export function renderStock({ app, view }) {
  app.setTitle("Kitchen stock");
  const { ingredients, ingById } = app.catalogue;
  let filter = "";
  let editing = null;      // id of the item whose details are open
  let staplesOpen = false;
  let customName = null;   // text waiting for the "own item" form

  view.innerHTML = `
    <div class="screen">
      <div id="fs"></div>
      <form class="panel custom-form" id="custom" hidden></form>
      <div class="chips" id="quick" aria-label="Quick add"></div>
      <div id="body"></div>
    </div>`;
  // Listeners go on this wrapper, which is replaced on every visit
  // (the #view element itself lives for the whole session).
  const root = $(".screen", view);

  mountFoodSearch($("#fs", view), {
    placeholder: "Find or add food, e.g. chickpeas",
    ingredients: ingredients.filter((i) => !k.isStaple(i.id)),
    status: (i) => (k.stockItem(i.id) ? (k.stockItem(i.id).low ? "In stock · low" : "In stock ✓") : ""),
    onInput: (text) => { filter = text; drawBody(); },
    onPick: (i) => add(i.id),
    onCustom: (text) => { customName = text; drawCustom(); },
  });

  async function add(ingId) {
    const had = k.stockItem(ingId);
    await k.addStock(ingId);
    const name = ingById[ingId].name;
    if (had) undoToast(had.low ? `${name}: low mark cleared` : `${name} is already in stock`, had.low ? async () => { await k.restoreStock(had); drawAll(); } : null);
    else undoToast(`Added ${name}`, async () => { await k.removeStock(ingId); drawAll(); });
    drawAll();
  }

  function drawCustom() {
    const form = $("#custom", view);
    if (!customName) { form.hidden = true; form.innerHTML = ""; return; }
    form.hidden = false;
    form.innerHTML = `
      <p><b>Add “${esc(customName)}”</b><br><span class="small muted">Your own items are kept in stock but aren't used to match recipes.</span></p>
      <div class="filters">
        <label class="small">Kept in<select name="storage">${STORAGE.map((s) => `<option value="${s.id}">${esc(s.label)}</option>`).join("")}</select></label>
        <label class="small">Shop aisle<select name="aisle">${AISLES.map((a) => `<option value="${a.id}"${a.id === "other" ? " selected" : ""}>${esc(a.label)}</option>`).join("")}</select></label>
      </div>
      <div class="row" style="justify-content:flex-end;padding-bottom:8px">
        <button type="button" class="btn secondary" data-cancel>Cancel</button>
        <button type="submit" class="btn">Add</button>
      </div>`;
    form.onsubmit = async (e) => {
      e.preventDefault();
      const name = customName;
      const rec = await k.addCustomStock(name, { storage: form.storage.value, aisle: form.aisle.value });
      customName = null;
      drawCustom();
      undoToast(`Added ${name}`, async () => { await k.removeStock(rec.id); drawAll(); });
      drawAll();
    };
    $("[data-cancel]", form).onclick = () => { customName = null; drawCustom(); };
    form.scrollIntoView({ block: "nearest" });
  }

  function drawQuick() {
    const quick = QUICK_ADD.filter((id) => ingById[id] && !k.stockItem(id) && !k.isStaple(id)).slice(0, 14);
    $("#quick", view).innerHTML = quick.map((id) => `<button type="button" class="chip" data-add="${id}">+ ${esc(ingById[id].name)}</button>`).join("");
    $("#quick", view).hidden = !quick.length;
  }

  function itemRow(r) {
    const soon = r.expiry ? k.daysUntil(r.expiry) : null;
    const expClass = soon == null ? "" : soon < 0 ? " expired" : soon <= 3 ? " soon" : "";
    const open = editing === r.id;
    return `
      <li class="srow${r.low ? " is-low" : ""}${expClass}" data-id="${esc(r.id)}">
        <div class="swipe-bg" aria-hidden="true">Delete</div>
        <div class="swipe-inner">
          <button type="button" class="sname" data-edit aria-expanded="${open}">
            <span>${esc(r.name)}${r.ingId ? "" : ` <small class="muted">(own item)</small>`}</span>
            ${r.expiry ? `<small class="exp">${esc(k.expiryText(r.expiry))}</small>` : ""}
          </button>
          <button type="button" class="lowbtn" data-low aria-pressed="${!!r.low}" title="Mark as running low">${r.low ? "Low" : "Low?"}</button>
          <button type="button" class="del" data-del aria-label="Remove ${esc(r.name)}">✕</button>
        </div>
        ${open ? `
        <div class="sedit">
          <label class="small">Use by
            <span class="row"><input type="date" data-exp value="${esc(r.expiry || "")}">
            ${r.expiry ? `<button type="button" class="btn secondary" data-noexp>Clear</button>` : ""}</span></label>
          <label class="small">Kept in
            <select data-storage>${STORAGE.map((s) => `<option value="${s.id}"${s.id === r.storage ? " selected" : ""}>${esc(s.label)}</option>`).join("")}</select></label>
          ${r.ingId ? "" : `<label class="small">Shop aisle
            <select data-aisle>${AISLES.map((a) => `<option value="${a.id}"${a.id === r.aisle ? " selected" : ""}>${esc(a.label)}</option>`).join("")}</select></label>`}
        </div>` : ""}
      </li>`;
  }

  function drawBody() {
    const body = $("#body", view);
    const all = k.stockList().sort((a, b) => a.name.localeCompare(b.name));
    const q = filter.toLowerCase();
    const shown = q ? all.filter((r) => r.name.toLowerCase().includes(q)) : all;
    const lowCount = all.filter((r) => r.low).length;
    const useUp = k.useItUp();

    let html = "";
    if (!q && useUp.length) {
      html += `<section class="useup" aria-label="Use it up"><h3>⏰ Use it up</h3><div class="useup-list">${useUp.map((r) =>
        `<button type="button" class="useup-item${k.daysUntil(r.expiry) < 0 ? " expired" : ""}" data-jump="${esc(r.id)}"><b>${esc(r.name)}</b><small>${esc(k.expiryText(r.expiry))}</small></button>`).join("")}</div></section>`;
    }
    html += `<p class="count">${all.length ? `${all.length} item${all.length === 1 ? "" : "s"} in stock${lowCount ? ` · ${lowCount} running low` : ""}` : ""}${q ? ` · showing ${shown.length} matching “${esc(filter)}”` : ""}</p>`;

    if (!all.length) {
      html += `<div class="empty"><div style="font-size:2.4rem">🥫</div>Nothing in stock yet.<br>Search above or tap the quick-add buttons to add what's in your kitchen.</div>`;
    } else {
      const groups = [...STORAGE, ...[...new Set(shown.map((r) => r.storage))].filter((s) => !STORAGE_BY_ID[s]).map((s) => ({ id: s, label: s, emoji: "📦" }))];
      for (const g of groups) {
        const items = shown.filter((r) => r.storage === g.id);
        if (!items.length) continue;
        html += `<h3 class="group-h">${g.emoji} ${esc(g.label)} <small class="muted">${items.length}</small></h3><ul class="slist">${items.map(itemRow).join("")}</ul>`;
      }
      if (q && !shown.length) html += `<p class="empty">None of your stock matches. Pick from the suggestions above to add it.</p>`;
      if (!q) html += `<p class="small muted center">Tip: swipe an item left to remove it. Tap a name to add a use-by date.</p>`;
    }

    // Staples
    const st = k.staples().map((id) => ingById[id]).filter(Boolean).sort((a, b) => a.name.localeCompare(b.name));
    html += `
      <details class="panel staples" ${staplesOpen ? "open" : ""}>
        <summary><b>Staples</b> <span class="small muted">· always count as in stock (${st.length})</span></summary>
        <p class="small muted">Things you never run out of. Recipes treat them as in stock, and they're not counted as missing.</p>
        <div class="taglist">${st.map((i) => `<span class="tag">${esc(i.name)}<button type="button" data-unstaple="${i.id}" aria-label="Remove ${esc(i.name)} from staples">✕</button></span>`).join("") || `<span class="small muted">None</span>`}</div>
        <div id="staple-add"></div>
      </details>`;
    body.innerHTML = html;

    mountFoodSearch($("#staple-add", body), {
      placeholder: "Add a staple, e.g. garlic",
      ingredients: ingredients.filter((i) => !k.isStaple(i.id)),
      onPick: async (i) => { await k.setStaple(i.id, true); await k.removeStock(i.id); staplesOpen = true; drawAll(); },
    });
    $("details.staples", body).addEventListener("toggle", (e) => { staplesOpen = e.target.open; });
  }

  function drawAll() { drawQuick(); drawBody(); }

  // One set of listeners on the container (rows are redrawn often).
  root.addEventListener("click", async (e) => {
    const t = e.target;
    const quick = t.closest("[data-add]");
    if (quick) return add(quick.dataset.add);
    const jump = t.closest("[data-jump]");
    if (jump) {
      editing = jump.dataset.jump; drawBody();
      $(`.srow[data-id="${CSS.escape(editing)}"]`, view)?.scrollIntoView({ block: "center", behavior: "smooth" });
      return;
    }
    const un = t.closest("[data-unstaple]");
    if (un) { await k.setStaple(un.dataset.unstaple, false); staplesOpen = true; drawAll(); return; }
    const row = t.closest(".srow");
    if (!row) return;
    const id = row.dataset.id;
    if (t.closest("[data-low]")) {
      const r = await k.toggleLow(id);
      app.toast(r.low ? `${r.name} marked as running low` : `${r.name}: low mark cleared`);
      drawBody();
    } else if (t.closest("[data-del]")) {
      await deleteRow(id);
    } else if (t.closest("[data-edit]")) {
      editing = editing === id ? null : id; drawBody();
    } else if (t.closest("[data-noexp]")) {
      await k.updateStock(id, { expiry: null }); drawBody();
    }
  });
  root.addEventListener("change", async (e) => {
    const row = e.target.closest(".srow");
    if (!row) return;
    const id = row.dataset.id;
    if (e.target.matches("[data-exp]")) await k.updateStock(id, { expiry: e.target.value || null });
    else if (e.target.matches("[data-storage]")) await k.updateStock(id, { storage: e.target.value });
    else if (e.target.matches("[data-aisle]")) await k.updateStock(id, { aisle: e.target.value });
    else return;
    drawBody();
  });
  enableSwipe(root, ".srow", (row) => deleteRow(row.dataset.id));

  async function deleteRow(id) {
    const rec = await k.removeStock(id);
    if (!rec) return;
    if (editing === id) editing = null;
    undoToast(`Removed ${rec.name}`, async () => { await k.restoreStock(rec); drawAll(); });
    drawAll();
  }

  drawAll();
}
