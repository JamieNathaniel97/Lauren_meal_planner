// "What do you fancy?" Phase 1: pick a cuisine and see its recipes.
// The full finder (time, calories, what's in stock) arrives in phase 3.

import { CUISINES } from "../constants.js";
import { fitsProfile } from "../derive.js";
import { esc } from "../ui.js";

export function renderFind({ app, view }) {
  app.setTitle("What do you fancy?");
  const { recipes, ingById } = app.catalogue;
  const fitting = recipes.filter((r) => fitsProfile(r, r.d, app.profile, ingById).ok);
  const count = (id) => fitting.filter((r) => r.cuisine === id).length;
  const tiles = CUISINES.filter((c) => count(c.id) > 0).map((c) => `
    <a class="cuisine" style="--c:${c.color}" href="#/recipes?cuisine=${c.id}">
      <span aria-hidden="true">${c.emoji}</span>${esc(c.label)}<small>${count(c.id)} recipe${count(c.id) === 1 ? "" : "s"}</small>
    </a>`).join("");

  view.innerHTML = `
    <p class="muted" style="margin-top:4px">Pick a cuisine for ideas${app.profile.diets.length ? " that suit your profile" : ""}.</p>
    <div class="cuisines">
      <a class="cuisine any" href="#/recipes"><span aria-hidden="true">🎲</span>Anything<small>${fitting.length} recipes</small></a>
      ${tiles}
    </div>
    <p class="small muted" style="margin-top:18px">Coming soon: filter by time and calories, and see what you can cook with the food you already have.</p>`;
}
