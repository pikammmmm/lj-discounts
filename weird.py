"""Flag weird/suspicious offers.

"Weird" means: unusually cheap, suspiciously high discount, likely OCR garbage,
or price that doesn't make sense for the category.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from models import Offer

@dataclass
class Flag:
    offer: Offer
    reason: str
    severity: int  # 1=interesting, 2=weird, 3=probably garbage


def flag_weird(offers: list[Offer]) -> list[Flag]:
    flags: list[Flag] = []
    for o in offers:
        # OCR garbage: product name is mostly symbols/numbers/template text
        alpha = sum(1 for c in o.product if c.isalpha())
        if len(o.product) > 5 and alpha / len(o.product) < 0.4:
            flags.append(Flag(o, "name is mostly junk characters", 3))
            continue
        if re.search(r"(CENEJE\s*){2,}|PC\s*30:|RETSINIM|PPPPP", o.product):
            flags.append(Flag(o, "PDF watermark text in name", 3))
            continue

        # Suspiciously cheap for food
        if o.discount_price < 0.10:
            flags.append(Flag(o, f"only {o.discount_price:.2f}€ — probably a unit price, not real", 3))
            continue

        # Discount over 70% — could be real clearance or bad price parsing
        if o.discount_pct and o.discount_pct > 70:
            flags.append(Flag(o, f"{o.discount_pct:.0f}% off — verify this is real", 2))

        # Discount over 50% — flag as interesting deal
        elif o.discount_pct and o.discount_pct > 50:
            flags.append(Flag(o, f"{o.discount_pct:.0f}% off — great deal if real", 1))

        # Price went UP (negative discount) — data error
        if o.discount_pct and o.discount_pct < 0:
            flags.append(Flag(o, "discount is negative — price went up?", 3))

        # Regular price is suspiciously round (like 0.00 or 99.99)
        if o.regular_price and o.regular_price > 50 and o.discount_price < 5:
            flags.append(Flag(o, f"was {o.regular_price:.2f}€ now {o.discount_price:.2f}€ — 10x drop, verify", 2))

    return flags
