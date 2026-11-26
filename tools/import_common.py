"""Shared code for the recipe importers (ForkRecipe, UniTools).

Source data is treated purely as data: nothing from it is executed, and its
text is only copied into recipe fields. See tools/import_all.py.
"""

import json
import math
import re
import unicodedata
from pathlib import Path

from ingnorm import norm

ROOT = Path(__file__).resolve().parent.parent
TOOLS = ROOT / "tools"

AISLES = {"fv": "fruit-veg", "mf": "meat-fish", "de": "dairy-eggs", "td": "tins-dry",
          "ss": "spices-sauces", "bk": "bakery", "fz": "frozen", "dr": "drinks"}
STORAGE = {"c": "cupboard", "f": "fridge", "s": "spices", "v": "fruit-veg", "z": "freezer"}
LABELS = {
    "GF": "Often contains wheat or is contaminated; choose one labelled gluten-free.",
    "SP": "Spice blends can contain wheat flour or be packed with nuts; check the label.",
    "ST": "Many stock cubes contain wheat; check it is labelled gluten-free.",
    "MT": "Processed meat can contain wheat (rusk); check the label.",
    "BR": "Recipes vary by brand (wheat, nuts); check the label.",
    "NUT": "Can be made alongside nuts; check 'may contain' warnings if nuts are a problem.",
    "OAT": "Oats are often contaminated with wheat; use oats labelled gluten-free. Some coeliacs also react to oats.",
}
VALID_FLAGS = {"meat", "pork", "fish", "shellfish", "dairy", "egg", "honey", "gluten", "coconut",
               "pine-nut", "alcohol", "animal-rennet", "gelatin"}
VALID_ALLERGENS = {"gluten", "peanuts", "nuts", "milk", "eggs", "fish", "crustaceans", "molluscs",
                   "sesame", "soya", "celery", "mustard", "lupin", "sulphites"}

# Grams per unit when an ingredient has no figure of its own. Must match
# DEFAULT_UNIT_GRAMS in js/derive.js.
DEFAULT_UNIT_GRAMS = {"tsp": 5, "tbsp": 15, "pinch": 0.5, "ml": 1, "g": 1, "kg": 1000, "l": 1000,
                      "sprig": 1, "leaf": 0.3, "slice": 25, "bunch": 25, "handful": 30, "clove": 4,
                      "cm": 5, "stick": 40, "tin": 400}
# Rough grams for "1 of these" by aisle, used when a new ingredient is counted
# in pieces but has no "each" weight yet.
EACH_BY_AISLE = {"fruit-veg": 120, "meat-fish": 150, "dairy-eggs": 50, "bakery": 60, "spices-sauces": 1}


# ------------------------------------------------------------------ ingredients

def _phrases(text):
    return [p.strip() for p in text.split(",") if p.strip()]


