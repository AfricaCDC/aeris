# AERIS – Africa CDC Emergency Response Inventory System

AERIS is the Africa CDC build of [OpenBoxes](https://github.com/openboxes/openboxes), used as the stock system of record for emergency response commodities (first deployment: Ebola response, Bunia warehouse). It is a **thin fork**: branch `aeris/v0.9.8` holds upstream release `v0.9.8` plus the branding commits below, and nothing else. Functional behaviour is unchanged, so the OpenBoxes user guide applies as is.

![AERIS](branding/aeris_wordmark.png)

## What differs from upstream

| Area | Change | Files |
| --- | --- | --- |
| Name | "OpenBoxes" → "AERIS" in page titles, analytics navbar, footers, email footer, bug-report email, and every UI string in the message bundles. "Powered by OpenBoxes" kept as attribution. | `grails-app/views/layouts/*.gsp`, `grails-app/views/common/_navbar.gsp`, `grails-app/views/email/_footer.gsp`, `grails-app/views/email/_errorReport.gsp`, `grails-app/views/report/showInventoryReport.gsp`, `grails-app/i18n/messages*.properties` |
| French | Emails, the "Entered in AERIS?" flag and the import success message were still English in the FR bundle; now translated. | `grails-app/i18n/messages_fr.properties` |
| Logo and favicon | AERIS mark (40 px header, 100 px reports), favicon. | `grails-app/assets/images/aeris_logo_*.png`, `favicon.ico`, `src/main/webapp/images/` |
| Colours | Upstream blue palette re-pointed to green `#1F6F43` and gold `#C9A227`, gold rule under the header. | `src/css/aeris-theme.scss`, imported in `src/js/index.jsx` |
| Defaults | French first (`fr`, `en`), USD/EUR, self-signup off, error and feedback emails to Africa CDC instead of openboxes.com, mail prefix `[AERIS]`. | `grails-app/conf/application.yml` |
| Packaging | Multi-stage Docker build, compose file with MariaDB, sample external config. | `aeris/docker/`, `.dockerignore` |

## To confirm before go-live

- **Logo and colours.** The mark and the two colours are provisional, made without the Africa CDC brand guide. Replace `aeris_logo_40x40.png`, `aeris_logo_100.png` and `favicon.ico` (same names, same sizes), and the four `--aeris-*` values in `src/css/aeris-theme.scss`. To show the official Africa CDC logo without rebuilding, host it and set `openboxes.logo.url` in `openboxes.yml`.
- **Email addresses.** `stocks-ebola@africacdc.org` (sender) and `aeris-support@africacdc.org` (error reports) are proposals. Africa CDC IT must create them or name others.
- **Name use.** Check with Africa CDC communications that "AERIS" is free to use and clashes with no other Africa CDC system.

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

## Image versioning

Tag images `aeris:<openboxes version>-acdc<n>`, for example `aeris:0.9.8-acdc1`. Bump `n` for each AERIS change on the same upstream release. Never deploy `latest`.

## Upgrading to a new OpenBoxes release

```bash
git fetch --depth 1 https://github.com/openboxes/openboxes.git tag v0.9.9
git checkout -b aeris/v0.9.9 v0.9.9
git cherry-pick <AERIS commits from aeris/v0.9.8>
```

Conflicts are expected only in `messages*.properties` (new strings that mention OpenBoxes) and `application.yml`. After the cherry-pick, rerun the message rebrand check:

```bash
grep -n "OpenBoxes" grails-app/i18n/messages.properties grails-app/i18n/messages_fr.properties
```

Only the two `poweredBy` keys and `react.loadData.error.content.label` (a link to the OpenBoxes community) should still say OpenBoxes. Test on a copy of the production database before switching.

## Licence

OpenBoxes is under the Eclipse Public License 1.0 (`LICENSE.md`, `epl-v10.html`). AERIS keeps the upstream copyright notices and the "Powered by OpenBoxes" attribution. If AERIS is distributed outside Africa CDC (to a ministry or partner, for example), the modified source must be made available under the EPL as well.
