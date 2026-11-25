// Shopping-list rounding: show amounts you'd actually buy.
//   2½ onions        -> 3 onions          (whole items)
//   2½ cloves garlic -> 1 bulb            (1 bulb ≈ 10 cloves, at least 1)
//   1 tsp cumin      -> Cumin             (spices, sauces, oils, spoonfuls: no amount)
//   130 g            -> 150 g             (weights up to pack-ish steps)
//   1½ tins          -> 2 tins
// The precise sum stays available as a small grey detail ("needs 2½ cloves").
// Pure functions (only ../ui.js for number formatting), tested in tools/finder-test.html.

import { formatQty } from "./ui.js";

/** Units you can only buy whole of. */
export const WHOLE_UNITS = new Set(["each", "tin", "bunch", "block", "nest", "stick", "slice", "pack", "jar"]);

/** Units too small to shop by: shown as just the item name. */
export const NAME_ONLY_UNITS = new Set(["tsp", "tbsp", "pinch"]);

/** Units converted to grams first (then rounded like a weight), when the ingredient gives a weight. */
export const TO_GRAMS_UNITS = new Set(["handful", "cm"]);

/** Aisles where amounts aren't useful on a list (you buy a jar or bottle). */
export const NAME_ONLY_AISLES = new Set(["spices-sauces"]);

/** Weight / volume steps: [below this amount, round up to a multiple of]. */
export const WEIGHT_STEPS = [[500, 50], [Infinity, 100]];

/**
 * Per-ingredient overrides.
 *   convert: { fromUnit: { to, per } }  e.g. 10 cloves = 1 "each" (bulb)
 *   names:   { unit: [singular, plural] } shown after the number
 *   nameOnly: true                        never show an amount
 */
export const INGREDIENT_RULES = {
  garlic: { convert: { clove: { to: "each", per: 10 } }, names: { each: ["bulb", "bulbs"] } },
};

/** Garlic cloves -> bulbs etc., before parts are combined. */
export function preconvert(parts, ing) {
  const rule = ing && INGREDIENT_RULES[ing.id];
  if (!rule?.convert) return parts;
  return parts.map((p) => {
    const c = p.qty != null && rule.convert[p.unit || "each"];
    return c ? { ...p, qty: p.qty / c.per, unit: c.to } : p;
  });
}

function roundWeight(g) {
  for (const [below, step] of WEIGHT_STEPS) if (g < below) return Math.max(step, Math.ceil(g / step - 1e-9) * step);
  return g;
}

/**
 * Round combined amounts ([{ qty, unit }], from combineParts) for the list.
 * Returns the text to show, or "" for name-only items.
 */
export function roundedText(combined, ing) {
  if (!ing || !combined.length) return "";
  const rule = INGREDIENT_RULES[ing.id] || {};
  if (rule.nameOnly || NAME_ONLY_AISLES.has(ing.aisle)) return "";
  const out = new Map();
  for (const { qty, unit: u0 } of combined) {
    let unit = u0 || "each", q = qty;
    if (q == null || NAME_ONLY_UNITS.has(unit)) continue;
    if (TO_GRAMS_UNITS.has(unit) && typeof ing.units?.[unit] === "number") { q *= ing.units[unit]; unit = "g"; }
    out.set(unit, (out.get(unit) || 0) + q);
  }
  return [...out].map(([unit, q]) => {
    if (unit === "g" || unit === "ml") return formatQty(roundWeight(q), unit);
    const whole = Math.max(1, Math.ceil(q - 0.05));
    const names = rule.names?.[unit];
    if (names) return `${whole} ${whole === 1 ? names[0] : names[1]}`;
    return formatQty(WHOLE_UNITS.has(unit) ? whole : q, unit);
  }).join(" + ");
}

/** The exact sum, e.g. "2½ cloves" (shown small and grey when it differs from the rounded text). */
export function preciseText(combined) {
  return combined.filter((c) => c.qty != null).map(({ qty, unit }) => formatQty(qty, unit)).join(" + ");
}
