"""Drive the local AERIS in Chrome and capture the screens for the storekeeper training video.

Each step = one 1920x1080 screenshot + boxes to highlight + the narration line (French).
Output: shots/<n>.png and steps.json. Run scenes selectively: python capture.py 1 2 3
"""
import json
import os
import re
import sys
import time

from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8")

BASE = "http://localhost:8080/openboxes"
HERE = os.path.dirname(os.path.abspath(__file__))
SHOTS = os.path.join(HERE, "shots")
os.makedirs(SHOTS, exist_ok=True)
STEPS_FILE = os.path.join(HERE, "steps.json")
ACCOUNTS = os.path.join(sys.argv[1], "aeris", "tools", "test-accounts.local.txt")
SCENES = [int(a) for a in sys.argv[2:]]

BUNIA = "2c938083a153d0e401a153d92d8d0052"
ISIRO = "2c938083a154558001a1545cad71001a"

steps = json.load(open(STEPS_FILE, encoding="utf-8")) if os.path.exists(STEPS_FILE) else {}


def password():
    line = open(ACCOUNTS, encoding="utf-8").read().splitlines()[1]
    return line.split(" / ", 1)[1].strip()


class Recorder:
    def __init__(self, page, scene):
        self.page = page
        self.scene = scene
        self.n = 0
        steps[str(scene)] = []

    def box(self, target):
        if target is None:
            return None
        loc = self.page.locator(target) if isinstance(target, str) else target
        try:
            el = loc.first
            # a react-select's real input is tiny: highlight the whole control instead
            if (el.get_attribute("id", timeout=4000) or "").startswith("react-select"):
                el = el.locator("xpath=ancestor::div[contains(@class,'control')][1]")
            b = el.bounding_box(timeout=4000)
        except Exception:
            print("    (no highlight for", target, ")")
            return None
        return [b["x"], b["y"], b["width"], b["height"]] if b else None

    def shot(self, say, caption=None, hl=None, pause=0.6):
        """Screenshot with highlight boxes (CSS px, scaled later) and the narration."""
        time.sleep(pause)
        self.n += 1
        name = f"s{self.scene:02d}_{self.n:02d}.png"
        boxes = [b for b in ([self.box(h) for h in (hl if isinstance(hl, list) else [hl])] if hl else []) if b]
        self.page.screenshot(path=os.path.join(SHOTS, name))
        steps[str(self.scene)].append({"img": name, "say": say, "caption": caption or say, "boxes": boxes})
        print(" ", name, "-", (caption or say)[:70])


def wait_idle(page, extra=0.8):
    try:
        page.wait_for_load_state("networkidle", timeout=15000)
    except Exception:
        pass
    time.sleep(extra)


def login(page, user="magasinier.bunia", pw=None):
    page.goto(f"{BASE}/auth/logout")
    page.goto(f"{BASE}/auth/login?lang=fr")
    page.fill("input[name=username]", user)
    page.fill("input[name=password]", pw or password())
    page.click("button[type=submit]")
    wait_idle(page)


def react_select(page, container, text, option_text=None):
    """Type in a react-select inside `container` and click the option containing option_text."""
    page.locator(container).locator("input").first.click()
    page.keyboard.type(text, delay=60)
    opt = page.locator("[class*='option']", has_text=option_text or text).first
    opt.wait_for(timeout=15000)
    opt.click()
    time.sleep(0.4)


# ---------------------------------------------------------------- scenes

