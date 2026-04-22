"""Eurospin Slovenia public promotions page."""
from __future__ import annotations

import re

import requests
from bs4 import BeautifulSoup

from models import Offer
from stores import STORES
from .common import HEADERS, clean_text, parse_price, parse_slovenian_range

NAME = "Eurospin"
URL = "https://www.eurospin.si/akcije/"


def fetch() -> list[Offer]:
    response = requests.get(URL, headers=HEADERS, timeout=25)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    offers: list[Offer] = []
    seen: set[str] = set()
    for item in soup.select(".sn_promo_grid_item"):
        offer = _item_to_offer(item)
        if not offer or offer.source_url in seen:
            continue
        seen.add(offer.source_url)
        offers.append(offer)
    return offers


def _item_to_offer(item) -> Offer | None:
    title = clean_text(_text(item, ".i_title"))
    brand = clean_text(_text(item, ".i_brand"))
    discounted = parse_price(_text(item, '.i_price [itemprop="price"]'))
    if not title or not discounted:
        return None

    price_box = item.select_one(".i_price")
    prices = _prices(price_box.get_text(" ", strip=True) if price_box else "")
    regular = prices[0] if prices and prices[0] > discounted else None
    valid_from, valid_to = parse_slovenian_range(_text(item, ".date_current_promo"))
    image = item.select_one(".i_image[src]")
    unit = clean_text(_text(item, ".i_price_info"))
    product = f"{brand} {title}".strip() if brand else title

    return Offer(
        chain=NAME,
        store_hint=STORES[NAME],
        product=product,
        category="Akcija",
        category1="Eurospin",
        regular_price=regular,
        discount_price=discounted,
        unit=unit or None,
        unit_price=None,
        valid_from=valid_from,
        valid_to=valid_to,
        source_url=f"{URL}#{_slug(product)}",
        image_path=image.get("src") if image else None,
    )


def _prices(value: str) -> list[float]:
    found: list[float] = []
    for match in re.finditer(r"\d{1,4}(?:[,.]\d{1,2})?", value):
        price = parse_price(match.group(0))
        if price is not None:
            found.append(price)
    return found


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")[:80]


def _text(root, selector: str) -> str:
    node = root.select_one(selector)
    return node.get_text(" ", strip=True) if node else ""
