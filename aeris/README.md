# AERIS – Africa CDC Emergency Response Inventory System

AERIS is the Africa CDC build of [OpenBoxes](https://github.com/openboxes/openboxes), used as the stock system of record for emergency response commodities (first deployment: Ebola response, Bunia warehouse). It is a **thin fork**: branch `aeris/v0.9.8` holds upstream release `v0.9.8` plus the branding commits below, and nothing else. Functional behaviour is unchanged, so the OpenBoxes user guide applies as is.

![AERIS](branding/aeris_wordmark.png)

## What differs from upstream

| Area | Change | Files |
| --- | --- | --- |
| Name | "OpenBoxes" → "AERIS" in page titles, analytics navbar, footers, email footer, bug-report email, and every UI string in the message bundles. "Powered by OpenBoxes" kept as attribution. | `grails-app/views/layouts/*.gsp`, `grails-app/views/common/_navbar.gsp`, `grails-app/views/email/_footer.gsp`, `grails-app/views/email/_errorReport.gsp`, `grails-app/views/report/showInventoryReport.gsp`, `grails-app/i18n/messages*.properties` |
| French | Emails, the "Entered in AERIS?" flag and the import success message were still English in the FR bundle; now translated. | `grails-app/i18n/messages_fr.properties` |
| Logo and favicon | Full Africa CDC logo in the header (since acdc23); Africa CDC seal (cropped from the official logo, `aeris/branding/africacdc_logo_full.png`) on printed reports and as favicon. Logo URLs come from `application.yml` and follow the context path (`/openboxes`, `/aeris`); `openboxes.yml` no longer overrides them. | `grails-app/assets/images/africacdc_logo.png`, `aeris_logo_*.png`, `favicon.ico`, `application.yml` (`openboxes.logo`) |
| Colours | Upstream blue palette re-pointed to the official Africa CDC colours (design system): crimson `#9F2241` (primary), AU green `#1A5632`, AU gold `#B4A269`; dashboard charts use the same palette (crimson, green, gold, navy, bronze…). | `src/css/aeris-theme.scss` (imported in `src/js/index.jsx`), `src/js/components/dashboard/ColorPalette.scss` |
| Brand after sign-in | Africa CDC design system on every page, Grails and React (acdc23): Encode Sans for titles, menu, figures and labels (bundled, SIL OFL, no call to Google) and Arial for text; white header with the Africa CDC logo and a crimson rule; page titles in crimson capitals; square dashboard tiles with a coloured top bar and heavy figures; tables with an AU-green header and sand rows; product tags in green; square crimson buttons; footer with a crimson bar and www.africacdc.org. Version, server IP, hostname and timings in the footer show to administrators only. | `src/main/webapp/css/aeris-brand.css` (loaded last by `layouts/custom.gsp` and `layouts/react.gsp`), `src/main/webapp/css/fonts/encode-sans/`, `grails-app/views/common/_footer.gsp`, `src/js/components/Layout/Footer.jsx` |
| Dependencies | npm packages updated for the Dependabot alerts (acdc24): `npm audit fix` within semver ranges plus axios 1.21.0, lodash 4.18.1, moment 2.31.0, @babel/core 7.29.7, postcss 8.5.32, webpack 5.112.2. npm audit went from 521 to 228 paths with no criticals; shipped code keeps 4 low-impact paths that need major upgrades (zod 3 → 4, query-string 6 → 10, node-fetch inside react-localize-redux, not used in browsers). The rest are build tools (webpack dev server, glob, old loaders) that never ship. The build stays on Node 14 / npm 6: npm 6 drops the `react-datepicker-6` alias from the lockfile when it rewrites it, so check `npm ci` after any dependency change. | `package.json`, `package-lock.json` |
| Defaults | English by default with French as the option (`en`, `fr`), USD/EUR, self-signup off, error and feedback emails to Africa CDC instead of openboxes.com, mail prefix `[AERIS]`. | `grails-app/conf/application.yml` |
| Bon de sortie | French labels on the delivery note ("Bon de sortie", Expéditeur, Destinataire, Total demandé/livré, Quantité par lot, Expédié/Livré/Reçu par). Upstream kept English in the FR bundle. | `grails-app/i18n/messages_fr.properties` |
| Works without internet | Every CDN script, stylesheet, font and image the pages used (jQuery, jQuery UI, Bootstrap, DataTables, select2, Font Awesome, Remix Icon, Inter…) is served by AERIS itself, so a weak or broken warehouse link no longer leaves pages unstyled on "Loading ...". The HelpScout support chat (OpenBoxes vendor) is off, and the sample `openboxes.yml` keeps every third-party widget off. Only exception: `country/list.gsp` still points at the dead Yahoo YUI CDN (broken upstream too). | `src/main/webapp/vendor/`, `aeris/tools/vendor_cdn.py`, `grails-app/views/**`, `.gitattributes` |
| Login page | Africa CDC login page in the layout of the Ebola response's teleconsultation platform: maroon brand panel with the DRC flag stripe, country, AERIS, system name, outbreak line and the Africa CDC logo; white form with show-password, a "Forgot password?" note (who to ask) and a language selector. No external files. Strings `aeris.login.*` in EN and FR. | `grails-app/views/auth/login.gsp`, `grails-app/assets/images/africacdc_logo.png` |
| Microsoft 365 sign-in | "Sign in with Microsoft" for Africa CDC accounts (Entra ID, OpenID Connect with PKCE). Microsoft proves identity only; roles stay in AERIS. First sign-in creates an inactive account that an AERIS admin activates. Local password form kept behind "Local account (administrator)" for outages. Off until configured, see below. | `MicrosoftAuthService.groovy`, `MicrosoftAuthController.groovy`, `SecurityInterceptor.groovy`, `application.yml` (`openboxes.auth`), `build.gradle` (nimbus-jose-jwt), `aeris/tools/dev_mock_entra.py` |
| Dashboard | Three tabs for the depot instead of five: **Overview** (expired lots, requests awaiting approval, open requests, negative stock; expiry, stock vs min/max, outbound and inbound movements), **Stock & expiry** (items counted, discrepancies at receipt, delayed inbound) and **Distribution** (issued/received per month, stock-outs, fill rate). Bin, putaway, valuation, purchasing and ad-hoc widgets switched off. | `grails-app/conf/runtime.groovy` (`openboxes.dashboardConfig`) |
| Expiry alerts | Daily expiry alert covers lots expiring within **180 days** (upstream 60), per the 6-month rule in the configuration plan. | `application.yml` (`openboxes.jobs.sendStockAlertsJob.daysUntilExpiry`) |
| Stock uploads | Staff upload **deliveries** (inbound items step) and **stock counts** (Inventory → Cycle count → Import stock count) from **.xlsx, .xls or .csv**. Fixed the library clash that broke every .xlsx; French Excel sheet names and ";" CSV with day-first dates are handled. Storekeepers check counts, a Manager imports them; other import types are admin-only. | `build.gradle`, `ExcelToCsv.groovy`, `ImportFileNormalizer.groovy`, `BatchController.groovy`, `StockMovementController.groovy`, `ImportDataCommand.groovy`, `batch/*.gsp`, inbound `AddItemsPage.jsx`, `runtime.groovy` (menu) |
| Warehouses | Bunia, **Isiro** (Haut-Uélé) and **Beni** (Nord-Kivu) as depots, each with its own stock; transfers between them are stock movements ("Transfert sortant" / "Transfert entrant"). Users get roles per warehouse. | data: `4b_entrepots_isiro_beni.xlsx` (Logistics folder) |
| Excel exports | Reporting → **Excel exports**: (1) **stock cards in the MCM format** of the logistics team, one sheet per item and batch with opening balance, every receipt and issue, running balance, totals and a verification line; (2) **stock across warehouses**: stock on hand by warehouse/item/lot with expiry and min-level status, item × warehouse totals, all transactions in the period. | `AerisExportService.groovy`, `AerisExportController.groovy`, `views/aerisExport/index.gsp`, `runtime.groovy` (menu) |
| Deployment kit | Production compose with nginx/HTTPS, backups, restore test and a runbook for IT, rehearsed on a test machine. | `aeris/deploy/` (see `DEPLOY.md`) |
| French on daily screens | 173 upstream strings still in English translated for receiving, issuing, statuses, shipment events, dialogs and buttons; bon de sortie page titled "Bon de sortie <number>" (also the PDF file name). | `grails-app/i18n/messages_fr.properties`, `views/deliveryNote/print.gsp` |
| Stock counts per lot | Upstream treats a count file as a full count of each product: lots of that product missing from the file were set to zero. AERIS sets only the lots in the file (and empties that lot's other bins); other lots keep their stock. Found in the storekeeper test, where a 3-line count wiped 54,700 units. | `InventoryImportDataService.groovy` |
| Receipts into stock | No temporary "R-&lt;shipment&gt;" receiving bins (there is no putaway step in AERIS): received stock goes straight to the depot, and the "lines without a bin" question no longer appears on every receipt. | `application.yml` (`openboxes.receiving.createReceivingLocation.enabled: false`), `ReceivingCheckScreen.jsx` |
| Donations | Donors (location type code `DONOR`) can be the origin of an inbound movement; upstream allowed suppliers only. | `LocationService.groovy` |
| Typed dates | A date typed as numbers is read day-first and exactly (`31/03/2028`, `31-03-28`). Upstream silently saved `31/03/2028` as 31 Mar **2026** in every React date field. | `DateField.jsx`, `v2/DateFieldDateFns.jsx` |
| Count upload page | Count date and time default to now, with a help line; missing French/English labels added; French "Charger" (upload) instead of "Télécharger"; storekeepers are no longer told to click a button they do not have. | `batch/_uploadFileForm.gsp`, `BatchController.groovy`, `messages*.properties` |
| Depot name in header | Cut at the start ("…Africa CDC Bunia") so the three depots can be told apart. | `src/css/aeris-theme.scss`, `src/main/webapp/css/openboxes.css` |
| Excel exports page | The upstream stylesheet hides any element with class `actions`, which hid both "Download Excel" buttons; renamed. | `views/aerisExport/index.gsp` |
| Behind a proxy or tunnel | `SERVER_USE_FORWARD_HEADERS` passed through the local compose file (production already sets it), so sign-in redirects stay on https behind nginx or a Cloudflare tunnel; `aeris/tools/quick-tunnel.ps1` publishes a test copy through a Cloudflare quick tunnel. | `aeris/docker/docker-compose.yml`, `aeris/tools/quick-tunnel.ps1` |
| Signup | Upstream bug fixed: with signup disabled, `/auth/signup` returned HTTP 500 instead of redirecting. The signup link on the login page is hidden when signup is off. | `AuthController.groovy`, `grails-app/views/auth/login.gsp` |
| Packaging | Multi-stage Docker build, compose file with MariaDB, sample external config. | `aeris/docker/`, `.dockerignore` |

## To confirm before go-live

- **Logo use.** The seal is taken from the official Africa CDC logo, and the colours are measured from it. Africa CDC communications should confirm that the seal may appear on an internal system under the AERIS name. To change the logo later, replace `aeris_logo_40x40.png`, `aeris_logo_100.png` and `favicon.ico` under the same names, or host a file and set `openboxes.logo.url` in `openboxes.yml` (no rebuild needed).
- **Email addresses.** `stocks-ebola@africacdc.org` (sender) and `aeris-support@africacdc.org` (error reports) are proposals. Africa CDC IT must create them or name others.
- **French wording.** Some dashboard widget titles (Inventory Summary, Expiration Summary, In Progress Shipments) still show in English in the French UI, because upstream has no French text for them. A storekeeper should list the English text seen during the test week, so it can be added to `messages_fr.properties` or overridden in the in-app Localization screen.
- **Units on the bon de sortie.** Import products from `2_produits_unites_bilingues.csv` (Logistics folder): units read "tablet / comprimé", "piece / pièce", "bottle / flacon"… so documents read well in both languages.
- **Name use.** Check with Africa CDC communications that "AERIS" is free to use and clashes with no other Africa CDC system.
- **Donors and suppliers.** Only the placeholder "Donateur – à compléter" exists. Load the real donors (UNICEF, OMS, …) as locations of type *Donateur* before the first delivery, or receipts cannot name the right donor. Run `aeris/deploy/scripts/golive-cleanup.sh` after loading data (demo depot, seed admin name, French shipment types).
- **Storekeeper test.** Findings and fixes of the 20 October 2026 test run are in `AERIS_test_findings.md` (Logistics folder). Repeat the test with a real storekeeper once the server is up.

## Build and run

Requirements: Docker Engine 24+ (Docker Desktop on Windows), 8 GB RAM for the build.

```bash
cd aeris/docker
docker compose up -d --build
```

The image is built from the **committed** state of the repository (the Dockerfile clones `.git`), so commit changes before building. First build: about 20–40 minutes (Gradle, Node and npm downloads are then cached). Open http://localhost:8080/openboxes once `docker compose ps` shows `aeris-app` as healthy. The first start creates the database schema, which takes several minutes.

Deployment-specific settings (server URL, SMTP server, logo URLs) go in `aeris/docker/openboxes.yml`, mounted at `/app/.grails/openboxes.yml`. They override the image defaults, so they survive image upgrades. Database credentials and the public URL go in a `.env` file next to the compose file:

```
DATASOURCE_PASSWORD=<strong password>
MYSQL_ROOT_PASSWORD=<strong password>
GRAILS_SERVER_URL=https://aeris.<domain>/openboxes/
```

In production, put nginx with HTTPS in front (see upstream `docker/nginx`) and keep port 8080 closed to the internet.

## Microsoft 365 sign-in (Entra ID)

Users click **Sign in with Microsoft** and use their Africa CDC account, with the tenant's MFA and conditional access. AERIS checks the token signature, issuer, audience, expiry, tenant and that the email ends in `@africacdc.org`. **Microsoft grants no privileges**: what someone may do is the role an AERIS admin gives them.

| Situation | What AERIS does |
| --- | --- |
| Email matches an active AERIS user | Signed in, same as a password login |
| First sign-in, no AERIS account | Creates an **inactive** account from the Microsoft profile (name, email) and notifies admins by email. The person sees "awaiting approval". |
| Account inactive | "Awaiting approval" |
| Email outside `africacdc.org`, cancelled, or tampered request | Refused with a message; nothing created |

**Approving someone:** Admin → Users → open the person → tick *Active* → add the role (Manager, Assistant, Browser…) and the Bunia location.

### What Africa CDC IT needs to do (once)

1. Entra admin center → App registrations → **New registration**: name `AERIS`, supported accounts **this organization only**, redirect URI (Web) `https://<aeris host>/openboxes/microsoftAuth/callback`.
2. Certificates & secrets → **New client secret** (24 months). Note its expiry date: sign-in stops when it expires.
3. API permissions: `openid`, `profile`, `email` (Microsoft Graph, delegated). Grant admin consent.
4. Enterprise applications → AERIS → Properties → **Assignment required = Yes**, then assign the response team (a group). Only assigned people can even reach the "awaiting approval" step.
5. Send the AERIS technical owner: tenant ID, client ID, client secret (through a password manager, never email), and the exact redirect URI.

### Server settings

In `aeris/docker/.env` (not committed):

```
AERIS_ENTRA_ENABLED=true
AERIS_ENTRA_TENANT_ID=<tenant id>
AERIS_ENTRA_CLIENT_ID=<application (client) id>
AERIS_ENTRA_CLIENT_SECRET=<client secret>
AERIS_ENTRA_REDIRECT_URI=https://<aeris host>/openboxes/microsoftAuth/callback
```

The AERIS server must reach `login.microsoftonline.com` over HTTPS. If the link or Microsoft is down, the system focal point can still sign in with **Local account (administrator)**. Keep at least one local admin with a strong password, stored in the Africa CDC password manager.

**Testing without Entra:** `python -I aeris/tools/dev_mock_entra.py` runs a stand-in on port 8099; its header lists the `.env` values to use. Development only.

## Stock cards and Excel exports (logistics team)

Reporting → **Excel exports**.

- **Stock cards (MCM format)**: choose the warehouse, optionally one item and one batch, and the period. The workbook opens on an index (one line per card, with links); each card follows the MCM Ebola response stock card: warehouse, item, category, unit, opening balance, batch, expiry, minimum level, storage conditions, custodian (the warehouse manager in Configuration → Locations), reporting period, then one line per receipt or issue with document number (stock movement or bon de sortie number), type, source, destination, quantities and running balance. Print one card per page, landscape.
- **Transaction types** use the card's vocabulary: Réception (from a donor or supplier), Distribution (to a health zone, CTE, facility or pillar), Transfert entrant / sortant (between AERIS warehouses), Retour (back from a site), Ajustement + / − (corrections and count results, marked "Comptage / count"), Perte / destruction (damaged, expired, lost).
- **Stock across warehouses**: one workbook with sheets *Stock on hand* (filterable, with expiry and minimum-level status), *By product* (item × warehouse), *Transactions* (period) and *About*.

The card's closing balance always equals AERIS stock on hand: it is computed from the same transactions.

## Uploading stock from Excel or CSV (for staff)

Files can be `.xlsx`, `.xls` or `.csv` (comma or semicolon). Dates: an Excel date cell, `2028-04-01`, or day-first `01/04/2028`.

**A delivery arrives (donation or purchase)** - storekeeper or logistics lead
1. Entrée / Inbound → Create inbound: origin = the donor, destination = Entrepôt Africa CDC Bunia, then Next.
2. On the items step click **Export template**, open it in Excel and fill one row per lot: product code, lot number, expiry date, quantity. Save (Excel format is fine).
3. Click **Import template** and choose the file. The lines appear; check them, then continue to send and receive as usual. Lot numbers made only of digits (e.g. `150326`) are kept as typed.

**A physical count** - storekeepers prepare, the logistics lead imports
1. Inventaire / Inventory → Cycle count → **Import stock count (Excel/CSV)**. Click *Download data*: an Excel sheet of the current stock by lot (product code, name, lot, expiry, system quantity) with an empty *Physical QOH* column.
2. Type the counted quantity in column G (*Physical QOH*) for every line; add a line for any lot found that is not listed. Keep columns A (product code), C (lot) and D (expiry).
3. Upload it with the **date and time of the count** (pre-filled with now, in server time UTC: Bunia is UTC+2). Movements recorded *after* that time are applied on top of the counted quantities, so do not back-date a count to before the day's receipts and issues. AERIS checks the file and shows each line.
   - Storekeeper: the check ends there, with "Ask the logistics lead to import it".
   - Logistics lead (Manager): uploads the same file and clicks **Finish**. Each lot in the file is set to the counted quantity, recorded as an inventory count (baseline and adjustment transactions) on the count date. **Lots not in the file are not changed**, so a partial count (one shelf, one product) is safe.

Min/max levels (Manager) and all other imports (products, sites, users: admin) use Configuration → Import data.

## Stock alert emails

The daily alert job (midnight) emails expiring lots (180 days), low stock, reorder and stock-outs. It sends nothing until three things are in place:

1. Mail on: in `aeris/docker/openboxes.yml`, `grails.mail.enabled: true` with the Africa CDC SMTP host, port and sender.
2. The Bunia depot has the **Enable notifications** activity: Configuration → Locations → Entrepôt Africa CDC Bunia → supported activities (or on the Dépôt location type).
3. Each recipient has a notification role: *Item all notification*, or one of *Item expiry / out of stock / low stock / reorder / overstock notification* (Admin → Users → roles). The plan in the configuration document: Managers get out-of-stock; the logistics lead gets low stock, out of stock and expiry; the information management officer gets expiry.

A user who saved their own Overview layout keeps it after an upgrade. To give them the new default, clear their saved layout in the database: `update user set dashboard_config = null where username = '…';`

## Loading the reference data

Tested on 2026-10-19 with `ACDC_OpenBoxes_fichiers_import.zip`: all files load once the points below are handled.

| Order | File | How | Notes |
| --- | --- | --- | --- |
| 1 | Location types | Configuration → Location types, by hand | Dépôt = code DEPOT with the same activities as the stock "Depot" type. The five destination types = CONSUMER with "Receive stock" and "Submit request". Donateur = DONOR with "Send stock" and "External". Description: a short label, shown in brackets after site names in pickers (Dépôt, Zone de santé, CTE, Formation sanitaire, Pilier, Point d'entrée, Donateur). |
| 2 | Location groups | Configuration → Location groups | Create Ituri, Nord-Kivu, Sud-Kivu **before** the site import, which only matches existing groups. |
| 3 | `1_categories` | Configuration → Import data → Category | |
| 4 | `2_produits.csv` | Products → Import products (CSV) | Categories must exist first. |
| 5 | `3_noms_francais` | Configuration → Import data → Product synonym | |
| 6 | `4_sites` | Configuration → Import data → Location | **Organization is required** for every site that is not internal. Only the warehouse row has one, so fill the column first. |
| 7 | `6_stock_initial` | Configuration → Import data → Inventory, logged in at the Bunia depot, with the count date | After replacing column G with counted quantities. |

Upload the files as they are: `.xlsx`, `.xls` or `.csv` (fixed in AERIS; upstream 0.9.8 could not read `.xlsx`).

## Image versioning

Tag images `aeris:<openboxes version>-acdc<n>`, for example `aeris:0.9.8-acdc21`. Bump `n` for each AERIS change on the same upstream release. Never deploy `latest`.

## Upgrading to a new OpenBoxes release

```bash
git fetch --depth 1 https://github.com/openboxes/openboxes.git tag v0.9.9
git checkout -b aeris/v0.9.9 v0.9.9
git cherry-pick <AERIS commits from aeris/v0.9.8>
```

Conflicts are expected only in `messages*.properties` (new strings that mention OpenBoxes), `application.yml` and views that gained new CDN links. Then run `python -I aeris/tools/vendor_cdn.py` to localize any new CDN links; `--check` must report 2 references (the dead YUI ones) and nothing else. After the cherry-pick, rerun the message rebrand check:

```bash
grep -n "OpenBoxes" grails-app/i18n/messages.properties grails-app/i18n/messages_fr.properties
```

Only the two `poweredBy` keys and `react.loadData.error.content.label` (a link to the OpenBoxes community) should still say OpenBoxes. Test on a copy of the production database before switching.

## Licence

OpenBoxes is under the Eclipse Public License 1.0 (`LICENSE.md`, `epl-v10.html`). AERIS keeps the upstream copyright notices and the "Powered by OpenBoxes" attribution. If AERIS is distributed outside Africa CDC (to a ministry or partner, for example), the modified source must be made available under the EPL as well.
