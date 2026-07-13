# Self-hosting guide

How to run the scraper 24/7 on your own server. Any small VPS works — a
1–2 GB RAM box (Hetzner, DigitalOcean, Scaleway, …) is enough, since only one
headless Chrome instance runs at a time.

## 1. Provision a server

- Ubuntu 22.04+ (or any distro with Docker), 2 GB RAM recommended
  (headless Chrome is memory-hungry; 1 GB works with swap enabled)
- **amd64/x86_64 strongly recommended** — Google Chrome for Linux is only
  published for amd64. On an arm64 server the container needs qemu emulation,
  which is slow.

Install Docker:

```bash
curl -fsSL https://get.docker.com | sh
```

## 2. Deploy the scraper

```bash
git clone <this-repo> /opt/newdomo-scraper
cd /opt/newdomo-scraper
cp .env.example .env
nano .env        # fill in SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, CITIES
docker compose build
```

Test one cycle manually and watch the logs:

```bash
docker compose up
```

You should see `INFO: ... Supabase client initialized.` followed by per-site
listing counts, and new rows in your Supabase `apartments` table.

## 3. Schedule it

The container runs one scrape cycle and exits. Schedule it with cron
(`crontab -e`):

```cron
# Scrape every 6 hours
0 */6 * * * cd /opt/newdomo-scraper && /usr/bin/docker compose up >> /var/log/newdomo-scraper.log 2>&1
```

Pick an interval that suits you — every 1–6 hours is typical. Shorter
intervals give faster alerts but more load on the sites; be considerate.

Prefer systemd? Create a oneshot service plus a timer:

```ini
# /etc/systemd/system/newdomo-scraper.service
[Unit]
Description=newdomo scraper (one cycle)

[Service]
Type=oneshot
WorkingDirectory=/opt/newdomo-scraper
ExecStart=/usr/bin/docker compose up
```

```ini
# /etc/systemd/system/newdomo-scraper.timer
[Unit]
Description=Run newdomo scraper every 6 hours

[Timer]
OnCalendar=*-*-* 0/6:00:00
Persistent=true

[Install]
WantedBy=timers.target
```

```bash
systemctl daemon-reload && systemctl enable --now newdomo-scraper.timer
```

## 4. Maintenance

Check recent runs:

```bash
tail -100 /var/log/newdomo-scraper.log
```

Update to a new version:

```bash
cd /opt/newdomo-scraper && git pull && docker compose build
```

Common issues:

| Symptom | Likely cause |
|---------|-------------|
| A site suddenly finds 0 listings | The site changed its HTML; the hunter's selectors need updating |
| Chrome crashes / `session deleted` | Not enough memory or `/dev/shm` too small — the compose file sets `shm_size: 1gb`; keep it |
| `23505` errors in logs | Harmless — that's the unique-link constraint deduplicating listings |
| Funda returns nothing | Funda has aggressive bot detection; it may block datacenter IPs. The other sites are more tolerant. |

## 5. Building on top

Everything lands in one Postgres table (`apartments`), so consuming the data
is standard Supabase work: subscribe to inserts with Supabase Realtime for
instant notifications (Telegram, Discord, email via an edge function), or
point any dashboard/BI tool at the table.
