# LJ Discounts

Scrapes weekly discount catalogs from grocery stores in southern Ljubljana and
ranks the biggest discounts across chains.

## Target stores (southern LJ)
- Mercator — e.g. Rudnik, Barje
- Eurospin — Rudnik
- Hofer — Rudnik / Vič
- E.Leclerc — Rudnik (Jurčkova)
- Lidl — Rudnik / Vič

## Layout
- `scrapers/` — one module per chain. Each exposes `fetch() -> list[Offer]`.
- `models.py` — shared `Offer` dataclass.
- `run.py` — runs every scraper, stores results in SQLite, prints top N.

## Status
Scaffold only. Mercator scraper is a working starting point; others are stubs
you (or I, next session) fill in by inspecting each chain's public catalog.

## Run
```
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python run.py
```
