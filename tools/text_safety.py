"""Make a recipe's WORDS match its safe ingredients.

Used by tools/import_all.py on every imported recipe and converted version.
For a recipe that is gluten-free (or nut-free) by its main ingredients:

1. Optional extras that aren't safe ("Naan; to serve", "flour, for dusting")
   are swapped for the safe version, or dropped if there isn't one.
2. Gluten words in the name/description/notes/steps are rewritten to the safe
   version: soy sauce -> tamari, "lightly floured surface" -> "surface dusted
   with gluten-free flour", "serve with crusty bread" -> "serve with
   gluten-free bread", and so on. Nut words in nut-free recipes likewise.
3. Hand-reviewed fixes from tools/recipe_fixes.json are applied last.

tools/safety_scan.py then checks that nothing unsafe is left.
"""

import json
import re
from pathlib import Path

import safety_scan as scan

TOOLS = Path(__file__).resolve().parent
FIXES = json.loads((TOOLS / "recipe_fixes.json").read_text(encoding="utf-8"))

GF_FLOURS = ["gf-flour", "rice-flour", "glutinous-rice-flour", "gram-flour", "buckwheat-flour", "potato-starch",
             "tapioca-starch", "masa-harina", "cornmeal", "teff-flour", "coconut-flour", "cassava-flour", "sorghum-flour"]

# Optional extras: unsafe id -> safe id (None = drop the line).
OPTIONAL_GF = {"plain-flour": "gf-flour", "strong-flour": "gf-flour", "bread": "gf-bread", "baguette": "gf-bread",
               "brioche": "gf-bread", "rye-bread": "gf-bread", "flatbread": "gf-flatbread", "biscuits": "gf-biscuits",
               "soy-sauce": "tamari", "dark-soy": "tamari", "egg-noodles": "rice-noodles", "spaghetti": "gf-spaghetti",
               "dried-pasta": "gf-pasta", "porridge-oats": "gf-oats", "breadcrumbs": "gf-breadcrumbs",
               "cornflakes": None, "couscous": "quinoa", "bulgur": "quinoa", "tortilla-wraps": "corn-tortillas"}
OPTIONAL_NF = {"walnuts": "pumpkin-seeds", "pecans": "pumpkin-seeds", "pistachios": "pumpkin-seeds",
               "almonds": "sunflower-seeds", "hazelnuts": "sunflower-seeds", "cashews": "sunflower-seeds",
               "peanuts": "sunflower-seeds", "pine-nuts": "sunflower-seeds", "peanut-butter": "sunflower-butter",
               "peanut-oil": "vegetable-oil"}


def _gluten(ing):
    return "gluten" in ing["flags"] or "gluten" in ing["allergens"]


def _nuts(ing):
    return bool({"nuts", "peanuts"} & set(ing["allergens"])) or "pine-nut" in ing["flags"]


def _cap(src, rep):
    return rep[:1].upper() + rep[1:] if src[:1].isupper() else rep


# ------------------------------------------------------------------ word rewriting

def _protect(text, recipe_id):
    """Hide allowed phrases (figures of speech, stated swaps) from the rewrites."""
    kept = []

    def hide(m):
        kept.append(m.group(0))
        return f"\x00{len(kept) - 1}\x00"
    for p in scan.ALLOW_PHRASES + scan.ALLOW_RECIPE.get(recipe_id, []):
        text = re.sub(p, hide, text, flags=re.I)
    return text, kept


def _restore(text, kept):
    while "\x00" in text:
        text = re.sub(r"\x00(\d+)\x00", lambda m: kept[int(m.group(1))], text)
    return text


def _qualified(text, start):
    return bool(scan.GF_QUALIFIER.search(text[max(0, start - 30):start]))


