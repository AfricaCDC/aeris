# AERIS weekly stock brief (prototype)

A short weekly note for leadership, in English and French, built from AERIS's own "Stock across warehouses"
export (Reporting → Excel exports). Shows, per warehouse: products and lots in stock, receipts and issues in the
period, expired lots, lots expiring within 90 days, stock-outs and items below minimum, main destinations, and
incidents (remarks, losses, negative adjustments).

**The figures are computed by the script, never by the AI.** Claude (`claude-opus-5-5`) only writes the opening
summary paragraph from `facts.json`, and is told to use no other figures. Without Claude API credentials the
script writes a plain built-in summary instead and says so at the bottom of the brief.

## Run

    pip install anthropic openpyxl requests
    # laptop copy (test account read from the git-excluded test-accounts file, never printed)
    python weekly_brief.py --base http://localhost:8080/openboxes --user admin --password-file ../tools/test-accounts.local.txt --out out
    # live site: a read-only (Browser role) account, password in an environment variable
    python weekly_brief.py --base https://tools.africacdc.org/aeris --user <read-only account> --password-env AERIS_BRIEF_PASSWORD --out out
    # or from an export downloaded by hand
    python weekly_brief.py --workbook "AERIS stock - all warehouses - 2026-11-07.xlsx" --out out

Options: `--days 7` (period length), `--no-ai` (never call Claude).

Output in `--out`: `brief_en.html`, `brief_fr.html` (email-ready), `brief_en.txt`, `brief_fr.txt`, `facts.json`,
and the downloaded export.

## Claude API access

Set `ANTHROPIC_API_KEY`, or sign in once with `ant auth login`; the SDK finds either. Requests send only
`facts.json` (stock figures, product names, warehouse and site names), with no personal data. Confirm with Africa CDC IT
which provider and region are acceptable before using it on live data. Refusal fallbacks are on
(`fallbacks: "default"`); if the model still declines, the plain summary is used.

## Status

Prototype, run against the laptop copy only (7 November 2026), with the Claude summary in English and French;
every figure in the summary was checked against `facts.json`. Scheduling (for example a Monday 07:00 task on the
server) and emailing are not part of it yet.

If the Claude call fails with "Connection error" caused by `process() takes no keyword arguments`, the Python
environment has an old Brotli package: `pip install --upgrade "brotli>=1.1"`.
