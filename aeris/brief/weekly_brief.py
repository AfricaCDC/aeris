"""AERIS weekly stock brief for leadership, in English and French.

Reads AERIS's own "Stock across warehouses" export (the same workbook staff download from Reporting → Excel
exports), computes the figures in code, and writes a short brief:
  brief_en.html / brief_fr.html  email-ready pages
  brief_en.txt  / brief_fr.txt   plain text
  facts.json                     every figure the brief uses

The figures never come from the AI. Claude only writes the opening summary paragraph from facts.json, and only
when Claude API credentials are available (ANTHROPIC_API_KEY or an `ant auth login` profile); otherwise a plain
built-in summary is used and the page says so.

    python weekly_brief.py --base http://localhost:8080/openboxes --user admin --password-env AERIS_BRIEF_PASSWORD --out ./out
    python weekly_brief.py --workbook "AERIS stock - all warehouses - 2026-11-07.xlsx" --out ./out

Use a read-only (Browser role) AERIS account for --user on the live site.
"""
import argparse
import collections
import datetime as dt
import html
import json
import os
import re
import sys

import openpyxl
import requests

MODEL = "claude-opus-5-5"
SOON_DAYS = 90
LEVEL_ALERTS = ("Stock-out", "Below minimum", "Below reorder point")
ISSUE_TYPES = ("Distribution", "Transfert sortant")
RECEIPT_TYPES = ("Réception", "Transfert entrant")
LOSS_TYPES = ("Perte / destruction", "Ajustement -")


# ---------------------------------------------------------------- fetch
def password_from(args):
    if args.password_env:
        pw = os.environ.get(args.password_env)
        if not pw:
            sys.exit(f"Environment variable {args.password_env} is empty")
        return pw
    if args.password_file:  # local test-accounts file: "<label>: <user> / <password>"
        for line in open(args.password_file, encoding="utf-8"):
            if " / " in line and line.split(":", 1)[0].strip() == args.user:
                return line.split(" / ", 1)[1].strip()
        sys.exit(f"No line for {args.user} in the password file")
    sys.exit("Give --password-env or --password-file (never a password on the command line)")


def fetch_workbook(base, user, password, start, end, dest):
    s = requests.Session()
    s.get(f"{base}/auth/login", timeout=60)
    r = s.post(f"{base}/auth/handleLogin", data={"username": user, "password": password}, timeout=60)
    if "/auth/login" in r.url:
        sys.exit("AERIS sign-in failed (check the account)")
    url = f"{base}/aerisExport/consolidated?startDate={start:%Y-%m-%d}&endDate={end:%Y-%m-%d}"
    for _ in range(2):
        r = s.get(url, timeout=300)
        if "spreadsheetml" in r.headers.get("Content-Type", ""):
            open(dest, "wb").write(r.content)
            return dest
        # AERIS asks which warehouse to work in first: pick the first one offered, then retry
        m = re.search(r"chooseLocation/([0-9a-f]{32})", r.text)
        if not m:
            break
        s.get(f"{base}/dashboard/chooseLocation/{m.group(1)}", timeout=60)
    sys.exit("Could not download the AERIS export (is the account allowed to use Reporting → Excel exports?)")


# ---------------------------------------------------------------- read
def rows(ws, first_header):
    data = list(ws.iter_rows(values_only=True))
    for i, r in enumerate(data):
        if r and r[0] == first_header:
            head = [str(c).strip() if c is not None else "" for c in r]
            return [dict(zip(head, x)) for x in data[i + 1:] if x and any(v not in (None, "") for v in x)]
    return []


def num(v):
    try:
        return float(v or 0)
    except (TypeError, ValueError):
        return 0.0


def as_date(v):
    if isinstance(v, dt.datetime):
        return v.date()
    if isinstance(v, dt.date):
        return v
    if isinstance(v, str):
        for f in ("%d/%m/%Y", "%Y-%m-%d", "%d/%b/%Y"):
            try:
                return dt.datetime.strptime(v.strip()[:11], f).date()
            except ValueError:
                pass
    return None


