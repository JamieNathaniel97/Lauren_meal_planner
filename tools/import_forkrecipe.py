"""Read the ForkRecipe dataset (CC BY-SA 4.0) into the importer's common format.

The recipe files are JavaScript modules, but they are never executed: each is
parsed by tools/jslit.py, which accepts only plain literal data.

    python tools/import_forkrecipe.py raw/forkrecipe/repo      (prints a summary)
"""

import re
import sys
from pathlib import Path

from jslit import JSLiteralError, parse_module

SOURCE = {"name": "ForkRecipe", "licence": "CC BY-SA 4.0",
          "home": "https://github.com/futurechef/forkrecipe-recipes"}

# Dish categories; condiments, sauces, stocks, ferments, drinks and breads are
# components rather than meals, so they're left out for now.
MEAL_CATEGORIES = {"proteins": ["dinner", "lunch"], "seafood": ["dinner", "lunch"],
                   "grains": ["dinner", "lunch"], "vegetables": ["side", "lunch"],
                   "eggs": ["breakfast", "lunch"], "desserts": ["dessert"]}
TARGET_G_PER_SERVING = {"proteins": 300, "seafood": 300, "grains": 300, "vegetables": 220,
                        "eggs": 220, "desserts": 140}

UNIT_MAP = {"g": "g", "kg": "kg", "ml": "ml", "l": "l", "liters": "l", "litres": "l", "liter": "l",
            "tsp": "tsp", "tbsp": "tbsp", "pinch": "pinch", "cup": "cup", "cups": "cup",
            "clove": "clove", "cloves": "clove", "leaf": "leaf", "leaves": "leaf",
            "sprig": "sprig", "sprigs": "sprig", "slice": "slice", "slices": "slice",
            "bundle": "bunch", "bunch": "bunch", "lb": "lb", "oz": "oz", "stick": "stick",
            "parts": "parts", "part": "parts", "%": "parts", "to taste": None}
EACH_UNITS = {"whole", "pcs", "pc", "pieces", "piece", "ea", "each", "unit", "medium", "large", "small",
              "eggs", "egg", "yolks", "yolk", "lemon", "lemons", "lime", "limes", "pod", "pods", "wedges",
              "berries", "heads", "head", "fillets", "fillet", "shallots", "shallot", "sheets", "sheet", "stalks", "stalk"}


COUNT_NOUNS = re.compile(r"^(strips?|packs?|pieces?|small pieces?|sausages?|sheets?|large sheets?|peppercorns?|"
                         r"whites?|ears?|rounds?|fish|quarters?|leeks?|oysters?|cutlets?|loaf|loaves|chunks?|"
                         r"units?|peppers?|tortillas?|beans?|legs?|fillets?|steaks?|chops?|links?|bulbs?|"
                         r"heads?|stalks?|cobs?|knobs?|thumbs?|bags?|blocks?|bottles?|jars?)\b")


def normalise_unit(raw_unit, qty):
    """Source unit text -> (our unit, quantity). Unknown units come back as
    '?text' so the recipe is reported rather than guessed."""
    u = re.sub(r"\(.*?\)", "", raw_unit).strip()
    grams_each = re.search(r"(\d+(?:\.\d+)?)\s*g\b", raw_unit)
    if raw_unit in EACH_UNITS or u in EACH_UNITS:
        return "each", qty
    if u in UNIT_MAP:
        return UNIT_MAP[u], qty
    if re.match(r"^(cans?|tins?)\b", u):
        if grams_each and qty is not None:
            return "g", qty * float(grams_each.group(1))
        return "tin", qty
    if u.startswith("parts"):
        return "parts", qty
    if re.match(r"^cups?\b", u):
        return "cup", qty
    if re.match(r"^(lbs?|pounds?)\b", u):
        return "lb", qty
    if re.search(r"\bbunch(es)?\b", u):
        return "bunch", qty
    if u in ("serving", "servings", "to serve"):
        return None, None
    if u == "bouquet":
        return "each", qty
    if COUNT_NOUNS.match(u) or u.startswith(("whole", "yolks")):
        if grams_each and qty is not None:
            return "g", qty * float(grams_each.group(1))
        return "each", qty
    return "?" + raw_unit, qty


