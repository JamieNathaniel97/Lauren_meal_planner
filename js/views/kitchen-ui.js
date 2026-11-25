// Small UI pieces shared by the Stock and Shopping screens:
// a toast with an Undo button, and swipe-left-to-delete on list rows.

import { esc } from "../ui.js";

let toastTimer = null;

/** Show "message [Undo]" for a few seconds. onUndo runs if Undo is tapped. */
export function undoToast(message, onUndo) {
  document.querySelector(".toast")?.remove();
  clearTimeout(toastTimer);
  const t = document.createElement("div");
  t.className = "toast with-action";
  t.setAttribute("role", "status");
  t.innerHTML = `<span>${esc(message)}</span>${onUndo ? `<button type="button">Undo</button>` : ""}`;
  document.body.append(t);
  t.querySelector("button")?.addEventListener("click", () => { t.remove(); onUndo(); });
  toastTimer = setTimeout(() => t.remove(), 5000);
}

/**
 * Swipe a row left to delete it (touch screens). The row needs a child
 * .swipe-inner that moves; onDelete(row) runs when swiped far enough.
 * Vertical scrolling still works: the swipe only starts on a mostly
 * sideways movement.
 */
export function enableSwipe(container, selector, onDelete) {
  let row = null, inner = null, startX = 0, startY = 0, dx = 0, active = false;
  container.addEventListener("touchstart", (e) => {
    row = e.target.closest(selector);
    // Big row buttons (name, tick box) can be swiped; small controls can't.
    if (!row || e.target.closest(".del, .lowbtn, input, select, a, .sedit")) { row = null; return; }
    inner = row.querySelector(".swipe-inner");
    startX = e.touches[0].clientX; startY = e.touches[0].clientY; dx = 0; active = false;
  }, { passive: true });
  container.addEventListener("touchmove", (e) => {
    if (!row) return;
    const x = e.touches[0].clientX - startX, y = e.touches[0].clientY - startY;
    if (!active) {
      if (Math.abs(x) > 10 && Math.abs(x) > Math.abs(y) * 1.5 && x < 0) { active = true; row.classList.add("swiping"); }
      else if (Math.abs(y) > 10) { row = null; return; }
    }
    if (active) { dx = Math.min(0, x); inner.style.transform = `translateX(${dx}px)`; }
  }, { passive: true });
  const end = () => {
    if (!row) return;
    const r = row, i = inner;
    if (active && dx < -Math.min(110, r.offsetWidth * 0.35)) {
      i.style.transform = `translateX(-100%)`;
      setTimeout(() => onDelete(r), 150);
    } else if (i) {
      i.style.transform = "";
    }
    r.classList.remove("swiping");
    row = null; active = false;
  };
  container.addEventListener("touchend", end);
  container.addEventListener("touchcancel", end);
}
