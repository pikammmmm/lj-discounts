"""Run every scraper, upsert offers into SQLite, purge expired, print top discounts.

Freshness rules:
  * An offer row is keyed by (chain, source_url, product, discount_price).
  * On each run we re-insert whatever each scraper returns and bump `fetched_at`.
  * Rows whose `valid_to` is in the past are deleted.
  * Rows for a chain that weren't seen in this run AND are older than 8 days
    are also deleted (handles chains whose PDFs don't embed validity dates).
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
import webbrowser
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models import Offer
    from weird import Flag

STALE_DAYS = 8
DEFAULT_TOP = 20


def _app_dir() -> Path:
    """Return a writable application directory for source and frozen builds."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


APP_DIR = _app_dir()
DEFAULT_DB = APP_DIR / "offers.db"
DEFAULT_HTML_OUT = APP_DIR / "offers.html"


def configure_stdio() -> None:
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except (OSError, ValueError):
                pass


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Scrape Mercator Rudnik discounts and write an HTML report."
    )
    parser.set_defaults(open_browser=getattr(sys, "frozen", False))
    parser.add_argument(
        "--db",
        type=Path,
        default=DEFAULT_DB,
        help=f"SQLite database path (default: {DEFAULT_DB})",
    )
    parser.add_argument(
        "--html",
        type=Path,
        default=DEFAULT_HTML_OUT,
        help=f"HTML report path (default: {DEFAULT_HTML_OUT})",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=DEFAULT_TOP,
        help=f"number of top percentage discounts to print (default: {DEFAULT_TOP})",
    )
    parser.add_argument(
        "--stale-days",
        type=int,
        default=STALE_DAYS,
        help=f"days before undated unseen offers are purged (default: {STALE_DAYS})",
    )
    parser.add_argument(
        "--open",
        dest="open_browser",
        action="store_true",
        help="open the generated HTML report in the default browser",
    )
    parser.add_argument(
        "--no-open",
        dest="open_browser",
        action="store_false",
        help="do not open the generated HTML report",
    )
    args = parser.parse_args(argv)
    if args.top < 0:
        parser.error("--top must be 0 or greater")
    if args.stale_days < 0:
        parser.error("--stale-days must be 0 or greater")
    return args


def init_db(con: sqlite3.Connection) -> None:
    con.executescript(
        """
        CREATE TABLE IF NOT EXISTS offers (
            chain TEXT NOT NULL,
            store_hint TEXT,
            product TEXT NOT NULL,
            category TEXT,
            regular REAL,
            discount REAL NOT NULL,
            pct REAL,
            valid_from TEXT,
            valid_to TEXT,
            source_url TEXT NOT NULL,
            image_url TEXT,
            fetched_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (chain, source_url, product, discount)
        );
        CREATE INDEX IF NOT EXISTS idx_offers_chain_fetched ON offers(chain, fetched_at);
        CREATE INDEX IF NOT EXISTS idx_offers_valid_to ON offers(valid_to);
        """
    )


def upsert(con: sqlite3.Connection, offers: list[Offer]) -> None:
    con.executemany(
        """INSERT INTO offers(chain,store_hint,product,category,regular,discount,pct,valid_from,valid_to,source_url,image_url,fetched_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)
           ON CONFLICT(chain, source_url, product, discount) DO UPDATE SET
             regular=excluded.regular, pct=excluded.pct, category=excluded.category,
             valid_from=excluded.valid_from, valid_to=excluded.valid_to,
             image_url=excluded.image_url,
             fetched_at=CURRENT_TIMESTAMP""",
        [(o.chain, o.store_hint, o.product, o.category, o.regular_price, o.discount_price,
          o.discount_pct,
          o.valid_from.isoformat() if o.valid_from else None,
          o.valid_to.isoformat() if o.valid_to else None,
          o.source_url,
          o.image_path) for o in offers],
    )


def purge(con: sqlite3.Connection, seen_chains: set[str], stale_days: int = STALE_DAYS) -> int:
    today = date.today().isoformat()
    cutoff = (date.today() - timedelta(days=stale_days)).isoformat()
    cur = con.execute("DELETE FROM offers WHERE valid_to IS NOT NULL AND valid_to < ?", (today,))
    removed = cur.rowcount
    for chain in seen_chains:
        cur = con.execute(
            "DELETE FROM offers WHERE chain=? AND valid_to IS NULL AND fetched_at < ?",
            (chain, cutoff),
        )
        removed += cur.rowcount
    return removed


