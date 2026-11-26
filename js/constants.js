// Fixed lists used across the app: cuisines, meal types, diets, allergens, tools.

export const CUISINES = [
  { id: "chinese", label: "Chinese", emoji: "🥡", color: "#d64545" },
  { id: "italian", label: "Italian", emoji: "🍝", color: "#2f9e44" },
  { id: "mexican", label: "Mexican", emoji: "🌮", color: "#e8590c" },
  { id: "indian", label: "Indian", emoji: "🍛", color: "#e09f00" },
  { id: "thai", label: "Thai", emoji: "🍜", color: "#0ca678" },
  { id: "japanese", label: "Japanese", emoji: "🍣", color: "#d6336c" },
  { id: "korean", label: "Korean", emoji: "🍚", color: "#9c36b5" },
  { id: "vietnamese", label: "Vietnamese", emoji: "🥢", color: "#5c940d" },
  { id: "middle-eastern", label: "Middle Eastern", emoji: "🧆", color: "#a0673a" },
  { id: "greek", label: "Greek", emoji: "🫒", color: "#1c7ed6" },
  { id: "spanish", label: "Spanish", emoji: "🥘", color: "#f76707" },
  { id: "french", label: "French", emoji: "🥖", color: "#4263eb" },
  { id: "turkish", label: "Turkish", emoji: "🍳", color: "#c92a2a" },
  { id: "caribbean", label: "Caribbean", emoji: "🌴", color: "#099268" },
  { id: "north-african", label: "North African", emoji: "🍲", color: "#d9480f" },
  { id: "american", label: "American", emoji: "🍔", color: "#1864ab" },
  { id: "british", label: "British & Irish", emoji: "🫖", color: "#5f6b7a" },
  { id: "latin-american", label: "Latin American", emoji: "🌽", color: "#c2255c" },
  { id: "southeast-asian", label: "South-East Asian", emoji: "🍢", color: "#2b8a3e" },
  { id: "african", label: "African", emoji: "🍠", color: "#b35c00" },
  { id: "eastern-european", label: "Eastern European", emoji: "🥟", color: "#5c7cfa" },
  { id: "european", label: "European", emoji: "🧀", color: "#7048e8" },
  { id: "central-asian", label: "Central Asian", emoji: "🫓", color: "#a61e4d" },
  { id: "international", label: "International", emoji: "🌍", color: "#1098ad" },
];
export const CUISINE_BY_ID = Object.fromEntries(CUISINES.map((c) => [c.id, c]));

export const MEAL_TYPES = [
  { id: "breakfast", label: "Breakfast" },
  { id: "lunch", label: "Lunch" },
  { id: "dinner", label: "Dinner" },
  { id: "snack", label: "Snack" },
  { id: "side", label: "Side" },
  { id: "dessert", label: "Dessert" },
];

// Where imported recipes come from (all CC BY-SA 4.0). Shown in Profile > Credits.
export const SOURCES = {
  ForkRecipe: { url: "https://github.com/futurechef/forkrecipe-recipes", note: "the ForkRecipe open recipe dataset, by FoodML and contributors" },
  UniTools: { url: "https://theunitools.com/en/data", note: "UniTools World Recipes, theunitools.com" },
};

// Diet tags are worked out from ingredients in derive.js.
export const DIETS = [
  { id: "gluten-free", label: "Gluten-free", short: "GF" },
  { id: "nut-free", label: "Nut-free (peanuts & tree nuts)", short: "NF" },
  { id: "vegetarian", label: "Vegetarian", short: "V" },
  { id: "vegan", label: "Vegan", short: "VG" },
  { id: "pescatarian", label: "Pescatarian", short: "P" },
  { id: "dairy-free", label: "Dairy-free", short: "DF" },
  { id: "halal", label: "Halal-friendly (no pork or alcohol)", short: "H" },
  { id: "low-carb", label: "Low-carb (20 g carbs or less)", short: "LC" },
];
export const DIET_BY_ID = Object.fromEntries(DIETS.map((d) => [d.id, d]));

// The 14 allergens UK food law requires to be declared.
// Peanuts and tree nuts are separate, as on UK labels.
export const ALLERGENS = [
  { id: "gluten", label: "Cereals containing gluten" },
  { id: "peanuts", label: "Peanuts" },
  { id: "nuts", label: "Tree nuts" },
  { id: "milk", label: "Milk" },
  { id: "eggs", label: "Eggs" },
  { id: "fish", label: "Fish" },
  { id: "crustaceans", label: "Crustaceans (prawns, crab)" },
  { id: "molluscs", label: "Molluscs (mussels, squid)" },
  { id: "sesame", label: "Sesame" },
  { id: "soya", label: "Soya" },
  { id: "celery", label: "Celery" },
  { id: "mustard", label: "Mustard" },
  { id: "lupin", label: "Lupin" },
  { id: "sulphites", label: "Sulphites" },
];
export const ALLERGEN_BY_ID = Object.fromEntries(ALLERGENS.map((a) => [a.id, a]));

export const TOOLS = [
  { id: "hob", label: "Hob" },
  { id: "oven", label: "Oven" },
  { id: "microwave", label: "Microwave" },
  { id: "grill", label: "Grill" },
  { id: "air-fryer", label: "Air fryer" },
  { id: "slow-cooker", label: "Slow cooker" },
  { id: "pressure-cooker", label: "Pressure cooker / Instant Pot" },
  { id: "food-processor", label: "Food processor" },
  { id: "blender", label: "Blender" },
  { id: "stick-blender", label: "Stick blender" },
  { id: "stand-mixer", label: "Stand mixer" },
  { id: "wok", label: "Wok" },
  { id: "griddle", label: "Griddle pan" },
  { id: "steamer", label: "Steamer" },
  { id: "bbq", label: "BBQ" },
];
export const TOOL_BY_ID = Object.fromEntries(TOOLS.map((t) => [t.id, t]));

// The one-tap "Coeliac + nut-free" preset for Lauren (Profile screen).
export const COELIAC_NF_PRESET = {
  diets: ["gluten-free", "nut-free"],
  allergens: ["gluten", "peanuts", "nuts"],
  coeliac: true,
};

export const DIFFICULTY = { easy: "Easy", medium: "Medium", hard: "Hard" };
export const COST = { 1: "£", 2: "££", 3: "£££" };

// The profile starts empty. tools: null means "not set yet" (no tool filtering).
export const DEFAULT_PROFILE = {
  id: "me",
  diets: [],
  allergens: [],
  coeliac: false,
  dislikes: [],
  tools: null,
  household: 2,
};