def gluten_rules(ids, ing_by_id):
    """(regex, replacement-function) pairs for a gluten-free recipe."""
    has = lambda *xs: any(x in ids for x in xs)
    flours = [f for f in GF_FLOURS if f in ids]
    if "gf-flour" in flours or len(flours) != 1:
        flour_name = "gluten-free flour"
    else:
        flour_name = ing_by_id[flours[0]]["name"].lower()
    grain = "quinoa" if has("quinoa") else "brown rice" if has("brown-rice") else "rice"

    def plain(rep):
        return lambda m, t: _cap(m.group(0), rep)

    def unless_covered(word_key, rep):
        def f(m, t):
            if scan.COVERED_BY.get(word_key, set()) & ids or _qualified(t, m.start()):
                return m.group(0)
            return _cap(m.group(0), rep(m) if callable(rep) else rep)
        return f

    def flour(m, t):
        if _qualified(t, m.start()):
            return m.group(0)
        return _cap(m.group(0), flour_name + ("s" if m.group(0).lower().endswith("s") else ""))

    return [
        (r"\bboth soy sauces\b", plain("the tamari")),
        (r"\bsweet soy sauce\b", unless_covered("-", "gluten-free sweet soy sauce")),
        (r"\b(light |dark |regular |thin |thick |chinese |japanese )?soy sauces?\b", unless_covered("-", "tamari")),
        (r"\bshoyu\b", plain("tamari")),
        (r"\b(a |an |the )?(very lightly |lightly |well |generously |liberally |heavily )?floured "
         r"(clean |cool |dry |wooden |marble |large )?(work surface|work top|worktop|surface|board|counter|countertop|"
         r"bench|table)\b",
         lambda m, t: _cap(m.group(0), f"{m.group(1) or ''}{(m.group(3) or '')}{m.group(4)} dusted with gluten-free flour")),
        (r"\b(very lightly |lightly |well |generously |liberally )?floured "
         r"(?!(?:and|or|with|then|in|on|to|the|a|an|until|for|is|it|side|sides|all)\b)([a-z]+)\b",
         lambda m, t: _cap(m.group(0), f"{m.group(2)} dusted with gluten-free flour")),
        # Anything else "floured" (e.g. "a greased and floured 9x13-inch pan").
        (r"\bfloured\b(?! \(use)", lambda m, t: m.group(0) + " (use gluten-free flour)"),
        (r"\b(plain |all-purpose |all purpose |wheat |white |00 |\"00\" |cake |bread |strong |wholemeal |whole wheat |self-raising )?flours?\b", flour),
        # Bread is always named as gluten-free: a gluten-free bread line doesn't excuse "serve with rye bread".
        (r"\b(crusty |warm |good |fresh |toasted |grilled |rustic |dark |white |black |country |sourdough |rye |corn |"
         r"day-old |stale |thick |sliced |plenty of |french )*(bread|breads|baguettes?|bread rolls?)\b",
         lambda m, t: m.group(0) if _qualified(t, m.start()) else _cap(m.group(0), "gluten-free bread")),
        (r"\b(soft |crusty |burger |brioche |hot dog )*(buns?|loaf|loaves)\b(?! (tin|pan))",
         unless_covered("bun", lambda m: "gluten-free " + m.group(0).lower())),
        (r"\b(warm |hot |toasted |thin |soft )*(flatbreads?|pittas?|pitas?|pita bread|pitta bread|naans?|lavash|"
         r"chapatis?|rotis?|parathas?|injera|tortilla wraps?)\b",
         lambda m, t: m.group(0) if (_qualified(t, m.start()) or ("injera" in m.group(0).lower() and "teff-flour" in ids))
         else _cap(m.group(0), "gluten-free flatbread")),
        (r"\btortilla chips\b", unless_covered("-", "corn tortilla chips (check the label)")),
        (r"\b(flour )?tortillas?\b", unless_covered("tortilla", lambda m: "corn tortilla" + ("s" if m.group(0).endswith("s") else ""))),
        (r"\b(pearl )?couscous\b", unless_covered("-", grain)),
        (r"\b(fine |coarse )?bulgu?a?r( wheat)?\b|\bcracked wheat\b|\bwheat berries\b", unless_covered("-", grain)),
        (r"\b(pearl )?barley\b|\bfarro\b|\bfreekeh\b|\bspelt\b", unless_covered("-", grain)),
        (r"\b(whole |the )?wheat\b", unless_covered("-", lambda m: (m.group(1) or "") + grain)),
        (r"\bpanko( breadcrumbs)?\b",
         lambda m, t: m.group(0) if _qualified(t, m.start()) else _cap(m.group(0), "gluten-free breadcrumbs")),
        (r"\bbreadcrumbs\b", unless_covered("breadcrumb", "gluten-free breadcrumbs")),
        (r"\bsemolina (couscous|quinoa|rice|grains?)\b", lambda m, t: m.group(1)),
        (r"\bsemolina\b", unless_covered("-", "fine polenta")),
        (r"\b(buttered )?(filo|phyllo)\b(?! pastry)",
         lambda m, t: m.group(0) if _qualified(t, m.start()) else _cap(m.group(0), (m.group(1) or "") + "gluten-free filo")),
        (r"\bramen\b", unless_covered("ramen", "gluten-free ramen")),
        (r"\bcroutons?\b", unless_covered("-", "gluten-free croutons")),
        (r"\b(egg |wheat |ramen |udon |soba )?noodles\b", unless_covered("noodle", "rice noodles")),
        (r"\bpasta\b", unless_covered("pasta", "gluten-free pasta")),
        (r"\b(spaghetti|linguine|tagliatelle|fettuccine|penne|macaroni|pappardelle|rigatoni|fusilli)\b",
         lambda m, t: m.group(0) if (scan.COVERED_BY.get(m.group(0).lower(), {"gf-pasta", "gf-spaghetti"}) & ids
                                     or _qualified(t, m.start()))
         else _cap(m.group(0), "gluten-free " + m.group(0).lower())),
        (r"\borzo\b", unless_covered("-", "gluten-free orzo")),
        (r"\bgnocchi\b", unless_covered("gnocchi", "gluten-free gnocchi")),
        (r"\b(shortcrust |puff |filo |phyllo )?(pastry|pastries)\b",
         lambda m, t: m.group(0) if ({"gf-pastry", "gf-flour"} & ids or _qualified(t, m.start()))
         else _cap(m.group(0), "gluten-free " + m.group(0).lower())),
        # Bought products are always named as gluten-free, even when the ingredient line already is.
        (r"\s*\bor langue de chat\b", lambda m, t: ""),
        (r"\b(lobster |nut |crab )(crackers?)\b", lambda m, t: m.group(0)),   # tools, not food
        (r"\b(digestive |graham |shortbread |milk |sweet )?(biscuits?|crackers?|cookies)\b",
         lambda m, t: m.group(0) if (_qualified(t, m.start()) or ("gf-flour" in ids and not m.group(1)))
         else _cap(m.group(0), "gluten-free " + m.group(0).lower())),
        (r"\b(savoiardi|ladyfingers|sponge fingers)\b",
         lambda m, t: m.group(0) if _qualified(t, m.start()) else _cap(m.group(0), "gluten-free sponge fingers")),
        (r"\b(dark |pale |light |brown )?(beers?|ales?|lager|stout)\b",
         lambda m, t: m.group(0) if _qualified(t, m.start()) else _cap(m.group(0), "gluten-free beer")),
        (r"\bmalt([- ])vinegar\b", lambda m, t: _cap(m.group(0), f"cider{m.group(1)}vinegar")),
        (r"\bhoisin( sauce)?\b", lambda m, t: m.group(0) if _qualified(t, m.start()) else _cap(m.group(0), "gluten-free hoisin")),
        (r"\boyster sauce\b", lambda m, t: m.group(0) if _qualified(t, m.start()) else _cap(m.group(0), "gluten-free oyster sauce")),
        (r"\bsoba( noodles?)?\b", lambda m, t: m.group(0) if _qualified(t, m.start()) else _cap(m.group(0), "rice noodles")),
        (r"\bworcestershire( sauce)?\b", unless_covered("-", "gluten-free Worcestershire sauce")),
    ]