def scene1(page):
    """Se connecter et choisir son dépôt."""
    r = Recorder(page, 1)
    page.goto(f"{BASE}/auth/logout")
    page.goto(f"{BASE}/auth/login?lang=en")
    wait_idle(page)
    r.shot("Voici la page de connexion d'AERIS, le système de gestion des stocks de la riposte Ebola d'Africa CDC. "
           "Ouvrez l'adresse donnée par votre responsable dans Chrome ou Edge.",
           "Ouvrir AERIS dans le navigateur")
    r.shot("D'abord, mettez l'écran en français : cliquez sur F R, en haut à droite.",
           "Cliquer sur FR pour le français", hl="a[href*='lang=fr']")
    page.click("a[href*='lang=fr']")
    wait_idle(page)
    page.fill("input[name=username]", "magasinier.bunia")
    page.fill("input[name=password]", password())
    r.shot("Saisissez votre nom d'utilisateur et votre mot de passe, puis cliquez sur Se connecter. "
           "Ne partagez jamais votre mot de passe : chaque mouvement est enregistré à votre nom.",
           "Nom d'utilisateur + mot de passe → Se connecter",
           hl=["input[name=username]", "input[name=password]", "button[type=submit]"])
    page.click("button[type=submit]")
    wait_idle(page)
    r.shot("AERIS vous demande ensuite dans quel entrepôt vous travaillez. Les trois entrepôts d'Africa CDC sont "
           "classés par province : Isiro, Bunia et Beni. Cliquez sur le vôtre.",
           "Choisir son entrepôt", hl=f"a[href*='{BUNIA}']")
    page.click(f"a[href*='{BUNIA}']")
    wait_idle(page, 2.5)
    r.shot("Vous voilà sur le tableau de bord de l'entrepôt de Bunia. Le nom de l'entrepôt est toujours affiché "
           "en haut à gauche : vérifiez-le avant chaque opération.",
           "Vérifier le nom de l'entrepôt en haut à gauche", hl=".location-chooser__button")


def scene2(page):
    """Le tableau de bord et les menus."""
    r = Recorder(page, 2)
    page.goto(f"{BASE}/dashboard/index")
    wait_idle(page, 3)
    r.shot("Le tableau de bord résume l'état du stock : produits expirés, stock négatif, et le graphique des "
           "péremptions à venir.",
           "Le tableau de bord", hl=".dashboard-container, main")
    tab = page.get_by_text("Stock et péremptions").first
    r.shot("Trois onglets à gauche : Vue d'ensemble, Stock et péremptions, et Distribution. "
           "Consultez Stock et péremptions chaque semaine.",
           "Onglets : Vue d'ensemble, Stock et péremptions, Distribution", hl=tab)
    r.shot("En haut, les menus. Pour un magasinier, quatre suffisent : Entrée pour recevoir, Sortie pour "
           "distribuer, Inventaire pour compter, et Rapport pour les fiches de stock.",
           "Menus utiles : Entrée · Sortie · Inventaire · Rapport",
           hl=[page.get_by_role("menuitem", name="Entrée"), page.get_by_role("menuitem", name="Sortie"),
               page.get_by_role("menuitem", name="Inventaire"), page.get_by_role("menuitem", name="Rapport")])
    r.shot("La loupe, en haut à droite, retrouve n'importe quel article en tapant quelques lettres de son nom.",
           "La loupe : rechercher un article", hl="[aria-label=search]")


def rsel(page, k):
    return page.locator("input[id^='react-select']").nth(k)


def pick(page, k, text, option_text=None):
    """Type in the k-th react-select of the page and click the matching option."""
    inp = rsel(page, k)
    opt = page.locator("[id*='-option-']", has_text=option_text or text).first
    for attempt in range(3):
        inp.click(force=True)
        page.keyboard.press("Control+A")
        page.keyboard.press("Backspace")
        time.sleep(0.3)
        page.keyboard.type(text, delay=80)
        try:
            opt.wait_for(timeout=8000)
            break
        except Exception:
            print("    retry select", text)
    opt.click()
    time.sleep(0.5)


