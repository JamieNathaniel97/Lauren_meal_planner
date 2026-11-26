"""Import the ForkRecipe and UniTools datasets into the app's recipe batches.

    python tools/import_all.py raw/forkrecipe/repo raw/unitools/repo/unitools-recipes-v1.json

Writes:
  data/ingredients.json            existing ingredients + new master ones
  data/recipes/unitools-NN.json    imported recipes (~100 per file)
  data/recipes/fork-NN.json
  data/recipes/index.json          batch list (our own batch-01 first)
  tools/import_report.md           what was imported, converted and rejected

Re-running is safe: imported batch files are rebuilt from scratch, and our
own batches (batch-NN.json) are never touched. Diet tags, allergens and
nutrition are not stored; the app works them out from the ingredients.
"""

import collections
import json
import re
import sys

from import_common import (ROOT, EACH_BY_AISLE, LIQUIDS, STOCK_CUBES, Matcher, diet_facts, fit_servings, grams_for,
                           guess_cost, guess_spice, infer_tools, load_ingredients, make_free_version,
                           name_key, recipe_kcal_per_portion, safety_issue, slugify, stock_line, tidy_grams)
from ingnorm import norm
import import_forkrecipe
import import_unitools
from text_safety import apply_fixes, make_text_safe

DATA = ROOT / "data"
BATCH_SIZE = 100

# ---- cuisines: source label or country code -> our cuisine id
CUISINE = {}
for ids, cid in [
    ("Chinese Taiwanese CN TW Cantonese Sichuan HK", "chinese"),
    ("Italian Italian-American IT MT", "italian"),
    ("Mexican MX", "mexican"),
    ("Indian South-Indian PK BD NP LK BT MV IN", "indian"),
    ("Thai TH", "thai"), ("Japanese JP", "japanese"), ("Korean Korean-American KR", "korean"),
    ("Vietnamese VN", "vietnamese"),
    ("Middle-Eastern Lebanese Levantine Persian Israeli Syrian Iraqi Jordanian Palestinian Yemeni Saudi Emirati "
     "Kuwaiti Omani Armenian Azerbaijani LB IL IR SY IQ JO YE SA AE KW OM AM AZ", "middle-eastern"),
    ("Greek Cypriot GR CY", "greek"), ("Spanish ES", "spanish"), ("French French-Creole FR LU", "french"),
    ("Turkish TR", "turkish"),
    ("Caribbean Jamaican Cuban Dominican Trinidadian Puerto-Rican CU JM DO TT", "caribbean"),
    ("Moroccan Egyptian Tunisian Algerian Libyan North-African Sudanese MA EG TN DZ SD", "north-african"),
    ("American Asian-American Southern Cajun Creole Hawaiian US CA", "american"),
    ("British Irish English Scottish Welsh GB IE", "british"),
    ("Peruvian Brazilian Argentine Argentinian Colombian Chilean Venezuelan Latin-American Bolivian Ecuadorian "
     "Uruguayan Guatemalan Honduran Nicaraguan Panamanian Paraguayan Costa-Rican Salvadoran Mexican-(Jalisco) "
     "PE BR AR CO CL VE BO EC UY GT HN NI PA PY CR", "latin-american"),
    ("Russian Polish Ukrainian Hungarian Georgian Eastern-European Czech Slovak Romanian Bulgarian Serbian "
     "Croatian Bosnian Slovenian Macedonian Albanian Montenegrin Kosovar Moldovan Belarusian Lithuanian Latvian "
     "Estonian RU PL UA HU GE CZ SK RO BG RS HR BA SI MK AL ME XK MD BY LT LV EE", "eastern-european"),
    ("German Austrian Swiss Dutch Belgian Scandinavian Swedish Danish Norwegian Finnish Icelandic Portuguese "
     "Mediterranean Ancient-Roman Medieval-European Continental European Alsatian DE AT CH NL BE SE DK NO FI IS PT",
     "european"),
    ("Ethiopian Nigerian West-African South-African Ghanaian Senegalese Kenyan Tanzanian Ugandan Cameroonian "
     "Ivorian Congolese Malian Mozambican Malagasy Zimbabwean African ET NG GH SN ZA KE TZ UG CM CI CD ML MZ MG ZW",
     "african"),
    ("Indonesian Malaysian Filipino Singaporean Burmese Khmer Cambodian Lao Laotian Southeast-Asian ID MY PH SG MM KH LA",
     "southeast-asian"),
    ("Uzbek Kazakh Kyrgyz Tajik Turkmen Afghan Mongolian Central-Asian UZ KZ KG TJ TM AF MN", "central-asian"),
    ("Global Universal International Australian AU NZ", "international"),
]:
    for key in ids.split():
        CUISINE[key.replace("-", " ").lower()] = cid