def main(argv: list[str] | None = None) -> int:
    configure_stdio()
    args = parse_args(argv)
    db_path = args.db.expanduser()
    html_out = args.html.expanduser()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    html_out.parent.mkdir(parents=True, exist_ok=True)

    from scrapers import ALL
    from stores import STORES
    from weird import flag_weird

    all_offers: list[Offer] = []
    seen: set[str] = set()
    for mod in ALL:
        try:
            got = mod.fetch()
            print(f"{mod.NAME:10} {STORES.get(mod.NAME, '-'):32}  "
                  f"{len(got):4d} on sale", file=sys.stderr)
            all_offers.extend(got)
            if got:
                seen.add(mod.NAME)
        except Exception as e:
            print(f"{mod.NAME:10} FAILED — {e}", file=sys.stderr)
            import traceback; traceback.print_exc(file=sys.stderr)

    with sqlite3.connect(db_path) as con:
        init_db(con)
        upsert(con, all_offers)
        removed = purge(con, seen, args.stale_days)
        con.commit()
        total = con.execute("SELECT COUNT(*) FROM offers").fetchone()[0]

    print(f"\npurged {removed} expired/stale rows; {total} live offers in DB")

    with_pct = [o for o in all_offers if o.discount_pct is not None]
    with_pct.sort(key=lambda o: o.discount_pct, reverse=True)
    print(f"\n== TOP {args.top} % DISCOUNTS (Mercator Rudnik) ==")
    for o in with_pct[:args.top]:
        print(f"{o.discount_pct:5.1f}%  {o.chain:10}  {o.product[:48]:48}  "
              f"{o.regular_price}€ -> {o.discount_price}€")

    fresh_offers = [o for o in all_offers if o.valid_to is None or o.valid_to >= date.today()]
    flags = flag_weird(fresh_offers)
    # Remove severity-3 (garbage) from display
    garbage_ids = {id(f.offer) for f in flags if f.severity == 3}
    clean_offers = [o for o in fresh_offers if id(o) not in garbage_ids]
    interesting = [f for f in flags if f.severity <= 2]

    print(f"\nflagged {len(flags)} weird ({sum(1 for f in flags if f.severity==3)} garbage removed, "
          f"{len(interesting)} interesting deals)")
    for f in interesting[:10]:
        print(f"  {'!!'if f.severity==2 else ' >'} {f.offer.chain:10} {f.offer.product[:40]:40} {f.reason}")

    write_html(clean_offers, interesting, html_out)
    print(f"\nwrote {html_out}")
    if args.open_browser:
        webbrowser.open(html_out.resolve().as_uri())
    return 0


CATEGORY_LABELS = {
    "SVEŽ KRUH IN PECIVO": "Kruh in pecivo",
    "MLEKO, JAJCA IN MLEČNI IZDELKI": "Mleko, jajca, sir",
    "MESO, MESNI IZDELKI IN RIBE": "Meso in ribe",
    "SADJE IN ZELENJAVA": "Sadje in zelenjava",
    "PIJAČE": "Pijače",
    "ČOKOLADA IN DRUGI SLADKI PROGRAM": "Sladkarije",
    "SLANI PRIGRIZKI IN APERITIVI (JEDI)": "Prigrizki",
    "VSE ZA ZAJTRK": "Zajtrk (kava, čaj, namazi)",
    "OSNOVNA ŽIVILA / SHRAMBA": "Osnovna živila",
    "TESTENINE, JUHE, RIŽ IN OMAKE": "Testenine, riž, omake",
    "KONZERVIRANA HRANA": "Konzervirana hrana",
    "ZAMRZNJENA HRANA": "Zamrznjena hrana",
    "DELIKATESNI IZDELKI IN PRIPRAVLJENE JEDI": "Delikatesa",
    "ČISTILA": "Čistila",
    "HIGIENA IN LEPOTA": "Higiena",
    "VSE ZA DOM IN GOSPODINJSTVO": "Gospodinjstvo",
}


def _cat_label(cat1: str | None) -> str:
    if not cat1:
        return "Ostalo"
    return CATEGORY_LABELS.get(cat1, cat1.title())