def scene3(page):
    """Recevoir une livraison (don)."""
    r = Recorder(page, 3)
    page.goto(f"{BASE}/dashboard/index")
    wait_idle(page, 2)
    page.get_by_role("menuitem", name="Entrée").first.hover()
    time.sleep(1)
    r.shot("Un camion de l'UNICEF arrive avec des intrants. Ouvrez le menu Entrée, puis Créer un mouvement de stock "
           "entrant.", "Entrée → Créer un mouvement de stock entrant",
           hl=page.get_by_text("Créer un mouvement de stock entrant").first)
    page.goto(f"{BASE}/stockMovement/createInbound?direction=INBOUND")
    wait_idle(page, 2)
    page.fill("input[name=description]", "Don UNICEF – BL-UNICEF-0457")
    pick(page, 0, "UNICEF")
    pick(page, 3, "Magasinier", "Magasinier Bunia")
    page.locator("input[name=dateRequested]").click()
    page.keyboard.type("20/10/2026", delay=40)
    page.keyboard.press("Tab")
    time.sleep(0.5)
    r.shot("Remplissez l'en-tête. Description : le numéro du bordereau de livraison. Origine : le donateur, ici "
           "UNICEF. La destination est déjà votre entrepôt. Demandé par : votre nom. Et la date. Puis Suivant.",
           "Description = n° du bordereau · Origine = le donateur · Date",
           hl=["input[name=description]", rsel(page, 0), rsel(page, 3), "input[name=dateRequested]"])
    page.get_by_role("button", name="Suivant").click()
    wait_idle(page, 2.5)

    def li(i, field):
        return page.locator(f"[name='values.lineItems.{i}.{field}']")

    def fill_line(i, search, option, lot, expiry, qty):
        rsel(page, 1 + 2 * i).click()
        page.keyboard.type(search, delay=60)
        page.locator("[id*='-option-']", has_text=option).first.click()
        time.sleep(0.4)
        li(i, "lotNumber").fill(lot)
        li(i, "expirationDate").click()
        page.keyboard.type(expiry, delay=40)
        page.keyboard.press("Tab")
        li(i, "quantityRequested").fill(qty)
        time.sleep(0.6)

    fill_line(0, "Paracé", "Paracétamol 500 mg", "PCM2410", "31/08/2028", "2000")
    r.shot("Ajoutez une ligne par lot, comme sur le bordereau : l'article, le numéro de lot, la date d'expiration, "
           "et la quantité. Tapez la date en chiffres, jour, mois, année : trente-et-un, zéro huit, deux mille "
           "vingt-huit.",
           "Une ligne par lot : article · lot · expiration (jj/mm/aaaa) · quantité",
           hl=[rsel(page, 1), li(0, "lotNumber"), li(0, "expirationDate"), li(0, "quantityRequested")])
    page.get_by_role("button", name="Ajouter une ligne").click()
    time.sleep(0.8)
    fill_line(1, "Ringer", "Ringer", "RL1130", "30/11/2027", "120")
    r.shot("Pour un deuxième lot, cliquez sur Ajouter une ligne. Vérifiez chaque ligne avec le bordereau, "
           "puis Suivant.", "« Ajouter une ligne » pour chaque lot, puis Suivant",
           hl=[page.get_by_role("button", name="Ajouter une ligne"), page.get_by_role("button", name="Suivant")])
    page.get_by_role("button", name="Suivant").click()
    wait_idle(page, 2.5)
    # shipment type + expected delivery date on the send page
    st = rsel(page, 2)
    st.click(force=True)
    time.sleep(0.8)
    page.locator("[id*='-option-']", has_text=re.compile("Route|Land")).first.click()
    page.locator("input[name=expectedDeliveryDate]").click()
    page.keyboard.type("20/10/2026", delay=40)
    page.keyboard.press("Tab")
    time.sleep(0.6)
    r.shot("Dernière étape de l'enregistrement : choisissez le type de livraison, par exemple Route, et la date "
           "d'arrivée. Cliquez ensuite sur Send shipment : cela enregistre la livraison comme en route vers vous.",
           "Type de livraison · date d'arrivée → « Send shipment »",
           hl=[st, "input[name=expectedDeliveryDate]",
               page.get_by_role("button", name="Send shipment")])
    page.get_by_role("button", name="Send shipment").click()
    wait_idle(page, 3)
    r.shot("La livraison est enregistrée, au statut Envoyé. Les intrants ne sont pas encore dans votre stock : "
           "il faut maintenant les réceptionner, après les avoir comptés au déchargement.",
           "Statut « Envoyé » → maintenant, Réceptionner", hl=page.get_by_role("link", name="Réceptionner"))
    page.get_by_role("link", name="Réceptionner").click()
    wait_idle(page, 3)
    page.get_by_role("button", name="Remplissage automatique des quantités").click()
    time.sleep(1)
    ringer = page.locator("tr, [class*=row]").filter(has_text="Ringer").last
    rec = ringer.locator("input[id$='quantityReceiving']")
    rec.fill("110")
    ringer.locator("input[id$='.comment']").fill("10 flacons cassés")
    time.sleep(0.6)
    r.shot("Saisissez dans Reçu maintenant ce que vous avez réellement compté. Le bouton Remplissage automatique "
           "recopie les quantités du bordereau. Corrigez s'il manque quelque chose : ici, 110 flacons au lieu de 120, "
           "avec un commentaire.",
           "« Reçu maintenant » = ce que vous avez compté · commentaire si écart",
           hl=[page.get_by_role("button", name="Remplissage automatique des quantités"), rec])
    page.get_by_role("button", name="Suivant").click()
    wait_idle(page, 2.5)
    r.shot("Vérifiez le récapitulatif : le reçu et ce qui reste en attente. Puis cliquez sur Recevoir la livraison.",
           "Vérifier, puis « Recevoir la livraison »", hl=page.get_by_role("button", name="Recevoir la livraison"))
    page.get_by_role("button", name="Recevoir la livraison").click()
    wait_idle(page, 3.5)
    r.shot("C'est fait : le statut passe à Reçu, et les quantités reçues sont ajoutées à votre stock, lot par lot. "
           "L'écart de 10 flacons reste visible.",
           "Statut « Reçu » : le stock est à jour, l'écart reste visible")


