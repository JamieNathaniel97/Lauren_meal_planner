"""Coeliac and nut safety scan of recipe TEXT.

Diet tags come from the ingredients, but a recipe's words can still mislead:
a gluten-free version whose method says "add the soy sauce", or a nut-free one
that says "scatter with almonds". For every recipe that is gluten-free and/or
nut-free by its ingredients, this checks the name, description, ingredient
notes and method steps for gluten words (gluten-free recipes) and nut words
(nut-free recipes) that aren't clearly the safe version.

    python tools/safety_scan.py           list every problem (exit 1 if any)
    python tools/safety_scan.py --test    run the built-in tests

tools/validate.py runs this too, so validation fails on any problem.

Reviewed exceptions:
  ALLOW_PHRASES   harmless figures of speech, removed before scanning
  ALLOW_RECIPE    per-recipe phrases reviewed by hand
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

# Harmless wording, removed from the text before it's scanned (case-insensitive).
ALLOW_PHRASES = [
    r"hazelnut[- ]?(brown|gold|golden|coloured|colored|colou?r)", r"(butter|it) to (a )?hazelnut\b(?![- ](oil|flour|paste|butter|meal))",
    r"noisette", r"nutty", r"nuttiness", r"(lobster|nut|crab) ?crackers?", r"nutcrackers?",
    r"walnut[- ]sized?", r"(size|sized?) of (a |small |large )?(walnut|hazelnut|almond)s?",
    r"(smells?|smelling) (faintly )?(like|of) (toasted |roasted |brown(ed)? )*(hazelnuts?|nuts|almonds?)",
    r"(aroma|scent|taste|flavou?r)s? of (toasted |roasted )*(hazelnuts?|nuts|almonds?)",
    r"almond[- ]shaped", r"almond bitterness", r"\bbitter almond (note|flavou?r)s?",
    r"(resembles?|resembling|look like|looks like|like|texture of|until it is like) (very |fine |coarse |damp |wet |pea-sized |coarse, pea-sized )*breadcrumbs",
    r"breadcrumb (texture|consistency)", r"do not add breadcrumbs", r"no breadcrumbs",
    r"without (any )?(flour|breadcrumbs|bread|wheat)", r"no flour", r"not fine flour", r"un-?floured",
    r"flour(-|\s)?free", r"nut[- ]free", r"wheat[- ]free",
    r"substitute with flour", r"floury (smell|streaks?|texture|potatoes?)", r"raw floury smell",
    r"coconut\w*", r"nutmeg", r"butternut", r"doughnuts?", r"water chestnuts?", r"chestnut mushrooms?",
    r"nut of butter", r"knob of butter", r"chestnut[- ]brown", r"\b(no|without) (pea)?nuts\b",
    r"without (any )?(added )?(eggs? or )?(bread|breadcrumbs?|flour)", r"floured \(use gluten-free flour\)", r"pineapple", r"pine needles?",
    r"rice paper", r"rice wine", r"breadfruit", r"bread ?(and |& )?butter pickles?",
    r"as (thin|thick) as (a )?pasta( sheet)?", r"pasta[- ]like", r"\bpastry (cream|bag|brush|cutter|board|scraper)",
    r"(ice|egg|choux|crème|creme) pastry",  # choux made with GF flour is checked through the flour word
    r"bread knife", r"bread machine", r"loaf (tin|pan)", r"(serrated|bread) knife", r"bread-and-butter pudding dish",
    r"(not|no|without) (one |a |any )?(grain|trace|gram|scrap|speck|pinch) of (flour|wheat)",
    r"instead of [^.;]*",   # a stated swap: "sunflower seeds instead of walnuts"
    r"rather than [^.;,()]*", r"in place of [^.;,()]*",
]

# Reviewed by hand: recipe id -> phrases that are fine in that recipe
# (the "allow" entries in tools/recipe_fixes.json).
_FIXES = Path(__file__).resolve().parent / "recipe_fixes.json"
ALLOW_RECIPE = {rid: f["allow"] for rid, f in
                (json.loads(_FIXES.read_text(encoding="utf-8"))["fixes"].items() if _FIXES.exists() else [])
                if f.get("allow")}

GLUTEN = re.compile(
    r"\b(wheat|flours?|floured|flouring|breadcrumbs?|panko|bread|breads|loaf|baguette|brioche|croutons?|"
    r"pastry|pastries|shortcrust|puff pastry|filo|phyllo|soy sauces?|shoyu|couscous|bulgu?a?r|barley|rye|spelt|"
    r"semolina|beers?|ales?|lager|stout|malt|malted|seitan|udon|ramen|soba|langue de chat|orzo|pasta|noodles?|spaghetti|linguine|"
    r"tagliatelle|fettuccine|penne|macaroni|lasagne|gnocchi|tortillas?|pittas?|pitas?|naan|chapatis?|rotis?|bhaturas?|puris?|kulchas?|"
    r"flatbreads?|crackers?|biscuits?|cookies|savoiardi|ladyfingers|sponge fingers|cake crumbs|hoisin|"
    r"oyster sauce|worcestershire|farro|freekeh|wheat berries|crumpets?|bagels?|buns?|loaves|dumpling wrappers?)\b",
    re.I)
NUTS = re.compile(
    r"\b(peanuts?|peanut butter|groundnuts?|almonds?|amarett[oi]s?|cashews?|walnuts?|pecans?|pistachios?|"
    r"hazelnuts?|macadamias?|brazil nuts?|pine ?nuts?|pignoli|praline|marzipan|frangipane|nougat|satay|"
    r"pesto|nut butters?|nut oils?|nuts|candlenuts?|gianduja|nutella|chestnuts?)\b", re.I)

# A gluten word is fine right after one of these qualifiers ("gluten-free pasta", "rice flour").
GF_QUALIFIER = re.compile(
    r"(gluten[- ]free|gf|rice|corn|maize|chickpea|gram|buckwheat|teff|tapioca|potato|cassava|coconut|"
    r"sorghum|millet|quinoa|soy|soya|banana|arrowroot|glass|sweet potato|kelp|mung bean|bean thread|"
    r"cellophane|shirataki|courgette|zucchini|cauliflower|lettuce|seeds?|"
    r"almond|hazelnut|walnut|pistachio|chestnut|nut)[- ]((?!or |and |with )\w+[- ])?$", re.I)

# Words that are fine in a gluten-free recipe whose own ingredient is the GF version,
# e.g. "drain the pasta" when the ingredient list says gluten-free pasta.
COVERED_BY = {
    "pasta": {"gf-pasta", "gf-spaghetti", "gf-lasagne"},
    "spaghetti": {"gf-spaghetti"}, "linguine": {"gf-spaghetti"}, "lasagne": {"gf-lasagne"},
    "penne": {"gf-pasta"}, "macaroni": {"gf-pasta"}, "tagliatelle": {"gf-pasta", "gf-spaghetti"},
    "fettuccine": {"gf-pasta", "gf-spaghetti"},
    "ramen": {"rice-noodles", "gf-ramen-noodles"},
    "noodle": {"rice-noodles", "glass-noodles", "gf-ramen-noodles", "gf-udon", "soba-gf", "sweet-potato-noodles",
               "rice-vermicelli", "rice-sticks", "kelp-noodles"},
    "gnocchi": {"gf-gnocchi"},
    "tortilla": {"corn-tortillas"},
    "bread": {"gf-bread"}, "breadcrumb": {"gf-breadcrumbs"},
    "loaf": {"gf-bread", "gf-flour"}, "loaves": {"gf-bread", "gf-flour"}, "bun": {"gf-bread", "gf-flour"},
    "pastry": {"gf-pastry", "gf-flour"}, "shortcrust": {"gf-pastry", "gf-flour"}, "puff pastry": {"gf-pastry"},
    # Home-made from gluten-free flour. Bought biscuits, beer, hoisin and oyster sauce must say "gluten-free".
    "biscuit": {"gf-flour"}, "cracker": {"gf-flour"}, "cookies": {"gf-flour"},
    "wrap": {"corn-tortillas", "rice-paper"},
}


def _singular(w):
    w = w.lower()
    for a, b in (("pastries", "pastry"), ("cookies", "cookies"), ("noodles", "noodle"), ("breadcrumbs", "breadcrumb"),
                 ("buns", "bun"), ("loaves", "loaves")):
        if w == a:
            return b
    return w[:-1] if w.endswith("s") and w[:-1] in COVERED_BY else w


def load_all():
    ings = {i["id"]: i for i in json.loads((DATA / "ingredients.json").read_text(encoding="utf-8"))}
    index = json.loads((DATA / "recipes" / "index.json").read_text(encoding="utf-8"))
    recipes = []
    for b in index["batches"]:
        batch = json.loads((DATA / "recipes" / b).read_text(encoding="utf-8"))
        sp = DATA / "steps" / b
        steps = json.loads(sp.read_text(encoding="utf-8")) if sp.exists() else {}
        for r in batch:
            if "steps" not in r:
                r = dict(r, steps=steps.get(r["id"], []))
            recipes.append(r)
    return ings, recipes


def facts(recipe, ings):
    flags, allergens = set(), set()
    for line in recipe["ingredients"]:
        if line.get("optional"):
            continue
        i = ings[line["id"]]
        flags |= set(i["flags"])
        allergens |= set(i["allergens"])
    gf = "gluten" not in flags and "gluten" not in allergens
    nf = not ({"nuts", "peanuts"} & allergens) and "pine-nut" not in flags
    return gf, nf


def texts(recipe, ings):
    yield "name", recipe.get("name", "")
    yield "description", recipe.get("description", "")
    for line in recipe["ingredients"]:
        if line.get("note"):
            yield f"note on {line['id']}", line["note"]
    for n, s in enumerate(recipe.get("steps", []), 1):
        yield f"step {n}", s if isinstance(s, str) else json.dumps(s)


def strip_allowed(text, recipe_id):
    for p in ALLOW_PHRASES + ALLOW_RECIPE.get(recipe_id, []):
        text = re.sub(p, " ", text, flags=re.I)
    return text


def scan_recipe(recipe, ings):
    """Problems as (where, word, context) for one recipe."""
    gf, nf = facts(recipe, ings)
    if not (gf or nf):
        return []
    ids = {l["id"] for l in recipe["ingredients"]}
    out = []
    for where, raw in texts(recipe, ings):
        if where == "name":
            # "(gluten-free)" in a name is the label itself.
            raw = re.sub(r"\((gluten|nut)[^)]*\)", " ", raw)
        t = strip_allowed(raw, recipe["id"])
        if gf:
            for m in GLUTEN.finditer(t):
                w = m.group(0)
                if GF_QUALIFIER.search(t[max(0, m.start() - 30):m.start()]):
                    continue
                if re.match(r"\s*\(gluten[- ]free", t[m.end():], re.I):   # "oyster sauce (gluten-free)"
                    continue
                if COVERED_BY.get(_singular(w), set()) & ids:
                    continue
                if w.lower().startswith("tortilla") and recipe.get("cuisine") == "spanish" and "eggs" in ids:
                    continue   # a Spanish tortilla is a potato omelette
                out.append((where, w, t[max(0, m.start() - 50):m.end() + 40].strip()))
        if nf:
            for m in NUTS.finditer(t):
                w = m.group(0)
                if re.search(r"(seeds?|sunflower|pumpkin|tiger)[- ]$", t[max(0, m.start() - 12):m.start()], re.I):
                    continue
                out.append((where, w, t[max(0, m.start() - 50):m.end() + 40].strip()))
    return out


def scan(ings=None, recipes=None):
    if ings is None:
        ings, recipes = load_all()
    problems = []
    for r in recipes:
        for where, w, ctx in scan_recipe(r, ings):
            problems.append((r["id"], where, w, ctx))
    return problems


# ------------------------------------------------------------------ tests

def _tests():
    ings = {
        "gf-flour": {"flags": [], "allergens": []}, "plain-flour": {"flags": ["gluten"], "allergens": ["gluten"]},
        "gf-pasta": {"flags": [], "allergens": []}, "tamari": {"flags": [], "allergens": ["soya"]},
        "sunflower-seeds": {"flags": [], "allergens": []}, "walnuts": {"flags": [], "allergens": ["nuts"]},
        "egg": {"flags": ["egg"], "allergens": ["eggs"]},
    }

    def r(steps, ingredients=("egg",), name="Test"):
        return {"id": "t", "name": name, "description": "", "steps": steps,
                "ingredients": [{"id": i} for i in ingredients]}

    cases = [
        # (recipe, expected number of problems, label)
        (r(["Add the soy sauce."]), 1, "soy sauce in a GF recipe"),
        (r(["Add the tamari."]), 0, "tamari is fine"),
        (r(["Roll out on a lightly floured surface."]), 1, "floured surface"),
        (r(["Roll out on a surface dusted with gluten-free flour."]), 0, "GF-dusted surface"),
        (r(["Add the rice flour and cornflour."]), 0, "qualified flours"),
        (r(["Drain the pasta."], ("gf-pasta",)), 0, "pasta covered by GF pasta ingredient"),
        (r(["Drain the pasta."]), 1, "pasta with no GF pasta ingredient"),
        (r(["Serve with crusty bread."]), 1, "bread serving suggestion"),
        (r(["Serve with gluten-free bread."]), 0, "GF bread suggestion"),
        (r(["Scatter with the walnuts."]), 1, "walnuts in a NF recipe"),
        (r(["Scatter with the walnuts."], ("walnuts",)), 0, "walnuts in a recipe that isn't NF"),
        (r(["Cook until hazelnut-brown and smelling of toasted hazelnuts."]), 0, "figures of speech"),
        (r(["Roll into walnut-sized balls."]), 0, "walnut-sized"),
        (r(["Rub in until it resembles fine breadcrumbs."]), 0, "rubbed-in texture"),
        (r(["Toast the sunflower seeds instead of walnuts."]), 0, "stated swap"),
        (r(["Grate over nutmeg; add coconut milk; roast the butternut."]), 0, "false friends"),
        (r(["Beat in the praline paste."]), 1, "praline"),
        (r(["Add the almonds."], ("plain-flour",)), 1, "nut word in NF-only recipe"),
        (r(["Add the bread."], ("walnuts",)), 1, "gluten word in GF-only recipe"),
        (r(["x"], name="Peanut stew (nut-free)"), 1, "nut word in a name"),
        (r(["x"], name="Fish stew (gluten-free)"), 0, "label in a name"),
        (r(["Add both soy sauces."]), 1, "plural soy sauces"),
    ]
    failed = 0
    for rec, want, label in cases:
        got = scan_recipe(rec, ings)
        ok = len(got) == want
        failed += not ok
        print(("PASS" if ok else "FAIL"), label, "" if ok else f"(expected {want}, got {len(got)}: {got})")

    # The automatic rewrites (tools/text_safety.py) must leave nothing for the scan to find.
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import text_safety
    ings.update({"mixed-seeds": {"flags": [], "allergens": []}, "gf-bread": {"flags": [], "allergens": []},
                 "rice-noodles": {"flags": [], "allergens": []}, "gf-beer": {"flags": [], "allergens": []}})
    rewrites = [
        ("Add the soy sauce and stir.", ("egg",), "tamari"),
        ("Roll out on a lightly floured surface.", ("egg",), "surface dusted with gluten-free flour"),
        ("Pour into a greased and floured 9x13-inch pan.", ("egg",), "floured (use gluten-free flour)"),
        ("Serve with crusty bread.", ("egg",), "gluten-free bread"),
        ("Serve with rye bread.", ("gf-bread",), "gluten-free bread"),
        ("Scatter with toasted walnuts.", ("sunflower-seeds",), "sunflower seeds"),
        ("Stir in the peanut sauce.", ("sunflower-seeds",), "sunflower seed sauce"),
        ("Beat in the hazelnut praline paste.", ("sunflower-seeds",), "sunflower seed praline paste"),
        ("Brown the butter to hazelnut, then add sage.", ("egg",), "Brown the butter to hazelnut"),
        ("Roll into walnut-sized balls.", ("egg",), "walnut-sized"),
        ("Fry in peanut, vegetable or sunflower oil.", ("egg",), "Fry in vegetable or sunflower oil"),
        ("Batter the fish in beer.", ("gf-beer",), "gluten-free beer"),
        ("Drain the soba noodles.", ("rice-noodles",), "rice noodles"),
        ("Press in a shortbread biscuit or langue de chat.", ("egg",), "gluten-free shortbread biscuit"),
    ]
    for text, ingredients, want in rewrites:
        rec = r([text], ingredients)
        text_safety.make_text_safe(rec, ings)
        out = rec["steps"][0]
        ok = want in out and not scan_recipe(rec, ings)
        failed += not ok
        print(("PASS" if ok else "FAIL"), "rewrite:", text, "" if ok else f"-> {out!r} {scan_recipe(rec, ings)}")
    total = len(cases) + len(rewrites)
    print(f"{total - failed}/{total} passed")
    return failed == 0


def main():
    if "--test" in sys.argv:
        sys.exit(0 if _tests() else 1)
    problems = scan()
    for rid, where, w, ctx in problems:
        print(f"{rid} | {where} | {w} | {ctx}")
    print(f"SAFETY PROBLEMS: {len(problems)} in {len({p[0] for p in problems})} recipes")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