def compute(path, start, end):
    wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
    soh = rows(wb["Stock on hand"], "Warehouse")
    tx = rows(wb["Transactions"], "Date")
    # Every warehouse in the export, also those with no stock or movements yet ("By product" has one column each)
    by_product = list(wb["By product"].iter_rows(values_only=True))
    head = next((r for r in by_product if r and r[0] == "Item code"), ())
    listed = [c for c in head[3:] if c and c != "Total"]
    houses = sorted(set(listed) | {r["Warehouse"] for r in soh} | {r["Warehouse"] for r in tx if r.get("Warehouse")})
    out = {"period": {"start": f"{start:%Y-%m-%d}", "end": f"{end:%Y-%m-%d}"},
           "generated": f"{dt.datetime.now():%Y-%m-%d %H:%M}", "warehouses": {}}
    for w in houses:
        stock = [r for r in soh if r["Warehouse"] == w and num(r.get("Quantity on hand")) > 0]
        lot = lambda r: {"code": r.get("Item code"), "item": r.get("Item description"), "item_fr": r.get("Description (FR)"),
                         "lot": r.get("Batch / Lot No."), "qty": num(r.get("Quantity on hand")),
                         "unit": r.get("Unit"), "expiry": str(as_date(r.get("Expiry date")) or ""),
                         "days": int(r["Days to expiry"]) if isinstance(r.get("Days to expiry"), (int, float)) else None}
        expired = [lot(r) for r in stock if r.get("Expiry status") == "Expired"]
        soon = sorted([lot(r) for r in stock if r.get("Expiry status") != "Expired"
                       and isinstance(r.get("Days to expiry"), (int, float)) and r["Days to expiry"] <= SOON_DAYS],
                      key=lambda x: x["days"])
        within6 = [r for r in stock if r.get("Expiry status") == "Expires within 6 months"]
        levels = {}
        for r in soh:
            if r["Warehouse"] == w and r.get("Stock level status") in LEVEL_ALERTS:
                levels[r.get("Item code")] = {"code": r.get("Item code"), "item": r.get("Item description"), "item_fr": r.get("Description (FR)"),
                                              "status": r.get("Stock level status"),
                                              "total": num(r.get("Total at warehouse")), "unit": r.get("Unit")}
        week = [r for r in tx if r.get("Warehouse") == w and as_date(r.get("Date"))
                and start <= as_date(r.get("Date")) <= end]
        typ = lambda r: (r.get("Transaction Type") or "")
        received = [r for r in week if typ(r) in RECEIPT_TYPES]
        issued = [r for r in week if typ(r) in ISSUE_TYPES]
        # Destinations by deliveries and item lines: quantities of different products can't be added up
        dest_docs, dest_lines = collections.defaultdict(set), collections.Counter()
        for r in issued:
            d = r.get("Destination / Receiving Unit") or "?"
            dest_docs[d].add(r.get("Source Document Reference"))
            dest_lines[d] += 1
        incidents = [{"date": str(as_date(r.get("Date"))), "item": r.get("Item description"), "item_fr": r.get("Item description"),
                      "remark": r.get("Remarks / Incident"), "type": typ(r)}
                     for r in week if r.get("Remarks / Incident") or typ(r) in LOSS_TYPES]
        docs = lambda rs: len({r.get("Source Document Reference") for r in rs if r.get("Source Document Reference")})
        out["warehouses"][w] = {
            "products_in_stock": len({r.get("Item code") for r in stock}),
            "lots_in_stock": len(stock),
            "expired_lots": expired,
            "expiring_within_90_days": soon,
            "lots_expiring_within_6_months": len(within6),
            "stock_level_alerts": sorted(levels.values(), key=lambda x: x["status"]),
            "week": {"receipts": docs(received), "receipt_lines": len(received),
                     "issues": docs(issued), "issue_lines": len(issued),
                     "top_destinations": [{"destination": d, "deliveries": len(dest_docs[d]), "item_lines": n}
                                          for d, n in dest_lines.most_common(5)],
                     "incidents": incidents},
        }
    return out


# ---------------------------------------------------------------- summary
SYSTEM = (
    "You write the opening paragraph of a weekly stock brief for the Africa CDC Ebola response leadership in the "
    "DRC (warehouses in Bunia, Isiro and Beni). Use ONLY the figures in the JSON you are given; never estimate, "
    "round differently or add figures. 3 to 5 sentences: overall activity this week, then the most important "
    "risks (expired stock, lots expiring within 90 days, stock-outs or items below minimum), naming the "
    "warehouse. Never add up quantities of different products. Plain, factual, no headings, no bullet points. "
    "If nothing needs attention, say so.\n"
    "Write it twice: first in English after a line 'EN:', then in French after a line 'FR:'."
)


