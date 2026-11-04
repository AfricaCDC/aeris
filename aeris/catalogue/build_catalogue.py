"""Build the AERIS catalogue review workbook and the import files from the logistics team's commodity lists.

Inputs (scratchpad): catalogue_master.json, tr_out_1..3.json (French names), refdata/live/2_products.csv (32 products in AERIS).
Outputs: <review.xlsx> for the logistics team; catalogue_import/ with categories, products CSV and French names.
"""
import csv
import collections
import json
import os
import re
import sys

import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

HERE = os.path.dirname(os.path.abspath(__file__))
REVIEW = sys.argv[1]
OUT = os.path.join(HERE, "catalogue_import")
os.makedirs(OUT, exist_ok=True)

master = json.load(open(os.path.join(HERE, "catalogue_master.json"), encoding="utf-8"))
fr = {}
for i in (1, 2, 3):
    fr.update(json.load(open(os.path.join(HERE, f"tr_out_{i}.json"), encoding="utf-8")))
missing = [m["code"] for m in master if m["code"] not in fr]
assert not missing, f"no French name for {missing[:5]}"
# Corrections from the logistics review (apply_review.py): names, French names and units as the reviewer left them.
OVERRIDES = os.path.join(HERE, "review_overrides.json")
reviewed = set()
if os.path.exists(OVERRIDES):
    over = json.load(open(OVERRIDES, encoding="utf-8"))
    for m in master:
        o = over.get(m["code"])
        if not o:
            continue
        t = fr[m["code"]]
        if (o["name"], o["fr"], o["unit"]) != (m["name"], t["fr"], m["unit"]):
            reviewed.add(m["code"])
        m["name"], m["unit"], t["fr"] = o["name"], o["unit"], o["fr"]
    for code in reviewed:
        if fr[code].get("flag"):
            fr[code]["flag"] = "Changed in review (GB)"
# Units are copied from the logistics lists; flag the ones that cannot be right for the item.
for m in master:
    n = m["name"].lower()
    note = ""
    if re.search(r"(soft|flex\.?|flexible) bag|bag.*pvc", n) and "vial" in m["unit"]:
        note = "Unit is vial but the item is an infusion bag: use bag / poche?"
    elif re.search(r"capsule", n) and m["unit"].startswith(("tube", "tablet")):
        note = "Item is a capsule: unit should be capsule / gélule?"
    if note:
        t = fr[m["code"]]
        t["flag"] = (t.get("flag", "") + " | " if t.get("flag") else "") + note
# One French convention across the three translation batches: decimal comma, space before %.
for t in fr.values():
    t["fr"] = re.sub(r"(?<=\d)%", " %", re.sub(r"(?<=\d)\.(?=\d)", ",", t["fr"])).strip()

cur = list(csv.reader(open(os.path.join(HERE, "refdata", "live", "2_products.csv"), encoding="utf-8")))
H = cur[0]
current = {r[H.index("ProductCode")]: r for r in cur[1:]}

LOT = {"MED", "LAB", "IPC", "SDB"}          # lot + expiry required at receipt
EXISTING_CATS = {"Medicines", "Medical equipment", "IPC / PPE", "Community / training supplies"}

MAROON, GOLD, SAND, GREEN = "9F2241", "B4A269", "F5F3EE", "1A5632"
head_font = Font(bold=True, color="FFFFFF")
head_fill = PatternFill("solid", fgColor=GREEN)
flag_fill = PatternFill("solid", fgColor="FFF2CC")
dup_fill = PatternFill("solid", fgColor="FCE4E4")
have_fill = PatternFill("solid", fgColor="E3EEE7")
wrap = Alignment(wrap_text=True, vertical="top")


def status(m):
    if m["status"] == "existing":
        return f"Already in AERIS ({m['code']}) / Déjà dans AERIS"
    if m.get("possible"):
        return f"Possible duplicate of {m['possible']} / Doublon possible"
    return "New / Nouveau"


