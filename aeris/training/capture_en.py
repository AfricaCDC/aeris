"""Drive the local AERIS in Chrome and capture the screens for the storekeeper training video.

Each step = one 1920x1080 screenshot + boxes to highlight + the narration line (English).
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
SHOTS = os.path.join(HERE, "shots_en")
os.makedirs(SHOTS, exist_ok=True)
STEPS_FILE = os.path.join(HERE, "steps_en.json")
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
    page.goto(f"{BASE}/auth/login?lang=en")
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


def add_image(r, img, say, caption):
    """A step showing a prepared picture (e.g. an Excel file) instead of the browser."""
    steps[str(r.scene)].append({"img": img, "say": say, "caption": caption, "boxes": [], "full": True})
    print(" ", img, "-", caption[:70])


# ---------------------------------------------------------------- scenes (English interface, English narration)

def scene1(page):
    """Sign in and choose your warehouse."""
    r = Recorder(page, 1)
    page.goto(f"{BASE}/auth/logout")
    page.goto(f"{BASE}/auth/login?lang=en")
    wait_idle(page)
    r.shot("This is the sign-in page of AERIS, the stock management system of the Africa CDC Ebola response. "
           "Open the address given by your supervisor in Chrome or Edge.",
           "Open AERIS in your browser")
    r.shot("The screen is in English by default. If you prefer French, click F R at the top right; E N brings "
           "English back.",
           "EN / FR: choose the language", hl=["a[href*='lang=en']", "a[href*='lang=fr']"])
    page.fill("input[name=username]", "magasinier.bunia")
    page.fill("input[name=password]", password())
    r.shot("Enter your username and password, then click Sign in. Never share your password: every movement is "
           "recorded under your name.",
           "Username + password → Sign in",
           hl=["input[name=username]", "input[name=password]", "button[type=submit]"])
    page.click("button[type=submit]")
    wait_idle(page)
    r.shot("AERIS then asks which warehouse you work in. The three Africa CDC warehouses are grouped by province: "
           "Isiro, Bunia and Beni. Click yours.",
           "Choose your warehouse", hl=f"a[href*='{BUNIA}']")
    page.click(f"a[href*='{BUNIA}']")
    wait_idle(page, 2.5)
    r.shot("You are now on the dashboard of the Bunia warehouse. The warehouse name is always shown at the top "
           "left: check it before every operation.",
           "Check the warehouse name at the top left", hl=".location-chooser__button")


def scene2(page):
    """The dashboard and menus."""
    r = Recorder(page, 2)
    page.goto(f"{BASE}/dashboard/index")
    wait_idle(page, 3)
    r.shot("The dashboard summarises the stock: expired products, negative stock, and a chart of upcoming expiries.",
           "The dashboard", hl=".dashboard-container, main")
    tab = page.get_by_text("Stock & expiry").first
    r.shot("Three tabs on the left: Overview, Stock and expiry, and Distribution. Look at Stock and expiry every week.",
           "Tabs: Overview · Stock & expiry · Distribution", hl=tab)
    r.shot("At the top are the menus. A storekeeper needs four of them: Inbound to receive, Outbound to issue, "
           "Inventory to count, and Reporting for stock cards.",
           "Useful menus: Inbound · Outbound · Inventory · Reporting",
           hl=[page.get_by_role("menuitem", name="Inbound"), page.get_by_role("menuitem", name="Outbound"),
               page.get_by_role("menuitem", name="Inventory"), page.get_by_role("menuitem", name="Reporting")])
    r.shot("The magnifying glass at the top right finds any item: type a few letters of its name.",
           "The magnifying glass: search for an item", hl="[aria-label=search]")


def choose_type(page, st, label="Land"):
    """Open the shipment-type select (click the whole control) and pick label."""
    opt = page.locator("[id*='-option-']", has_text=label).first
    ctrl = st.locator("xpath=ancestor::div[contains(@class,'control')][1]")
    for attempt in range(3):
        ctrl.click(force=True)
        time.sleep(0.8)
        if not opt.is_visible():
            page.keyboard.type(label[:2], delay=80)
            time.sleep(0.8)
        if opt.is_visible():
            break
    opt.click()
    time.sleep(0.5)


def scene3(page):
    """Receive a delivery (donation)."""
    r = Recorder(page, 3)
    page.goto(f"{BASE}/dashboard/index")
    wait_idle(page, 2)
    page.get_by_role("menuitem", name="Inbound").first.hover()
    time.sleep(1)
    r.shot("A UNICEF truck arrives with supplies. Open the Inbound menu, then Create Inbound Movement.",
           "Inbound → Create Inbound Movement", hl=page.get_by_text("Create Inbound Movement").first)
    page.goto(f"{BASE}/stockMovement/createInbound?direction=INBOUND")
    wait_idle(page, 2)
    page.fill("input[name=description]", "UNICEF donation – BL-UNICEF-0457")
    pick(page, 0, "UNICEF")
    pick(page, 3, "Magasinier", "Magasinier Bunia")
    page.locator("input[name=dateRequested]").click()
    page.keyboard.type("20/10/2026", delay=40)
    page.keyboard.press("Tab")
    time.sleep(0.5)
    r.shot("Fill in the header. Description: the delivery note number. Origin: the donor, here UNICEF. The "
           "destination is already your warehouse. Requested by: your name. Then the date, and Next.",
           "Description = delivery note no. · Origin = the donor · Date",
           hl=["input[name=description]", rsel(page, 0), rsel(page, 3), "input[name=dateRequested]"])
    page.get_by_role("button", name="Next").click()
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

    fill_line(0, "Parac", "Paracetamol 500 mg", "PCM2410", "31/08/2028", "2000")
    r.shot("Add one line per batch, as on the delivery note: the item, the batch number, the expiry date and the "
           "quantity. Type the date as numbers, day, month, year: thirty-one, zero eight, twenty twenty-eight.",
           "One line per batch: item · batch · expiry (dd/mm/yyyy) · quantity",
           hl=[rsel(page, 1), li(0, "lotNumber"), li(0, "expirationDate"), li(0, "quantityRequested")])
    add = page.get_by_role("button", name=re.compile("Add line", re.I))
    add.click()
    time.sleep(0.8)
    fill_line(1, "Ringer", "Ringer", "RL1130", "30/11/2027", "120")
    r.shot("For a second batch, click Add line. Check every line against the delivery note, then Next.",
           "“Add line” for each batch, then Next", hl=[add, page.get_by_role("button", name="Next")])
    page.get_by_role("button", name="Next").click()
    wait_idle(page, 2.5)
    st = rsel(page, 2)
    choose_type(page, st)
    page.locator("input[name=expectedDeliveryDate]").click()
    page.keyboard.type("20/10/2026", delay=40)
    page.keyboard.press("Tab")
    time.sleep(0.6)
    r.shot("Last step of the record: choose the shipment type, for example Land, and the arrival date. Then click "
           "Send shipment: this records the delivery as on its way to you.",
           "Shipment type · arrival date → “Send shipment”",
           hl=[st, "input[name=expectedDeliveryDate]", page.get_by_role("button", name="Send shipment")])
    page.get_by_role("button", name="Send shipment").click()
    wait_idle(page, 3)
    recv = page.get_by_role("link", name=re.compile("^Receive", re.I)).first
    r.shot("The delivery is recorded with status Shipped. The supplies are not in your stock yet: you now receive "
           "them, after counting them at unloading.",
           "Status “Shipped” → now, Receive", hl=recv)
    recv.click()
    wait_idle(page, 3)
    auto = page.get_by_role("button", name=re.compile("Autofill", re.I))
    auto.click()
    time.sleep(1)
    ringer = page.locator("tr, [class*=row]").filter(has_text="Ringer").last
    rec = ringer.locator("input[id$='quantityReceiving']")
    rec.fill("110")
    ringer.locator("input[id$='.comment']").fill("10 bottles broken")
    time.sleep(0.6)
    r.shot("In Receiving now, enter what you actually counted. Autofill quantities copies the quantities from the "
           "delivery note. Correct anything missing: here 110 bottles instead of 120, with a comment. Note that "
           "this screen shows dates month first.",
           "“Receiving now” = what you counted · a comment for any difference", hl=[auto, rec])
    page.get_by_role("button", name="Next").click()
    wait_idle(page, 2.5)
    fin = page.get_by_role("button", name=re.compile("Receive shipment", re.I))
    r.shot("Check the summary: what was received and what is still outstanding. Then click Receive shipment.",
           "Check, then “Receive shipment”", hl=fin)
    fin.click()
    wait_idle(page, 3.5)
    r.shot("Done: the status changes to Received, and the received quantities are added to your stock, batch by "
           "batch. The 10-bottle difference stays visible.",
           "Status “Received”: stock is updated, the difference stays visible")


def scene4(page):
    """Look up an item's stock."""
    r = Recorder(page, 4)
    page.goto(f"{BASE}/dashboard/index")
    wait_idle(page, 2)
    page.locator("[aria-label=search]").first.click()
    time.sleep(0.5)
    page.keyboard.type("Ringer", delay=80)
    time.sleep(2)
    r.shot("A doctor asks how much Ringer's lactate is left. Click the magnifying glass and type a few letters: "
           "AERIS shows the total quantity in stock straight away.",
           "Magnifying glass → type the name → the quantity appears", hl=rsel(page, 0))
    page.keyboard.press("ArrowDown")
    page.keyboard.press("Enter")
    wait_idle(page, 3)
    r.shot("The item page shows the stock batch by batch, with the expiry date of each batch. The batch that "
           "expires first must go out first.",
           "The item page: stock per batch and expiry date",
           hl=page.locator("table").filter(has_text="RL").first)