def ai_summary(facts):
    try:
        import anthropic
    except ImportError:
        return None, "anthropic package not installed"
    try:
        client = anthropic.Anthropic()
        r = client.beta.messages.create(
            model=MODEL, max_tokens=2000, system=SYSTEM,
            betas=["server-side-fallback-2026-07-01"], fallbacks="default",
            output_config={"effort": "low"},
            messages=[{"role": "user", "content": json.dumps(facts, ensure_ascii=False, default=str)}],
        )
    except anthropic.AuthenticationError:
        return None, "no valid Claude API credentials"
    except anthropic.APIConnectionError:
        return None, "Claude API not reachable"
    except anthropic.APIStatusError as e:
        return None, f"Claude API error {e.status_code}"
    except TypeError as e:  # the SDK raises this before any request when no credentials are set
        if "authentication" in str(e):
            return None, "no Claude API credentials set up"
        raise
    if r.stop_reason == "refusal":
        return None, "the model declined"
    text = "".join(b.text for b in r.content if b.type == "text")
    m = re.search(r"EN:\s*(.+?)\s*FR:\s*(.+)", text, re.S)
    if not m:
        return None, "unexpected summary format"
    return {"en": m.group(1).strip(), "fr": m.group(2).strip()}, f"written by Claude ({r.model}) from these figures"


def plain_summary(facts, lang):
    w = facts["warehouses"]
    rec = sum(x["week"]["receipts"] for x in w.values())
    iss = sum(x["week"]["issues"] for x in w.values())
    exp = [(n, len(x["expired_lots"])) for n, x in w.items() if x["expired_lots"]]
    soon = [(n, len(x["expiring_within_90_days"])) for n, x in w.items() if x["expiring_within_90_days"]]
    low = [(n, len(x["stock_level_alerts"])) for n, x in w.items() if x["stock_level_alerts"]]
    j = lambda items, fmt: "; ".join(fmt.format(n, k) for n, k in items)
    if lang == "fr":
        s = [f"Cette semaine : {rec} réception(s) et {iss} sortie(s) enregistrées dans les {len(w)} entrepôts."]
        s.append(f"Lots expirés en stock : {j(exp, '{} ({})')}." if exp else "Aucun lot expiré en stock.")
        if soon:
            s.append(f"Lots qui expirent dans les {SOON_DAYS} jours : {j(soon, '{} ({})')}.")
        if low:
            s.append(f"Articles en rupture ou sous le minimum : {j(low, '{} ({})')}.")
        return " ".join(s)
    s = [f"This week: {rec} receipt(s) and {iss} issue(s) recorded across {len(w)} warehouses."]
    s.append(f"Expired lots still in stock: {j(exp, '{} ({})')}." if exp else "No expired lots in stock.")
    if soon:
        s.append(f"Lots expiring within {SOON_DAYS} days: {j(soon, '{} ({})')}.")
    if low:
        s.append(f"Items out of stock or below minimum: {j(low, '{} ({})')}.")
    return " ".join(s)