def scene4(page):
    """Consulter le stock d'un article."""
    r = Recorder(page, 4)
    page.goto(f"{BASE}/dashboard/index")
    wait_idle(page, 2)
    page.locator("[aria-label=search]").first.click()
    time.sleep(0.5)
    page.keyboard.type("Ringer", delay=80)
    time.sleep(2)
    r.shot("Un médecin demande combien de Ringer lactate il reste. Cliquez sur la loupe et tapez quelques lettres : "
           "AERIS affiche tout de suite la quantité totale en stock.",
           "Loupe → taper le nom → la quantité s'affiche",
           hl=rsel(page, 0))
    page.keyboard.press("ArrowDown")
    page.keyboard.press("Enter")
    wait_idle(page, 3)
    r.shot("La fiche de l'article montre le stock lot par lot, avec la date d'expiration de chaque lot. "
           "C'est le lot qui expire en premier qui doit sortir en premier.",
           "La fiche article : stock par lot et date d'expiration",
           hl=page.locator("table").filter(has_text="RL").first)


def outbound(page, r, destination, dest_option, description, items, narrate=True):
    """Create, pick and send an outbound movement. items = [(search, option, qty)]."""
    page.goto(f"{BASE}/stockMovement/createOutbound?direction=OUTBOUND")
    wait_idle(page, 2.5)
    banner = page.locator(".version-box ~ * button, [class*=close]").first
    page.fill("#description", description)
    pick(page, 1, destination, dest_option)
    pick(page, 2, "Magasinier", "Magasinier Bunia")
    page.locator("#dateRequested").click()
    page.keyboard.type("20/10/2026", delay=40)
    page.keyboard.press("Escape")
    pick(page, 3, "Ad", "Adhoc")
    time.sleep(0.5)
    if narrate:
        r.shot("Description : l'objet de la sortie. Destination : la zone de santé, le centre de traitement ou "
               "l'entrepôt qui reçoit. Demandé par, la date, et le type de requête. Puis Suivant.",
               "Description · Destination · Demandé par · Date · Type → Suivant",
               hl=["#description", rsel(page, 1), rsel(page, 2), "#dateRequested", rsel(page, 3)])
    page.get_by_role("button", name="Suivant").click()
    wait_idle(page, 3)
    for i, (search, option, qty) in enumerate(items):
        if i:
            page.get_by_role("button", name="Ajouter une ligne").click()
            time.sleep(0.6)
        prod = page.locator("input[id^='react-select']").nth(1 + 2 * i)
        prod.click()
        page.keyboard.type(search, delay=60)
        page.locator("[id*='-option-']", has_text=option).first.click()
        time.sleep(0.4)
        page.locator(f"[id='lineItems[{i}].quantityRequested']").fill(qty)
        time.sleep(0.4)
    if narrate:
        r.shot("Ajoutez les articles demandés et la quantité, sans choisir de lot : AERIS le fera à l'étape "
               "suivante. Puis Suivant.",
               "Articles + quantités (pas de lot ici) → Suivant",
               hl=[page.locator("input[id^='react-select']").nth(1), page.locator("[id='lineItems[0].quantityRequested']")])
    page.get_by_role("button", name="Suivant").click()
    wait_idle(page, 3.5)
    if narrate:
        r.shot("L'écran Modifier compare la demande au stock disponible. Si une quantité dépasse le stock, "
               "corrigez-la ici. Puis Suivant.",
               "Modifier : vérifier la demande face au stock disponible")
    page.get_by_role("button", name="Suivant").click()
    wait_idle(page, 4)
    if narrate:
        r.shot("À l'étape Choisir, AERIS propose automatiquement les lots, en commençant par celui qui expire en "
               "premier. Préparez les colis avec exactement ces lots. Vous pouvez imprimer la liste de sélection.",
               "Choisir : AERIS propose le lot qui expire en premier",
               hl=[page.get_by_text("Imprimer la liste de sélection").first,
                   page.locator("[class*='rt-table'], [role=grid], table").first])
    page.get_by_role("button", name="Suivant").click()
    wait_idle(page, 3.5)
    st = page.locator("input[id^='react-select']").last
    st.click(force=True)
    time.sleep(0.8)
    page.locator("[id*='-option-']", has_text=re.compile("Route|Land")).first.click()
    page.locator("#expectedDeliveryDate, input[name=expectedDeliveryDate]").first.click()
    time.sleep(0.6)
    page.locator(".react-datepicker__day--today, .react-datepicker__day--020:not(.react-datepicker__day--outside-month)").first.click()
    time.sleep(0.6)
    if narrate:
        r.shot("Dernier écran : le type de livraison, Route, et la date d'arrivée prévue. Vérifiez la liste, "
               "puis cliquez sur Envoyer la livraison. Le stock diminue à ce moment-là.",
               "Type de livraison · date prévue → « Envoyer la livraison »",
               hl=[st, page.get_by_role("button", name="Envoyer la livraison")])
    page.get_by_role("button", name="Envoyer la livraison").click()
    wait_idle(page, 4)


