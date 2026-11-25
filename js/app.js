// App shell: loads data, keeps the profile, routes between screens.
// Routes (hash based, so it works on GitHub Pages):
//   #/find  #/recipes?cuisine=thai  #/recipe/<id>  #/stock  #/shopping  #/profile

import { loadCatalogue } from "./data.js";
import * as db from "./db.js";
import { $, $$ } from "./ui.js";
import { DEFAULT_PROFILE } from "./constants.js";
import { renderFind } from "./views/find.js";
import { renderRecipes } from "./views/recipes.js";
import { renderRecipe } from "./views/recipe.js";
import { renderProfile } from "./views/profile.js";
// --- Kitchen stock & shopping list (phases 2 & 4)
import { loadKitchen } from "./kitchen.js";
import { renderStock } from "./views/stock.js";
import { renderShopping } from "./views/shopping.js";

const app = {
  catalogue: null,
  profile: { ...DEFAULT_PROFILE },
  async saveProfile(changes) {
    this.profile = { ...this.profile, ...changes };
    this.profile = await db.put("profile", this.profile);
  },
  go(hash) { location.hash = hash; },
  setTitle(text, { back = false } = {}) {
    $("#title").textContent = text;
    $("#back").hidden = !back;
    document.title = text === "Meal Planner" ? text : `${text} · Meal Planner`;
  },
  toast(message) {
    $(".toast")?.remove();
    const t = document.createElement("div");
    t.className = "toast";
    t.setAttribute("role", "status");
    t.textContent = message;
    document.body.append(t);
    setTimeout(() => t.remove(), 2200);
  },
};

function parseRoute() {
  const raw = location.hash.replace(/^#\/?/, "") || "find";
  const [path, query = ""] = raw.split("?");
  const [name, ...rest] = path.split("/");
  return { name, param: rest.join("/") ? decodeURIComponent(rest.join("/")) : null, query: new URLSearchParams(query) };
}

const TAB_FOR = { find: "find", recipes: "recipes", recipe: "recipes", stock: "stock", shopping: "shopping", profile: "profile" };

async function render() {
  const route = parseRoute();
  const view = $("#view");
  $$(".tabs a").forEach((a) => a.classList.toggle("active", a.dataset.tab === TAB_FOR[route.name]));
  if (!app.catalogue) return;
  const ctx = { app, route, view };
  switch (route.name) {
    case "find": renderFind(ctx); break;
    case "recipes": renderRecipes(ctx); break;
    case "recipe": renderRecipe(ctx); break;
    case "profile": renderProfile(ctx); break;
    case "stock": renderStock(ctx); break;
    case "shopping": renderShopping(ctx); break;
    default: app.go("#/find"); return;
  }
  if (route.name !== "recipes") window.scrollTo(0, 0);
}

async function start() {
  $("#back").addEventListener("click", () => (history.length > 1 ? history.back() : app.go("#/recipes")));
  try {
    const [catalogue, saved] = await Promise.all([loadCatalogue(new URL("./", location.href)), db.get("profile", "me")]);
    app.catalogue = catalogue;
    if (saved) app.profile = { ...DEFAULT_PROFILE, ...saved };
    await loadKitchen(catalogue.ingById); // kitchen stock & shopping list
    if (catalogue.problems.length) console.warn("Recipe data problems:", catalogue.problems);
  } catch (e) {
    $("#view").innerHTML = `<p class="empty">Couldn't load the recipes. Check your connection and reopen the app.<br><small>${e.message}</small></p>`;
    return;
  }
  window.addEventListener("hashchange", render);
  render();
}

if ("serviceWorker" in navigator && location.protocol !== "file:") {
  navigator.serviceWorker.register("sw.js").catch((e) => console.warn("Service worker not registered:", e));
}

start();
