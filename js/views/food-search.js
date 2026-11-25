// "Find or add a food" box used by the Stock and Shopping screens.
// Matches ingredient names and synonyms by prefix, word prefix, substring,
// and small typos ("tomatos", "chiken"), and always offers the typed text
// as your own item.

import { esc, $ } from "../ui.js";

const norm = (s) => s.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/[^a-z0-9 ]+/g, " ").replace(/\s+/g, " ").trim();

/** Edit distance, stopping early once it's over max. */
function distance(a, b, max) {
  if (Math.abs(a.length - b.length) > max) return max + 1;
  let prev = Array.from({ length: b.length + 1 }, (_, j) => j);
  for (let i = 1; i <= a.length; i++) {
    const cur = [i];
    let best = i;
    for (let j = 1; j <= b.length; j++) {
      cur[j] = Math.min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (a[i - 1] === b[j - 1] ? 0 : 1));
      best = Math.min(best, cur[j]);
    }
    if (best > max) return max + 1;
    prev = cur;
  }
  return prev[b.length];
}

/** Score how well a query matches a name (lower is better, null = no match). */
function score(q, name) {
  const n = norm(name);
  if (!q) return null;
  if (n === q) return 0;
  if (n.startsWith(q)) return 1;
  const words = n.split(" ");
  if (words.some((w) => w.startsWith(q))) return 2;
  if (n.includes(q)) return 3;
  // Typos: compare with the start of each word (or the whole name).
  const max = q.length >= 7 ? 2 : q.length >= 4 ? 1 : 0;
  if (!max) return null;
  for (const w of [n, ...words]) {
    if (distance(q, w.slice(0, q.length), max) <= max) return 4;
    if (distance(q, w, max) <= max) return 4;
  }
  return null;
}

/** Best ingredient matches for a query: [{ ing, via }] (via = synonym matched, if any). */
export function searchFoods(query, ingredients, limit = 8) {
  const q = norm(query);
  if (!q) return [];
  const hits = [];
  for (const i of ingredients) {
    let best = score(q, i.name), via = null;
    for (const s of i.synonyms || []) {
      const sc = score(q, s);
      if (sc != null && (best == null || sc < best)) { best = sc; via = s; }
    }
    if (best != null) hits.push({ ing: i, via, best });
  }
  hits.sort((a, b) => a.best - b.best || a.ing.name.length - b.ing.name.length || a.ing.name.localeCompare(b.ing.name));
  return hits.slice(0, limit);
}

/**
 * Mount the box inside `host`.
 * options: placeholder, ingredients, status(ing) -> short label or "",
 *          onPick(ing), onCustom(text), onInput(text) (e.g. to filter a list),
 *          customLabel(text) -> button text for the "own item" row.
 */
export function mountFoodSearch(host, opts) {
  host.innerHTML = `
    <div class="fsearch">
      <input class="search" type="search" placeholder="${esc(opts.placeholder)}" autocomplete="off" autocapitalize="none" enterkeyhint="done" aria-label="${esc(opts.placeholder)}">
      <ul class="fsearch-list" role="listbox" hidden></ul>
    </div>`;
  const input = $("input", host);
  const list = $("ul", host);
  let hits = [];

  function draw() {
    const text = input.value.trim();
    opts.onInput?.(text);
    if (!text) { list.hidden = true; list.innerHTML = ""; return; }
    hits = searchFoods(text, opts.ingredients);
    const exact = hits.some((h) => norm(h.ing.name) === norm(text) || (h.ing.synonyms || []).some((s) => norm(s) === norm(text)));
    list.innerHTML = hits.map((h, k) => {
      const st = opts.status?.(h.ing) || "";
      return `<li><button type="button" data-k="${k}"><span>${esc(h.ing.name)}${h.via ? ` <small class="muted">(${esc(h.via)})</small>` : ""}</span>${st ? `<small class="fs-status">${esc(st)}</small>` : ""}</button></li>`;
    }).join("") + (exact || !opts.onCustom ? "" : `<li><button type="button" data-custom class="fs-custom">${esc(opts.customLabel ? opts.customLabel(text) : `Add “${text}” as your own item`)}</button></li>`);
    list.hidden = !list.innerHTML;
  }

  input.addEventListener("input", draw);
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      if (hits[0]) pick(hits[0].ing); else if (input.value.trim() && opts.onCustom) custom();
    } else if (e.key === "Escape") { input.value = ""; draw(); }
  });
  list.addEventListener("click", (e) => {
    const b = e.target.closest("button");
    if (!b) return;
    if (b.hasAttribute("data-custom")) custom(); else pick(hits[Number(b.dataset.k)].ing);
  });
  function pick(i) { opts.onPick(i); clear(); }
  function custom() { const t = input.value.trim(); if (t) opts.onCustom(t); clear(); }
  function clear() { input.value = ""; draw(); input.focus({ preventScroll: true }); }
  return { input, refresh: draw, clear };
}
