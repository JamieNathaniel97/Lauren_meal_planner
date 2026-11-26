"""Build review/conversion_review.xlsx: every gluten-free / nut-free version
the importer made, with what changed and a Y/N "Keep?" dropdown.

Sheet 1 "Ambitious" lists conversions likely to be hard to get right
(doughs, pastry, dumplings, batters, nut-based dishes). Sheet 2 lists the
rest. Fill in Keep? with Y or N; blank means keep.

Usage:  python tools/conversion_review.py
"""

import glob
import json
import re
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "review" / "conversion_review.xlsx"

DOUGH_WORDS = re.compile(
    r"\b(knead\w*|dough|pastry|laminat\w*|proof\w*|prove|rise until|yeast|wrappers?|"
    r"pleat\w*|choux|roll (it |the dough |out )|batter|sponge|crumb structure)\b", re.I)
DISH_WORDS = re.compile(
    r"\b(dumplings?|bao|xiao long|gyoza|jiaozi|momo|pelmeni|pierogi|varenyky|khinkali|"
    r"manti|mantu|buuz|samosa|empanadas?|pastizzi|burek|byrek|b[öo]rek|strudel|croissant|"
    r"eclairs?|profiteroles?|paris-brest|cannoli|sfogliatelle|tart|pie|quiche|cake|torte?|"
    r"bread|roti|naan|chapati|paratha|flatbread|pizza|lahmacun|gnocchi|noodles|pasta|"
    r"lasagne|spaetzle|sp[äa]tzle|doughnuts?|beignets?|churros|waffles?|pancakes?|crepes?|"
    r"muffins?|biscuits?|cookies?|baklava|kunafa|macarons?|dacquoise|praline|tempura|"
    r"schnitzel|katsu|tonkatsu|karaage|fried chicken|batter)\b", re.I)


def load():
    ings = {i["id"]: i for i in json.loads((ROOT / "data/ingredients.json").read_text("utf-8"))}
    recipes = {}
    for f in sorted(glob.glob(str(ROOT / "data/recipes/*.json"))):
        if f.endswith("index.json"):
            continue
        for r in json.loads(Path(f).read_text("utf-8")):
            recipes[r["id"]] = r
    steps = {}
    for f in glob.glob(str(ROOT / "data/steps/*.json")):
        steps.update(json.loads(Path(f).read_text("utf-8")))
    return ings, recipes, steps


def is_risky(ing):
    allergens = set(ing.get("allergens", []))
    return bool(allergens & {"gluten", "nuts", "peanuts"}) or "pine-nut" in ing.get("flags", [])


def describe_changes(orig, var, ings):
    name = lambda i: ings.get(i, {}).get("name", i)
    o_ids = [x["id"] for x in orig["ingredients"]]
    v_ids = [x["id"] for x in var["ingredients"]]
    removed = [i for i in o_ids if i not in v_ids]
    added = [i for i in v_ids if i not in o_ids]
    lines = []
    # Pair swaps by position where the counts line up, else list separately.
    if removed and len(removed) == len(added):
        lines += [f"{name(a)} → {name(b)}" for a, b in zip(removed, added)]
    else:
        lines += [f"Removed: {name(a)}" for a in removed]
        lines += [f"Added: {name(b)}" for b in added]
    return lines, removed


def nut_share(orig, removed, ings):
    """Rough share of the dish's weight made up of the removed nut items."""
    def grams(x):
        ing = ings.get(x["id"], {})
        qty, unit = x.get("qty") or 0, x.get("unit") or ""
        if unit in ("g", "ml"):
            return qty
        if unit == "kg":
            return qty * 1000
        return qty * (ing.get("units", {}).get(unit) or 0)
    total = sum(grams(x) for x in orig["ingredients"]) or 1
    nuts = sum(grams(x) for x in orig["ingredients"]
               if x["id"] in removed and set(ings.get(x["id"], {}).get("allergens", [])) & {"nuts", "peanuts"})
    return nuts / total


