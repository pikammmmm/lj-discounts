from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass
class Offer:
    chain: str
    store_hint: str
    product: str
    category: Optional[str]
    regular_price: Optional[float]
    discount_price: float
    unit: Optional[str]
    unit_price: Optional[float]
    valid_from: Optional[date]
    valid_to: Optional[date]
    source_url: str
    category1: Optional[str] = None
    page: Optional[int] = None
    bbox: Optional[tuple] = None
    image_path: Optional[str] = None

    @property
    def discount_pct(self) -> Optional[float]:
        if self.regular_price and self.regular_price > 0:
            return round(100 * (1 - self.discount_price / self.regular_price), 1)
        return None
