# LJ Discounts

![Build Windows app](https://github.com/pikammmmm/lj-discounts/actions/workflows/windows.yml/badge.svg)
![Scrape & Deploy](https://github.com/pikammmmm/lj-discounts/actions/workflows/scrape.yml/badge.svg)
[![Latest release](https://img.shields.io/github/v/release/pikammmmm/lj-discounts)](https://github.com/pikammmmm/lj-discounts/releases/latest)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Tracks weekly grocery discounts across Ljubljana and ranks the best deals by
percentage, in one searchable report.

**Live site:** https://pikammmmm.github.io/lj-discounts/
*(Rebuilds twice daily at 07:00 and 12:00 Europe/Ljubljana.)*

## Stores covered

| Chain      | Source                                  |
|------------|-----------------------------------------|
| Mercator   | Supernova Rudnik online assortment API  |
| Lidl       | `lidl.si/c/ponudba` offer pages         |
| Hofer      | `hofer.si` online offer pages           |
| Eurospin   | `eurospin.si` online offer pages        |
| TEDi       | `tedi.com` Ljubljana offer pages        |
| Tuš        | `tus.si` weekly offer pages             |
| SPAR       | `online.spar.si` Next.js data chunks    |
| dm         | `dm.si` product-search API (clearance)  |
| E.Leclerc  | *planned — catalogue published as PDF*  |

## Install

### Windows — no Python required

Download the latest [`lj-discounts-windows.zip`](https://github.com/pikammmmm/lj-discounts/releases/latest),
unzip, and double-click **`run-lj-discounts.cmd`**. The desktop app window
opens, scrapes once, and displays the report. `lj-discounts-cli.exe` is
bundled for scheduled/headless use.

### Android — Add to Home Screen (PWA)

Open the [live site](https://pikammmmm.github.io/lj-discounts/) in Chrome on
Android → menu → **Add to Home Screen**. The site installs as a standalone app
with its own icon.

### Run from source — Windows

Install Python 3.12+, then double-click **`refresh.bat`** (or run
`.\refresh.ps1` from PowerShell). A `.venv` is created, dependencies are
installed, and the app window opens.

### Run from source — macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python run.py --open
```

macOS users can double-click `refresh.command`.

## CLI

```bash
python run.py [--html PATH] [--db PATH] [--top N] [--stale-days N] [--open|--no-open]
```

| Flag            | Default        | Purpose                                       |
|-----------------|----------------|-----------------------------------------------|
| `--html PATH`   | `offers.html`  | Where to write the generated HTML report      |
| `--db PATH`     | `offers.db`    | SQLite cache path                             |
| `--top N`       | `20`           | How many % discounts to print to stdout      |
| `--stale-days N`| `8`            | Purge undated, unseen offers after N days     |
| `--open`        | auto           | Open the HTML in the default browser          |
| `--no-open`     | —              | Skip browser launch                           |

## Layout

```
.
├── app.py                    # pywebview desktop shell
├── run.py                    # CLI entry point + HTML renderer
├── scrapers/                 # one module per chain (fetch() -> list[Offer])
│   ├── common.py             # shared helpers (UA, price/date parse)
│   ├── mercator.py, lidl.py, hofer.py, eurospin.py,
│   │ tedi.py, tus.py, spar.py, dm.py
│   └── __init__.py           # exports ALL = [...]
├── models.py                 # Offer dataclass
├── stores.py                 # physical-store labels
├── weird.py                  # hot/suspicious deal flagging
├── categorize.py             # category normalization
├── assets/                   # app icon (ICO + PNG) + generator
├── manifest.json             # PWA manifest (served from gh-pages)
├── windows/                  # Windows-only launchers bundled in the exe zip
├── refresh.{bat,ps1,command} # source-run launchers per platform
├── requirements.txt          # scrape-only deps (requests, beautifulsoup4)
├── requirements-windows.txt  # adds pywebview for the desktop app
└── .github/workflows/
    ├── scrape.yml            # daily scrape → gh-pages
    └── windows.yml           # tag-triggered exe build + release
```

## Pipeline

1. **Scrape (scheduled):** `scrape.yml` runs `python run.py` on GitHub-hosted
   Ubuntu daily at 05:00 and 10:00 UTC (07:00 / 12:00 local).
2. **Deploy:** generated `offers.html` is copied to `index.html`, icons and
   `manifest.json` are staged, and the result is force-pushed to `gh-pages`.
3. **Release (tag-triggered):** pushing a `v*` tag runs `windows.yml`, which
   builds `lj-discounts.exe` (desktop) and `lj-discounts-cli.exe`, zips them
   with README and launcher, uploads as an artifact, and attaches the zip to
   the GitHub Release.

## Contributing

Adding a chain is small: write `scrapers/<chain>.py` exposing `NAME` and
`fetch() -> list[Offer]`, register it in `scrapers/__init__.py`, add a store
label to `stores.py`. Existing scrapers in `scrapers/` are the template.

## License

[MIT](LICENSE) © 2026 David Ninic
