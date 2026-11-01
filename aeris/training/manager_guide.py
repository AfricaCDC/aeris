"""Illustrated guide for AERIS managers and administrators (EN + FR): roles, accounts, passwords, counts.

    python manager_guide.py <screenshot dir> <out.docx>
Screenshots m1..m8 come from a run against a local test copy (user creation, single-warehouse role, sign-in check).
"""
import os
import sys

from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
SHOTS, OUT = sys.argv[1], sys.argv[2]
LOGO = os.path.join(HERE, "..", "branding", "africacdc_logo_full.png")
CRIMSON = RGBColor(0x9F, 0x22, 0x41)
GREEN = RGBColor(0x1A, 0x56, 0x32)
GREY = RGBColor(0x53, 0x57, 0x5A)


def crop(name, top=0.0, bottom=1.0, left=0.0, right=1.0):
    im = Image.open(os.path.join(SHOTS, name))
    w, h = im.size
    out = os.path.join(SHOTS, "c_" + name)
    im.crop((int(w * left), int(h * top), int(w * right), int(h * bottom))).save(out)
    return out


doc = Document()
for s in doc.sections:
    s.left_margin = s.right_margin = Cm(2)
    s.top_margin = s.bottom_margin = Cm(1.6)
st = doc.styles["Normal"]
st.font.name = "Arial"
st.font.size = Pt(10)


def para(text, size=10, bold=False, color=None, italic=False, after=4):
    p = doc.add_paragraph()
    r = p.add_run(text)
    r.font.size, r.font.bold, r.font.italic = Pt(size), bold, italic
    if color:
        r.font.color.rgb = color
    p.paragraph_format.space_after = Pt(after)
    return p


def heading(en, fr):
    p = para(f"{en} / {fr}", 14, True, CRIMSON, after=2)
    p.paragraph_format.space_before = Pt(14)
    p.paragraph_format.keep_with_next = True


def step(n, en, fr, img=None, width=14.5):
    p = para(f"{n}. {en}", 10.5, True, GREEN, after=1)
    p.paragraph_format.keep_with_next = True
    para(fr, 10, False, GREY, True, after=4).paragraph_format.keep_with_next = bool(img)
    if img:
        doc.add_picture(img, width=Cm(width))
        doc.paragraphs[-1].paragraph_format.space_after = Pt(8)


def shade(cell, fill):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:fill"), fill)
    tcPr.append(shd)


doc.add_picture(LOGO, width=Cm(6))
para("AERIS – Guide for managers and administrators", 20, True, CRIMSON, after=0)
para("Guide du responsable et de l'administrateur", 14, False, GREY, after=6)
para("Accounts and roles, passwords, people leaving, stock-count validation. Every step was checked on a copy of "
     "AERIS. / Comptes et rôles, mots de passe, départs, validation des comptages. Chaque étape a été vérifiée sur "
     "une copie d'AERIS.", 10)

heading("1. Who can do what", "Qui peut faire quoi")
roles = [
    ("Role / Rôle", "Does / Fait", "Setting in AERIS / Réglage"),
    ("Storekeeper / Magasinier", "Receipts, issues, transfers, counts, exports in their own warehouse. / Entrées, "
     "sorties, transferts, comptages, exports dans son entrepôt.",
     "No default role. Location role Assistant at their warehouse. / Aucun rôle par défaut. Rôle d'emplacement "
     "Assistant sur son entrepôt."),
    ("Manager / Responsable", "As a storekeeper, plus validating stock counts. / Comme le magasinier, plus la "
     "validation des comptages.",
     "All warehouses: default role Manager. One warehouse: location role Manager. / Tous : rôle par défaut Manager. "
     "Un seul : rôle d'emplacement Manager."),
    ("Viewer / Lecture seule", "Sees stock and reports, changes nothing. / Consulte, ne modifie rien.",
     "Default role Browser, or location role Browser. / Rôle par défaut Browser, ou rôle d'emplacement Browser."),
    ("Administrator / Administrateur", "Accounts, products, configuration (1–2 people). / Comptes, produits, "
     "configuration (1 à 2 personnes).", "Default role Admin. / Rôle par défaut Admin."),
]
t = doc.add_table(rows=len(roles), cols=3)
t.style = "Table Grid"
for i, row in enumerate(roles):
    for j, txt in enumerate(row):
        c = t.rows[i].cells[j]
        c.text = ""
        r = c.paragraphs[0].add_run(txt)
        r.font.size = Pt(9)
        if i == 0:
            r.font.bold = True
            r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
            shade(c, "1A5632")
        elif j == 0:
            r.font.bold = True
para("A default role applies in every warehouse. A location role applies in one warehouse only: a storekeeper must "
     "have no default role, otherwise they see all three warehouses. / Un rôle par défaut vaut pour tous les "
     "entrepôts ; un rôle d'emplacement pour un seul. Un magasinier ne doit avoir aucun rôle par défaut, sinon il "
     "voit les trois entrepôts.", 9.5, italic=True, after=6).paragraph_format.space_before = Pt(6)

heading("2. Create an account", "Créer un compte")
step(1, "Gear icon (Configuration) → Users → Create User.",
     "Icône engrenage (Configuration) → Utilisateurs → Créer un utilisateur.", crop("m1_users.png", 0, 0.55))
