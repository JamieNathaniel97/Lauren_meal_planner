"""Read the UniTools World Recipes dataset (CC BY-SA 4.0) into the importer's
common format. The file is plain JSON.

    python tools/import_unitools.py raw/unitools/repo/unitools-recipes-v1.json
"""

import json
import sys

SOURCE = {"name": "UniTools", "licence": "CC BY-SA 4.0", "home": "https://theunitools.com/en/data"}

MEAL_TYPES = {"main": ["dinner", "lunch"], "soup": ["lunch", "dinner"], "dessert": ["dessert"],
              "snack": ["snack"], "breakfast": ["breakfast"], "bread": ["side", "snack"],
              "side": ["side"], "salad": ["lunch", "side"], "sauce": ["side"], "drink": ["snack"]}
UNIT_MAP = {"g": "g", "kg": "kg", "ml": "ml", "l": "l", "tbsp": "tbsp", "tsp": "tsp", "pinch": "pinch",
            "clove": "clove", "sprig": "sprig", "slice": "slice", "piece": "each", "toTaste": None}
# Licences that allow reuse with credit. Photos without one are left out.
OPEN_PHOTO = ("CC BY", "CC0", "PUBLIC DOMAIN", "GFDL", "KOGL")


def load(path):
    data = json.loads(open(path, encoding="utf-8").read())
    if "CC BY-SA" not in (data.get("license") or ""):
        raise SystemExit(f"Unexpected licence: {data.get('license')}")
    countries = {c["code"]: c for c in data["countries"]}
    out, skipped = [], []
    for r in data["recipes"]:
        lines = []
        for ing in r["ingredients"]:
            unit = UNIT_MAP.get(ing.get("unit"), "?" + str(ing.get("unit")))
            note = (ing.get("note") or {}).get("en") or ""
            lines.append({"raw": ing["name"]["en"], "qty": ing.get("quantity") if unit else None,
                          "unit": unit, "note": note, "size": None, "role": None, "srcId": ing.get("id")})
        photo = r.get("photo")
        if photo and photo.get("url") and str(photo.get("license") or "").upper().startswith(OPEN_PHOTO):
            photo = {"url": photo["url"], "credit": photo.get("author") or "",
                     "licence": photo["license"], "via": "Wikimedia Commons"}
        else:
            photo = None
        c = countries.get(r["country"], {})
        heat_words = sum(1 for l in lines if any(w in l["raw"].lower() for w in ("chil", "pepper flakes", "cayenne", "scotch", "habanero", "jalape")))
        out.append({
            "srcId": r["slug"], "source": "unitools",
            "name": r["name"]["en"],
            "description": (r.get("summary") or {}).get("en", "").strip(),
            "nativeName": r.get("nativeName"),
            "origin": (c.get("name") or {}).get("en", r["country"]),
            "cuisineRaw": r["country"],
            "category": r["category"], "mealTypes": MEAL_TYPES.get(r["category"], ["dinner"]),
            "servings": r.get("baseServings") or 4, "targetPerServing": None,
            "prepMins": r.get("prepMinutes") or 0, "cookMins": r.get("cookMinutes") or 0,
            "difficulty": r.get("difficulty") if r.get("difficulty") in ("easy", "medium", "hard") else "medium",
            "spice": min(2, heat_words) if heat_words else 0,
            "steps": [s["text"]["en"].strip() for s in r["steps"] if s["text"]["en"].strip()],
            "toolText": " ".join(s["text"]["en"] for s in r["steps"]),
            "tags": [r["category"]],
            "lines": lines, "ratio": "weight", "photo": photo,
            "source_info": {**SOURCE, "url": data.get("landingPage") or SOURCE["home"], "author": "UniTools"},
            "srcDiets": r.get("diets") or [],
            "srcNutrition": r.get("nutritionPerServing"),
        })
    return out, skipped


if __name__ == "__main__":
    recipes, skipped = load(sys.argv[1])
    print(f"{len(recipes)} recipes, {len(skipped)} skipped, {sum(1 for r in recipes if r['photo'])} with photos")