def scene5(page):
    """Sortie vers une zone de santé + bon de sortie."""
    r = Recorder(page, 5)
    page.goto(f"{BASE}/dashboard/index")
    wait_idle(page, 2)
    page.get_by_role("menuitem", name="Sortie").first.hover()
    time.sleep(1)
    r.shot("La zone de santé de Bunia demande des intrants. Menu Sortie, puis Créer un mouvement de stock sortant.",
           "Sortie → Créer un mouvement de stock sortant",
           hl=page.get_by_text("Créer un mouvement de stock sortant").first)
    outbound(page, r, "BCZ Bunia", "BCZ Bunia", "Dotation BCZ Bunia – semaine 43",
             [("Paracé", "Paracétamol 500 mg", "1500"), ("Ringer", "Ringer", "30")])
    r.shot("La sortie est enregistrée au statut Envoyé. Maintenant, le bon de sortie : menu Télécharger, puis "
           "Delivery Note.",
           "Télécharger → « Delivery Note » = le bon de sortie",
           hl=page.get_by_role("button", name="Télécharger").or_(page.get_by_text("Télécharger")).first)
    page.get_by_text("Télécharger").first.click()
    time.sleep(1)
    r.shot("Dans la liste, le bon de sortie s'appelle Delivery Note, shipment order.",
           "Choisir « Delivery Note (shipment order) »",
           hl=page.get_by_text("Delivery Note (shipment order)").first)
    with page.context.expect_page() as pop:
        page.get_by_text("Delivery Note (shipment order)").first.click()
    note = pop.value
    note.set_viewport_size({"width": 1280, "height": 720})
    wait_idle(note, 2.5)
    r.page = note
    r.shot("Voici le bon de sortie, en français, avec le logo d'Africa CDC : chaque lot, sa date d'expiration et "
           "la quantité livrée. Cliquez sur Imprimer.",
           "Le bon de sortie : lots, expirations, quantités → Imprimer",
           hl=note.get_by_role("button", name="Imprimer").or_(note.get_by_text("Imprimer", exact=True)).first)
    note.mouse.wheel(0, 900)
    time.sleep(1)
    r.shot("En bas, faites signer celui qui expédie, celui qui approuve et celui qui transporte. Le destinataire "
           "signe à la réception. Classez le bon signé : c'est la preuve de la distribution.",
           "Signatures : expédié · approuvé · livré · reçu. Classer le bon signé.")
    note.close()
    r.page = page


