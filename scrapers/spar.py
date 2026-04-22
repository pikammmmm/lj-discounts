"""SPAR Slovenia public offer pages.

online.spar.si streams product data through Next.js/RSC script chunks instead of
rendering classic product cards. This scraper decodes those chunks and extracts
the CatalogProductModel objects from current public "Aktualno" categories.
"""
from __future__ import annotations

import json
import re
from datetime import datetime

import requests
from bs4 import BeautifulSoup

from models import Offer
from stores import STORES
from .common import HEADERS, parse_price

NAME = "SPAR"
BASE = "https://online.spar.si"
PAGES = {
    f"{BASE}/ca/aktualno/S17": "Aktualno",
    f"{BASE}/ca/aktualno/iz-letaka/S17/S17-1": "Iz letaka",
    f"{BASE}/ca/aktualno/iz-letaka-dom-in-prosti-cas/S17/S17-2": "Iz letaka, dom in prosti čas",
    f"{BASE}/ca/aktualno/manj-plastike/S17/S17-4": "Manj plastike",
    f"{BASE}/ca/aktualno/novo-na-nasi-polici/S17/S17-5": "Novo na naši polici",
    f"{BASE}/ca/aktualno/priporocamo/S17/S17-7": "Priporočamo",
    f"{BASE}/ca/aktualno/strokovnjaki-priporocajo/S17/S17-10": "Strokovnjaki priporočajo",
}
PUSH_RE = re.compile(r"self\.__next_f\.push\((.*)\)\s*$", re.S)
REF_RE = re.compile(r"^([0-9a-f]+):(\{.*\}|\[.*\])$")


def fetch() -> list[Offer]:
    session = requests.Session()
    session.headers.update(HEADERS)

    offers: list[Offer] = []
    seen: set[str] = set()
    for url, label in PAGES.items():
        response = session.get(url, timeout=30)
        response.raise_for_status()
        refs = _decode_refs(response.text)
        for ref_id, data in refs.items():
            if not isinstance(data, dict) or data.get("__typename") != "CatalogProductModel":
                continue
            offer = _product_to_offer(data, refs, label, url)
            if not offer:
                continue
            key = data.get("sku") or offer.source_url or ref_id
            if key in seen:
                continue
            seen.add(key)
            offers.append(offer)
    return offers


def _decode_refs(html: str) -> dict[str, object]:
    soup = BeautifulSoup(html, "html.parser")
    chunks: list[str] = []
    for script in soup.find_all("script"):
        text = script.string if script.string is not None else script.get_text()
        if not text or "self.__next_f.push" not in text:
            continue
        match = PUSH_RE.search(text)
        if not match:
            continue
        try:
            payload = json.loads(match.group(1))
        except json.JSONDecodeError:
            continue
        if len(payload) > 1 and isinstance(payload[1], str):
            chunks.append(payload[1])

    refs: dict[str, object] = {}
    for line in "".join(chunks).splitlines():
        match = REF_RE.match(line)
        if not match:
            continue
        try:
            refs[match.group(1)] = json.loads(match.group(2))
        except json.JSONDecodeError:
            continue
    return refs


def _product_to_offer(
    data: dict[str, object],
    refs: dict[str, object],
    category: str,
    page_url: str,
) -> Offer | None:
    product = str(data.get("name") or "").strip()
    regular_price = parse_price(data.get("price"))
    discount_price = _discount_price(data, regular_price)
    if not product or not discount_price:
        return None

    if regular_price and regular_price <= discount_price:
        regular_price = parse_price(data.get("previousPrice"))
    if regular_price and regular_price <= discount_price:
        regular_price = None

    promo = _resolve(refs, data.get("promotion"))
    slug = data.get("slug")

    return Offer(
        chain=NAME,
        store_hint=STORES[NAME],
        product=product,
        category=category,
        category1="SPAR",
        regular_price=regular_price,
        discount_price=discount_price,
        unit=_unit(data),
        unit_price=parse_price(data.get("promotionPricePerSubUnit") or data.get("pricePerSubUnit")),
        valid_from=_date(promo.get("startDateTime") if isinstance(promo, dict) else None),
        valid_to=_date(promo.get("endDateTime") if isinstance(promo, dict) else None),
        source_url=f"{BASE}/p/{slug}" if slug else page_url,
        image_path=_image_url(data, refs),
    )


def _discount_price(data: dict[str, object], regular_price: float | None) -> float | None:
    promo_unit = parse_price(data.get("promotionPricePerSubUnit"))
    regular_unit = parse_price(data.get("pricePerSubUnit"))
    sub_qty = parse_price(data.get("subQty")) or 1.0
    if promo_unit and regular_unit and promo_unit < regular_unit:
        return round(promo_unit * sub_qty, 2)

    previous = parse_price(data.get("previousPrice"))
    current = parse_price(data.get("price"))
    if previous and current and previous > current:
        return current
    return current or regular_price


def _image_url(data: dict[str, object], refs: dict[str, object]) -> str | None:
    images = _resolve(refs, data.get("photosUrl"))
    if isinstance(images, list):
        for image in images:
            if isinstance(image, str) and image.startswith("http"):
                return image
    return None


def _unit(data: dict[str, object]) -> str | None:
    sub_qty = data.get("subQty")
    sub_unit = data.get("subUnit")
    unit = data.get("unit")
    if sub_qty and sub_unit:
        return f"{sub_qty} {sub_unit}"
    return str(unit) if unit else None


def _resolve(refs: dict[str, object], value: object) -> object | None:
    if isinstance(value, str) and value.startswith("$"):
        return refs.get(value[1:])
    return value


def _date(value: str | None):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
    except ValueError:
        return None
