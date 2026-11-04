"""Test-import the catalogue files into the LOCAL test AERIS (localhost) as the local test admin."""
import os
import re
import sys
import time

from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8")
B = "http://localhost:8080/openboxes"
HERE = os.path.dirname(os.path.abspath(__file__))
IMP = os.path.join(HERE, "catalogue_import")
ACC = os.path.join(HERE, "..", "tools", "test-accounts.local.txt")  # git-excluded local test logins
pw = [l for l in open(ACC, encoding="utf-8").read().splitlines() if l.startswith("admin:")][0].split(" / ", 1)[1].strip()
BUNIA = "2c938083a153d0e401a153d92d8d0052"


def msg(page):
    return " | ".join(t.strip()[:300] for t in page.locator(".message, .errors, .error").all_inner_texts() if t.strip())


def batch(page, kind, path):
    page.goto(B + "/batch/importData")
    page.set_input_files("input[type=file]", path)
    page.locator(f"input[type=radio][value={kind}]").check()
    page.get_by_role("button", name="Upload").click()
    page.wait_for_load_state("networkidle")
    time.sleep(1)
    print(f"{kind} check:", msg(page))
    fin = page.get_by_role("button", name="Finish")
    if fin.count() == 0:
        return False
    fin.click()
    page.wait_for_load_state("networkidle")
    time.sleep(1)
    print(f"{kind} import:", msg(page))
    return True


with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome", headless=True)
    page = b.new_page(viewport={"width": 1366, "height": 800})
    page.set_default_timeout(120000)
    page.goto(B + "/auth/login?lang=en")
    page.fill("input[name=username]", "admin")
    page.fill("input[name=password]", pw)
    page.click("button[type=submit]")
    page.wait_for_load_state("networkidle")
    page.goto(B + f"/dashboard/chooseLocation/{BUNIA}")
    page.wait_for_load_state("networkidle")

    if "--skip-categories" not in sys.argv:
        batch(page, "category", os.path.join(IMP, "1_categories.xlsx"))

    page.goto(B + "/product/importAsCsv")
    page.set_input_files("input[type=file]", os.path.join(IMP, "Ebola 2026.csv"))
    page.get_by_role("button", name="Upload").click()
    page.wait_for_load_state("networkidle")
    time.sleep(2)
    print("products check:", msg(page))
    page.evaluate("document.querySelector('a[href=\"#import-data-tab\"]')?.click()")
    page.get_by_role("button", name="Import").click()
    page.wait_for_load_state("networkidle")
    time.sleep(2)
    print("products import:", msg(page))

    batch(page, "productSynonym", os.path.join(IMP, "3_synonyms.xlsx"))

    r = page.evaluate("""async () => {
        const t = await (await fetch('/openboxes/product/list?max=1')).text();
        return t.length; }""")
    b.close()