def cuisine_for(raw):
    key = raw.strip().lower()
    return CUISINE.get(key) or CUISINE.get(key.split(" (")[0]) or "international"


# ---- units
DENSITY = {"plain-flour": .53, "gf-flour": .55, "strong-flour": .53, "sugar": .85, "brown-sugar": .9,
           "icing-sugar": .5, "long-grain-rice": .8, "basmati-rice": .8, "short-grain-rice": .85,
           "jasmine-rice": .8, "arborio-rice": .85, "porridge-oats": .4, "gf-oats": .4, "breadcrumbs": .45,
           "cheddar": .45, "parmesan": .4, "pecorino": .4, "coconut": .35, "cocoa": .45, "almonds": .6,
           "walnuts": .5, "peanuts": .6, "cashews": .6, "quinoa": .75, "red-lentils": .8, "lentils-brown": .8,
           "chickpeas": .65, "black-beans": .7, "peas-frozen": .6, "sweetcorn": .65, "spinach": .12,
           "coriander": .06, "parsley": .06, "basil": .06, "mint": .06, "dill": .06, "berries": .6,
           "raisins": .65, "polenta": .7, "masa-harina": .5, "cornflour": .55, "butter": .95, "tomato": .7,
           "rice-flour": .6, "potato-starch": .65, "mushrooms": .3, "white-cabbage": .4, "kale": .1,
           "cottage-cheese": .9, "feta": .6, "mozzarella": .5, "dried-pasta": .45, "yellow-split-peas": .8,
           "white-beans": .7, "coconut-milk": 1, "vegetable-oil": .92, "olive-oil": .92, "honey": 1.4,
           "golden-syrup": 1.4, "maple-syrup": 1.3}
LIQUID_AISLES = {"drinks"}


def to_grams(qty, unit, ing):
    if unit == "cup":
        dens = DENSITY.get(ing["id"], 1.0 if ing["aisle"] in LIQUID_AISLES or ing["aisle"] == "spices-sauces" else 0.6)
        return qty * 240 * dens
    if unit == "lb":
        return qty * 454
    if unit == "oz":
        return qty * 28.35
    if unit == "stick":
        return qty * (113 if ing["id"] in ("butter", "margarine") else 40)
    return None


FRYING = re.compile(r"fry|frying|deep.?fry|for the oil|shallow", re.I)
GARNISH = re.compile(r"\b(to serve|for serving|serving|garnish|optional|to finish|for dusting|dusting|for sprinkling)\b", re.I)
FAT_IDS = {"vegetable-oil", "olive-oil", "coconut-oil", "lard", "animal-fat", "ghee", "sesame-oil", "pork-fat"}


def primary_allergens(ids, ing_by_id):
    return [a for i in ids for a in ing_by_id[i]["allergens"]]


def primary_flags(ids, ing_by_id):
    return [f for i in ids for f in ing_by_id[i]["flags"]]


