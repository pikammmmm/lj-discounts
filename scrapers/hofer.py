"""Hofer Slovenia reduced regular prices page."""
from __future__ import annotations

import requests
from bs4 import BeautifulSoup

from models import Offer
from stores import STORES
from .common import HEADERS, absolute_url, clean_text, parse_price

NAME = "Hofer"
BASE = "https://www.hofer.si"
URL = f"{BASE}/izdelki/vse-spuscene-cene/k/1588161418378360"


def fetch() -> list[Offer]:
    response = requests.get(URL, headers=HEADERS, timeout=25)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    offers: list[Offer] = []
    seen: set[str] = set()
    for tile in soup.select(".product-tile"):
        offer = _tile_to_offer(tile)
        if not offer or offer.source_url in seen:
            continue
        seen.add(offer.source_url)
        offers.append(offer)
    return offers


def _tile_to_offer(tile) -> Offer | None:
    name = clean_text(_text(tile, '[data-test="product-tile__name"]'))
    if not name:
        name = clean_text(tile.get("title"))
    price = parse_price(_text(tile, '[data-test="product-tile__price"]'))
    if not name or not price:
        return None

    brand = clean_text(_text(tile, '[data-test="product-tile__brandname"]'))
    unit = clean_text(_text(tile, '[data-test="product-tile__unit-of-measurement"]'))
    comparison = clean_text(_text(tile, '[data-test="product-tile__comparison-price"]'))
    product = f"{brand} {name}".strip() if brand else name

    link = tile.select_one('a[href*="/izdelek/"]')
    image = tile.select_one("img[src]")
    source_url = absolute_url(BASE, link.get("href") if link else URL)

    return Offer(
        chain=NAME,
        store_hint=STORES[NAME],
        product=product,
        category="Spuščene redne cene",
        category1="Hofer",
        regular_price=None,
        discount_price=price,
        unit=unit or comparison or None,
        unit_price=None,
        valid_from=None,
        valid_to=None,
        source_url=source_url,
        image_path=image.get("src") if image else None,
    )


def _text(root, selector: str) -> str:
    node = root.select_one(selector)
    return node.get_text(" ", strip=True) if node else ""
