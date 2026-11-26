// Offline support: the app shell and recipe data are cached on install and
// served from the cache first.
// IMPORTANT: bump CACHE whenever any file changes (code, CSS or recipes),
// otherwise installed phones keep showing the old version.
const CACHE = "meal-planner-v5";

const SHELL = [
  "./",
  "index.html",
  "manifest.webmanifest",
  "css/app.css",
  "js/app.js",
  "js/constants.js",
  "js/data.js",
  "js/db.js",
  "js/derive.js",
  "js/ui.js",
  "js/views/coming-soon.js",
  "js/views/find.js",
  "js/views/profile.js",
  "js/views/recipe.js",
  "js/views/recipes.js",
  "data/ingredients.json",
  "data/recipes/index.json",
  "icons/icon.svg",
  "icons/icon-192.png",
  "icons/icon-512.png",
  "icons/icon-maskable-512.png",
  "icons/apple-touch-icon.png",
];

self.addEventListener("install", (event) => {
  event.waitUntil((async () => {
    const cache = await caches.open(CACHE);
    await cache.addAll(SHELL);
    // Recipe batches are listed in data/recipes/index.json. Imported batches
    // keep their method steps in data/steps/, cached too so recipes open offline.
    // (Recipe photos come from another site and need a connection.)
    const index = await (await fetch("data/recipes/index.json", { cache: "no-store" })).json();
    await cache.addAll(index.batches.map((f) => `data/recipes/${f}`));
    await cache.addAll(index.batches.filter((f) => !f.startsWith("batch-")).map((f) => `data/steps/${f}`));
    await self.skipWaiting();
  })());
});

self.addEventListener("activate", (event) => {
  event.waitUntil((async () => {
    for (const key of await caches.keys()) if (key !== CACHE) await caches.delete(key);
    await self.clients.claim();
  })());
});

self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET" || new URL(req.url).origin !== location.origin) return;
  event.respondWith((async () => {
    const cache = await caches.open(CACHE);
    const hit = await cache.match(req, { ignoreSearch: true });
    if (hit) return hit;
    try {
      const res = await fetch(req);
      if (res.ok && req.mode !== "navigate") cache.put(req, res.clone());
      return res;
    } catch (e) {
      // Offline and not cached: page loads fall back to the app itself.
      if (req.mode === "navigate") {
        const page = await cache.match("index.html");
        if (page) return page;
      }
      return new Response("Offline", { status: 503, statusText: "Offline" });
    }
  })());
});