def build_lines(src, matcher, ing_by_id, added_each):
    """Convert source lines. Returns (lines, None) or (None, reason)."""
    lines, notes_estimated = [], False
    parts_total = 0.0
    for l in src["lines"]:
        if l["unit"] == "parts" and l["qty"]:
            ids = matcher.match(l["raw"])
            if not (ids and (ids[0] == "water" or (ids[0] in FAT_IDS and FRYING.search(l["raw"])))):
                parts_total += l["qty"]
    scale = None
    if parts_total:
        servings = src["servings"] or 4
        scale = servings * (src["targetPerServing"] or 300) / parts_total
        notes_estimated = True
        # A line that states its real weight ("pork shoulder, 2 kg") anchors the scale.
        for l in src["lines"]:
            m = re.search(r"(?<!per )\b(\d+(?:\.\d+)?)\s*(?:[-–]|to)?\s*(\d+(?:\.\d+)?)?\s*(kg|g)\b", l["raw"])
            if l["unit"] == "parts" and l["qty"] and m and not re.search(r"\beach\b|\bper\b", l["raw"]):
                w = (float(m.group(1)) + float(m.group(2) or m.group(1))) / 2 * (1000 if m.group(3) == "kg" else 1)
                if w >= 100:
                    scale = w / l["qty"]
                    break

    for l in src["lines"]:
        raw = l["raw"].strip()
        if not raw:
            continue
        ids = matcher.match(raw)
        if not ids:
            return None, f"unmatched ingredient: {raw}"
        note_main = re.split(r";|\bor\b|\bworks\b|\binstead\b", l["note"] or "")[0]
        issue = safety_issue(raw, ids, ing_by_id) or (safety_issue(note_main, ids, ing_by_id) if note_main.strip() else None)
        if issue:
            return None, f"safety check ({issue}): {raw}"
        # An alternative that isn't safe for Lauren ("sunflower or peanut oil"): say so.
        warn = []
        alt_text = " ".join(re.findall(r"\bor\b(.*)", raw.lower() + " ; " + (l["note"] or "").lower()))
        if re.search(r"peanut|groundnut|\bnuts?\b|almond|walnut|hazelnut|cashew|pistachio|pecan|pine ?nut", alt_text) \
                and not ({"nuts", "peanuts"} & set(primary_allergens(ids, ing_by_id))) \
                and "pine-nut" not in primary_flags(ids, ing_by_id):
            warn.append("the source also suggests a nut option; use the first one")
        if re.search(r"\bwheat|\bflour\b|barley|\brye\b|\bmalt|soy sauce|beer|\bbread|pasta|noodle", alt_text) \
                and "gluten" not in primary_flags(ids, ing_by_id) \
                and not any(ing_by_id[i].get("checkLabel") for i in ids) \
                and not re.search(r"gluten.free|rice|corn|chickpea|buckwheat|potato|tapioca|teff|soy flour", alt_text) \
                and "water" not in ids:
            warn.append("the source also suggests a gluten option; use the first one")
        unit, qty = l["unit"], l["qty"]
        if isinstance(unit, str) and unit.startswith("?"):
            return None, f"unknown unit '{unit[1:]}' for {raw}"
        primary = ing_by_id[ids[0]]
        line = {"id": primary["id"]}
        if unit == "parts":
            g = (qty or 0) * scale
            qty, unit = tidy_grams(g, primary) if g else (None, None)
        elif unit in ("cup", "lb", "oz", "stick"):
            qty, unit = tidy_grams(to_grams(qty, unit, primary), primary)
        elif unit == "g" and qty and src["source"] == "forkrecipe" and (qty <= 30 or primary["id"] in LIQUIDS):
            qty, unit = tidy_grams(qty, primary)     # "6 g garlic" -> "1 clove", "120 g vinegar" -> "120 ml"
        if qty is not None and unit == "each" and l["unit"] == "each":
            # "Pork knuckle, about 1 kg each" / "pork shoulder, 2–3 kg": use the stated weight.
            m = re.search(r"(?<!per )(?<!per)\b(\d+(?:[.,]\d+)?)\s*(?:[-–]|to)?\s*(\d+(?:[.,]\d+)?)?\s*(kg|g)\b(\s*each)?",
                          f"{raw} {l['note']}")
            if m and primary["aisle"] in ("meat-fish", "fruit-veg", "bakery"):
                lo_w = float(m.group(1).replace(",", "."))
                hi_w = float((m.group(2) or m.group(1)).replace(",", "."))
                per = (lo_w + hi_w) / 2 * (1000 if m.group(3) == "kg" else 1)
                total = per * qty if (m.group(4) or qty > 1 and per < 1500) else per
                qty, unit = tidy_grams(total, primary) if primary["aisle"] != "meat-fish" else (round(total / 50) * 50 or total, "g")
        if unit == "each" and "clove" in (primary.get("units") or {}) and re.search(r"\bcloves?\b", raw.lower()):
            unit = "clove"
        if qty is not None and unit == "each" and "each" not in (primary.get("units") or {}):
            if "clove" in (primary.get("units") or {}):
                unit = "clove"
            elif "sprig" in (primary.get("units") or {}):
                unit = "sprig"
            else:
                guess = EACH_BY_AISLE.get(primary["aisle"], 30)
                primary.setdefault("units", {})["each"] = guess
                added_each[primary["id"]] = guess
        if primary["id"] in STOCK_CUBES and unit in ("ml", "l", "g", "kg") and qty:
            ml = qty * (1000 if unit in ("l", "kg") else 1)
            qty, stock_note = stock_line(ml)
            unit = "each"
            line["note"] = stock_note
        if unit in ("kg", "l") and qty is not None:
            qty, unit = qty * 1000, "g" if unit == "kg" else "ml"
        if qty is not None:
            line["qty"] = round(qty, 2) if isinstance(qty, float) else qty
            line["unit"] = unit
        # Keep the source's wording where our ingredient name is more generic.
        words = raw if norm(raw) != norm(primary["name"]) else ""
        note = "; ".join(x for x in (words, l["note"]) if x)
        if note and "note" not in line:
            line["note"] = note[:140]
        elif note:
            line["note"] = f"{note[:100]}; {line['note']}"
        if l.get("size") == "large" and line.get("unit") == "each":
            line["note"] = (line.get("note", "") + "; large").strip("; ")
        if warn:
            line["note"] = "; ".join(([line["note"]] if line.get("note") else []) + warn)
        if GARNISH.search(raw) or GARNISH.search(l["note"]):
            line["optional"] = True
        g = grams_for(line.get("qty"), line.get("unit"), primary) or 0
        if primary["id"] in FAT_IDS and (g >= 200 or (g >= 80 and (FRYING.search(raw) or FRYING.search(l["note"])))):
            # Frying oil: only part of it ends up in the food.
            line["absorb"] = 0.15
            line["note"] = (line.get("note", "") + "; for frying (only some is absorbed)").strip("; ")
        lines.append(line)
        for extra in ids[1:]:
            ex = {"id": extra}
            if line.get("optional"):
                ex["optional"] = True
            lines.append(ex)
    # Merge "to taste" repeats of the same thing (salt in three steps, etc.).
    merged, seen_taste = [], set()
    for line in lines:
        if "qty" not in line and line["id"] in seen_taste:
            continue
        if "qty" not in line:
            seen_taste.add(line["id"])
        merged.append(line)
    return (merged, notes_estimated), None