def outbound(page, r, destination, dest_option, description, items, narrate=True):
    """Create, pick and send an outbound movement. items = [(search, option, qty)]."""
    page.goto(f"{BASE}/stockMovement/createOutbound?direction=OUTBOUND")
    wait_idle(page, 2.5)
    page.fill("#description", description)
    pick(page, 1, destination, dest_option)
    pick(page, 2, "Magasinier", "Magasinier Bunia")
    page.locator("#dateRequested").click()
    page.keyboard.type("20/10/2026", delay=40)
    page.keyboard.press("Escape")
    pick(page, 3, "Ad", "Adhoc")
    time.sleep(0.5)
    if narrate:
        r.shot("Description: what the issue is for. Destination: the health zone, treatment centre or warehouse "
               "receiving it. Requested by, the date, and the request type. Then Next.",
               "Description · Destination · Requested by · Date · Type → Next",
               hl=["#description", rsel(page, 1), rsel(page, 2), "#dateRequested", rsel(page, 3)])
    page.get_by_role("button", name="Next").click()
    wait_idle(page, 3)
    for i, (search, option, qty) in enumerate(items):
        if i:
            page.get_by_role("button", name=re.compile("Add line", re.I)).click()
            time.sleep(0.6)
        prod = page.locator("input[id^='react-select']").nth(1 + 2 * i)
        prod.click()
        page.keyboard.type(search, delay=60)
        page.locator("[id*='-option-']", has_text=option).first.click()
        time.sleep(0.4)
        page.locator(f"[id='lineItems[{i}].quantityRequested']").fill(qty)
        time.sleep(0.4)
    if narrate:
        r.shot("Add the requested items and quantities, without choosing batches: AERIS does that at the next step. "
               "Then Next.",
               "Items + quantities (no batch here) → Next",
               hl=[page.locator("input[id^='react-select']").nth(1),
                   page.locator("[id='lineItems[0].quantityRequested']")])
    page.get_by_role("button", name="Next").click()
    wait_idle(page, 3.5)
    if narrate:
        r.shot("The Edit screen compares the request with the stock available. If a quantity is more than the "
               "stock, correct it here. Then Next.",
               "Edit: check the request against available stock")
    page.get_by_role("button", name="Next").click()
    wait_idle(page, 4)
    if narrate:
        r.shot("At the Pick step, AERIS proposes the batches automatically, starting with the one that expires "
               "first. Prepare the parcels with exactly these batches. You can print the picklist.",
               "Pick: AERIS proposes the batch that expires first",
               hl=[page.get_by_text(re.compile("Print picklist", re.I)).first,
                   page.locator("[class*='rt-table'], [role=grid], table").first])
    page.get_by_role("button", name="Next").click()
    wait_idle(page, 3.5)
    st = page.locator("input[id^='react-select']").last
    choose_type(page, st)
    page.locator("#expectedDeliveryDate, input[name=expectedDeliveryDate]").first.click()
    time.sleep(0.6)
    page.locator(".react-datepicker__day--today, .react-datepicker__day--020:not(.react-datepicker__day--outside-month)").first.click()
    time.sleep(0.6)
    send = page.get_by_role("button", name=re.compile("Send shipment", re.I))
    if narrate:
        r.shot("Last screen: the shipment type, Land, and the expected arrival date. Check the list, then click "
               "Send shipment. The stock goes down at that moment.",
               "Shipment type · expected date → “Send shipment”", hl=[st, send])
    send.click()
    wait_idle(page, 4)


