import { esc } from "../ui.js";

export function renderComingSoon({ app, view }, { title, emoji, phase, text }) {
  app.setTitle(title);
  view.innerHTML = `
    <div class="coming">
      <div class="emoji" aria-hidden="true">${emoji}</div>
      <h2>${esc(title)} is coming soon</h2>
      <p class="muted">${esc(text)}</p>
      <p class="small muted">Planned for build phase ${phase}.</p>
      <p><a class="btn secondary" href="#/recipes">Browse recipes</a></p>
    </div>`;
}
