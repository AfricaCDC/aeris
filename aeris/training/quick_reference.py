"""One-page quick reference for storekeepers, English page then French page (A4, to print and pin up).

    python quick_reference.py <out.docx>
Menu names match the training videos (steps_en.json / steps.json captions).
"""
import os
import sys

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

HERE = os.path.dirname(os.path.abspath(__file__))
LOGO = os.path.join(HERE, "..", "branding", "africacdc_logo_full.png")
CRIMSON, GREEN, GOLD, INK, GREY = "9F2241", "1A5632", "B4A269", "1F2937", "53575A"
ADDRESS = "https://tools.africacdc.org/aeris/"

PAGES = {
    "en": {
        "title": "AERIS – Quick reference for storekeepers",
        "sub": "Africa CDC Ebola response · Bunia, Isiro and Beni warehouses",
        "addr": f"Open {ADDRESS} in Chrome or Edge",
        "cards": [
            ("1  Sign in", [
                "Username + password → Sign in.",
                "Choose your warehouse.",
                "Check the warehouse name at the top left before every operation.",
                "Language menu under the Sign in button: English / Français."]),
            ("2  Find stock", [
                "Magnifying glass (top right) → type the item name → the quantity appears.",
                "The item page shows the stock per batch and expiry date."]),
            ("3  Receive a delivery", [
                "Inbound → Create Inbound Movement.",
                "Description = delivery note no. · Origin = the donor.",
                "One line per batch: item · batch · expiry (dd/mm/yyyy) · quantity → Next.",
                "Shipment type · arrival date → Send shipment.",
                "Receive → enter what you counted, a comment for any difference → Receive shipment."]),
            ("4  Issue stock", [
                "Outbound → Create Outbound Movement.",
                "Destination · requested by · date → items and quantities → Next.",
                "AERIS picks the batch that expires first → Send shipment.",
                "Download → Delivery Note → print, sign, file."]),
            ("5  Transfer to another warehouse", [
                "An issue whose destination is the other warehouse (see 4).",
                "The receiving warehouse: Inbound → List Inbound Movements → Receive."]),
            ("6  Count stock", [
                "Inventory → Import stock count (Excel/CSV).",
                "Download Data → write the counted quantity, a comment for every difference.",
                "Count date · choose the file → Upload.",
                "The logistics lead validates the count."]),
            ("7  Excel reports", [
                "Reporting → Excel exports.",
                "Stock cards (MCM format): warehouse · item · period → Download Excel.",
                "Stock across warehouses: one workbook for the 3 warehouses."]),
            ("8  Golden rules", [
                "Record every movement the same day.",
                "One line per batch; dates day/month/year.",
                "A difference gets a comment: never correct stock silently.",
                "File every signed delivery note. Never share your password."]),
        ],
        "help": "Help",
        "help_lines": ["AERIS contact for this warehouse: ______________________",
                       "Phone / WhatsApp: ______________________",
                       "Forgot your password? Ask the AERIS administrator; do not create a new account."],
        "videos": "Training video: AERIS_training_storekeepers_EN.mp4 (9 min)",
    },
    "fr": {
        "title": "AERIS – Aide-mémoire du magasinier",
        "sub": "Riposte Ebola d'Africa CDC · Entrepôts de Bunia, Isiro et Beni",
        "addr": f"Ouvrir {ADDRESS} dans Chrome ou Edge",
        "cards": [
            ("1  Se connecter", [
                "Nom d'utilisateur + mot de passe → Se connecter.",
                "Choisir son entrepôt.",
                "Vérifier le nom de l'entrepôt en haut à gauche avant chaque opération.",
                "Menu des langues sous le bouton : English / Français."]),
            ("2  Trouver le stock", [
                "Loupe (en haut à droite) → taper le nom → la quantité s'affiche.",
                "La fiche article montre le stock par lot et date d'expiration."]),
            ("3  Recevoir une livraison", [
                "Entrée → Créer un mouvement de stock entrant.",
                "Description = n° du bordereau · Origine = le donateur.",
                "Une ligne par lot : article · lot · expiration (jj/mm/aaaa) · quantité → Suivant.",
                "Type de livraison · date d'arrivée → Send shipment.",
                "Réceptionner → saisir ce que vous avez compté, un commentaire si écart → Recevoir la livraison."]),
            ("4  Sortir du stock", [
                "Sortie → Créer un mouvement de stock sortant.",
                "Destination · demandé par · date → articles et quantités → Suivant.",
                "AERIS choisit le lot qui expire en premier → Envoyer la livraison.",
                "Télécharger → Delivery Note (bon de sortie) → imprimer, signer, classer."]),
            ("5  Transférer vers un autre entrepôt", [
                "Une sortie dont la destination est l'autre entrepôt (voir 4).",
                "L'entrepôt qui reçoit : Entrée → Liste des mouvements entrants → Réceptionner."]),
            ("6  Compter le stock", [
                "Inventaire → Importer un comptage de stock (Excel/CSV).",
                "Télécharger les données → écrire la quantité comptée, un commentaire pour chaque écart.",
                "Date du comptage · choisir le fichier → Charger.",
                "Le responsable logistique valide le comptage."]),
            ("7  Rapports Excel", [
                "Rapport → Exports Excel.",
                "Fiches de stock (format MCM) : entrepôt · article · période → télécharger.",
                "Stock de tous les entrepôts : un classeur pour les 3 entrepôts."]),
            ("8  Règles d'or", [
                "Enregistrer chaque mouvement le jour même.",
                "Une ligne par lot ; dates jour/mois/année.",
                "Un écart = un commentaire : ne jamais corriger le stock en silence.",
                "Classer chaque bon de sortie signé. Ne jamais partager son mot de passe."]),
        ],
        "help": "Aide",
        "help_lines": ["Contact AERIS de cet entrepôt : ______________________",
                       "Téléphone / WhatsApp : ______________________",
                       "Mot de passe oublié ? Demandez à l'administrateur AERIS ; ne créez pas de nouveau compte."],
        "videos": "Vidéo de formation : AERIS_formation_magasiniers.mp4 (10 min)",
    },
}