def scene5(page):
    """Issue to a health zone + delivery note."""
    r = Recorder(page, 5)
    page.goto(f"{BASE}/dashboard/index")
    wait_idle(page, 2)
    page.get_by_role("menuitem", name="Outbound").first.hover()
    time.sleep(1)
    r.shot("The Bunia health zone asks for supplies. Outbound menu, then Create Outbound Movement.",
           "Outbound → Create Outbound Movement", hl=page.get_by_text("Create Outbound Movement").first)
    outbound(page, r, "BCZ Bunia", "BCZ Bunia", "Allocation BCZ Bunia – week 43",
             [("Parac", "Paracetamol 500 mg", "1500"), ("Ringer", "Ringer", "30")])
    dl = page.get_by_text("Download").first
    r.shot("The issue is recorded with status Shipped. Now the delivery note, the bon de sortie: open the Download "
           "menu.",
           "Download → “Delivery Note” = the bon de sortie", hl=dl)
    dl.click()
    time.sleep(1)
    r.shot("In the list, choose Delivery Note, shipment order.",
           "Choose “Delivery Note (shipment order)”",
           hl=page.get_by_text("Delivery Note (shipment order)").first)
    with page.context.expect_page() as pop:
        page.get_by_text("Delivery Note (shipment order)").first.click()
    note = pop.value
    note.set_viewport_size({"width": 1280, "height": 720})
    wait_idle(note, 2.5)
    r.page = note
    r.shot("Here is the delivery note with the Africa CDC logo: each batch, its expiry date and the quantity "
           "delivered. Click Print.",
           "The delivery note: batches, expiry dates, quantities → Print",
           hl=note.get_by_role("button", name="Print").or_(note.get_by_text("Print", exact=True)).first)
    note.mouse.wheel(0, 900)
    time.sleep(1)
    r.shot("At the bottom, have it signed by whoever ships, approves and transports it. The recipient signs on "
           "receipt. File the signed note: it is the proof of distribution.",
           "Signatures: shipped · approved · delivered · received. File the signed note.")
    note.close()
    r.page = page


