# LJ Discounts

Scrapes weekly grocery discounts for southern Ljubljana and builds a searchable
static `offers.html` report. The current working scraper targets Mercator
Rudnik; the project is structured so more store scrapers can be added under
`scrapers/`.

## Target Stores

- Mercator - Hipermarket Rudnik / Supernova Rudnik
- Eurospin - Rudnik
- Hofer - Rudnik / Vic
- E.Leclerc - Rudnik
- Lidl - Rudnik / Vic

Only Mercator is implemented right now. The other stores are planned targets.

## Quick Start

### Windows, No Python Required

The repository includes a GitHub Actions workflow that builds a portable
Windows zip:

1. Open **Actions** in GitHub.
2. Run **Build Windows app** manually, or push a `v*` tag to attach the zip to a
   release.
3. Download `lj-discounts-windows.zip`.
4. Extract it and double-click `run-lj-discounts.cmd`.

The generated report is saved as `offers.html` in the same folder as the app.

### Windows, From Source

Install Python 3.12 or newer, then double-click `refresh.bat`.

You can also run it from PowerShell:

```powershell
.\refresh.ps1
```

The script creates `.venv`, installs dependencies, runs the scraper, and opens
`offers.html`.

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python run.py --open
```

On macOS, `refresh.command` does the same thing.

## CLI

```bash
python run.py --help
python run.py --html out/offers.html --db out/offers.db --top 30 --open
```

Useful options:

- `--html PATH` - write the report somewhere else
- `--db PATH` - write the SQLite cache somewhere else
- `--top N` - choose how many top discounts to print
- `--open` / `--no-open` - control browser launch
- `--stale-days N` - purge old undated offers after N days

## Project Layout

- `scrapers/` - one module per grocery chain, each exposing `fetch() -> list[Offer]`
- `models.py` - shared `Offer` dataclass
- `run.py` - runs scrapers, stores offers in SQLite, prints highlights, writes HTML
- `weird.py` - flags suspicious or unusually good deals
- `.github/workflows/scrape.yml` - scheduled scraper and GitHub Pages deploy
- `.github/workflows/windows.yml` - Windows executable build

## Deploy

The scheduled scraper runs on GitHub Actions and pushes the generated report to
the `gh-pages` branch. You can also trigger it manually from the **Scrape &
Deploy** workflow.