def shade(cell, hex_fill):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_fill)
    tcPr.append(shd)


def borders(cell, top=None, others="EEE7D6", top_size=36):
    tcPr = cell._tc.get_or_add_tcPr()
    b = OxmlElement("w:tcBorders")
    for side in ("top", "left", "bottom", "right"):
        e = OxmlElement(f"w:{side}")
        color = top if side == "top" and top else others
        e.set(qn("w:val"), "single")
        e.set(qn("w:sz"), str(top_size if side == "top" and top else 6))
        e.set(qn("w:color"), color)
        b.append(e)
    tcPr.append(b)


def run(p, text, size=9, bold=False, color=INK):
    r = p.add_run(text)
    r.font.size = Pt(size)
    r.font.bold = bold
    r.font.color.rgb = RGBColor.from_string(color)
    r.font.name = "Arial"
    return r


def tight(p, before=0, after=0):
    p.paragraph_format.space_before = Pt(before)
    p.paragraph_format.space_after = Pt(after)
    p.paragraph_format.line_spacing = 1.05


def page(doc, lang, first):
    t = PAGES[lang]
    if not first:
        doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
    head = doc.add_table(rows=1, cols=2)
    head.alignment = WD_TABLE_ALIGNMENT.CENTER
    a, b = head.rows[0].cells
    a.width, b.width = Cm(5.2), Cm(12.8)
    pa = a.paragraphs[0]
    pa.add_run().add_picture(LOGO, width=Cm(4.6))
    pb = b.paragraphs[0]
    tight(pb)
    run(pb, t["title"], 19, True, CRIMSON)
    p2 = b.add_paragraph()
    tight(p2, 2)
    run(p2, t["sub"], 10, False, GREY)
    for c in (a, b):
        borders(c, others="FFFFFF")
    bar = doc.add_table(rows=1, cols=1)
    cell = bar.rows[0].cells[0]
    shade(cell, CRIMSON)
    borders(cell, others=CRIMSON)
    pp = cell.paragraphs[0]
    tight(pp, 4, 4)
    run(pp, t["addr"], 13, True, "FFFFFF")

    grid = doc.add_table(rows=4, cols=2)
    grid.alignment = WD_TABLE_ALIGNMENT.CENTER
    accents = [CRIMSON, GREEN, CRIMSON, GREEN, GOLD, GREEN, GOLD, CRIMSON]
    for k, (title, lines) in enumerate(t["cards"]):
        c = grid.rows[k // 2].cells[k % 2]
        c.width = Cm(9)
        shade(c, "F5F3EE")
        borders(c, top=accents[k])
        p = c.paragraphs[0]
        tight(p, 5, 3)
        run(p, title, 12.5, True, accents[k] if accents[k] != GOLD else "7A6A33")
        for line in lines:
            q = c.add_paragraph()
            tight(q, 0, 3)
            q.paragraph_format.left_indent = Cm(0.35)
            q.paragraph_format.first_line_indent = Cm(-0.3)
            run(q, "• ", 10.5, True, GREY)
            run(q, line, 10.5)
        tight(c.add_paragraph(), 0, 4)

    hb = doc.add_table(rows=1, cols=1)
    c = hb.rows[0].cells[0]
    borders(c, top=GREEN, others="C3D9CB")
    p = c.paragraphs[0]
    tight(p, 3, 1)
    run(p, t["help"], 12.5, True, GREEN)
    for line in t["help_lines"]:
        q = c.add_paragraph()
        tight(q, 0, 3)
        run(q, line, 10.5)
    q = c.add_paragraph()
    tight(q, 1, 3)
    run(q, t["videos"], 9.5, False, GREY)


def main(out):
    doc = Document()
    s = doc.sections[0]
    s.page_height, s.page_width = Cm(29.7), Cm(21)
    s.left_margin = s.right_margin = Cm(1.4)
    s.top_margin = s.bottom_margin = Cm(1.1)
    st = doc.styles["Normal"]
    st.font.name = "Arial"
    st.font.size = Pt(9)
    page(doc, "en", True)
    page(doc, "fr", False)
    doc.save(out)
    print("saved", out)


if __name__ == "__main__":
    main(sys.argv[1])