def scene6(page):
    """Transfer to another warehouse, and receipt on arrival."""
    r = Recorder(page, 6)
    page.goto(f"{BASE}/stockMovement/createOutbound?direction=OUTBOUND")
    wait_idle(page, 2.5)
    rsel(page, 1).click()
    page.keyboard.type("Entrepôt", delay=60)
    page.locator("[id*='-option-']").first.wait_for()
    time.sleep(0.8)
    r.shot("A transfer to Isiro or Beni is done exactly like an issue: simply choose the warehouse as the "
           "destination.",
           "Transfer = an issue whose destination is a warehouse",
           hl=page.locator("[class*='menu']").filter(has=page.locator("[id*='-option-']")).first)
    page.keyboard.press("Escape")
    outbound(page, r, "Isiro", "Isiro", "Transfer to Isiro – restock",
             [("Parac", "Paracetamol 500 mg", "500")], narrate=False)
    r.shot("The transfer leaves Bunia. Bunia's stock goes down straight away; Isiro's stock goes up once Isiro "
           "has received it.",
           "Shipped from Bunia: Isiro must now receive it")
    page.goto(f"{BASE}/dashboard/chooseLocation/{ISIRO}")
    wait_idle(page, 2)
    page.goto(f"{BASE}/stockMovement/list?direction=INBOUND")
    wait_idle(page, 4)
    r.shot("In Isiro, the storekeeper opens Inbound, List Inbound Movements. The transfer is waiting with status "
           "Shipped. They open it and click Receive, as for a donation.",
           "On arrival: Inbound → List Inbound Movements → Receive",
           hl=page.get_by_text("Transfer to Isiro").first)
    page.goto(f"{BASE}/dashboard/chooseLocation/{BUNIA}")
    wait_idle(page, 1)