def convert(src, matcher, ing_by_id, added_each):
    got, reason = build_lines(src, matcher, ing_by_id, added_each)
    if reason:
        return None, reason
    lines, estimated = got
    if not src["steps"]:
        return None, "no method steps"
    prefix = "ut" if src["source"] == "unitools" else "fr"
    ids = [l["id"] for l in lines]
    tools = infer_tools(src["toolText"])
    cat = src["category"]
    recipe = {
        "id": f"{prefix}-{slugify(src['srcId'])}",
        "name": src["name"].strip(),
        "description": src["description"],
        "cuisine": cuisine_for(src["cuisineRaw"]),
        "origin": src["origin"],
        "mealTypes": src["mealTypes"],
        "servings": int(src["servings"] or 4),
        "prepMins": int(src["prepMins"]), "cookMins": int(src["cookMins"]),
        "difficulty": src["difficulty"],
        "spice": max(src["spice"] or 0, guess_spice(ids)) if src["source"] == "unitools" else src["spice"],
        "cost": guess_cost(ids, ing_by_id),
        "tools": tools,
        "onePot": False,
        "batchCook": cat in ("soup",) or "slow-cooker" in tools,
        "freezerFriendly": cat in ("soup",),
        "goodForLeftovers": cat in ("soup",),
        "lunchbox": cat in ("salad",),
        "season": "all year",
        "tags": [t for t in dict.fromkeys(src["tags"]) if t and t.lower() != src["origin"].lower()][:5],
        "ingredients": lines,
        "steps": src["steps"],
        "source": {k: src["source_info"][k] for k in ("name", "url", "licence", "author")},
    }
    if src.get("nativeName") and src["nativeName"] != recipe["name"]:
        recipe["nativeName"] = src["nativeName"]
    if estimated:
        recipe["quantitiesEstimated"] = True
    if src.get("photo"):
        recipe["photo"] = src["photo"]
    if recipe_kcal_per_portion(recipe, ing_by_id) is None:
        return None, "an ingredient amount has no weight"
    if not fit_servings(recipe, ing_by_id):
        k = recipe_kcal_per_portion(recipe, ing_by_id)
        return None, f"implausible calories ({k:.0f} kcal per portion even after adjusting servings)"
    return recipe, None


