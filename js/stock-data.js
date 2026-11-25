// Fixed lists for kitchen stock and the shopping list: storage places,
// supermarket aisles (in a typical UK walk-round order), default staples
// and quick-add buttons. Ids that aren't in data/ingredients.json are
// skipped at run time, so this file can't break if the list changes.

export const STORAGE = [
  { id: "fridge", label: "Fridge", emoji: "🧊" },
  { id: "freezer", label: "Freezer", emoji: "❄️" },
  { id: "cupboard", label: "Cupboard", emoji: "🥫" },
  { id: "fruit-veg", label: "Fruit & veg", emoji: "🥕" },
  { id: "spices", label: "Spices", emoji: "🧂" },
];
export const STORAGE_BY_ID = Object.fromEntries(STORAGE.map((s) => [s.id, s]));

export const AISLES = [
  { id: "fruit-veg", label: "Fruit & veg", emoji: "🥬" },
  { id: "meat-fish", label: "Meat & fish", emoji: "🥩" },
  { id: "dairy-eggs", label: "Dairy & eggs", emoji: "🥛" },
  { id: "bakery", label: "Bakery", emoji: "🍞" },
  { id: "tins-dry", label: "Tins, rice & pasta", emoji: "🥫" },
  { id: "spices-sauces", label: "Spices, oils & sauces", emoji: "🌶️" },
  { id: "frozen", label: "Frozen", emoji: "❄️" },
  { id: "drinks", label: "Drinks", emoji: "🧃" },
  { id: "household", label: "Household", emoji: "🧻" },
  { id: "other", label: "Other", emoji: "🛍️" },
];
export const AISLE_BY_ID = Object.fromEntries(AISLES.map((a) => [a.id, a]));

/** Aisle label for any id, including ones added to the data later. */
export function aisleOf(id) {
  return AISLE_BY_ID[id] || { id, label: id ? id.replace(/-/g, " ").replace(/^./, (c) => c.toUpperCase()) : "Other", emoji: "🛍️" };
}

// Where a food goes when it's added to stock, if the ingredient has no
// storage set (e.g. a custom item): guessed from the aisle.
export const STORAGE_FOR_AISLE = {
  "fruit-veg": "fruit-veg", "meat-fish": "fridge", "dairy-eggs": "fridge", bakery: "cupboard",
  "tins-dry": "cupboard", "spices-sauces": "cupboard", frozen: "freezer", drinks: "cupboard",
  household: "cupboard", other: "cupboard",
};

// Extra staples suggested on top of ingredients marked "staple" in the data.
export const SUGGESTED_STAPLES = ["salt", "black-pepper", "olive-oil", "vegetable-oil", "water"];

// Quick-add buttons on the Stock screen (most-bought foods first).
export const QUICK_ADD = [
  "onion", "garlic", "potatoes", "carrot", "eggs", "milk", "butter", "cheddar", "chicken-breast",
  "beef-mince", "rice", "basmati-rice", "gf-pasta", "gf-spaghetti", "chopped-tomatoes", "tomatoes",
  "lemon", "peppers", "red-pepper", "spinach", "broccoli", "frozen-peas", "tamari", "gf-veg-stock",
  "gf-chicken-stock", "coconut-milk", "chickpeas", "greek-yogurt", "bananas", "banana",
];

// "Use it up" warns about anything expiring within this many days.
export const EXPIRY_SOON_DAYS = 3;