def table(ws, header, rows, widths):
    ws.append(header)
    for c in ws[1]:
        c.font, c.fill, c.alignment = head_font, head_fill, Alignment(wrap_text=True, vertical="center")
    for r in rows:
        ws.append(r)
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w
    for row in ws.iter_rows(min_row=2):
        for c in row:
            c.alignment = wrap
    ws.freeze_panes = "C2"
    ws.auto_filter.ref = ws.dimensions
    ws.row_dimensions[1].height = 32


wb = openpyxl.Workbook()
rm = wb.active
rm.title = "Lisez-moi - Read me"
lines = [
    ("AERIS – Catalogue des produits Ebola / Ebola product catalogue", True),
    ("Source : listes de la logistique (CTE, PCI en formations sanitaires, enterrements dignes et sécurisés), "
     "516 articles distincts. / Source: logistics lists (treatment centre, IPC in health facilities, safe and "
     "dignified burials), 516 distinct items.", False),
    ("", False),
    ("Que vérifier / What to check (feuille « Catalogue »)", True),
    ("1. Nom (FR) : traduction proposée. Corrigez-la si besoin dans la colonne « Correction ». Surtout les "
     "médicaments (lignes jaunes = point à vérifier). / French name: proposed translation; correct it in "
     "\"Correction\" if needed, especially medicines (yellow rows = point to check).", False),
    ("2. Unité : l'unité de base dans laquelle le stock sera compté (comprimé, pièce, paire…). / Unit: the base "
     "unit stock is counted in.", False),
    ("3. Lignes roses : l'article ressemble à un produit déjà dans AERIS. Dites s'il s'agit du même produit "
     "(on garde un seul code) ou d'un produit différent. / Pink rows: looks like a product already in AERIS; "
     "say whether it is the same product (one code kept) or a different one.", False),
    ("4. Colonne « Décision » : OK, Modifier ou Retirer. / \"Decision\" column: OK, Change or Remove.", False),
    ("5. Lot/expiration obligatoire : Oui pour médicaments, laboratoire, EPI et enterrements ; Non pour "
     "équipements, WASH et soins intensifs. Changez si besoin. / Lot & expiry required: Yes for medicines, lab, "
     "PPE and burials; No for equipment, WASH and intensive care. Change if needed.", False),
    ("", False),
    ("Les 32 produits déjà reçus (feuille « Déjà dans AERIS ») gardent leurs codes. / The 32 products already "
     "received (sheet \"Already in AERIS\") keep their codes.", False),
    ("Rien n'est chargé dans AERIS avant votre validation. / Nothing is loaded into AERIS before your approval.", True),
]
for t, bold in lines:
    rm.append([t])
    c = rm.cell(rm.max_row, 1)
    c.alignment = Alignment(wrap_text=True, vertical="top")
    if bold:
        c.font = Font(bold=True, color=MAROON, size=12 if rm.max_row == 1 else 11)
rm.column_dimensions["A"].width = 120

ws = wb.create_sheet("Catalogue")
hdr = ["Code", "Catégorie / Category", "Name (EN)", "Nom (FR)", "Unité / Unit", "Classe / Class", "Source",
       "Statut / Status", "Lot/expiration obligatoire / Lot & expiry", "Coût unitaire USD (PCI) / Unit cost",
       "À vérifier / Check", "Décision", "Correction / Commentaire"]
rows = []
for m in master:
    t = fr[m["code"]]
    rows.append([m["code"], m["category"], m["name"], t["fr"], m["unit"], m.get("subclass", ""),
                 "; ".join(m["sources"]), status(m), "Oui / Yes" if m["prefix"] in LOT else "Non / No",
                 m.get("cost"), t.get("flag", ""), "", ""])
