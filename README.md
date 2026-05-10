# LJ Discounts

![Build Windows app](https://github.com/pikammmmm/lj-discounts/actions/workflows/windows.yml/badge.svg)
![Scrape & Deploy](https://github.com/pikammmmm/lj-discounts/actions/workflows/scrape.yml/badge.svg)
[![Latest release](https://img.shields.io/github/v/release/pikammmmm/lj-discounts)](https://github.com/pikammmmm/lj-discounts/releases/latest)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Tracks weekly grocery discounts at **Mercator Hipermarket Rudnik** (Supernova
Ljubljana) and ranks the best deals by percentage off.

**Live site:** https://pikammmmm.github.io/lj-discounts/
*(Rebuilds twice daily at 07:00 and 12:00 Europe/Ljubljana.)*

## Source

Hits Mercator's online assortment API pinned to the Rudnik distribution
center (HM LJUBLJANA RUDNIK, id=30) so the returned products match what's
actually available at the store.

## Install

### Windows — no Python required

Download the latest [`lj-discounts-windows.zip`](https://github.com/pikammmmm/lj-discounts/releases/latest),
unzip, and double-click **`run-lj-discounts.cmd`**. The desktop app window
opens, scrapes, and displays the report. `lj-discounts-cli.exe` is bundled
for scheduled/headless use.

### Android — APK

Grab [`download/lj-discounts.apk`](download/lj-discounts.apk) (also attached
to every tagged [release](https://github.com/pikammmmm/lj-discounts/releases/latest))
and install it — you may need to enable *Install unknown apps* for your
browser. The APK is a tiny WebView shell around the live site that runs
fullscreen with no URL bar, so it always shows the freshest scrape without
going through the Play Store.

To rebuild it locally (Debian/Ubuntu):

```bash
sudo apt-get install -y android-sdk-build-tools smali \
    default-jdk-headless zip curl
./android/build.sh   # writes download/lj-discounts.apk
```

The script fetches `android-34.jar` from a GitHub mirror on first run
(cached under `android/.cache/`) since Debian doesn't ship a recent
`android-sdk-platform-*` package.

The signing keystore at `android/release.keystore` is committed on purpose
(password `ljdiscounts`) so anyone with the repo can sign updates that
existing installs accept. Override `KS_PASS` / `KEY_ALIAS` env vars if you
generate your own.

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
├── scrapers/
│   ├── mercator.py           # Mercator online API scraper
│   └── __init__.py
├── models.py                 # Offer dataclass
├── stores.py                 # physical-store label
├── weird.py                  # hot/suspicious deal flagging
├── categorize.py             # grocery vs non-grocery filter
├── assets/                   # app icon (ICO + PNG) + generator
├── manifest.json             # PWA manifest (served from gh-pages)
├── android/                  # WebView-wrapper APK source (smali + aapt2)
│   ├── AndroidManifest.xml
│   ├── smali/                # MainActivity.smali (Dalvik assembly)
│   ├── res/                  # icons, strings, theme
│   ├── release.keystore      # committed signing key (pass: ljdiscounts)
│   └── build.sh              # apt-only local build
├── download/lj-discounts.apk # latest signed APK (refreshed by android.yml)
├── windows/                  # Windows-only launchers bundled in the exe zip
├── refresh.{bat,ps1,command} # source-run launchers per platform
├── requirements.txt          # scrape-only deps (requests, beautifulsoup4)
├── requirements-windows.txt  # adds pywebview for the desktop app
└── .github/workflows/
    ├── scrape.yml            # daily scrape → gh-pages
    ├── windows.yml           # tag-triggered exe build + release
    └── android.yml           # tag-triggered APK build + release
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
4. **Android APK:** `android.yml` runs `./android/build.sh` on every push to
   `main` that touches `android/**` (also on tag pushes and via *Run
   workflow*). It installs Debian's `android-sdk-build-tools` and `smali`
   packages, fetches `android-34.jar` from a GitHub mirror so the APK
   targets a current Android API (Debian's newest platform jar is API 23,
   which Android 14 rejects), assembles `MainActivity.smali`, links
   resources with `aapt2`, signs with the committed keystore, commits the
   rebuilt `download/lj-discounts.apk` back to `main` (`[skip ci]`-tagged
   so it doesn't loop), and attaches it to tagged releases.

## License

[MIT](LICENSE) © 2026 pikammmmm