def main():
    ings, recipes, steps = load()
    rows_amb, rows_rest = [], []
    for var in recipes.values():
        link = next((v for v in var.get("variants", []) if v.get("label", "").lower().startswith("original")), None)
        if not link or link["id"] not in recipes:
            continue
        orig = recipes[link["id"]]
        changes, removed = describe_changes(orig, var, ings)
        o_steps, v_steps = steps.get(orig["id"], []), steps.get(var["id"], [])
        changed_steps = sum(1 for a, b in zip(o_steps, v_steps) if a != b) + abs(len(o_steps) - len(v_steps))
        if changed_steps:
            changes.append(f"Method: {changed_steps} step(s) reworded")

        reasons = []
        method_text = " ".join(s if isinstance(s, str) else json.dumps(s) for s in o_steps)
        removed_gluten = [i for i in removed if "gluten" in ings.get(i, {}).get("allergens", [])]
        if removed_gluten and DOUGH_WORDS.search(method_text):
            reasons.append("Gluten-free dough/batter/pastry (behaves differently, harder to handle)")
        elif removed_gluten and DISH_WORDS.search(orig["name"]):
            reasons.append(f"Wheat is central to this dish ({orig['name']})")
        share = nut_share(orig, removed, ings)
        if share >= 0.08:
            reasons.append(f"Nuts were a main ingredient (~{share:.0%} of the dish)")
        row = {
            "name": var["name"],
            "id": var["id"],
            "orig": f"{orig['name']} ({orig['id']})",
            "cuisine": var.get("cuisine", ""),
            "reasons": "; ".join(reasons),
            "changes": "\n".join(changes) or "(no ingredient changes)",
        }
        (rows_amb if reasons else rows_rest).append(row)

    wb = Workbook()
    write_sheet(wb.active, "Ambitious", rows_amb,
                "Ambitious gluten-free / nut-free conversions. Put Y (keep) or N (remove) in the Keep? column. Blank = keep. "
                "Removing one only removes the converted version; the original recipe stays.")
    write_sheet(wb.create_sheet(), "Other conversions", rows_rest,
                "Simpler conversions (mostly sauce/stock/pasta swaps). These are kept unless you put N.")
    OUT.parent.mkdir(exist_ok=True)
    wb.save(OUT)
    print(f"Wrote {OUT} - ambitious: {len(rows_amb)}, other: {len(rows_rest)}")


def write_sheet(ws, title, rows, note):
    ws.title = title
    ws["A1"] = note
    ws["A1"].font = Font(italic=True, color="555555")
    ws.merge_cells("A1:G1")
    ws.row_dimensions[1].height = 32
    ws["A1"].alignment = Alignment(wrap_text=True, vertical="top")
    headers = ["Keep? (Y/N)", "Converted recipe", "Cuisine", "Why it's flagged", "What changed", "Original recipe", "id"]
    ws.append(headers)
    for c in ws[2]:
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor="2B8A3E")
        c.alignment = Alignment(vertical="center", wrap_text=True)
    for r in sorted(rows, key=lambda r: (r["cuisine"], r["name"])):
        ws.append(["", r["name"], r["cuisine"], r["reasons"], r["changes"], r["orig"], r["id"]])
    keep_fill = PatternFill("solid", fgColor="FFF4CC")
    for row in ws.iter_rows(min_row=3):
        for c in row:
            c.alignment = Alignment(wrap_text=True, vertical="top")
        row[0].fill = keep_fill
        row[0].alignment = Alignment(horizontal="center", vertical="top")
    dv = DataValidation(type="list", formula1='"Y,N"', allow_blank=True,
                        error="Please choose Y or N", errorTitle="Keep?")
    ws.add_data_validation(dv)
    if rows:
        dv.add(f"A3:A{len(rows) + 2}")
    for col, width in zip("ABCDEFG", [11, 38, 16, 40, 48, 38, 28]):
        ws.column_dimensions[col].width = width
    ws.freeze_panes = "B3"
    ws.auto_filter.ref = f"A2:G{len(rows) + 2}"


if __name__ == "__main__":
    main()