table(ws, hdr, rows, [14, 20, 46, 46, 18, 22, 22, 26, 14, 12, 34, 12, 30])
dv = DataValidation(type="list", formula1='"OK,Modifier / Change,Retirer / Remove"', allow_blank=True)
ws.add_data_validation(dv)
dv.add(f"L2:L{ws.max_row}")
for r in range(2, ws.max_row + 1):
    st = ws.cell(r, 8).value
    fill = have_fill if st.startswith("Already") else dup_fill if st.startswith("Possible") else (
        flag_fill if ws.cell(r, 11).value else None)
    if fill:
        for c in range(1, 12):
            ws.cell(r, c).fill = fill

ws2 = wb.create_sheet("Déjà dans AERIS")
matched = collections.defaultdict(list)
for m in master:
    if m["status"] == "existing":
        matched[m["code"]].append(m["name"] + " (identique / same)")
    elif m.get("possible"):
        matched[m["possible"]].append(f"{m['name']} → {m['code']} (doublon possible / possible duplicate)")
rows2 = [[c, r[H.index("Category")], r[H.index("Name")], r[H.index("Description")], r[H.index("UnitOfMeasure")],
          "\n".join(matched.get(c, [])) or "—"] for c, r in current.items()]
table(ws2, ["Code", "Catégorie / Category", "Name (EN)", "Nom (FR)", "Unité / Unit",
            "Dans la liste de la logistique / In the logistics list"], rows2, [14, 22, 44, 44, 18, 60])

ws3 = wb.create_sheet("Résumé - Summary")
cnt = collections.Counter((m["category"], m["status"]) for m in master)
cats = sorted({m["category"] for m in master})
rows3 = [[c, cnt[(c, "new")], cnt[(c, "existing")], sum(1 for m in master if m["category"] == c and fr[m["code"]].get("flag"))]
         for c in cats]
rows3.append(["Total", sum(r[1] for r in rows3), sum(r[2] for r in rows3), sum(r[3] for r in rows3)])
table(ws3, ["Catégorie / Category", "Nouveaux / New", "Déjà dans AERIS / Existing", "À vérifier / To check"],
      rows3, [34, 16, 22, 18])
for c in ws3[ws3.max_row]:
    c.font = Font(bold=True)
wb.save(REVIEW)
print("review:", REVIEW, len(master), "items,", sum(1 for m in master if fr[m["code"]].get("flag")), "flagged")

# ---- import files (new products only; possible duplicates included until the review says otherwise)
new = [m for m in master if m["status"] == "new"]
cwb = openpyxl.Workbook()
c = cwb.active
c.append(["id", "name", "parentCategoryId"])
for cat in sorted({m["category"] for m in new} - EXISTING_CATS):
    c.append(["", cat, ""])
cwb.save(os.path.join(OUT, "1_categories.xlsx"))

# OpenBoxes tags imported products with the file name, so the file is named after the existing tag
with open(os.path.join(OUT, "Ebola 2026.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f, lineterminator="\n")
    w.writerow(H)
    for m in new:
        row = dict.fromkeys(H, "")
        row.update(Active="true", ProductCode=m["code"], ProductType="Default", Name=m["name"],
                   Category=m["category"], Description=fr[m["code"]]["fr"], UnitOfMeasure=m["unit"],
                   Tags="Ebola 2026", UnitCost="" if m.get("cost") in (None, "") else m["cost"],
                   LotAndExpiryControl="true" if m["prefix"] in LOT else "false",
                   ControlledSubstance="true" if "opioid analgesic" in m.get("subclass", "").lower() else "")
        w.writerow([row[k] for k in H])

swb = openpyxl.Workbook()
s = swb.active
s.append(["Product Code", "Class of synonym", "Locale", "Synonym name"])
for m in new:
    s.append([m["code"], "DISPLAY_NAME", "fr", fr[m["code"]]["fr"]])
swb.save(os.path.join(OUT, "3_synonyms.xlsx"))
print("import files:", OUT, len(new), "products")