# ---------------------------------------------------------------- render
L = {
    "en": dict(title="AERIS weekly stock brief", period="Period", dest_col="Destination", deliveries="Deliveries", lines="Item lines", summary="Summary", wh="Warehouse",
               products="Products in stock", lots="Lots", rec="Receipts", iss="Issues", exp6="Lots expiring ≤ 6 months",
               expired="Expired lots in stock", soon=f"Lots expiring within {SOON_DAYS} days", item="Item",
               lot="Batch", qty="Quantity", expiry="Expiry", days="Days", low="Stock-outs and low stock",
               status="Status", total="Total", dest="Main destinations", incidents="Incidents and losses",
               remark="Remark", none="None", source="Figures computed from the AERIS export of {g}.",
               ai="Summary {how}.", noai="Summary generated automatically ({why}).",
               status_map={}),
    "fr": dict(title="AERIS – note hebdomadaire des stocks", period="Période", dest_col="Destination", deliveries="Livraisons", lines="Lignes d’articles", summary="Résumé", wh="Entrepôt",
               products="Articles en stock", lots="Lots", rec="Réceptions", iss="Sorties",
               exp6="Lots expirant ≤ 6 mois", expired="Lots expirés en stock",
               soon=f"Lots expirant dans les {SOON_DAYS} jours", item="Article", lot="Lot", qty="Quantité",
               expiry="Expiration", days="Jours", low="Ruptures et stocks bas", status="Statut", total="Total",
               dest="Principales destinations", incidents="Incidents et pertes", remark="Remarque",
               none="Aucun", source="Chiffres calculés à partir de l’export AERIS du {g}.",
               ai="Résumé rédigé par Claude à partir de ces chiffres.",
               noai="Résumé généré automatiquement ({why}).",
               why_map={"no Claude API credentials set up": "pas d’accès à l’API Claude configuré", "AI switched off": "IA désactivée", "Claude API not reachable": "API Claude injoignable", "the model declined": "le modèle a refusé", "unexpected summary format": "format de résumé inattendu"},
               status_map={"Stock-out": "Rupture", "Below minimum": "Sous le minimum",
                           "Below reorder point": "Sous le point de commande"}),
}
CSS = ("body{font-family:Arial,Helvetica,sans-serif;color:#1F2937;background:#F5F3EE;margin:0}"
       ".w{max-width:860px;margin:0 auto;background:#FBFAF7;border-top:8px solid #9F2241}"
       ".h{padding:24px 28px 8px}.h h1{color:#9F2241;font-size:24px;margin:0}.h p{color:#53575A;margin:4px 0 0}"
       ".s{margin:12px 28px;padding:14px 18px;background:#fff;border-left:6px solid #1A5632;line-height:1.5}"
       "h2{color:#1A5632;font-size:16px;margin:22px 28px 6px;text-transform:uppercase;letter-spacing:.05em}"
       "table{border-collapse:collapse;margin:0 28px;width:calc(100% - 56px);font-size:13px}"
       "th{background:#1A5632;color:#fff;text-align:left;padding:6px 8px}td{padding:6px 8px;border-bottom:1px solid #EEE7D6}"
       "td.n{text-align:right}.bad{color:#9F2241;font-weight:bold}.f{color:#53575A;font-size:12px;padding:18px 28px 24px}"
       ".bar{height:10px;background:#9F2241}")


def fmt_qty(q):
    return f"{q:,.0f}".replace(",", " ")


def render(facts, lang, summary, note):
    t, e = L[lang], html.escape
    w = facts["warehouses"]
    nm = lambda x: (x.get("item_fr") or x.get("item")) if lang == "fr" else x.get("item")
    p = [f"<!doctype html><html lang='{lang}'><head><meta charset='utf-8'><title>{e(t['title'])}</title>"
         f"<style>{CSS}</style></head><body><div class='w'><div class='h'><h1>{e(t['title'])}</h1>"
         f"<p>{t['period']}: {facts['period']['start']} → {facts['period']['end']}</p></div>"
         f"<div class='s'><b>{t['summary']}.</b> {e(summary)}</div>"]

    def table(head, body, numeric=()):
        if not body:
            return f"<p style='margin:0 28px;color:#53575A'>{t['none']}</p>"
        h = "".join(f"<th>{e(x)}</th>" for x in head)
        b = "".join("<tr>" + "".join(f"<td class='{'n' if i in numeric else ''}'>{c}</td>" for i, c in enumerate(r))
                    + "</tr>" for r in body)
        return f"<table><tr>{h}</tr>{b}</table>"

    p.append(table([t["wh"], t["products"], t["lots"], t["rec"], t["iss"], t["exp6"]],
                   [[e(n), x["products_in_stock"], x["lots_in_stock"], x["week"]["receipts"], x["week"]["issues"],
                     x["lots_expiring_within_6_months"]] for n, x in w.items()], numeric=(1, 2, 3, 4, 5)))
    p.append(f"<h2>{t['expired']}</h2>")
    p.append(table([t["wh"], t["item"], t["lot"], t["qty"], t["expiry"]],
                   [[e(n), e(str(nm(l))), e(str(l["lot"])), f"<span class='bad'>{fmt_qty(l['qty'])}</span>",
                     l["expiry"]] for n, x in w.items() for l in x["expired_lots"]], numeric=(3,)))
    p.append(f"<h2>{t['soon']}</h2>")
    p.append(table([t["wh"], t["item"], t["lot"], t["qty"], t["expiry"], t["days"]],
                   [[e(n), e(str(nm(l))), e(str(l["lot"])), fmt_qty(l["qty"]), l["expiry"], l["days"]]
                    for n, x in w.items() for l in x["expiring_within_90_days"][:10]], numeric=(3, 5)))
    p.append(f"<h2>{t['low']}</h2>")
    p.append(table([t["wh"], t["item"], t["status"], t["total"]],
                   [[e(n), e(str(nm(a))), f"<span class='bad'>{e(t['status_map'].get(a['status'], a['status']))}</span>",
                     fmt_qty(a["total"])] for n, x in w.items() for a in x["stock_level_alerts"]], numeric=(3,)))
    p.append(f"<h2>{t['dest']}</h2>")
    p.append(table([t["wh"], t["dest_col"], t["deliveries"], t["lines"]],
                   [[e(n), e(str(d["destination"])), d["deliveries"], d["item_lines"]]
                    for n, x in w.items() for d in x["week"]["top_destinations"]], numeric=(2, 3)))
    p.append(f"<h2>{t['incidents']}</h2>")
    p.append(table([t["wh"], "Date", t["item"], t["remark"]],
                   [[e(n), i["date"], e(str(nm(i))), e(str(i["remark"] or i["type"]))]
                    for n, x in w.items() for i in x["week"]["incidents"]]))
    p.append(f"<div class='f'>{t['source'].format(g=facts['generated'])} {e(note)}</div><div class='bar'></div>"
             "</div></body></html>")
    return "".join(p)


