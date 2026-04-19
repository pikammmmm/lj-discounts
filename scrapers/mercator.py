"""Mercator — JSON API at mercatoronline.si/products/browseProducts/getProducts.

Fetches all discounted products from the Rudnik distribution center catalog.
Sets the logistic center to HM LJUBLJANA RUDNIK (id=30) so the API returns
the correct product assortment, then pages through all items matching the
discount marker filter (~3000 items).
"""
from __future__ import annotations

from datetime import date

import requests

from models import Offer
from stores import STORES

NAME = "Mercator"
API = "https://mercatoronline.si/products/browseProducts/getProducts"
SET_DC_URL = "https://mercatoronline.si/products/local_assortment/ajax_set_logistic_center"
HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "X-Requested-With": "XMLHttpRequest",
}
PAGE_SIZE = 200
MAX_PAGES = 50

# Logistic center for HM LJUBLJANA RUDNIK (Supernova Rudnik area)
RUDNIK_DC_ID = "30"
RUDNIK_DC_CODE = "17788"

# All discount marker IDs used by mercatoronline.si "Ceneje vsak dan" filter
DISCOUNT_MARKERS = "1,2,3,4,5,6,10,11,15,16,18,100,103,109,113,114,115,126,101,108,110,111,104,105,106,112"


def _product_to_offer(p: dict) -> Offer | None:
    """Convert a single API product dict to an Offer, or None if not on sale."""
    pd = p.get("data", {})
    pname = pd.get("name", "")
    if not pname:
        return None

    np = _f(pd.get("normal_price"))
    cp = _f(pd.get("current_price"))
    discounts = pd.get("discounts", [])

    # Method 1: explicit discount entry with a real discount_price
    if discounts:
        dd = discounts[0]
        dp = _f(dd.get("discount_price"))
        actual_price = dp or cp
        if not actual_price or actual_price <= 0:
            return None
        regular = np if np and np > actual_price else (cp if cp and cp > actual_price else np)
        vto = _parse_date(dd.get("valid_to", ""))
    # Method 2: current_price < normal_price (on sale but no discount entry)
    elif np and cp and cp < np:
        actual_price = cp
        regular = np
        vto = None
    else:
        return None

    if not actual_price or actual_price <= 0:
        return None

    return Offer(
        chain=NAME,
        store_hint=STORES[NAME],
        product=pname,
        category=pd.get("category2") or pd.get("category1"),
        category1=pd.get("category1"),
        regular_price=regular,
        discount_price=actual_price,
        unit=pd.get("price_per_unit_base"),
        unit_price=_f(pd.get("price_per_unit")),
        valid_from=None,
        valid_to=vto,
        source_url="https://mercatoronline.si" + p.get("url", "/brskaj"),
        image_path=p.get("mainImageSrc"),
    )


def fetch() -> list[Offer]:
    session = requests.Session()
    session.headers.update(HEADERS)
    # Need a session cookie
    session.get("https://mercatoronline.si/", timeout=15)

    # Set distribution center to Rudnik — this determines the product assortment
    session.post(SET_DC_URL, data={
        "logCenterCode": RUDNIK_DC_CODE,
        "logCenterId": RUDNIK_DC_ID,
        "removeProducts": "false",
    }, timeout=15)

    offers: list[Offer] = []
    seen_products: set[str] = set()

    # Page through all discounted products using the discount marker filter.
    # The API uses offset=page_number, from=item_offset (not the same thing).
    for page_num in range(MAX_PAGES):
        r = session.get(API, params={
            "limit": PAGE_SIZE,
            "offset": page_num,
            "from": page_num * PAGE_SIZE,
            "filterData[discounts]": DISCOUNT_MARKERS,
        }, timeout=20)
        r.raise_for_status()
        data = r.json()
        products = [p for p in data.get("products", []) if p.get("type") == "product"]
        if not products:
            break
        for p in products:
            pname = p.get("data", {}).get("name", "")
            if not pname or pname in seen_products:
                continue
            offer = _product_to_offer(p)
            if offer:
                seen_products.add(pname)
                offers.append(offer)

    return offers


def _f(v) -> float | None:
    try:
        x = float(v)
        return x if x > 0 else None
    except (TypeError, ValueError):
        return None


def _parse_date(s: str) -> date | None:
    if not s or len(s) < 8:
        return None
    try:
        return date(int(s[:4]), int(s[4:6]), int(s[6:8]))
    except (ValueError, IndexError):
        return None