def load_ingredients():
    """Existing ingredients.json plus the new master list. Returns
    (ingredients list, phrase->id dict, problems)."""
    problems = []
    master_lines = (TOOLS / "ingredient_master_new.txt").read_text(encoding="utf-8").splitlines()
    master_ids = {l.split("|")[0].strip() for l in master_lines if l.strip() and not l.startswith("#")}
    # ingredients.json already holds the master entries after a previous run;
    # they're rebuilt from the master list, so only the hand-made ones are kept.
    existing = [i for i in json.loads((ROOT / "data" / "ingredients.json").read_text(encoding="utf-8"))
                if i["id"] not in master_ids]
    by_id = {i["id"]: i for i in existing}
    order = [i["id"] for i in existing]
    phrase_to_id = {}

    def add_phrase(p, iid, where):
        key = norm(p)
        if key in phrase_to_id and phrase_to_id[key] != iid:
            problems.append(f"{where}: phrase '{p}' used for both {phrase_to_id[key]} and {iid}")
            return
        phrase_to_id[key] = iid

    for line in (TOOLS / "ingredient_map_existing.txt").read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        iid, phrases = [x.strip() for x in line.split("|", 1)]
        if iid not in by_id:
            problems.append(f"map_existing: unknown id {iid}")
            continue
        for p in _phrases(phrases):
            add_phrase(p, iid, "map_existing")

    for n, line in enumerate((TOOLS / "ingredient_master_new.txt").read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip() or line.startswith("#"):
            continue
        cols = [c.strip() for c in line.split("|")]
        if len(cols) != 10:
            problems.append(f"master_new line {n}: {len(cols)} columns")
            continue
        iid, name, phrases, flags, allergens, aisle, storage, nut, units, label = cols
        if iid in by_id:
            problems.append(f"master_new line {n}: duplicate id {iid}")
            continue
        flags = [f for f in flags.replace(" ", "").split(",") if f]
        allergens = [a for a in allergens.replace(" ", "").split(",") if a]
        bad = [f for f in flags if f not in VALID_FLAGS] + [a for a in allergens if a not in VALID_ALLERGENS]
        if bad:
            problems.append(f"master_new line {n}: bad flags/allergens {bad}")
        if ("gluten" in flags) != ("gluten" in allergens):
            problems.append(f"master_new line {n}: gluten flag and allergen disagree")
        kcal, p, c, f, fib = [float(x) for x in nut.split()]
        ing = {"id": iid, "name": name, "flags": flags, "allergens": allergens,
               "aisle": AISLES[aisle], "storage": STORAGE[storage],
               "per100g": {"kcal": kcal, "protein": p, "carbs": c, "fat": f, "fibre": fib}}
        if units:
            ing["units"] = {u.split("=")[0]: float(u.split("=")[1]) for u in units.split(",")}
        if label:
            ing["checkLabel"] = LABELS[label]
        ing["new"] = True
        by_id[iid] = ing
        order.append(iid)
        for ph in _phrases(phrases):
            add_phrase(ph, iid, f"master_new line {n}")
    for i in by_id.values():   # an ingredient's own name always matches it
        phrase_to_id.setdefault(norm(i["name"]), i["id"])
    return [by_id[i] for i in order], phrase_to_id, problems


class Matcher:
    """Maps a free-text ingredient name to ingredient ids (longest phrase wins)."""

    def __init__(self, phrase_to_id):
        self.p2i = phrase_to_id
        self.maxlen = max(len(p.split()) for p in phrase_to_id)

    def _lookup(self, ngram):
        if ngram in self.p2i:
            return ngram
        words = ngram.split()
        for cut in ("es", "s"):
            if words[-1].endswith(cut) and len(words[-1]) > len(cut) + 2:
                cand = " ".join(words[:-1] + [words[-1][: -len(cut)]])
                if cand in self.p2i:
                    return cand
        return None

    def best(self, key):
        """(id, matched phrase) for the longest phrase inside key, or (None, None)."""
        words = key.split()
        best = None
        for n in range(min(self.maxlen, len(words)), 0, -1):
            for i in range(len(words) - n + 1):
                hit = self._lookup(" ".join(words[i:i + n]))
                if hit and (best is None or len(hit) > len(best)):
                    best = hit
            if best:
                break
        return (self.p2i[best], best) if best else (None, None)

    def match_key(self, key):
        """Ids for one normalised name. 'x or y' takes the first alternative and
        'x and y' is split into both, unless a known phrase covers the words."""
        if not key:
            return []
        iid, phrase = self.best(key)
        covers_or = " or " not in key or (phrase and " or " in phrase)
        covers_and = " and " not in key or (phrase and " and " in phrase)
        if iid and covers_or and covers_and:
            return [iid]
        if not covers_or:
            first, rest = [x.strip() for x in key.split(" or ", 1)]
            rest_words = rest.split()
            # "chicken or vegetable stock" means chicken stock, not chicken:
            # give the first alternative the second one's trailing words.
            for n in range(len(rest_words) - 1, 0, -1):
                cand = first + " " + " ".join(rest_words[-n:])
                cid, cphrase = self.best(cand)
                fid, fphrase = self.best(first)
                if cid and (not fid or (len(cphrase) > len(fphrase) and set(first.split()) & set(cphrase.split()))):
                    return self.match_key(cand)
            return self.match_key(first)
        if not covers_and:
            out = []
            for part in key.split(" and "):
                ids = self.match_key(part.strip())
                if not ids:
                    return []
                out += [i for i in ids if i not in out]
            return out
        return [iid] if iid else []

    def match(self, raw):
        """Ids for a raw source name such as 'Garlic cloves, crushed' or
        'Grated daikon, grated ginger, katsuobushi'. Returns [] if any
        listed item can't be matched."""
        text = re.sub(r"\([^)]*\)", " ", raw)
        parts = [p for p in re.split(r"[,;+]| & ", text) if p.strip()]
        ids = []
        for part in parts:
            key = norm(part)
            if not key:
                continue
            # Unmatched parts are usually prep notes ("crushed whole", "bone-in").
            ids += [g for g in self.match_key(key) if g not in ids]
        return ids


# ------------------------------------------------------------------ safety checks

_NUT_WORDS = re.compile(r"\b(almonds?|walnuts?|hazelnuts?|pecans?|cashews?|pistachios?|macadamias?|"
                        r"brazil nuts?|chestnuts?|praline|marzipan|frangipane|nut butter|nuts?|"
                        r"candlenuts?|nutella|gianduja)\b")
_PEANUT_WORDS = re.compile(r"\b(peanuts?|groundnuts?|satay|monkey nuts?)\b")
_PINE_WORDS = re.compile(r"\b(pine ?nuts?|pignoli|pesto)\b")
_GLUTEN_WORDS = re.compile(r"\b(wheat|flour|barley|rye|malt|spelt|semolina|couscous|bulgur|bulgar|"
                           r"breadcrumbs?|panko|soy sauce|shoyu|beer|ale|lager|stout|seitan|noodles?|"
                           r"pasta|bread|pastry|biscuits?|crackers?|croutons?|farro|freekeh|"
                           r"udon|ramen|orzo|gnocchi|filo|phyllo|tortillas?|pitta?|naan|roti|bun|brioche)\b")
_GLUTEN_SAFE = re.compile(r"gluten.free|rice (flour|noodles?|paper|vermicelli)|corn ?flour|cornflour|"
                          r"chickpea flour|gram flour|buckwheat|potato (flour|starch)|tapioca|coconut flour|"
                          r"cassava flour|almond flour|glass noodles?|corn tortillas?|masa|maize|teff|soy flour|"
                          r"rice bread|banana leaf|water chestnut|hazelnut flour|almond flour|nut flour")
_FISH_WORDS = re.compile(r"\b(fish|anchov\w*|katsuobushi|bonito|dashi|shrimp paste|oysters?|prawns?|shrimps?|"
                         r"crab|lobster|clams?|mussels?|squid)\b")
_MEAT_WORDS = re.compile(r"\b(bacon|ham|lard|pork|beef|chicken|lamb|mutton|veal|duck|gelatine?|suet|"
                         r"chorizo|sausages?|prosciutto|pancetta|guanciale|salami)\b")
_NOT_MEAT = re.compile(r"vegetarian|vegan|plant.based|meat.free|meatless|chicken.of.the.woods|mushroom")
# Words that look like allergens but aren't.
_FALSE_FRIENDS = ("water chestnut", "coconut", "nutmeg", "butternut", "doughnut", "oyster mushroom",
                  "king oyster", "fish sauce", "fish-sauce", "oyster cracker", "steamed fish soy sauce")


def main_text(raw):
    """The part of a source name that says what to use: without 'or ...'
    alternatives and without purpose clauses like 'for the pastry'."""
    t = unicodedata.normalize("NFKD", raw).encode("ascii", "ignore").decode().lower()
    # (…or…) asides and "(peanut or canola)" lists are alternatives.
    t = re.sub(r"\(([^)]*)\)", lambda m: " " if re.search(r"\bor\b|^\s*e\.?g\.?|optional|\bper\b", m.group(1)) else f" {m.group(1)} ", t)
    t = re.split(r"\bor\b", t)[0]
    purpose = (r"(pastry|dough|filling|crust|crouton|glaze|sauce|batter|coating|custard|syrup|pasta|noodle|"
               r"noodles|farro|praline|caramel|cream|fish|pork|chicken|frying|dusting|poaching|sealing|serving|"
               r"garnish|patting|cooking|water|marinade|topping|icing|base|filo|phyllo|tedouira|pastry cream)")
    t = re.sub(rf"\b(for|to|in) (the |a |an )?{purpose}\b.*", " ", t)
    t = re.sub(rf"\s[-–—]+\s*{purpose}\b.*", " ", t)      # "Caster sugar — pastry"
    if "mushroom" in t:
        t = t.replace("oyster", " ")
    return t


def safety_issue(raw_text, ids, ing_by_id):
    """Return a reason if the source text mentions an allergen or meat that
    the matched ingredients don't carry (so a mapping can't quietly drop it).
    Alternatives the cook can choose ('sunflower or peanut oil') don't count,
    because the first option is the one used; the wording is kept in the note."""
    t = main_text(raw_text)
    for w in _FALSE_FRIENDS:
        t = t.replace(w, " ")
    if set(ids) <= {"water", "salt"}:
        return None   # "pasta cooking water": the pasta is its own line
    ings = [ing_by_id[i] for i in ids]
    allergens = {a for i in ings for a in i["allergens"]}
    flags = {f for i in ings for f in i["flags"]}
    labelled = any(i.get("checkLabel") for i in ings)
    if "pine-nut" in flags:
        t = _PINE_WORDS.sub(" ", t)
    if _PEANUT_WORDS.search(t) and "peanuts" not in allergens:
        return "mentions peanuts"
    if _NUT_WORDS.search(t) and not ({"nuts", "peanuts"} & allergens) and "free" not in t:
        return "mentions nuts"
    if _PINE_WORDS.search(t) and "pine-nut" not in flags:
        return "mentions pine nuts or pesto"
    if _GLUTEN_WORDS.search(t) and "gluten" not in flags and not labelled and not _GLUTEN_SAFE.search(t):
        return "mentions a gluten source"
    if _FISH_WORDS.search(t) and not ({"fish", "shellfish"} & flags):
        return "mentions fish or seafood"
    if _MEAT_WORDS.search(t) and not ({"meat", "fish", "shellfish", "gelatin"} & flags) and not _NOT_MEAT.search(t):
        return "mentions meat"
    return None


# ------------------------------------------------------------------ quantities

def grams_for(qty, unit, ing):
    """Mirror of gramsFor() in js/derive.js."""
    if qty is None:
        return 0
    unit = unit or "each"
    per = (ing.get("units") or {}).get(unit, DEFAULT_UNIT_GRAMS.get(unit))
    return None if per is None else qty * per


def nice_number(x):
    """Round a quantity for display."""
    if x is None:
        return None
    if x >= 100:
        return int(round(x / 10) * 10) if x < 500 else int(round(x / 25) * 25)
    if x >= 20:
        return int(round(x / 5) * 5)
    if x >= 3:
        return int(round(x))
    return round(x * 4) / 4 or 0.25


LIQUIDS = {"water", "milk", "double-cream", "soy-sauce", "dark-soy", "tamari", "fish-sauce", "mirin", "sake",
           "rice-vinegar", "red-wine-vinegar", "white-wine-vinegar", "cider-vinegar", "balsamic", "malt-vinegar",
           "black-vinegar", "shaoxing", "dry-sherry", "white-wine", "red-wine", "beer", "gf-beer", "spirits",
           "dashi", "fish-stock", "coconut-milk", "coconut-cream", "coconut-water", "buttermilk", "evaporated-milk",
           "olive-oil", "vegetable-oil", "sesame-oil", "coconut-oil", "peanut-oil", "mustard-oil", "lemon-juice",
           "lime-juice", "orange-juice", "tomato-passata", "almond-milk", "soya-milk", "oyster-sauce",
           "gf-oyster-sauce", "worcestershire-sauce", "rose-water", "vanilla", "kecap-manis", "gf-kecap-manis"}


def tidy_grams(g, ing):
    """Turn a gram amount into a friendly (qty, unit): pieces for countable
    things, spoons for small amounts, ml for liquids, grams otherwise."""
    units = ing.get("units") or {}
    if ing["id"] in LIQUIDS:
        if g < 50:
            n = g / units.get("tbsp", 15)
            return (nice_number(n), "tbsp") if n >= 1 else (max(0.25, round(g / units.get("tsp", 5) * 4) / 4), "tsp")
        return nice_number(g), "ml"
    for u in ("each", "clove"):
        if u in units and units[u] >= 5 and ing["aisle"] in ("fruit-veg", "dairy-eggs"):
            n = g / units[u]
            if 0.4 <= n <= 30:
                return max(0.5, round(n * 2) / 2), u
    if g < 25 and ing["aisle"] in ("spices-sauces", "tins-dry") or g < 8:
        tsp = units.get("tsp", 5)
        n = g / tsp
        if n >= 3:
            return nice_number(g / units.get("tbsp", 15)), "tbsp"
        return max(0.25, round(n * 4) / 4), "tsp"
    return nice_number(g), "g"


STOCK_CUBES = {"gf-veg-stock", "gf-chicken-stock", "gf-beef-stock"}


def stock_line(qty_ml):
    """Liquid stock becomes cubes: 1 cube makes 500 ml."""
    cubes = max(0.5, math.ceil((qty_ml or 500) / 250) / 2)
    return cubes, f"made up to {int(round((qty_ml or 500) / 50) * 50)} ml with boiling water"


# ------------------------------------------------------------------ nutrition (mirror of derive.js)

def recipe_kcal_per_portion(recipe, ing_by_id):
    total = 0.0
    for line in recipe["ingredients"]:
        if line.get("optional"):
            continue
        ing = ing_by_id[line["id"]]
        g = grams_for(line.get("qty"), line.get("unit"), ing)
        if g is None:
            return None
        total += ing["per100g"]["kcal"] * g * line.get("absorb", 1) / 100
    return total / (recipe["servings"] or 1)


def diet_facts(recipe, ing_by_id):
    flags, allergens = set(), set()
    for line in recipe["ingredients"]:
        if line.get("optional"):
            continue
        ing = ing_by_id[line["id"]]
        flags |= set(ing["flags"])
        allergens |= set(ing["allergens"])
    gf = "gluten" not in flags and "gluten" not in allergens
    nf = not ({"peanuts", "nuts"} & allergens) and "pine-nut" not in flags
    veg = not ({"meat", "pork", "fish", "shellfish", "animal-rennet", "gelatin"} & flags)
    return {"gf": gf, "nf": nf, "vegetarian": veg,
            "vegan": veg and not ({"dairy", "egg", "honey"} & flags)}


KCAL_RANGE = {"dinner": (250, 900), "lunch": (200, 900), "breakfast": (150, 750),
              "snack": (60, 600), "dessert": (100, 700), "side": (40, 600)}


def fit_servings(recipe, ing_by_id, lo_s=1, hi_s=14):
    """Adjust servings so kcal per portion is plausible for the meal type.
    Returns False if no serving count in range works."""
    lo, hi = KCAL_RANGE[recipe["mealTypes"][0]]
    total = recipe_kcal_per_portion({**recipe, "servings": 1}, ing_by_id)
    if total is None:
        return False
    cur = recipe["servings"]
    if lo <= total / cur <= hi:
        return True
    # Change the serving count as little as possible.
    if total / cur > hi:
        s = max(cur, math.ceil(total / hi))
    else:
        s = min(cur, max(lo_s, math.floor(total / lo)))
    s = min(hi_s, max(lo_s, s))
    if s > max(10, cur * 3):    # needing far more portions means the amounts are off
        return False
    recipe["servings"] = s
    return lo <= total / s <= hi


# ------------------------------------------------------------------ tools, spice, cost

TOOL_RULES = [
    ("air-fryer", r"air.?fryer"),
    ("slow-cooker", r"slow.?cooker|crock.?pot"),
    ("pressure-cooker", r"pressure.?cooker|instant pot"),
    ("food-processor", r"food processor"),
    ("stick-blender", r"stick blender|immersion blender|hand blender"),
    ("blender", r"\bblender\b|\bblend (it|them|the|until|everything|to)|liquidi[sz]e"),
    ("stand-mixer", r"stand mixer|electric mixer|dough hook|paddle attachment|whisk attachment"),
    ("wok", r"\bwok\b"),
    ("griddle", r"griddle|\bcomal\b|plancha|\btawa\b"),
    ("bbq", r"barbecue|\bbbq\b|charcoal|\bsmoker\b|hot coals|embers"),
    ("grill", r"\bgrill\b|\bgrill (pan|it|them|for|under)|\bbroil|under the grill|grilled"),
    ("steamer", r"\bsteamer\b|steaming basket|steam (it|them|for|over)|bamboo steamer"),
    ("microwave", r"microwave"),
    ("oven", r"\boven\b|\bbake\b|\bbaked\b|\bbaking\b|preheat"),
    ("hob", r"\bpan\b|saucepan|skillet|frying pan|\bpot\b|casserole|dutch oven|simmer|\bboil|\bfry\b|"
            r"\bfried\b|\bsaut|stir.?fry|\bhob\b|stove|burner|\bwok\b|\bsear\b|\bheat (the|a|some|oil)"),
]


def infer_tools(text):
    t = text.lower()
    tools = [tid for tid, rx in TOOL_RULES if re.search(rx, t)]
    if "blender" in tools and "stick-blender" in tools:
        tools.remove("blender")
    return tools or ["hob"]


HOT = {"red-chilli": 1, "scotch-bonnet": 2, "dried-chillies": 1, "chilli-powder": 1, "chilli-flakes": 1,
       "sriracha": 1, "chilli-oil": 1, "gochujang": 1, "gf-gochujang": 1, "harissa": 1, "doubanjiang": 1,
       "thai-red-paste": 1, "thai-green-paste": 1, "chipotle-adobo": 1, "jerk-seasoning": 1}


def guess_spice(ids):
    return min(3, sum(HOT.get(i, 0) for i in set(ids)))


PRICEY = {"beef-steak", "lamb", "duck", "veal", "lobster", "crab", "scallops", "oysters", "king-prawns",
          "salmon", "tuna-steak", "foie-gras", "cured-ham", "mussels", "clams", "squid", "pine-nuts"}


def guess_cost(ids, ing_by_id):
    if PRICEY & set(ids):
        return 3
    if any({"meat", "fish", "shellfish"} & set(ing_by_id[i]["flags"]) for i in ids):
        return 2
    return 1


def slugify(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


def name_key(s):
    """For spotting the same dish twice."""
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"\([^)]*\)", " ", s)
    s = re.sub(r"\b(classic|traditional|authentic|easy|simple|homemade|the|a|with|and|style|recipe|"
               r"italian|french|mexican|indian|chinese|japanese|thai|korean|spanish|greek|filipino|"
               r"vietnamese|turkish|moroccan|lebanese|american|british|peruvian|german)\b", " ", s)
    return " ".join(sorted(re.sub(r"[^a-z ]", " ", s).split()))


# ------------------------------------------------------------------ gluten-free / nut-free versions

# offending id -> (replacement id, [(regex in step text, replacement text)])
GF_SWAPS = {
    "soy-sauce": ("tamari", [(r"\b(light |regular )?soy sauce\b", "tamari"), (r"\bshoyu\b", "tamari")]),
    "dark-soy": ("tamari", [(r"\bdark soy( sauce)?\b", "tamari"), (r"\bsoy sauce\b", "tamari")]),
    "spaghetti": ("gf-spaghetti", [(r"\b(spaghetti|linguine|bucatini|tonnarelli)\b", r"gluten-free \1")]),
    "dried-pasta": ("gf-pasta", [(r"\bpasta\b", "gluten-free pasta")]),
    "plain-flour": ("gf-flour", [(r"\b(plain |all.purpose |wheat )?flour\b", "gluten-free flour")]),
    "breadcrumbs": ("gf-breadcrumbs", [(r"\b(panko )?breadcrumbs\b", "gluten-free breadcrumbs"), (r"\bpanko\b", "gluten-free breadcrumbs")]),
    "bread": ("gf-bread", [(r"\bbread\b", "gluten-free bread")]),
    "baguette": ("gf-bread", [(r"\bbaguette\b", "gluten-free bread")]),
    "tortilla-wraps": ("corn-tortillas", [(r"\b(flour )?tortillas?\b", "corn tortillas")]),
    "egg-noodles": ("rice-noodles", [(r"\b(egg |wheat |ramen |udon )?noodles\b", "rice noodles")]),
    "soba": ("rice-noodles", [(r"\bsoba( noodles)?\b", "rice noodles")]),
    "vermicelli-wheat": ("rice-noodles", [(r"\bvermicelli\b", "rice vermicelli")]),
    "couscous": ("quinoa", [(r"\bcouscous\b", "quinoa")]),
    "bulgur": ("quinoa", [(r"\b(fine |coarse )?bulgu?a?r( wheat)?\b", "quinoa"), (r"\bcracked wheat\b", "quinoa")]),
    "barley": ("brown-rice", [(r"\b(pearl )?barley\b", "brown rice")]),
    "farro": ("brown-rice", [(r"\b(farro|freekeh|wheat berries)\b", "brown rice")]),
    "oyster-sauce": ("gf-oyster-sauce", [(r"\boyster sauce\b", "gluten-free oyster sauce")]),
    "hoisin": ("gf-hoisin", [(r"\bhoisin( sauce)?\b", "gluten-free hoisin sauce")]),
    "kecap-manis": ("gf-kecap-manis", [(r"\bkecap manis\b", "gluten-free kecap manis"), (r"\bsweet soy sauce\b", "gluten-free sweet soy sauce")]),
    "gochujang": ("gf-gochujang", [(r"\bgochujang\b", "gluten-free gochujang")]),
    "doenjang": ("miso", [(r"\bdoenjang\b", "gluten-free miso")]),
    "black-vinegar": ("rice-vinegar", [(r"\b(chinkiang |chinese )?black (rice )?vinegar\b", "rice vinegar")]),
    "shaoxing": ("dry-sherry", [(r"\bshaoxing( rice)?( wine)?\b", "dry sherry"), (r"\brice wine\b", "dry sherry")]),
    "beer": ("gf-beer", [(r"\b(dark |pale )?(beer|ale|lager|stout)\b", "gluten-free beer")]),
    "malt-vinegar": ("cider-vinegar", [(r"\bmalt vinegar\b", "cider vinegar")]),
    "puff-pastry": ("gf-pastry", [(r"\bpuff pastry\b", "gluten-free puff pastry")]),
    "shortcrust-pastry": ("gf-pastry", [(r"\b(shortcrust )?pastry\b", "gluten-free pastry")]),
    "biscuits": ("gf-biscuits", [(r"\b(digestive |graham )?(biscuits?|crackers?|cookies)\b", "gluten-free biscuits")]),
    "lasagne-sheets": ("gf-lasagne", [(r"\blasagne sheets?\b", "gluten-free lasagne sheets")]),
    "gnocchi": ("gf-gnocchi", [(r"\bgnocchi\b", "gluten-free gnocchi")]),
    "asafoetida": ("gf-asafoetida", [(r"\basafoetida\b", "gluten-free asafoetida")]),
    "porridge-oats": ("gf-oats", [(r"\b(rolled |porridge )?oats\b", "gluten-free oats")]),
    "worcestershire-sauce": ("tamari", [(r"\bworcestershire( sauce)?\b", "tamari")]),
    "fish-cake": (None, []),
}
NF_SWAPS = {
    "walnuts": ("pumpkin-seeds", [(r"\bwalnuts?\b", "pumpkin seeds")]),
    "pecans": ("pumpkin-seeds", [(r"\b(pecans?|macadamias?|brazil nuts?)\b", "pumpkin seeds")]),
    "almonds": ("sunflower-seeds", [(r"\b(flaked |slivered |blanched )?almonds?\b", "sunflower seeds")]),
    "hazelnuts": ("sunflower-seeds", [(r"\bhazelnuts?\b", "sunflower seeds")]),
    "pistachios": ("pumpkin-seeds", [(r"\bpistachios?\b", "pumpkin seeds")]),
    "cashews": ("sunflower-seeds", [(r"\bcashews?\b", "sunflower seeds")]),
    "peanuts": ("sunflower-seeds", [(r"\b(roasted |fried )?peanuts?\b", "toasted sunflower seeds")]),
    "peanut-butter": ("sunflower-butter", [(r"\bpeanut (butter|paste)\b", "sunflower seed butter")]),
    "pine-nuts": ("sunflower-seeds", [(r"\bpine ?nuts?\b", "sunflower seeds")]),
    "candlenuts": ("sunflower-seeds", [(r"\bcandlenuts?\b", "sunflower seeds"), (r"\bmacadamias?\b", "sunflower seeds")]),
    "almond-milk": ("soya-milk", [(r"\balmond milk\b", "soya milk")]),
    "mahlab": (None, []),   # dropped
    "peanut-oil": ("vegetable-oil", [(r"\b(groundnut|peanut) oil\b", "vegetable oil")]),
}
NO_CONVERT = {"strong-flour", "semolina", "flatbread", "rye-bread", "brioche", "filo-pastry", "dumpling-wrappers",
              "curry-roux", "tonkatsu-sauce", "ponzu", "doubanjiang", "ground-almonds", "chestnuts",
              "pistachios-major", "cornflakes"}
NUT_GARNISH_MAX_SHARE = 0.25   # nuts above this share of the dish are the dish; don't swap


def offending(line, ing):
    gl = "gluten" in ing["flags"] or "gluten" in ing["allergens"]
    nt = bool({"nuts", "peanuts"} & set(ing["allergens"])) or "pine-nut" in ing["flags"]
    return gl, nt


def make_free_version(recipe, ing_by_id):
    """A gluten-free and nut-free version of a recipe, or None if it can't be
    converted sensibly. Optional extras that clash are dropped."""
    ids = {l["id"] for l in recipe["ingredients"] if not l.get("optional")}
    if ids & {"yeast", "sourdough-starter"} and ids & {"plain-flour", "strong-flour"}:
        return None   # a kneaded yeast dough doesn't survive a flour swap
    total_g = sum((grams_for(l.get("qty"), l.get("unit"), ing_by_id[l["id"]]) or 0)
                  for l in recipe["ingredients"] if not l.get("optional"))
    new_lines, swaps, text_subs, did_gf, did_nf = [], [], [], False, False
    for line in recipe["ingredients"]:
        ing = ing_by_id[line["id"]]
        gl, nt = offending(line, ing)
        if not (gl or nt):
            new_lines.append(line)
            continue
        if line.get("optional"):
            did_gf |= gl
            did_nf |= nt
            continue
        if line["id"] in NO_CONVERT:
            return None
        if gl and nt:
            return None
        table = GF_SWAPS if gl else NF_SWAPS
        if line["id"] not in table:
            return None
        if nt:
            g = grams_for(line.get("qty"), line.get("unit"), ing) or 0
            if total_g and g / total_g > NUT_GARNISH_MAX_SHARE:
                return None
        repl, subs = table[line["id"]]
        did_gf |= gl
        did_nf |= nt
        text_subs += subs
        if repl is None:
            swaps.append((ing["name"], None))
            continue
        r_ing = ing_by_id[repl]
        new = dict(line, id=repl)
        if line.get("unit") not in (None, "g", "kg", "ml", "l", "tsp", "tbsp", "pinch") and line.get("unit") not in (r_ing.get("units") or {}):
            g = grams_for(line.get("qty"), line.get("unit"), ing)
            if g is None:
                return None
            new["qty"], new["unit"] = tidy_grams(g, r_ing)
        new.pop("note", None)
        if line.get("note"):
            new["note"] = f"instead of {line['note']}"
        swaps.append((ing["name"], r_ing["name"]))
        new_lines.append(new)
    if not (did_gf or did_nf):
        return None
    which = "gluten- & nut-free" if did_gf and did_nf else "gluten-free" if did_gf else "nut-free"
    steps = []
    for s in recipe["steps"]:
        for rx, rep in text_subs:
            s = re.sub(rx, rep, s, flags=re.I)
        steps.append(s)
    low = lambda s: s[0].lower() + s[1:] if s and not s[:2].isupper() else s
    changed = [f"{low(b)} instead of {low(a)}" if b else f"no {low(a)}" for a, b in dict.fromkeys(swaps)]
    v = dict(recipe)
    v["id"] = f"{recipe['id']}-{'gfnf' if did_gf and did_nf else 'gf' if did_gf else 'nf'}"
    v["name"] = f"{recipe['name']} ({which})"
    v["description"] = (recipe["description"].rstrip() + " " if recipe.get("description") else "") + \
        (f"This {which} version uses " + ", ".join(changed) + "." if changed else f"This {which} version leaves out the optional extras.")
    v["ingredients"] = new_lines
    v["steps"] = steps
    v["convertedFrom"] = recipe["id"]
    v["variants"] = [{"id": recipe["id"], "label": "Original version"}]
    label = {"gluten-free": "Gluten-free version", "nut-free": "Nut-free version"}.get(which, "Gluten- & nut-free version")
    recipe.setdefault("variants", []).append({"id": v["id"], "label": label})
    return v