def text_version(facts, lang, summary, note):
    t, w = L[lang], facts["warehouses"]
    lines = [t["title"], f"{t['period']}: {facts['period']['start']} → {facts['period']['end']}", "", summary, ""]
    for n, x in w.items():
        lines.append(f"{n}: {x['products_in_stock']} {t['products'].lower()}, {x['week']['receipts']} "
                     f"{t['rec'].lower()}, {x['week']['issues']} {t['iss'].lower()}, "
                     f"{len(x['expired_lots'])} {t['expired'].lower()}, {len(x['expiring_within_90_days'])} "
                     f"{t['soon'].lower()}, {len(x['stock_level_alerts'])} {t['low'].lower()}.")
    lines += ["", t["source"].format(g=facts["generated"]) + " " + note]
    return "\n".join(lines)


def main():
    a = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    a.add_argument("--base", help="AERIS address, e.g. http://localhost:8080/openboxes")
    a.add_argument("--user")
    a.add_argument("--password-env", help="name of the environment variable holding the password")
    a.add_argument("--password-file", help="local test-accounts file (laptop copy only)")
    a.add_argument("--workbook", help="use an export already downloaded instead of signing in")
    a.add_argument("--days", type=int, default=7)
    a.add_argument("--no-ai", action="store_true", help="never call Claude")
    a.add_argument("--out", default="out")
    args = a.parse_args()
    end = dt.date.today()
    start = end - dt.timedelta(days=args.days - 1)
    os.makedirs(args.out, exist_ok=True)
    path = args.workbook or fetch_workbook(args.base.rstrip("/"), args.user, password_from(args), start, end,
                                           os.path.join(args.out, f"aeris_export_{end:%Y-%m-%d}.xlsx"))
    facts = compute(path, start, end)
    json.dump(facts, open(os.path.join(args.out, "facts.json"), "w", encoding="utf-8"), ensure_ascii=False,
              indent=1, default=str)
    summ, how = (None, "AI switched off") if args.no_ai else ai_summary(facts)
    for lang in ("en", "fr"):
        if summ:
            text, note = summ[lang], (L[lang]["ai"].format(how=how))
        else:
            why = L[lang].get("why_map", {}).get(how, how)
            text, note = plain_summary(facts, lang), L[lang]["noai"].format(why=why)
        open(os.path.join(args.out, f"brief_{lang}.html"), "w", encoding="utf-8").write(render(facts, lang, text, note))
        open(os.path.join(args.out, f"brief_{lang}.txt"), "w", encoding="utf-8").write(text_version(facts, lang, text, note))
    print(f"Brief written to {os.path.abspath(args.out)} ({'AI summary' if summ else 'plain summary: ' + how})")


if __name__ == "__main__":
    main()
