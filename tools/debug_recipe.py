"""Print each ingredient line's grams and kcal for imported recipes (debug aid).
    python tools/debug_recipe.py ut-pho-bo ut-tortilla-espanola"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from import_common import grams_for
ROOT = Path(__file__).resolve().parent.parent
ings = {i["id"]: i for i in json.loads((ROOT / "data/ingredients.json").read_text(encoding="utf-8"))}
idx = json.loads((ROOT / "data/recipes/index.json").read_text(encoding="utf-8"))["batches"]
recs = {r["id"]: r for b in idx for r in json.loads((ROOT / "data/recipes" / b).read_text(encoding="utf-8"))}
for rid in sys.argv[1:]:
    r = recs[rid]; tot = 0
    print(f"== {rid} serves {r['servings']}")
    for l in r["ingredients"]:
        i = ings[l["id"]]; g = grams_for(l.get("qty"), l.get("unit"), i) or 0
        k = 0 if l.get("optional") else i["per100g"]["kcal"] * g * l.get("absorb", 1) / 100; tot += k
        print(f"   {str(l.get('qty')):>6} {str(l.get('unit')):6} {l['id']:22} {g:7.0f} g {k:6.0f} kcal  {l.get('note','')[:50]}")
    print(f"   total {tot:.0f}, per portion {tot / r['servings']:.0f}")
