"""dm Slovenia clearance offers from the public product-search API."""
from __future__ import annotations

import time

import requests

from models import Offer
from stores import STORES
from .common import HEADERS, absolute_url, parse_price

NAME = "dm"
BASE = "https://www.dm.si"
API = "https://product-search.services.dmtech.com/si/search/static"
FILTER = "popularFacet:Odprodaja"
PAGE_SIZE = 48
MAX_PAGES = 10


def fetch() -> list[Offer]:
    session = requests.Session()
    session.headers.update({
        **HEADERS,
        "Accept": "application/json",
        # The web client sends a numeric search token. The API accepts a simple
        # request-local value, so no login or private token is needed.
        "x-dm-product-search-token": str(int(time.time() * 1000) * 27),
    })

    offers: list[Offer] = []
    seen: set[int] = set()
    for page in range(MAX_PAGES):
        response = session.get(
            API,
            params={
                "query": "",
                "pageSize": PAGE_SIZE,
                "currentPage": page,
                "sort": "editorial_relevance",
                "enablePharmacy": "false",
                "filters": FILTER,
            },
            timeout=25,
        )
        response.raise_for_status()
        payload = response.json()
        for product in payload.get("products") or []:
            offer = _product_to_offer(product)
            if not offer:
                continue
            key = int(product.get("dan") or product.get("gtin") or 0)
            if key and key in seen:
                continue
            if key:
                seen.add(key)
            offers.append(offer)

        if page + 1 >= int(payload.get("totalPages") or 0):
            break
    return offers


def _product_to_offer(product: dict) -> Offer | None:
    tile = product.get("tileData") or {}
    price_box = tile.get("price") or {}
    price = price_box.get("price") or {}
    current = parse_price((price.get("current") or {}).get("value"))
    previous = parse_price((price.get("previous") or {}).get("value"))
    if not current:
        return None

    title = product.get("title") or (tile.get("title") or {}).get("tileHeadline")
    if not title:
        return None
    brand = product.get("brandName") or ((tile.get("brand") or {}).get("name"))
    product_name = f"{brand} {title}".strip() if brand and brand not in title else title
    tracking = tile.get("trackingData") or {}
    categories = tracking.get("categories") or []
    images = tile.get("images") or []

    return Offer(
        chain=NAME,
        store_hint=STORES[NAME],
        product=product_name,
        category=categories[0] if categories else "Odprodaja",
        category1="dm",
        regular_price=previous if previous and previous > current else None,
        discount_price=current,
        unit=_unit(tile),
        unit_price=None,
        valid_from=None,
        valid_to=None,
        source_url=absolute_url(BASE, tile.get("self") or f"/search?query={product.get('dan') or ''}"),
        image_path=_image_url(images),
    )


def _unit(tile: dict) -> str | None:
    infos = tile.get("tileInfos") or []
    return infos[0] if infos else None


def _image_url(images: list[dict]) -> str | None:
    for image in images:
        url = image.get("tileSrc") or image.get("src")
        if url:
            return url
    return None
