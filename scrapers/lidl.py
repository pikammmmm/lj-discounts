"""Lidl Slovenia public offer pages.

Lidl embeds product data as JSON in `data-grid-data` attributes on offer pages.
We collect the currently linked offer pages from the public "Ponudba" hub and
turn those product payloads into Offer rows.
"""
from __future__ import annotations

import json

import requests
from bs4 import BeautifulSoup

from models import Offer
from stores import STORES
from .common import HEADERS, absolute_url, parse_price, unix_date

NAME = "Lidl"
BASE = "https://www.lidl.si"
HUB = f"{BASE}/c/ponudba"
MAX_PAGES = 12


def fetch() -> list[Offer]:
    session = requests.Session()
    session.headers.update(HEADERS)

    page_urls = _offer_pages(session)
    offers: list[Offer] = []
    seen: set[tuple[str, float]] = set()

    for url in page_urls:
        response = session.get(url, timeout=20)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        for node in soup.select("[data-grid-data]"):
            offer = _payload_to_offer(node.get("data-grid-data"), url)
            if not offer:
                continue
            key = (offer.source_url, offer.discount_price)
            if key in seen:
                continue
            seen.add(key)
            offers.append(offer)

    return offers


def _offer_pages(session: requests.Session) -> list[str]:
    response = session.get(HUB, timeout=20)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    urls = [HUB]
    for link in soup.select('a[href*="/c/"]'):
        href = link.get("href", "")
        if not href:
            continue
        if not any(token in href for token in ("super-ponudba", "znizujemo-redne-cene", "cvetlicarna")):
            continue
        url = absolute_url(BASE, href)
        if url not in urls:
            urls.append(url)
        if len(urls) >= MAX_PAGES:
            break
    return urls


def _payload_to_offer(raw: str | None, page_url: str) -> Offer | None:
    if not raw:
        return None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None

    price_data = data.get("price") or {}
    discount_price = parse_price(price_data.get("price"))
    if not discount_price:
        return None

    regular_price = parse_price(price_data.get("oldPrice"))
    discount = price_data.get("discount") or {}
    deleted_price = parse_price(discount.get("deletedPrice"))
    if (not regular_price or regular_price <= discount_price) and deleted_price:
        regular_price = deleted_price

    product = data.get("fullTitle") or data.get("title")
    if not product:
        return None

    source_url = absolute_url(BASE, data.get("canonicalUrl") or data.get("canonicalPath") or page_url)
    base_price = price_data.get("basePrice") or {}
    packaging = price_data.get("packaging") or {}
    category = data.get("listName") or data.get("category")
    keyfacts = data.get("keyfacts") or {}

    return Offer(
        chain=NAME,
        store_hint=STORES[NAME],
        product=product,
        category=category,
        category1=keyfacts.get("analyticsCategory") or data.get("category"),
        regular_price=regular_price if regular_price and regular_price > discount_price else None,
        discount_price=discount_price,
        unit=packaging.get("text") or base_price.get("text"),
        unit_price=None,
        valid_from=unix_date(data.get("storeStartDate")),
        valid_to=unix_date(data.get("storeEndDate")),
        source_url=source_url,
        image_path=data.get("image") or (data.get("imageList") or [None])[0],
    )