def write_lines(path, items):
    """A JSON array with one compact item per line."""
    path.write_text("[\n" + ",\n".join(json.dumps(x, ensure_ascii=False, separators=(",", ":")) for x in items)
                    + "\n]\n", encoding="utf-8")


def main(fork_dir, unitools_json):
    ingredients, p2i, problems = load_ingredients()
    if problems:
        sys.exit("Ingredient table problems:\n  " + "\n  ".join(problems))
    ing_by_id = {i["id"]: i for i in ingredients}
    matcher = Matcher(p2i)
    added_each = {}

    ours = []
    index = json.loads((DATA / "recipes" / "index.json").read_text(encoding="utf-8"))
    own_batches = [b for b in index["batches"] if b.startswith("batch-")]
    for b in own_batches:
        ours += json.loads((DATA / "recipes" / b).read_text(encoding="utf-8"))
    taken = {name_key(r["name"]): r["id"] for r in ours}

    report = collections.defaultdict(list)
    out = {"unitools": [], "forkrecipe": []}
    fork, fork_skipped = import_forkrecipe.load(fork_dir)
    uni, uni_skipped = import_unitools.load(unitools_json)
    for slug, why in fork_skipped:
        report["fork_skipped"].append((slug, why))
    nutrition_gaps = []
    diet_mismatch = []
    for src in uni + fork:   # UniTools first: real quantities win a duplicate
        r, reason = convert(src, matcher, ing_by_id, added_each)
        if reason:
            report[f"{src['source']}_rejected"].append((src["srcId"], reason))
            continue
        key = name_key(r["name"])
        if key in taken:
            report[f"{src['source']}_duplicate"].append((src["srcId"], f"same dish as {taken[key]}"))
            continue
        taken[key] = r["id"]
        out[src["source"]].append(r)
        if src.get("srcNutrition"):
            ours_k = recipe_kcal_per_portion(r, ing_by_id) * r["servings"] / (src["servings"] or 1)
            theirs = src["srcNutrition"]["calories"]
            if theirs and abs(ours_k - theirs) / theirs > 0.4 and abs(ours_k - theirs) > 150:
                nutrition_gaps.append((r["id"], round(ours_k), theirs))
        if src.get("srcDiets") is not None:
            f = diet_facts(r, ing_by_id)
            for tag, ok in (("vegetarian", f["vegetarian"]), ("vegan", f["vegan"]), ("gluten-free", f["gf"])):
                if (tag in src["srcDiets"]) and not ok:
                    diet_mismatch.append((r["id"], f"source says {tag}, ours says not"))
                if tag == "vegetarian" and ok and tag not in src["srcDiets"] and "pescatarian" not in src["srcDiets"]:
                    diet_mismatch.append((r["id"], "ours says vegetarian, source doesn't"))

    # Gluten-free / nut-free versions of imported recipes.
    converted = {"unitools": [], "forkrecipe": []}
    for srcname, recipes in out.items():
        for r in recipes:
            f = diet_facts(r, ing_by_id)
            if f["gf"] and f["nf"]:
                continue
            v = make_free_version(r, ing_by_id)
            if not v:
                continue
            vf = diet_facts(v, ing_by_id)
            if not (vf["gf"] and vf["nf"]):   # e.g. other unsafe extras remain
                r["variants"] = [x for x in r.get("variants", []) if x["id"] != v["id"]] or None
                if r["variants"] is None:
                    del r["variants"]
                continue
            if not fit_servings(v, ing_by_id):
                r["variants"] = [x for x in r["variants"] if x["id"] != v["id"]]
                if not r["variants"]:
                    del r["variants"]
                continue
            converted[srcname].append(v)

    # Make every recipe's words match its safe ingredients (coeliac and nut
    # safety), then apply the hand-reviewed fixes in tools/recipe_fixes.json.
    text_fixed, dropped = 0, []
    for srcname in out:
        for r in out[srcname] + converted[srcname]:
            text_fixed += make_text_safe(r, ing_by_id)
        keep = []
        for v in converted[srcname]:
            if apply_fixes(v, ing_by_id) == "drop":
                dropped.append(v["id"])
            else:
                keep.append(v)
        converted[srcname] = keep
        for r in out[srcname]:
            if apply_fixes(r, ing_by_id) == "drop":
                sys.exit(f"recipe_fixes.json asks to drop {r['id']}, but only converted versions can be dropped")
            if r.get("variants"):
                r["variants"] = [x for x in r["variants"] if x["id"] not in dropped]
                if not r["variants"]:
                    del r["variants"]

    # Write ingredients (drop the importer-only "new" marker).
    used = {l["id"] for rs in list(out.values()) + list(converted.values()) for r in rs for l in r["ingredients"]}
    used |= {l["id"] for r in ours for l in r["ingredients"]}
    final_ings, new_used = [], 0
    for i in ingredients:
        is_new = i.pop("new", False)
        if is_new and i["id"] not in used:
            continue
        new_used += is_new
        final_ings.append(i)
    (DATA / "ingredients.json").write_text(
        "[\n" + ",\n".join("  " + json.dumps(i, ensure_ascii=False) for i in final_ings) + "\n]\n", encoding="utf-8")

    # Write batches: each original followed by its converted version.
    for folder in (DATA / "recipes", DATA / "steps"):
        for old in folder.glob("*.json"):
            if old.name.startswith(("unitools-", "fork-")):
                old.unlink()
    batches = list(own_batches)
    for srcname, prefix in (("unitools", "unitools"), ("forkrecipe", "fork")):
        by_orig = collections.defaultdict(list)
        for v in converted[srcname]:
            by_orig[v["convertedFrom"]].append(v)
        # A recipe and its converted version always share a file.
        chunk, chunks = [], []
        for r in out[srcname]:
            chunk += [r] + by_orig.get(r["id"], [])
            if len(chunk) >= BATCH_SIZE:
                chunks.append(chunk)
                chunk = []
        if chunk:
            chunks.append(chunk)
        for n, ch in enumerate(chunks, 1):
            name = f"{prefix}-{n:02d}.json"
            for r in ch:
                r.pop("convertedFrom", None)
            # Method steps go in a separate file, loaded when a recipe is opened,
            # so the recipe list starts quickly. One recipe per line keeps diffs readable.
            steps = {r["id"]: r.pop("steps") for r in ch}
            write_lines(DATA / "recipes" / name, ch)
            (DATA / "steps").mkdir(exist_ok=True)
            (DATA / "steps" / name).write_text(
                "{\n" + ",\n".join(f"{json.dumps(k)}:{json.dumps(v, ensure_ascii=False, separators=(',', ':'))}"
                                   for k, v in steps.items()) + "\n}\n", encoding="utf-8")
            batches.append(name)
    (DATA / "recipes" / "index.json").write_text(json.dumps({"batches": batches}, indent=2) + "\n", encoding="utf-8")

    # Report.
    def section(title, rows, limit=None):
        lines = [f"\n## {title} ({len(rows)})\n"]
        for a, b in rows[:limit] if limit else rows:
            lines.append(f"- `{a}`: {b}")
        if limit and len(rows) > limit:
            lines.append(f"- … and {len(rows) - limit} more")
        return lines

    reasons = collections.Counter(re.sub(r":.*", "", why) for k in ("unitools_rejected", "forkrecipe_rejected")
                                  for _, why in report[k])
    md = ["# Recipe import report", "",
          "Generated by `python tools/import_all.py`. Sources: ForkRecipe and UniTools, both CC BY-SA 4.0.", "",
          f"- UniTools: {len(uni)} read, {len(out['unitools'])} imported, {len(converted['unitools'])} "
          f"gluten-/nut-free versions added",
          f"- ForkRecipe: {len(fork) + len(fork_skipped)} read, {len(fork_skipped)} skipped as non-meals, "
          f"{len(out['forkrecipe'])} imported, {len(converted['forkrecipe'])} gluten-/nut-free versions added",
          f"- Ingredients in the master list: {len(final_ings)} ({new_used} added for the imports)",
          "", "Top rejection reasons: " + ", ".join(f"{r} ({n})" for r, n in reasons.most_common(8))]
    md += section("Rejected: UniTools", report["unitools_rejected"])
    md += section("Rejected: ForkRecipe", report["forkrecipe_rejected"])
    md += section("Duplicates skipped: UniTools", report["unitools_duplicate"])
    md += section("Duplicates skipped: ForkRecipe", report["forkrecipe_duplicate"])
    md += section("Calories differ a lot from the source's own figure (ours used)",
                  [(a, f"ours ≈{b} kcal, source {c} kcal per portion") for a, b, c in nutrition_gaps])
    md += section("Diet tag disagreements with the source (check the mapping)", diet_mismatch)
    md += section("Converted versions dropped by hand review (recipe_fixes.json)", [(d, "dropped") for d in dropped])
    md += section("Ingredients given a guessed weight per piece", [(k, f"{v} g each") for k, v in added_each.items()])
    md += section("ForkRecipe recipes skipped as components (sauces, stocks, drinks, breads)", report["fork_skipped"], 40)
    (ROOT / "tools" / "import_report.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    total = len(ours) + sum(len(v) for v in out.values()) + sum(len(v) for v in converted.values())
    print(f"imported: unitools {len(out['unitools'])} (+{len(converted['unitools'])} versions), "
          f"fork {len(out['forkrecipe'])} (+{len(converted['forkrecipe'])} versions); total recipes {total}")
    print("rejections:", dict(reasons.most_common(10)))
    print(f"nutrition gaps: {len(nutrition_gaps)}, diet mismatches: {len(diet_mismatch)}, guessed piece weights: {len(added_each)}")
    print(f"safety text rewrites: {text_fixed} recipes; versions dropped by review: {len(dropped)}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