def nut_rules(ids, ing_by_id):
    seed = ("sunflower seed" if {"sunflower-seeds", "sunflower-butter"} & ids
            else "pumpkin seed" if "pumpkin-seeds" in ids else "toasted seed")
    seeds = f"{seed}s" if seed != "toasted seed" else "toasted seeds"
    return [
        (r"\b(ground |toasted )?(almond|hazelnut|walnut|pistachio|nut) (flour|meal)\b", lambda m, t: _cap(m.group(0), f"ground {seeds}")),
        (r"\bground (almonds|hazelnuts|walnuts|pistachios)\b", lambda m, t: _cap(m.group(0), f"ground {seeds}")),
        (r"\s*\bor amarett[oi]( biscuits)?\b", lambda m, t: ""),
        (r"\bamarett[oi]( biscuits)?\b", lambda m, t: _cap(m.group(0), "gluten-free sponge fingers")),
        (r"\b((sunflower|pumpkin) seeds? |(almond|hazelnut|walnut|pistachio|nut) )?praline\b",
         lambda m, t: _cap(m.group(0), f"{seed} praline")),
        # The converter may already have written "sunflower seeds flour" for "hazelnut flour".
        (r"\b(toasted )?(sunflower|pumpkin) seeds? (flour|meal)\b", lambda m, t: _cap(m.group(0), f"ground {m.group(2)} seeds")),
        # Alternatives offered in notes: "(peanut, vegetable, or grapeseed)".
        (r"\b(peanut|groundnut)( oil)?(, or |, | or )", lambda m, t: ""),
        (r"(, or |, | or )(peanut|groundnut)( oil)?\b", lambda m, t: ""),
        (r"\b(peanut|groundnut) oil\b", lambda m, t: _cap(m.group(0), "vegetable oil")),
        (r"\b(almond|hazelnut|walnut|pistachio|macadamia|pecan|cashew|nut) oils?\b", lambda m, t: _cap(m.group(0), "sunflower oil")),
        (r"\balmond milk\b", lambda m, t: _cap(m.group(0), "soya milk")),
        # A nut used as an adjective: "walnut sauce" -> "pumpkin seed sauce".
        (r"\b(walnut|almond|hazelnut|pistachio|cashew|pecan|macadamia|pine ?nut)s?\b"
         r"(?= (sauce|cream|paste|butter|dressing|crust|top|topping|filling|mixture|crumb|crumble|pesto|milk|brittle|"
         r"crunch|garnish|dacquoise|cake|tart|biscuits?|cookies|bread|stew|soup))",
         lambda m, t: _cap(m.group(0), seed)),
        (r"\b(smooth |crunchy |natural )?(peanut|groundnut) (butter|paste)\b", lambda m, t: _cap(m.group(0), "sunflower seed butter")),
        (r"\b(peanut|groundnut)s?\b(?= (sauce|dressing|mixture|stew|soup|gravy|base|cream))",
         lambda m, t: _cap(m.group(0), "sunflower seed")),
        (r"\b(roasted |toasted |crushed |chopped |salted |raw )*(peanuts|groundnuts)\b",
         lambda m, t: _cap(m.group(0), f"toasted {seed}s")),
        (r"\b(flaked |slivered |sliced |blanched |toasted |chopped |ground |whole |roasted )*"
         r"(almonds?|walnuts?|pecans?|hazelnuts?|pistachios?|cashews?|macadamias?|pine ?nuts?)\b",
         lambda m, t: _cap(m.group(0), seeds)),
        (r"\b(peanut|groundnut)s?\b", lambda m, t: _cap(m.group(0), f"{seed}" + ("s" if m.group(0).lower().endswith("s") else ""))),
        (r"\b(toasted |chopped |mixed |roasted )*nuts\b", lambda m, t: _cap(m.group(0), seeds)),
    ]