def scene7(page):
    """Physical count."""
    r = Recorder(page, 7)
    page.goto(f"{BASE}/dashboard/index")
    wait_idle(page, 2)
    page.get_by_role("menuitem", name="Inventory").first.hover()
    time.sleep(1)
    link = page.get_by_text("Import stock count (Excel/CSV)").first
    link.scroll_into_view_if_needed()
    time.sleep(0.5)
    r.shot("For a physical count, open Inventory, then Import stock count.",
           "Inventory → Import stock count (Excel/CSV)", hl=link)
    page.goto(f"{BASE}/batch/importData?importType=inventory")
    wait_idle(page, 2)
    r.shot("Start with Download Data: you get an Excel file with the current stock, batch by batch.",
           "“Download Data”: the list of current stock", hl=page.get_by_text("Download Data").first)
    add_image(r, "x_count.png",
              "Print it or open it, count the shelves, and write the counted quantity in the Physical QOH column. "
              "Add a comment for every difference. You can keep only the batches you counted: the other batches "
              "do not change.",
              "Write the counted quantity · a comment for every difference")
    page.set_input_files("input[type=file]", os.path.join(HERE, "comptage_video_en.xlsx"))
    time.sleep(0.5)
    up = page.get_by_role("button", name="Upload")
    r.shot("Back in AERIS. The date and time of the count are already filled in: correct them if the count took "
           "place earlier. Choose your file, then click Upload.",
           "Count date · choose the file · “Upload”",
           hl=["select[name=date_day]", "input[type=file]", up])
    up.click()
    wait_idle(page, 3)
    r.shot("AERIS checks the file and shows each line. If everything is correct, it asks you to pass the file to "
           "the logistics lead, who validates the count. The stock only changes at that point.",
           "File checked → the logistics lead validates the count",
           hl=[page.get_by_text("File checked").first, page.get_by_text("Ask the logistics lead").first])


def scene8(page):
    """MCM stock card."""
    r = Recorder(page, 8)
    page.goto(f"{BASE}/dashboard/index")
    wait_idle(page, 2)
    page.get_by_role("menuitem", name="Reporting").first.hover()
    time.sleep(1)
    r.shot("For the stock card in the MCM format, open Reporting, then Excel exports, Stock cards.",
           "Reporting → Excel exports → Stock cards (MCM format)",
           hl=page.get_by_text("Stock cards (MCM format)").first)
    page.goto(f"{BASE}/aerisExport/index#cards")
    wait_idle(page, 2)
    page.select_option("#cardProduct", label="ACDC-MED-005 – Ringer's lactate 500 ml")
    page.fill("#cardLot", "RL1130")
    page.fill("#cardStart", "2026-10-01")
    page.fill("#cardEnd", "2026-10-20")
    time.sleep(0.5)
    btn = page.locator("#cardEnd").locator("xpath=ancestor::form").locator("button[type=submit]")
    r.shot("Choose the warehouse, the item, the batch number if needed, and the period. Leave Item empty to get "
           "all items. Then click Download Excel.",
           "Warehouse · item · period → Download Excel",
           hl=["#cardLocation", "#cardProduct", "#cardLot", "#cardStart", btn])
    with page.expect_download() as dl:
        btn.click()
    path = os.path.join(HERE, "fiche_ringer_en.xlsx")
    dl.value.save_as(path)
    print("   downloaded", path)
    add_image(r, "x_card.png",
              "The file follows the M C M stock card: one card per batch, with the opening stock, every receipt "
              "and issue with its document, and the balance. The closing balance must equal what you count on "
              "the shelf. If not, report the difference to your supervisor.",
              "One card per batch: opening · receipts · issues · balance = shelf stock")
    page.goto(f"{BASE}/aerisExport/index#all")
    wait_idle(page, 1.5)
    btn2 = page.locator("#allStart").locator("xpath=ancestor::form").locator("button[type=submit]")
    r.shot("On the right, Stock across warehouses gives a single workbook with the stock of Bunia, Isiro and "
           "Beni, for reports to the logistics lead.",
           "“Stock across warehouses”: one workbook for the 3 warehouses",
           hl=[page.locator("#allStart").locator("xpath=ancestor::div[contains(@class,'box')][1]"), btn2])


SCENE_FUNCS = {1: scene1, 2: scene2, 3: scene3, 4: scene4, 5: scene5, 6: scene6, 7: scene7, 8: scene8}

with sync_playwright() as p:
    browser = p.chromium.launch(channel="chrome", headless=True)
    ctx = browser.new_context(viewport={"width": 1280, "height": 720}, device_scale_factor=1.5, locale="en-GB",
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