def write_html(
    offers: list[Offer],
    flags: list[Flag] | None = None,
    output_path: Path = DEFAULT_HTML_OUT,
) -> None:
    from stores import STORES

    flagged_ids = {id(f.offer): f for f in (flags or [])}
    with_pct = sorted((o for o in offers if o.discount_pct is not None),
                      key=lambda o: o.discount_pct, reverse=True)
    without_pct = sorted((o for o in offers if o.discount_pct is None),
                         key=lambda o: o.discount_price)
    ranked = with_pct + without_pct

    from collections import defaultdict

    # Build hierarchy: category1 -> category2 -> [offers]
    # Classify every product via product-name keywords so chocolate from any
    # chain lands in "Sladkarije", drinks in "Pijače", etc. Mercator's native
    # category1 is kept as a fallback when inference finds no keyword match;
    # for other chains the fallback is "Ostalo" since their category1 is just
    # the chain name.
    #
    # For sub-grouping, infer_category2 returns a curated subcategory inside
    # the known categories (so e.g. a chip-flavoured "paprika" stays under
    # "Čips" and not under whatever Mercator labelled it). When the cat1
    # has no curated subcategories, we fall back to the source's category2.
    from categorize import infer_category1, infer_category2

    hierarchy: dict[str, dict[str, list[Offer]]] = defaultdict(lambda: defaultdict(list))
    for o in ranked:
        native = o.category1 if o.category1 in CATEGORY_LABELS else None
        cat1_raw = infer_category1(o.product, fallback=native) or "Ostalo"
        cat1 = CATEGORY_LABELS.get(cat1_raw, cat1_raw.title())
        sub = infer_category2(o.product, cat1_raw)
        if sub is not None:
            cat2 = sub
        else:
            cat2 = o.category or cat1
            if cat2 == cat1_raw:
                cat2 = cat1
        hierarchy[cat1][cat2].append(o)

    # Sort sections by item count
    sections = sorted(hierarchy.items(), key=lambda kv: -sum(len(v) for v in kv[1].values()))

    def make_card(o: Offer) -> str:
        img = ""
        if o.image_path:
            img = f'<img src="{_esc(o.image_path)}" loading=lazy alt="">'
        flag = flagged_ids.get(id(o))
        badge = ""
        extra_cls = ""
        if flag:
            if flag.severity == 2:
                badge = f'<span class="badge warn">!!</span>'
                extra_cls = " flagged"
            else:
                badge = f'<span class="badge hot">HOT</span>'
                extra_cls = " hot-card"
        pct_text = f"-{o.discount_pct:.0f}%" if o.discount_pct else "AKCIJA"
        old_html = f'<span class="old-price">{_fmt(o.regular_price)}</span>' if o.regular_price else ''
        return (
            f'<a href="{_esc(o.source_url)}" target="_blank" rel="noopener noreferrer" class="card{extra_cls}" '
            f'data-name="{_esc(o.product.lower())}">'
            f'<span class="add-btn" role="button" aria-label="Dodaj na seznam" tabindex="0">+</span>'
            f'<div class="card-img">{img}</div>'
            f'<div class="card-body">'
            f'<div class="card-pct">{pct_text}{badge}</div>'
            f'<div class="card-name">{_esc(o.product)}</div>'
            f'<div class="card-prices">{old_html}'
            f'<span class="new-price">{_fmt(o.discount_price)}</span></div>'
            f'</div></a>'
        )

    cards_html = ""
    for cat_name, subs in sections:
        total_cat = sum(len(v) for v in subs.values())
        sorted_subs = sorted(subs.items(), key=lambda kv: -len(kv[1]))
        cards_html += f'<div class="cat-header" data-cat="{_esc(cat_name)}">{_esc(cat_name)} <span class="cnt">({total_cat})</span></div>\n'
        cards_html += f'<div class="cat-section" data-cat="{_esc(cat_name)}">\n'
        # Subcategory buttons
        cards_html += '<div class="sub-filters">'
        cards_html += f'<button class="sub-btn active" data-sub="all">Vse ({total_cat})</button>'
        for sub_name, items in sorted_subs:
            cards_html += f'<button class="sub-btn" data-sub="{_esc(sub_name)}">{_esc(sub_name)} ({len(items)})</button>'
        cards_html += '</div>\n'
        # Grids per subcategory
        for sub_name, items in sorted_subs:
            items.sort(key=lambda o: o.discount_pct or 0, reverse=True)
            cards_html += f'<div class="sub-grid" data-sub="{_esc(sub_name)}">\n'
            cards_html += '<div class="grid">\n'
            for o in items:
                cards_html += make_card(o) + "\n"
            cards_html += '</div></div>\n'
        cards_html += '</div>\n'

    output_path.write_text(f"""<!doctype html>
<html lang=sl><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>Popusti — Mercator Rudnik</title>
<link rel="manifest" href="manifest.json">
<meta name="theme-color" content="#4ade80">
<link rel="icon" type="image/png" sizes="192x192" href="icon-192.png">
<link rel="icon" type="image/png" sizes="512x512" href="icon-512.png">
<link rel="apple-touch-icon" href="icon-192.png">
<link rel="shortcut icon" href="favicon.ico">
<style>
:root{{
  --bg:#08090d;
  --surface:#10121a;
  --surface2:#181b27;
  --border:rgba(255,255,255,.06);
  --accent:#4ade80;
  --accent2:#22d3ee;
  --accent-dim:rgba(74,222,128,.12);
  --yellow:#fbbf24;
  --red:#fb923c;
  --text:#e2e8f0;
  --text2:#94a3b8;
  --text3:#475569;
  --r:14px;
}}
*{{box-sizing:border-box;margin:0;padding:0}}
html{{scroll-behavior:smooth}}
body{{
  font-family:system-ui,-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
  background:var(--bg);color:var(--text);min-height:100vh;
  -webkit-font-smoothing:antialiased;
}}

/* === HERO === */
.hero{{padding:48px 20px 24px;text-align:center}}
.hero h1{{
  font-size:28px;font-weight:800;letter-spacing:-.5px;
  background:linear-gradient(135deg,#fff,var(--accent));
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;
  background-clip:text;
}}
.hero .sub{{font-size:13px;color:var(--text3);margin-top:6px}}
.hero .count{{
  display:inline-block;margin-top:12px;
  background:var(--surface2);border:1px solid var(--border);
  padding:5px 16px;border-radius:20px;
  font-size:12px;font-weight:600;color:var(--accent);
}}

/* === SEARCH === */
.search-wrap{{max-width:520px;margin:0 auto 12px;padding:0 16px;position:relative}}
.search-wrap input{{
  width:100%;padding:12px 16px 12px 44px;
  background:var(--surface);border:1px solid var(--border);
  border-radius:12px;color:#fff;font-size:15px;outline:none;
  transition:border-color .2s,box-shadow .2s;
}}
.search-wrap input::placeholder{{color:var(--text3)}}
.search-wrap input:focus{{
  border-color:var(--accent);
  box-shadow:0 0 0 3px var(--accent-dim);
}}
.search-wrap svg{{
  position:absolute;left:30px;top:50%;transform:translateY(-50%);
  width:17px;height:17px;stroke:var(--text3);stroke-width:2;fill:none;
  pointer-events:none;
}}
.search-count{{
  text-align:center;font-size:12px;color:var(--text3);
  margin:0 0 4px;min-height:16px;
}}

/* === FILTERS === */
.filters{{
  padding:10px 16px;display:flex;gap:7px;flex-wrap:wrap;
  justify-content:center;
  background:var(--bg);
  border-bottom:1px solid var(--border);
}}
.filters button{{
  background:var(--surface);color:var(--text2);
  border:1px solid var(--border);
  border-radius:20px;padding:6px 14px;font-size:12px;font-weight:500;
  cursor:pointer;white-space:nowrap;transition:all .15s;
}}
.filters button:hover{{background:var(--surface2);color:#fff}}
.filters button.active{{
  background:var(--accent);color:#000;
  border-color:var(--accent);font-weight:700;
}}

/* === CATEGORY HEADERS === */
.cat-header{{
  padding:28px 20px 6px;font-size:18px;font-weight:800;
  color:var(--text);letter-spacing:-.3px;
  border-top:1px solid var(--border);
}}
.cat-header:first-of-type{{border-top:none}}
.cat-header .cnt{{font-weight:400;color:var(--text3);font-size:14px}}
.cat-section{{content-visibility:auto;contain-intrinsic-size:auto 600px}}

/* === SUB FILTERS === */
.sub-filters{{
  display:flex;gap:6px;flex-wrap:wrap;padding:8px 16px 10px;
}}
.sub-btn{{
  background:var(--surface2);color:var(--text2);
  border:1px solid var(--border);border-radius:16px;
  padding:5px 12px;font-size:11px;font-weight:500;
  cursor:pointer;white-space:nowrap;transition:all .15s;
}}
.sub-btn:hover{{background:rgba(255,255,255,.08);color:#fff}}
.sub-btn.active{{background:var(--accent2);color:#000;border-color:var(--accent2);font-weight:700}}
.sub-grid.sub-hidden{{display:none}}

/* === GRID === */
.grid{{
  display:grid;
  grid-template-columns:repeat(auto-fill,minmax(155px,1fr));
  gap:10px;padding:4px 16px 16px;
}}

/* === CARDS — no blur, no pseudo-elements, lightweight === */
.card{{
  display:flex;flex-direction:column;position:relative;
  background:var(--surface);
  border:1px solid var(--border);
  border-radius:var(--r);
  overflow:hidden;text-decoration:none;color:var(--text);
  transition:transform .15s,box-shadow .15s,border-color .15s;
}}
.add-btn{{
  position:absolute;top:6px;right:6px;z-index:2;
  width:28px;height:28px;border-radius:50%;
  background:rgba(8,9,13,.78);color:var(--text);
  border:1px solid var(--border);
  display:grid;place-items:center;
  font-size:18px;font-weight:700;line-height:1;
  cursor:pointer;user-select:none;
  transition:background .15s,color .15s,border-color .15s,transform .15s;
}}
.add-btn:hover{{background:var(--accent);color:#000;border-color:var(--accent)}}
.card.in-list{{border-color:var(--accent)}}
.card.in-list .add-btn{{
  background:var(--accent);color:#000;border-color:var(--accent);
  font-size:0;
}}
.card.in-list .add-btn::before{{content:"\\2713";font-size:14px;color:#000}}
.card:hover{{
  transform:translateY(-2px);
  border-color:rgba(255,255,255,.12);
  box-shadow:0 8px 24px rgba(0,0,0,.4);
}}
.card.hot-card{{border-color:rgba(74,222,128,.2)}}
.card.flagged{{opacity:.55}}

.card-img{{
  aspect-ratio:1;display:flex;align-items:center;justify-content:center;
  background:var(--surface2);overflow:hidden;padding:10px;
}}
.card-img img{{max-width:100%;max-height:100%;object-fit:contain}}

.card-body{{padding:10px 12px 14px;flex:1;display:flex;flex-direction:column;gap:4px}}
.card-pct{{font-size:13px;font-weight:800;color:var(--accent);display:flex;align-items:center;gap:5px}}
.card-name{{
  font-size:12px;font-weight:500;line-height:1.35;color:var(--text2);
  display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;
}}
.card-prices{{margin-top:auto;display:flex;align-items:baseline;gap:8px;padding-top:4px}}
.old-price{{font-size:11px;color:var(--text3);text-decoration:line-through}}
.new-price{{font-size:16px;font-weight:700;color:var(--yellow)}}

.badge{{font-size:8px;padding:2px 5px;border-radius:3px;font-weight:800;text-transform:uppercase;letter-spacing:.3px}}
.badge.hot{{background:var(--accent);color:#000}}
.badge.warn{{background:var(--red);color:#000}}

/* hide filtered */
.cat-header.hidden,.cat-section.hidden,.card.hidden{{display:none!important}}
.no-results{{text-align:center;padding:60px 20px;color:var(--text3);font-size:15px;display:none}}
.no-results.show{{display:block}}
.app-refresh{{
  display:none;position:fixed;right:18px;bottom:18px;z-index:40;
  width:48px;height:48px;border:0;border-radius:8px;
  background:var(--accent);color:#000;font-size:22px;font-weight:900;
  cursor:pointer;box-shadow:0 8px 26px rgba(0,0,0,.45);
}}
.app-refresh:hover{{filter:brightness(1.05)}}
.app-refresh:disabled{{opacity:.65;cursor:wait}}
body.app-mode .app-refresh{{display:grid;place-items:center}}
body.app-mode #listFab{{bottom:78px}}

/* === SHOPPING LIST FAB + DRAWER === */
#listFab{{
  position:fixed;right:18px;bottom:18px;z-index:40;
  display:grid;place-items:center;
  width:52px;height:52px;border:0;border-radius:26px;
  background:var(--surface2);color:var(--text);
  border:1px solid var(--border);
  cursor:pointer;box-shadow:0 8px 26px rgba(0,0,0,.45);
  transition:background .15s,color .15s,transform .15s;
}}
#listFab:hover{{background:var(--accent);color:#000;border-color:var(--accent)}}
#listFab svg{{width:22px;height:22px;stroke:currentColor;stroke-width:2;fill:none}}
#listFab .badge-count{{
  position:absolute;top:-4px;right:-4px;
  min-width:20px;height:20px;padding:0 6px;
  border-radius:10px;background:var(--accent);color:#000;
  font-size:11px;font-weight:800;display:none;
  align-items:center;justify-content:center;
}}
#listFab.has-items .badge-count{{display:flex}}

#listPanel{{
  position:fixed;inset:0;z-index:50;
  background:rgba(0,0,0,.55);display:none;
}}
#listPanel.open{{display:flex;align-items:flex-end;justify-content:center}}
#listPanel .sheet{{
  width:100%;max-width:560px;max-height:80vh;
  background:var(--surface);
  border-top-left-radius:18px;border-top-right-radius:18px;
  display:flex;flex-direction:column;
  box-shadow:0 -8px 32px rgba(0,0,0,.5);
}}
#listPanel .sheet-head{{
  padding:14px 18px;display:flex;align-items:center;gap:12px;
  border-bottom:1px solid var(--border);
}}
#listPanel .sheet-head h2{{font-size:16px;font-weight:700;flex:1}}
#listPanel .sheet-head button{{
  background:transparent;border:0;color:var(--text2);
  font-size:13px;cursor:pointer;padding:6px 10px;border-radius:8px;
}}
#listPanel .sheet-head button:hover{{color:#fff;background:var(--surface2)}}
#listPanel .sheet-body{{
  padding:8px 0;overflow-y:auto;
}}
.list-row{{
  display:flex;align-items:center;gap:12px;padding:10px 18px;
  border-bottom:1px solid var(--border);
}}
.list-row:last-child{{border-bottom:0}}
.list-row .li-img{{
  width:42px;height:42px;border-radius:8px;background:var(--surface2);
  display:grid;place-items:center;overflow:hidden;flex-shrink:0;
}}
.list-row .li-img img{{max-width:100%;max-height:100%;object-fit:contain}}
.list-row .li-name{{
  flex:1;font-size:13px;color:var(--text);line-height:1.3;
  display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;
}}
.list-row .li-price{{
  font-size:14px;font-weight:700;color:var(--yellow);flex-shrink:0;
}}
.list-row .li-remove{{
  background:transparent;border:0;color:var(--text3);
  width:28px;height:28px;border-radius:50%;cursor:pointer;
  font-size:18px;line-height:1;flex-shrink:0;
}}
.list-row .li-remove:hover{{color:var(--red);background:var(--surface2)}}
.list-empty{{padding:32px 18px;text-align:center;color:var(--text3);font-size:14px}}
@media(min-width:768px){{
  #listPanel.open{{align-items:center}}
  #listPanel .sheet{{
    border-radius:18px;max-height:70vh;
  }}
}}

/* === DESKTOP === */
@media(min-width:768px){{
  .grid{{grid-template-columns:repeat(auto-fill,minmax(185px,1fr));gap:14px;padding:6px 24px 20px}}
  .cat-header{{padding:32px 24px 8px;font-size:20px}}
  .sub-filters{{padding:10px 24px 12px}}
  .hero{{padding:56px 24px 28px}}
  .hero h1{{font-size:34px}}
  .filters{{padding:12px 24px}}
}}
@media(min-width:1200px){{
  .grid,.cat-header,.sub-filters{{max-width:1400px;margin-left:auto;margin-right:auto}}
  .grid{{grid-template-columns:repeat(auto-fill,minmax(195px,1fr));gap:16px;padding:6px 32px 24px}}
  .cat-header{{padding:36px 32px 8px}}
  .sub-filters{{padding:12px 32px 14px}}
}}

/* === DESKTOP: sticky filters only on wide screens === */
@media(min-width:769px){{
  .filters{{position:sticky;top:0;z-index:15}}
}}
@media(max-width:380px){{
  .grid{{grid-template-columns:repeat(2,1fr);gap:8px;padding:4px 10px 12px}}
  .card-body{{padding:8px 10px 12px}}
  .card-name{{font-size:11px}}
  .new-price{{font-size:14px}}
}}

::-webkit-scrollbar{{width:5px}}
::-webkit-scrollbar-track{{background:transparent}}
::-webkit-scrollbar-thumb{{background:rgba(255,255,255,.08);border-radius:3px}}
</style>
</head><body>

<div class="hero">
  <h1>LJ Discounts</h1>
  <div class="sub">Supernova Rudnik &middot; {datetime.now():%d.%m.%Y %H:%M}</div>
  <div class="count">{len(ranked)} on sale</div>
</div>
<div class="search-wrap">
  <input type="text" id="search" placeholder="Search..." autocomplete="off">
  <svg viewBox="0 0 24 24"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
</div>
<div class="search-count" id="searchCount"></div>
<div class="filters" id="filters">
  <button class="active" data-cat="all">Vse ({len(ranked)})</button>
  {''.join('<button data-cat="' + _esc(name) + '">' + _esc(name) + ' (' + str(sum(len(v) for v in subs.values())) + ')</button>' for name, subs in sections)}
</div>

<div id="content">
{cards_html}
</div>
<div class="no-results" id="noResults">No results found</div>
<button class="app-refresh" id="appRefresh" title="Refresh" aria-label="Refresh">↻</button>
<button id="listFab" type="button" title="Moj seznam" aria-label="Moj seznam">
  <svg viewBox="0 0 24 24"><path d="M9 5h10M9 12h10M9 19h10"/><circle cx="4.5" cy="5" r="1.2" fill="currentColor" stroke="none"/><circle cx="4.5" cy="12" r="1.2" fill="currentColor" stroke="none"/><circle cx="4.5" cy="19" r="1.2" fill="currentColor" stroke="none"/></svg>
  <span class="badge-count" id="listCount">0</span>
</button>
<div id="listPanel" role="dialog" aria-label="Moj seznam">
  <div class="sheet">
    <div class="sheet-head">
      <h2>Moj seznam (<span id="listHeadCount">0</span>)</h2>
      <button type="button" id="listClear">Počisti</button>
      <button type="button" id="listClose">Zapri</button>
    </div>
    <div class="sheet-body" id="listBody">
      <div class="list-empty">Seznam je prazen. Pritisni + na izdelku, da ga dodaš.</div>
    </div>
  </div>
</div>

<script>
(()=>{{
  const search=document.getElementById('search');
  const btns=document.querySelectorAll('.filters button');
  const noResults=document.getElementById('noResults');
  const countEl=document.getElementById('searchCount');
  const appRefresh=document.getElementById('appRefresh');
  const catHeaders=document.querySelectorAll('.cat-header');
  const catSections=document.querySelectorAll('.cat-section');
  let activeCat='all';

  function applyFilters(){{
    const q=search.value.toLowerCase().trim();
    let visible=0;
    catHeaders.forEach((h,i)=>{{
      const cat=h.dataset.cat;
      const sec=catSections[i];
      const showCat=activeCat==='all'||activeCat===cat;
      if(!showCat){{h.classList.add('hidden');sec.classList.add('hidden');return}}
      h.classList.remove('hidden');sec.classList.remove('hidden');
      let catVis=0;
      sec.querySelectorAll('.card').forEach(c=>{{
        const subGrid=c.closest('.sub-grid');
        if(subGrid&&subGrid.classList.contains('sub-hidden'))return;
        const show=!q||c.dataset.name.includes(q);
        c.classList.toggle('hidden',!show);
        if(show){{catVis++;visible++}}
      }});
      if(!catVis){{h.classList.add('hidden');sec.classList.add('hidden')}}
    }});
    noResults.classList.toggle('show',visible===0);
    countEl.textContent=q?(visible+' result'+(visible!==1?'s':'')):'';
  }}

  btns.forEach(btn=>btn.addEventListener('click',()=>{{
    btns.forEach(b=>b.classList.remove('active'));
    btn.classList.add('active');
    activeCat=btn.dataset.cat;
    applyFilters();
  }}));

  let tid;
  search.addEventListener('input',()=>{{clearTimeout(tid);tid=setTimeout(applyFilters,120)}});

  /* Sub-category buttons */
  document.querySelectorAll('.sub-filters').forEach(bar=>{{
    const subBtns=bar.querySelectorAll('.sub-btn');
    const section=bar.parentElement;
    const subGrids=section.querySelectorAll('.sub-grid');
    subBtns.forEach(btn=>btn.addEventListener('click',()=>{{
      subBtns.forEach(b=>b.classList.remove('active'));
      btn.classList.add('active');
      const sub=btn.dataset.sub;
      subGrids.forEach(g=>{{
        g.classList.toggle('sub-hidden',sub!=='all'&&g.dataset.sub!==sub);
      }});
      applyFilters();
    }}));
  }});

  let appModeEnabled=false;
  function enableAppMode(){{
    if(appModeEnabled)return;
    appModeEnabled=true;
    document.body.classList.add('app-mode');
    appRefresh.disabled=false;
    appRefresh.textContent='↻';
    appRefresh.addEventListener('click',()=>{{
      appRefresh.disabled=true;
      appRefresh.textContent='...';
      window.pywebview.api.refresh();
    }});
  }}
  if(window.pywebview&&window.pywebview.api){{
    enableAppMode();
  }}
  window.addEventListener('pywebviewready',enableAppMode);

  /* === Shopping list (localStorage) === */
  const LIST_KEY='lj-list-v1';
  const fab=document.getElementById('listFab');
  const fabCount=document.getElementById('listCount');
  const headCount=document.getElementById('listHeadCount');
  const panel=document.getElementById('listPanel');
  const panelBody=document.getElementById('listBody');
  const closeBtn=document.getElementById('listClose');
  const clearBtn=document.getElementById('listClear');

  function loadList(){{
    try{{return JSON.parse(localStorage.getItem(LIST_KEY))||{{}};}}catch(e){{return {{}};}}
  }}
  function saveList(l){{
    try{{localStorage.setItem(LIST_KEY,JSON.stringify(l));}}catch(e){{}}
  }}
  function refreshFab(){{
    const list=loadList();
    const n=Object.keys(list).length;
    fabCount.textContent=n;
    headCount.textContent=n;
    fab.classList.toggle('has-items',n>0);
  }}
  function markCards(){{
    const list=loadList();
    document.querySelectorAll('.card[data-name]').forEach(c=>{{
      c.classList.toggle('in-list',!!list[c.dataset.name]);
    }});
  }}
  function renderList(){{
    const list=loadList();
    const keys=Object.keys(list).sort((a,b)=>(list[b].added||0)-(list[a].added||0));
    if(!keys.length){{
      panelBody.innerHTML='<div class="list-empty">Seznam je prazen. Pritisni + na izdelku, da ga dodaš.</div>';
      return;
    }}
    panelBody.innerHTML=keys.map(k=>{{
      const it=list[k];
      const img=it.img?'<img src="'+escapeAttr(it.img)+'" alt="">':'';
      return '<div class="list-row" data-key="'+escapeAttr(k)+'">'
        +'<div class="li-img">'+img+'</div>'
        +'<a class="li-name" href="'+escapeAttr(it.url||'#')+'" target="_blank" rel="noopener">'+escapeHtml(it.name||k)+'</a>'
        +'<div class="li-price">'+escapeHtml(it.price||'')+'</div>'
        +'<button class="li-remove" type="button" aria-label="Odstrani">×</button>'
        +'</div>';
    }}).join('');
  }}
  function escapeHtml(s){{return String(s).replace(/[&<>"']/g,c=>({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[c]));}}
  function escapeAttr(s){{return escapeHtml(s);}}

  function toggleItem(card){{
    const key=card.dataset.name;
    if(!key)return;
    const list=loadList();
    if(list[key]){{
      delete list[key];
    }}else{{
      const nameEl=card.querySelector('.card-name');
      const priceEl=card.querySelector('.new-price');
      const imgEl=card.querySelector('.card-img img');
      list[key]={{
        name:nameEl?nameEl.textContent:key,
        price:priceEl?priceEl.textContent:'',
        url:card.href||'',
        img:imgEl?imgEl.getAttribute('src')||'':'',
        added:Date.now(),
      }};
    }}
    saveList(list);
    refreshFab();
    markCards();
    if(panel.classList.contains('open'))renderList();
  }}

  document.querySelectorAll('.add-btn').forEach(btn=>{{
    const handler=e=>{{
      e.preventDefault();
      e.stopPropagation();
      const card=btn.closest('.card');
      if(card)toggleItem(card);
    }};
    btn.addEventListener('click',handler);
    btn.addEventListener('keydown',e=>{{
      if(e.key==='Enter'||e.key===' ')handler(e);
    }});
  }});

  fab.addEventListener('click',()=>{{
    renderList();
    panel.classList.add('open');
  }});
  closeBtn.addEventListener('click',()=>panel.classList.remove('open'));
  panel.addEventListener('click',e=>{{if(e.target===panel)panel.classList.remove('open');}});
  clearBtn.addEventListener('click',()=>{{
    if(!confirm('Počistim cel seznam?'))return;
    saveList({{}});
    refreshFab();
    markCards();
    renderList();
  }});
  panelBody.addEventListener('click',e=>{{
    const rm=e.target.closest('.li-remove');
    if(!rm)return;
    const row=rm.closest('.list-row');
    const key=row&&row.dataset.key;
    if(!key)return;
    const list=loadList();
    delete list[key];
    saveList(list);
    refreshFab();
    markCards();
    renderList();
  }});

  /* On load: ask whether to remove items that are no longer on discount. */
  function checkOffDiscount(){{
    const list=loadList();
    const keys=Object.keys(list);
    if(!keys.length)return;
    const onSale=new Set();
    document.querySelectorAll('.card[data-name]').forEach(c=>onSale.add(c.dataset.name));
    let changed=false;
    for(const k of keys){{
      if(onSale.has(k))continue;
      const label=list[k].name||k;
      if(confirm('"'+label+'" ni več v akciji.\\nOdstranim s seznama?')){{
        delete list[k];
        changed=true;
      }}
    }}
    if(changed)saveList(list);
  }}

  refreshFab();
  markCards();
  /* Defer the prompt so the page paints first. */
  setTimeout(checkOffDiscount,400);
}})();
</script>
</body></html>""", encoding="utf-8")


def _esc(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;"))


def _fmt(x) -> str:
    return f"{x:.2f} &euro;" if x else ""


if __name__ == "__main__":
    raise SystemExit(main())
