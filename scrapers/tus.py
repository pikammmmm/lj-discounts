"""Tuš Slovenia public offer pages."""
from __future__ import annotations

import re

import requests
from bs4 import BeautifulSoup

from models import Offer
from stores import STORES
from .common import HEADERS, absolute_url, clean_text, parse_price

NAME = "Tuš"
BASE = "https://www.tus.si"
URLS = [
    f"{BASE}/aktualno/akcijska-ponudba/",
    f"{BASE}/aktualno/akcijska-ponudba/aktualno-iz-kataloga/",
    f"{BASE}/aktualno/akcijska-ponudba/trajno-znizano/",
    f"{BASE}/aktualno/akcijska-ponudba/mojih-10/",
    f"{BASE}/aktualno/akcijska-ponudba/vec-je-ceneje/",
]


def fetch() -> list[Offer]:
    session = requests.Session()
    session.headers.update(HEADERS)

    offers: list[Offer] = []
    seen: set[tuple[str, str]] = set()
    for url in URLS:
        response = session.get(url, timeout=25)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        for card in soup.select(".card.card-product.product"):
            offer = _card_to_offer(card, url)
            if not offer:
                continue
            key = (offer.source_url, offer.product)
            if key in seen:
                continue
            seen.add(key)
            offers.append(offer)
    return offers


def _card_to_offer(card, page_url: str) -> Offer | None:
    link = card.select_one("h3 a[href]") or card.select_one("a[href]")
    title = clean_text(link.get_text(" ", strip=True) if link else _text(card, "h3"))
    discount_price = parse_price(_text(card, ".price"))
    regular_price = _regular_price(card)

    # Some "Mojih 10" items only publish a percentage off the daily price. The
    # current schema needs a numeric discount price, so keep those out.
    if not title or not discount_price:
        return None

    image = card.select_one("img.thumbnail") or card.select_one("img")
    image_url = None
    if image:
        image_url = image.get("data-src") or image.get("data-lazy-src") or image.get("src")

    return Offer(
        chain=NAME,
        store_hint=STORES[NAME],
        product=title,
        category=_page_label(page_url),
        category1="Tuš",
        regular_price=regular_price if regular_price and regular_price > discount_price else None,
        discount_price=discount_price,
        unit=None,
        unit_price=None,
        valid_from=None,
        valid_to=None,
        source_url=absolute_url(BASE, link.get("href") if link else page_url),
        image_path=absolute_url(BASE, image_url) if image_url else None,
    )


def _regular_price(card) -> float | None:
    candidates = [
        _text(card, ".price-regular"),
        _text(card, "s"),
        _text(card, ".regular-price"),
    ]
    for value in candidates:
        price = parse_price(value)
        if price:
            return price

    # Tuš often writes "Redna cena: 5,79 €" in the regular-price copy.
    text = clean_text(card.get_text(" ", strip=True))
    match = re.search(r"Redna cena:\s*(\d{1,4}(?:[.,]\d{1,2})?)", text, re.I)
    return parse_price(match.group(1)) if match else None


def _page_label(url: str) -> str:
    if "aktualno-iz-kataloga" in url:
        return "Aktualno iz kataloga"
    if "trajno-znizano" in url:
        return "Trajno znižano"
    if "mojih-10" in url:
        return "Mojih 10"
    if "vec-je-ceneje" in url:
        return "Več je ceneje"
    return "Akcijska ponudba"


def _text(root, selector: str) -> str:
    node = root.select_one(selector)
    return node.get_text(" ", strip=True) if node else ""
