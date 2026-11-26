// Tiny helpers for building HTML strings safely.

export function esc(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
}

const FRACTIONS = [[0.25, "¼"], [0.333, "⅓"], [0.5, "½"], [0.667, "⅔"], [0.75, "¾"]];

/** 1.5 -> "1½", 0.25 -> "¼", 2 -> "2". For countable units. */
export function niceNumber(n) {
  if (n >= 10) return String(Math.round(n));
  const whole = Math.floor(n + 0.04);
  const frac = n - whole;
  if (frac < 0.08) return String(whole || (n > 0 ? "¼" : "0"));
  let best = FRACTIONS[0];
  for (const f of FRACTIONS) if (Math.abs(frac - f[0]) < Math.abs(frac - best[0])) best = f;
  if (frac > 0.875) return String(whole + 1);
  return (whole ? whole : "") + best[1];
}

/** Round grams/ml sensibly after scaling. */
function niceWeight(n) {
  if (n < 10) return String(Math.round(n * 2) / 2);
  if (n < 100) return String(Math.round(n));
  if (n < 1000) return String(Math.round(n / 5) * 5);
  return String(Math.round(n / 10) * 10);
}

const PLURALS = { clove: "cloves", tin: "tins", slice: "slices", handful: "handfuls", bunch: "bunches",
  stick: "sticks", pinch: "pinches", nest: "nests", block: "blocks", cm: "cm", tsp: "tsp", tbsp: "tbsp",
  leaf: "leaves", sprig: "sprigs" };

/** "2 tins", "400 g", "1½ tsp", "3" (for "each"), "" for to-taste lines. */
export function formatQty(qty, unit) {
  if (qty == null) return "";
  if (unit === "g" || unit === "ml") {
    if (qty >= 1000) return `${Math.round(qty / 100) / 10} ${unit === "g" ? "kg" : "litres"}`;
    return `${niceWeight(qty)} ${unit}`;
  }
  const num = niceNumber(qty);
  if (!unit || unit === "each") return num;
  const plural = qty > 1.01 ? PLURALS[unit] || unit + "s" : unit;
  return `${num} ${plural}`;
}

export function minutes(m) {
  if (m < 60) return `${m} min`;
  const h = Math.floor(m / 60), r = m % 60;
  return r ? `${h} hr ${r} min` : `${h} hr`;
}

export function $(sel, root = document) { return root.querySelector(sel); }
export function $$(sel, root = document) { return [...root.querySelectorAll(sel)]; }
