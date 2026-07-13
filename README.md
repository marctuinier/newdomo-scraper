# newdomo-scraper

A multi-site scraper for Dutch rental housing listings. It checks six rental
websites for the cities you configure, extracts each listing (address, price,
m², agency, and the *actual* city from the listing URL), and stores new
listings in a Supabase (PostgreSQL) database — or just prints them if you
don't have a database yet.

Finding a rental in the Netherlands is a race: good listings are gone within
hours. Run this on a schedule and you have a live, deduplicated feed of new
listings the moment they appear, to power notifications, a dashboard, or
whatever you want to build on top.

## Supported sites

| Site | Coverage |
|------|----------|
| [Pararius](https://www.pararius.com) | Nationwide |
| [Funda](https://www.funda.nl) | Nationwide |
| [Kamernet](https://kamernet.nl) | Nationwide (rooms & apartments) |
| [Huurwoningen](https://www.huurwoningen.com) | Nationwide |
| [123Wonen / Expat Rentals Holland](https://www.expatrentalsholland.com) | Nationwide |
| [Gruno Verhuur](https://www.grunoverhuur.nl) | Groningen |

Cities supported out of the box: Amsterdam, Rotterdam, The Hague, Utrecht,
Groningen, Maastricht, Leiden, Delft, Eindhoven, Tilburg, Enschede, Hengelo,
Beetsterzwaag, Gorredijk — and adding more is usually a one-line change per
site (see [Adding cities](#adding-cities-or-sites)).

## How it works

```
┌──────────────────────────────────────────────┐
│  main.py — one scrape cycle                  │
│                                              │
│  for each city × site:                       │
│    headless Chrome (selenium-stealth)        │
│    → parse listing cards                     │
│    → extract real city from listing URL      │
│    → insert into Supabase                    │
│      (unique link = automatic dedup)         │
└──────────────────────────────────────────────┘
```

- **One cycle per run.** The script scrapes every configured city on every
  supported site once, then exits. Scheduling is up to you (cron, systemd
  timer, etc.) — see [Running on a schedule](#running-on-a-schedule).
- **Deduplication is done by the database.** The `apartments` table has a
  unique constraint on the listing URL; re-inserting a known listing is a
  no-op. Every run can safely re-scrape everything.
- **Real city, not search city.** Dutch sites return listings from nearby
  towns. The scrapers extract the actual city from each listing's URL slug
  (with an address-line fallback), so your data isn't polluted by
  mis-attributed listings.

## Quick start (no database needed)

Requirements: Python 3.10+ and Google Chrome installed.

```bash
git clone <this-repo>
cd newdomo-scraper
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Dry run: scrape Groningen and print listings to stdout
CITIES=Groningen python src/main.py
```

Without Supabase credentials the scraper automatically runs in **dry-run
mode**: every listing found is printed as a `LISTING:` line instead of being
stored. That's the fastest way to check everything works on your machine.

## Full setup with Supabase

1. Create a free project at [supabase.com](https://supabase.com).
2. In the SQL editor, run the contents of [`schema.sql`](schema.sql) to create
   the `apartments` table.
3. Copy `.env.example` to `.env` and fill in:
   - `SUPABASE_URL` — Project Settings → API → Project URL
   - `SUPABASE_SERVICE_ROLE_KEY` — Project Settings → API → `service_role` key
     (keep this secret; it bypasses row level security)
   - `CITIES` — comma-separated list of cities you care about
4. Run it:

```bash
python src/main.py
```

New listings land in the `apartments` table; duplicates are skipped
automatically.

## Running with Docker

```bash
cp .env.example .env   # then fill in your values
docker compose up --build
```

Or without compose:

```bash
docker build -t newdomo-scraper .
docker run --rm --env-file .env --shm-size=1g newdomo-scraper
```

> **Note:** the image is `linux/amd64` because Google only publishes Chrome
> for amd64 on Linux. On Apple Silicon, Docker Desktop runs it under
> emulation automatically.

## Running on a schedule

The container/script runs one cycle and exits, so scheduling is a one-line
cron job. Every 6 hours:

```cron
0 */6 * * * cd /path/to/newdomo-scraper && docker compose up >> scraper.log 2>&1
```

For deploying to a cheap VPS (a €4/month box is plenty), see
[docs/SELF_HOSTING.md](docs/SELF_HOSTING.md).

## Configuration

All configuration is via environment variables (a `.env` file in the working
directory is loaded automatically):

| Variable | Required | Description |
|----------|----------|-------------|
| `SUPABASE_URL` | No | Supabase project URL. Omit for dry-run mode. |
| `SUPABASE_SERVICE_ROLE_KEY` | No | Supabase service role key. Omit for dry-run mode. |
| `CITIES` | No | Comma-separated cities (default: `Amsterdam,Rotterdam,The Hague,Utrecht,Groningen`) |
| `DRY_RUN` | No | Set to `1` to print listings instead of storing them |
| `FUNDA_LOCAL_TEST` | No | Set to `1` to run Chrome non-headless (debugging selectors locally) |

## Adding cities or sites

**A new city:** add an entry to `supported_cities()` in each hunter you want
it on (usually just the city name and its URL slug), then add it to `CITIES`.

**A new site:** create a class in `src/hunters/` that extends `Hunter`, and
implement:

- `supported_cities()` — `{city name: search URL}` map
- `process()` — parse the loaded page into `Prey` objects (`name`, `price`,
  `link`, `agency`, `website`, `m2`)

Then add it to `ALL_HUNTER_CLASSES` in `src/main.py`. Look at
`src/hunters/pararius.py` for a compact example.

## A note on scraping

This tool automates viewing publicly listed rental ads for personal use, at a
gentle rate (one page per city per site per run). Be a good citizen: keep run
frequency reasonable, don't hammer the sites, and check the terms of service
of each site before using it. Sites change their markup regularly — if a
hunter suddenly finds 0 listings, its CSS selectors probably need updating,
and PRs are welcome.

## Credits & license

Started from [brenocq/groningen-hunter](https://github.com/brenocq/groningen-hunter)
(a Telegram-notification apartment hunter) and evolved into a multi-city,
multi-site scraper with database storage.

MIT — see [LICENSE](LICENSE).