def scene6(page):
    """Transfert vers un autre entrepôt, et réception à l'arrivée."""
    r = Recorder(page, 6)
    page.goto(f"{BASE}/stockMovement/createOutbound?direction=OUTBOUND")
    wait_idle(page, 2.5)
    rsel(page, 1).click()
    page.keyboard.type("Entrepôt", delay=60)
    page.locator("[id*='-option-']").first.wait_for()
    time.sleep(0.8)
    r.shot("Un transfert vers Isiro ou Beni se fait exactement comme une sortie : choisissez simplement l'entrepôt "
           "comme destination.",
           "Transfert = une sortie dont la destination est un entrepôt",
           hl=page.locator("[class*='menu']").filter(has=page.locator("[id*='-option-']")).first)
    page.keyboard.press("Escape")
    outbound(page, r, "Isiro", "Isiro", "Transfert vers Isiro – réassort",
             [("Paracé", "Paracétamol 500 mg", "500")], narrate=False)
    r.shot("Le transfert part de Bunia. Le stock de Bunia diminue tout de suite ; celui d'Isiro augmentera quand "
           "Isiro aura réceptionné.",
           "Envoyé depuis Bunia : Isiro doit maintenant réceptionner")
    page.goto(f"{BASE}/dashboard/chooseLocation/{ISIRO}")
    wait_idle(page, 2)
    page.goto(f"{BASE}/stockMovement/list?direction=INBOUND")
    wait_idle(page, 4)
    r.shot("À Isiro, le magasinier ouvre Entrée, Liste des mouvements de stock entrants. Le transfert attend, "
           "au statut Envoyé. Il l'ouvre et clique sur Réceptionner, comme pour un don.",
           "À l'arrivée : Entrée → Liste des mouvements entrants → Réceptionner",
           hl=page.get_by_text("Transfert vers Isiro").first)
    page.goto(f"{BASE}/dashboard/chooseLocation/{BUNIA}")
    wait_idle(page, 1)


def add_image(r, img, say, caption):
    """A step showing a prepared picture (e.g. an Excel file) instead of the browser."""
    steps[str(r.scene)].append({"img": img, "say": say, "caption": caption, "boxes": [], "full": True})
    print(" ", img, "-", caption[:70])


def scene7(page):
    """Comptage physique."""
    r = Recorder(page, 7)
    page.goto(f"{BASE}/dashboard/index")
    wait_idle(page, 2)
    page.get_by_role("menuitem", name="Inventaire").first.hover()
    time.sleep(1)
    link = page.get_by_text("Importer un comptage de stock (Excel/CSV)").first
    link.scroll_into_view_if_needed()
    time.sleep(0.5)
    r.shot("Pour un comptage physique, ouvrez Inventaire, puis Importer un comptage de stock.",
           "Inventaire → Importer un comptage de stock (Excel/CSV)", hl=link)
    page.goto(f"{BASE}/batch/importData?importType=inventory")
    wait_idle(page, 2)
    r.shot("Commencez par Télécharger les données : vous obtenez un fichier Excel avec le stock actuel, lot par lot.",
           "« Télécharger les données » : la liste du stock actuel",
           hl=page.get_by_text("Télécharger les données").first)
    add_image(r, "x_count.png",
              "Imprimez-le ou ouvrez-le, comptez les rayons, et écrivez la quantité comptée dans la colonne "
              "Physical QOH. Ajoutez un commentaire pour chaque écart. Vous pouvez ne garder que les lots comptés : "
              "les autres lots ne changent pas.",
              "Écrire la quantité comptée · un commentaire pour chaque écart")
    page.set_input_files("input[type=file]", os.path.join(HERE, "comptage_video.xlsx"))
    time.sleep(0.5)
    r.shot("Revenez dans AERIS. La date et l'heure du comptage sont déjà remplies : corrigez-les si le comptage "
           "a eu lieu plus tôt. Choisissez votre fichier, puis cliquez sur Charger.",
           "Date du comptage · choisir le fichier · « Charger »",
           hl=["select[name=date_day]", "input[type=file]", page.get_by_role("button", name="Charger")])
    page.get_by_role("button", name="Charger").click()
    wait_idle(page, 3)
    r.shot("AERIS vérifie le fichier et affiche chaque ligne. Si tout est correct, il vous demande de transmettre "
           "le fichier au responsable logistique : c'est lui qui valide le comptage. Le stock ne change qu'à ce "
           "moment-là.",
           "Fichier vérifié → le responsable logistique valide le comptage",
           hl=[page.get_by_text("Fichier vérifié").first, page.get_by_text("Demandez au responsable").first])


