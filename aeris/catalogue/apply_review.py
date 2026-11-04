"""Read a reviewed catalogue workbook and write review_overrides.json for build_catalogue.py.

    python apply_review.py <reviewed.xlsx>

Takes English name, French name and unit for every row from the reviewed file, then tidies what the review
introduced: unit labels back to the bilingual "english / français" style, stray spaces and tabs, and a few typos.
Prints every row it changed beyond the reviewer's own text.
"""
import json
import os
import re
import sys

import openpyxl

HERE = os.path.dirname(os.path.abspath(__file__))
REVIEWED = sys.argv[1]

UNITS = {
    "soft bag": "bag / poche",
    "bag / poche": "bag / poche",
    "capsule/gélule": "capsule / gélule",
    "flacon/bottle": "bottle / flacon",
    "sachet": "sachet",
    "suppository/suppositoire": "suppository / suppositoire",
    "vaginal tablet / comprimé": "vaginal tablet / comprimé vaginal",
}
TEXT_FIXES = [
    (r"\bpourdre\b", "poudre"),
    (r"\bIV pourdre lyophilisée\b", "poudre lyophilisée IV"),
    (r"\bIV poudre lyophilisée\b", "poudre lyophilisée IV"),
    (r"\bCatheterIV\b", "Cathéter IV"),
    (r"^Catheter IV\b", "Cathéter IV"),
    (r"(\d) ?ml,(\d)", r"\1 ml, \2"),
    (r"(\d)\s{2,}µ", r"\1 µ"),
]
EN_FIXES = [(r"\bintraveinous\b", "intravenous"), (r"(\d) ?mg/flacon\b", r"\1 mg/vial")]
# Same item type as rows the reviewer changed to bag / poche, but left untouched
SAME_AS_REVIEWED = {"ACDC-MED-109": "bag / poche"}


def clean(s):
    return re.sub(r"\s+", " ", (s or "").replace("\t", " ")).strip().rstrip(".").strip()


ws = openpyxl.load_workbook(REVIEWED)["Catalogue"]
over, notes = {}, []
for r in ws.iter_rows(min_row=2, values_only=True):
    if not r[0]:
        continue
    code, en, fr, unit = r[0], clean(r[2]), clean(r[3]), clean(r[4])
    if code.startswith("ACDC-ICU-043"):
        en = en.rstrip(" ,")
    u = UNITS.get(unit.lower(), unit) if unit else unit
    u = SAME_AS_REVIEWED.get(code, u)
    fr2 = fr
    for a, b in TEXT_FIXES:
        fr2 = re.sub(a, b, fr2)
        en = re.sub(a, b, en) if a.startswith(r"(\d)") else en
    en2 = en
    for a, b in EN_FIXES:
        en2 = re.sub(a, b, en2)
    if en2 != en:
        notes.append(f"{code}: EN '{en}' -> '{en2}'")
        en = en2
    if u != unit:
        notes.append(f"{code}: unit '{unit}' -> '{u}'")
    if fr2 != fr:
        notes.append(f"{code}: FR '{fr}' -> '{fr2}'")
    over[code] = {"name": en, "fr": fr2, "unit": u}

json.dump(over, open(os.path.join(HERE, "review_overrides.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=0)
print(len(over), "rows read;", len(notes), "tidied:")
for n in notes:
    print(" ", n)
