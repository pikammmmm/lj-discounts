"""TEDi Slovenia public product offer pages."""
from __future__ import annotations

import requests
from bs4 import BeautifulSoup

from models import Offer
from stores import STORES
from .common import HEADERS, absolute_url, clean_text, parse_price

NAME = "TEDi"
BASE = "https://www.tedi.com"
HUB = f"{BASE}/sl/ponudba"
MAX_PAGES = 12


def fetch() -> list[Offer]:
    session = requests.Session()
    session.headers.update(HEADERS)
    page_urls = _category_pages(session)

    offers: list[Offer] = []
    seen: set[str] = set()
    for url in page_urls:
        response = session.get(url, timeout=20)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        for panel in soup.select(".product-panel"):
            offer = _panel_to_offer(panel, url)
            if not offer or offer.source_url in seen:
                continue
            seen.add(offer.source_url)
            offers.append(offer)
    return offers


def _category_pages(session: requests.Session) -> list[str]:
    response = session.get(HUB, timeout=20, allow_redirects=True)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    urls = [response.url]
    for link in soup.select('a[href*="/sl/ponudba/"]'):
        href = link.get("href", "")
        if not href or "/podrobnosti/" in href or "/katalogi" in href:
            continue
        url = absolute_url(BASE, href)
        if url not in urls:
            urls.append(url)
        if len(urls) >= MAX_PAGES:
            break
    return urls


def _panel_to_offer(panel, page_url: str) -> Offer | None:
    title = clean_text(_text(panel, ".product-panel__title"))
    more = clean_text(_text(panel, ".product-panel__furtherinformation"))
    price = parse_price(_text(panel, ".product-price"))
    if not title or not price:
        return None

    category = clean_text(_text(panel, ".product-panel__category"))
    product = f"{title} - {more}" if more else title
    link = panel.select_one("a[href]")
    image = panel.select_one("img[src]")

    return Offer(
        chain=NAME,
        store_hint=STORES[NAME],
        product=product,
        category=category or "Ponudba",
        category1="TEDi",
        regular_price=None,
        discount_price=price,
        unit=None,
        unit_price=None,
        valid_from=None,
        valid_to=None,
        source_url=absolute_url(BASE, link.get("href") if link else page_url),
        image_path=absolute_url(BASE, image.get("src")) if image else None,
    )


def _text(root, selector: str) -> str:
    node = root.select_one(selector)
    return node.get_text(" ", strip=True) if node else ""