def scene8(page):
    """Fiche de stock MCM."""
    r = Recorder(page, 8)
    page.goto(f"{BASE}/dashboard/index")
    wait_idle(page, 2)
    page.get_by_role("menuitem", name="Rapport").first.hover()
    time.sleep(1)
    r.shot("Pour la fiche de stock, au format du MCM, ouvrez Rapport, puis Exports Excel, Fiches de stock.",
           "Rapport → Exports Excel → Fiches de stock (format MCM)",
           hl=page.get_by_text("Fiches de stock (format MCM)").first)
    page.goto(f"{BASE}/aerisExport/index#cards")
    wait_idle(page, 2)
    page.select_option("#cardProduct", label="ACDC-MED-005 – Ringer's lactate 500 ml")
    page.fill("#cardLot", "RL1130")
    page.fill("#cardStart", "2026-10-01")
    page.fill("#cardEnd", "2026-10-20")
    time.sleep(0.5)
    btn = page.locator("#cardEnd").locator("xpath=ancestor::form").locator("button[type=submit]")
    r.shot("Choisissez l'entrepôt, l'article, si besoin le numéro de lot, et la période. Laissez Article vide "
           "pour avoir tous les articles. Puis cliquez sur Télécharger le fichier Excel.",
           "Entrepôt · article · période → télécharger",
           hl=["#cardLocation", "#cardProduct", "#cardLot", "#cardStart", btn])
    with page.expect_download() as dl:
        btn.click()
    path = os.path.join(HERE, "fiche_ringer.xlsx")
    dl.value.save_as(path)
    print("   downloaded", path)
    # x_card.png is made afterwards: python excel_shots.py card fiche_ringer.xlsx
    add_image(r, "x_card.png",
              "Le fichier reprend la fiche de stock du M C M : une fiche par lot, avec le stock d'ouverture, chaque "
              "entrée et chaque sortie avec son document, et le solde. Le solde final doit être égal à ce que vous "
              "comptez dans le rayon. Sinon, signalez l'écart à votre responsable.",
              "Une fiche par lot : ouverture · entrées · sorties · solde = stock du rayon")
    page.goto(f"{BASE}/aerisExport/index#all")
    wait_idle(page, 1.5)
    btn2 = page.locator("#allStart").locator("xpath=ancestor::form").locator("button[type=submit]")
    r.shot("À droite, Stock de tous les entrepôts donne un seul classeur avec le stock de Bunia, Isiro et Beni, "
           "pour les rapports au responsable logistique.",
           "« Stock de tous les entrepôts » : un classeur pour les 3 entrepôts",
           hl=[page.locator("#allStart").locator("xpath=ancestor::div[contains(@class,'box')][1]"), btn2])


SCENE_FUNCS = {1: scene1, 2: scene2, 3: scene3, 4: scene4, 5: scene5, 6: scene6, 7: scene7, 8: scene8}

with sync_playwright() as p:
    browser = p.chromium.launch(channel="chrome", headless=True)
    ctx = browser.new_context(viewport={"width": 1280, "height": 720}, device_scale_factor=1.5, locale="fr-FR",
                              timezone_id="Africa/Lubumbashi")
    page = ctx.new_page()
    page.set_default_timeout(20000)
    for s in SCENES:
        print("scene", s)
        if s != 1:
            login(page)
            page.goto(f"{BASE}/dashboard/chooseLocation/{BUNIA}")
            wait_idle(page)
        try:
            SCENE_FUNCS[s](page)
        except Exception as e:
            page.screenshot(path=os.path.join(HERE, "fail.png"))
            print("FAILED:", str(e).splitlines()[0])
            print("URL:", page.url)
            print(page.evaluate(open(os.path.join(HERE, "dump.js"), encoding="utf-8").read()).replace(" || ", chr(10)))
            raise SystemExit(1)
        json.dump(steps, open(STEPS_FILE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    browser.close()