def parse_time(s):
    """'1 hr 30 min' -> 90. Returns None if unreadable."""
    if not s:
        return None
    t = s.lower()
    mins = 0
    found = False
    for num, unit in re.findall(r"(\d+(?:\.\d+)?)\s*(d|day|days|h|hr|hrs|hour|hours|m|min|mins|minute|minutes)\b", t):
        found = True
        n = float(num)
        mins += n * (1440 if unit.startswith("d") else 60 if unit.startswith("h") else 1)
    return int(round(mins)) if found else None


def difficulty(n):
    return "easy" if n <= 2 else "medium" if n == 3 else "hard"


def load(repo_dir):
    """Returns (recipes in the common format, skipped [(slug, reason)])."""
    repo = Path(repo_dir)
    out, skipped = [], []
    for f in sorted((repo / "recipes").glob("*.js")):
        if f.name.startswith("_") or f.name == "index.js":
            continue
        try:
            r = parse_module(f.read_text(encoding="utf-8"))
        except (JSLiteralError, ValueError, IndexError) as exc:
            skipped.append((f.stem, f"not plain data: {exc}"))
            continue
        cat = r.get("category")
        if cat not in MEAL_CATEGORIES:
            skipped.append((r.get("slug", f.stem), f"category '{cat}' is a component, not a meal"))
            continue
        if r.get("license") not in ("CC-BY-SA", "CC BY-SA", "CC BY-SA 4.0"):
            skipped.append((r.get("slug"), f"licence '{r.get('license')}'"))
            continue
        lines = []
        for ing in r.get("ingredients") or []:
            raw_unit = str(ing.get("defaultUnit") or "").strip().lower()
            qty = ing.get("ratioValue")
            unit, qty = normalise_unit(raw_unit, qty)
            if unit is None:
                qty = None
            lines.append({"raw": ing.get("name") or "", "qty": qty, "unit": unit, "note": "",
                          "size": raw_unit if raw_unit in ("large", "small") else None,
                          "role": ing.get("role")})
        steps = []
        text_for_tools = []
        for node in r.get("processNodes") or []:
            ins = (node.get("instructions") or "").strip()
            if ins:
                steps.append(ins)
            text_for_tools.append(f"{node.get('action', '')} {ins}")
        active, total = parse_time(r.get("activeTime")), parse_time(r.get("totalTime"))
        if active is None and total is None:
            active, total = 20, 45
        active = active if active is not None else min(total, 30)
        total = max(total if total is not None else active, active)
        heat = (r.get("flavorRadar") or {}).get("heat", 0) or 0
        out.append({
            "srcId": r["slug"], "source": "forkrecipe",
            "name": r.get("title") or r["slug"].replace("-", " ").title(),
            "description": (r.get("description") or "").strip(),
            "origin": r.get("culture") or r.get("cuisine") or "",
            "cuisineRaw": r.get("cuisine") or "",
            "category": cat, "mealTypes": MEAL_CATEGORIES[cat],
            "servings": r.get("servings"), "targetPerServing": TARGET_G_PER_SERVING[cat],
            "prepMins": active, "cookMins": total - active,
            "difficulty": difficulty(int(r.get("difficulty") or 2)),
            "spice": 0 if heat <= 0 else 1 if heat <= 2 else 2 if heat == 3 else 3,
            "steps": steps, "toolText": " ".join(text_for_tools),
            "tags": [t for t in (r.get("tags") or []) if isinstance(t, str)][:6],
            "lines": lines,
            "ratio": "parts" if r.get("ratioSystem") in ("parts", "bakers_percentage") else "weight",
            "photo": None,
            "source_info": {**SOURCE, "url": f"{SOURCE['home']}/blob/main/recipes/{f.name}",
                            "author": r.get("author") or "ForkRecipe Kitchen"},
            "srcDiets": None,
        })
    return out, skipped


if __name__ == "__main__":
    recipes, skipped = load(sys.argv[1])
    print(f"{len(recipes)} meal recipes, {len(skipped)} skipped")
