# Deploying AERIS on a server

For Africa CDC IT. This puts AERIS online at `https://<AERIS_HOST>/openboxes` for the Bunia, Isiro and Beni warehouses and HQ. Plan for half a day, plus whatever the certificate and DNS take.

## 1. What IT provides

| Item | Minimum | Recommended |
| --- | --- | --- |
| Server | Linux VM (Ubuntu 22.04/24.04), 2 vCPU, 8 GB RAM, 40 GB SSD | 4 vCPU, 16 GB RAM, 80 GB SSD |
| Network | Public IP, inbound TCP 80 and 443 only; SSH limited to IT addresses | Same, plus a firewall / NSG |
| Name | A DNS record, e.g. `aeris.africacdc.org` → the server's IP | — |
| Certificate | HTTPS certificate for that name (Africa CDC's own, or Let's Encrypt, see 4) | — |
| Mail | SMTP server and a sender address (alerts, notifications) | — |
| Backups | A place off the server for daily copies (storage account, another server) | — |
| Microsoft 365 | The Entra app registration in `aeris/README.md` → *Microsoft 365 sign-in* | — |

The warehouses reach AERIS over their own internet links (Starlink). The server must reach `login.microsoftonline.com` (sign-in) and the SMTP server.

## 2. Install Docker

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER    # log out and back in
```

## 3. Get AERIS onto the server

Either build on the server (needs the repository, about 20 minutes the first time):

```bash
sudo mkdir -p /opt/aeris && sudo chown $USER /opt/aeris && cd /opt/aeris
git clone <Africa CDC repository URL> openboxes && cd openboxes && git checkout aeris/v0.9.8
docker build -f aeris/docker/Dockerfile -t aeris:0.9.8-acdc15 .
```

or copy a built image from the build PC:

```bash
docker save aeris:0.9.8-acdc15 | gzip > aeris-0.9.8-acdc15.tar.gz      # on the build PC
docker load < aeris-0.9.8-acdc15.tar.gz                                   # on the server
```

Then copy the `aeris/deploy` folder to `/opt/aeris/deploy`.

## 4. Configure

```bash
cd /opt/aeris/deploy
cp .env.example .env && chmod 600 .env
nano .env                      # AERIS_HOST, AERIS_IMAGE, two passwords (openssl rand -hex 24: no spaces or quotes)
nano openboxes.yml             # SMTP host/port/sender, then grails.mail.enabled: true when ready
mkdir -p certs                 # fullchain.pem + privkey.pem for AERIS_HOST
```

Certificate with Let's Encrypt (if Africa CDC does not issue one), before the first start:

```bash
sudo apt-get install -y certbot
sudo certbot certonly --standalone -d aeris.africacdc.org
sudo cp /etc/letsencrypt/live/aeris.africacdc.org/{fullchain,privkey}.pem certs/
```

Renewal: a monthly cron that runs `certbot renew --pre-hook "docker compose -f /opt/aeris/deploy/docker-compose.prod.yml stop nginx" --post-hook "cp ... certs/ && docker compose -f /opt/aeris/deploy/docker-compose.prod.yml start nginx"`.

## 5. Start

```bash
docker compose -f docker-compose.prod.yml up -d
docker compose -f docker-compose.prod.yml logs -f app     # first start creates the database: 3-5 minutes
```

Open `https://<AERIS_HOST>/openboxes`. Then, at once:

1. Sign in with **Local account**: `admin` / `password`, and **change that password** (Admin → Users). Store it in the Africa CDC password manager. It is the break-glass account for outages.
2. Load the reference data in the order of `aeris/README.md` → *Loading the reference data* (location types and groups, categories, products, French names, sites, the three warehouses from `4b_entrepots_isiro_beni.xlsx`).
3. Give each user a role **per warehouse** (Admin → Users → user → Location roles), e.g. an Isiro storekeeper: Assistant at *Entrepôt Africa CDC Isiro* only.
4. Deactivate OpenBoxes' built-in demo depot **Main Warehouse** (Configuration → Locations → Main Warehouse → untick *Active*), so it does not appear in warehouse lists and Excel exports.

## 6. Backups (do not skip)

```bash
sudo mkdir -p /var/backups/aeris
chmod +x scripts/*.sh
./scripts/backup.sh                     # test once by hand
crontab -e                              # add:
30 2 * * *  cd /opt/aeris/deploy && ./scripts/backup.sh >> /var/log/aeris-backup.log 2>&1
0 4 1 * *   cd /opt/aeris/deploy && ./scripts/restore-test.sh >> /var/log/aeris-backup.log 2>&1
```

Set `BACKUP_OFFSITE_CMD` in `.env` so each dump is copied off the server. A backup on the same disk does not survive the loss of the server. Check `/var/log/aeris-backup.log` after the first night and after the first monthly restore test.

**Full restore** (after losing the server): install, configure and start as above. Then stop the app, load the latest dump into `openboxes`, and start the app again:

```bash
docker compose -f docker-compose.prod.yml stop app
gunzip -c aeris-YYYYMMDD-HHMMSS.sql.gz | docker compose -f docker-compose.prod.yml exec -T db sh -c 'exec mariadb -uroot -p"$MARIADB_ROOT_PASSWORD" openboxes'
docker compose -f docker-compose.prod.yml start app
```

## 7. Updating AERIS

1. Build or load the new image (`aeris:0.9.8-acdcN`).
2. Run `./scripts/backup.sh`.
3. Set `AERIS_IMAGE` in `.env`, then `docker compose -f docker-compose.prod.yml up -d app`.
4. Keep the previous image until the new one has run for a week. Rolling back means setting the old tag and running `up -d app` again.

## 8. Daily checks for the system focal point

- `docker compose -f docker-compose.prod.yml ps`: three services `running` / `healthy`
- Last line of `/var/log/aeris-backup.log`: `OK` with today's date
- Disk space: `df -h /` below 80%