step(2, "Username firstname.lastname, first and last name, a temporary password, email, language → Save.",
     "Nom d'utilisateur prenom.nom, prénom et nom, un mot de passe provisoire, email, langue → Enregistrer.",
     crop("m2_create.png", 0.12, 0.62, 0, 0.6), 12)
step(3, "New accounts are inactive. User Details tab: tick Active → Save.",
     "Un nouveau compte est inactif. Onglet Détails : cocher Actif → Enregistrer.",
     crop("m3_activate.png", 0.12, 0.62))
step(4, "Authorization tab. Storekeeper: leave Default Roles empty. Click Add Location Roles.",
     "Onglet Autorisation. Magasinier : laisser Rôles par défaut vide. Cliquer sur Ajouter des rôles d'emplacement.",
     crop("m4_authorization.png", 0.12, 0.75))
step(5, "Choose the warehouse and the role (Assistant for a storekeeper) → Save.",
     "Choisir l'entrepôt et le rôle (Assistant pour un magasinier) → Enregistrer.",
     crop("m5_location_role.png", 0.12, 0.62, 0.15, 0.85), 13)
step(6, "Check the line in Location Roles. To change a warehouse later: Delete this line and add a new one.",
     "Vérifier la ligne dans Rôles d'emplacement. Pour changer d'entrepôt plus tard : Supprimer la ligne et en "
     "ajouter une nouvelle.", crop("m6_roles_saved.png", 0.12, 0.72))
step(7, "Check what the person sees: Impersonate (button at the top), then Logout in the orange bar to come back. "
        "This storekeeper sees only Isiro.",
     "Vérifier ce que la personne voit : Impersonate (bouton en haut), puis Logout dans la barre orange pour revenir. "
     "Ce magasinier ne voit qu'Isiro.", crop("m8_storekeeper_sees.png", 0, 0.75, 0.3, 0.95), 11)
step(8, "Give the password privately (in person or by phone), never by email or in a WhatsApp group. Note the "
        "account in AERIS_users_template.xlsx (grey columns), without the password.",
     "Remettre le mot de passe en privé (en personne ou par téléphone), jamais par email ni dans un groupe WhatsApp. "
     "Noter le compte dans AERIS_users_template.xlsx (colonnes grises), sans le mot de passe.")

heading("3. Forgotten password", "Mot de passe oublié")
step(1, "Users → the person → Edit User → Change Password tab. Clear both fields (they are pre-filled), type the new "
        "password twice → Save. Give it privately.",
     "Utilisateurs → la personne → Modifier → onglet Changer le mot de passe. Vider les deux champs (ils sont "
     "pré-remplis), saisir le nouveau mot de passe deux fois → Enregistrer. Le remettre en privé.",
     crop("m7_password.png", 0.12, 0.62))

heading("4. Someone leaves or moves", "Départ ou mutation")
step(1, "Leaves: User Details tab → untick Active → Save. Do not delete the account: past movements keep their name.",
     "Départ : onglet Détails → décocher Actif → Enregistrer. Ne pas supprimer le compte : les mouvements passés "
     "gardent son nom.")
step(2, "Moves to another warehouse: Authorization tab → Delete the old location role → Add Location Roles for the "
        "new warehouse.",
     "Mutation : onglet Autorisation → Supprimer l'ancien rôle d'emplacement → Ajouter un rôle pour le nouvel "
     "entrepôt.")

heading("5. Validate a stock count", "Valider un comptage")
step(1, "The storekeeper checks the count file (Inventory → Import stock count) and sends it to you. With the "
        "Manager role, open the same page, upload the same file → Upload → check the lines → Finish. Steps with "
        "pictures: AERIS_stock_initial_guide.docx, step 7.",
     "Le magasinier vérifie le fichier de comptage (Inventaire → Importer un comptage) et vous l'envoie. Avec le "
     "rôle Manager, ouvrez la même page, chargez le même fichier → Charger → vérifier les lignes → Finir. Étapes "
     "illustrées : AERIS_stock_initial_guide.docx, étape 7.")

heading("6. Good practice", "Bonnes pratiques")
for en, fr in [
    ("One account per person; never share an account.", "Un compte par personne ; jamais de compte partagé."),
    ("Do not use Import data → Users: it gives every new account the same password.",
     "Ne pas utiliser Importer des données → Utilisateurs : tous les nouveaux comptes reçoivent le même mot de passe."),
    ("Keep the admin password in the Africa CDC password manager; use your own account for daily work.",
     "Garder le mot de passe admin dans le gestionnaire de mots de passe d'Africa CDC ; utiliser son propre compte "
     "au quotidien."),
    ("Once a month: deactivate accounts of people who have left.",
     "Une fois par mois : désactiver les comptes des personnes parties."),
    ("Microsoft sign-in (when IT enables it): the first sign-in creates an inactive account; activate it and add "
     "roles as in section 2.",
     "Connexion Microsoft (quand l'IT l'active) : la première connexion crée un compte inactif ; l'activer et "
     "ajouter les rôles comme en section 2."),
]:
    p = para("• " + en, 10, after=0)
    para("  " + fr, 9.5, color=GREY, italic=True, after=4)

doc.save(OUT)
print("saved", OUT)