def rewrite(text, rules, recipe_id):
    if not text:
        return text
    t, kept = _protect(text, recipe_id)
    for rx, fn in rules:
        t = re.sub(rx, lambda m: fn(m, t), t, flags=re.I)
    return _restore(t, kept)


# ------------------------------------------------------------------ the whole recipe

def _facts(recipe, ing_by_id):
    main = [ing_by_id[l["id"]] for l in recipe["ingredients"] if not l.get("optional")]
    return not any(_gluten(i) for i in main), not any(_nuts(i) for i in main)


def make_text_safe(recipe, ing_by_id):
    """Rewrite a recipe in place. Returns True if anything changed."""
    before = json.dumps(recipe, sort_keys=True, ensure_ascii=False)
    gf, nf = _facts(recipe, ing_by_id)
    if not (gf or nf):
        return False
    rid = recipe["id"]

    # 1. Optional extras.
    lines = []
    for line in recipe["ingredients"]:
        ing = ing_by_id[line["id"]]
        if line.get("optional") and ((gf and _gluten(ing)) or (nf and _nuts(ing))):
            table = OPTIONAL_GF if (gf and _gluten(ing)) else OPTIONAL_NF
            repl = table.get(line["id"], None)
            if repl is None or (gf and _gluten(ing_by_id[repl])) or (nf and _nuts(ing_by_id[repl])):
                continue   # drop it; the words are fixed below
            line = dict(line, id=repl)
        lines.append(line)
    recipe["ingredients"] = lines
    ids = {l["id"] for l in lines}

    rules = (nut_rules(ids, ing_by_id) if nf else []) + (gluten_rules(ids, ing_by_id) if gf else [])

    # 2. Words. A converted version's description ends with the stated swaps; keep those as written.
    desc = recipe.get("description") or ""
    m = re.search(r"\s*This (gluten|nut)[^.]*version (uses|leaves)[^.]*\.$", desc)
    head, tail = (desc[:m.start()], desc[m.start():]) if m else (desc, "")
    recipe["description"] = rewrite(head, rules, rid) + tail
    base_name = re.sub(r"\s*\((gluten|nut)[^)]*\)$", "", recipe["name"])
    recipe["name"] = rewrite(base_name, rules, rid) + recipe["name"][len(base_name):]
    for line in recipe["ingredients"]:
        if line.get("note"):
            line["note"] = rewrite(line["note"], rules, rid)
    recipe["steps"] = [rewrite(s, rules, rid) for s in recipe.get("steps", [])]

    # Words that now ask for gluten-free flour need it on the list (as an optional dusting).
    text = " ".join([recipe["description"]] + recipe["steps"])
    if gf and "gluten-free flour" in text.lower() and not ({"gf-flour"} & ids):
        recipe["ingredients"].append({"id": "gf-flour", "qty": 2, "unit": "tbsp", "optional": True,
                                      "note": "for dusting"})
    if gf and re.search(r"\btamari\b", text, re.I) and "tamari" not in ids:
        recipe["ingredients"].append({"id": "tamari", "qty": 1, "unit": "tbsp", "optional": True, "note": "to taste"})
    # Words now say "seeds" where nuts were (often an optional garnish that was dropped): list them.
    if nf and re.search(r"\bseeds\b", text, re.I) and not ({"sunflower-seeds", "pumpkin-seeds", "mixed-seeds",
                                                            "sunflower-butter", "sesame-seeds"} & ids):
        recipe["ingredients"].append({"id": "mixed-seeds", "qty": 2, "unit": "tbsp", "optional": True,
                                      "note": "toasted, to scatter (instead of nuts)"})
    return json.dumps(recipe, sort_keys=True, ensure_ascii=False) != before


def apply_fixes(recipe, ing_by_id):
    """Hand-reviewed per-recipe fixes. Returns 'drop' if the recipe should be removed."""
    fix = FIXES["fixes"].get(recipe["id"])
    if not fix:
        return None
    if fix.get("drop"):
        return "drop"
    for field in ("name", "description"):
        for rx, rep in fix.get("subs", []):
            recipe[field] = re.sub(rx, rep, recipe.get(field) or "")
    recipe["steps"] = [s for s in recipe.get("steps", [])]
    for rx, rep in fix.get("subs", []):
        recipe["steps"] = [re.sub(rx, rep, s) for s in recipe["steps"]]
        for line in recipe["ingredients"]:
            if line.get("note"):
                line["note"] = re.sub(rx, rep, line["note"])
    for drop_id in fix.get("removeIngredients", []):
        recipe["ingredients"] = [l for l in recipe["ingredients"] if l["id"] != drop_id]
    for line in fix.get("addIngredients", []):
        if line["id"] not in {l["id"] for l in recipe["ingredients"]}:
            recipe["ingredients"].append(dict(line))
    for old, new in fix.get("swapIngredients", {}).items():
        for line in recipe["ingredients"]:
            if line["id"] == old:
                line["id"] = new
    return None
