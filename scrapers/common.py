from __future__ import annotations

import re
from datetime import date, datetime
from urllib.parse import urljoin

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
}

PRICE_RE = re.compile(r"(?<!\d)(\d{1,4}(?:[.,]\d{1,2})?)\s*(?:€|EUR)?")


def clean_text(value: str | None) -> str:
    if not value:
        return ""
    return " ".join(value.replace("\xa0", " ").split())


def absolute_url(base: str, maybe_url: str | None) -> str:
    return urljoin(base, maybe_url or "")


def parse_price(value) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value) if value > 0 else None

    text = clean_text(str(value)).replace("€", "").replace("EUR", "").strip()
    match = PRICE_RE.search(text)
    if not match:
        return None
    number = match.group(1).replace(".", "").replace(",", ".")
    try:
        price = float(number)
    except ValueError:
        return None
    return price if price > 0 else None


def parse_slovenian_range(value: str) -> tuple[date | None, date | None]:
    """Parse ranges like '16.04 - 22.04' using the current year."""
    matches = re.findall(r"(\d{1,2})\.\s*(\d{1,2})\.?", value)
    if not matches:
        return None, None

    today = date.today()

    def build(day: str, month: str) -> date | None:
        try:
            candidate = date(today.year, int(month), int(day))
        except ValueError:
            return None
        # Handle year-crossing flyers such as 28.12 - 03.01.
        if candidate.month == 1 and today.month == 12:
            return date(today.year + 1, candidate.month, candidate.day)
        return candidate

    start = build(*matches[0])
    end = build(*matches[-1])
    return start, end


def unix_date(timestamp) -> date | None:
    if not timestamp:
        return None
    try:
        return datetime.fromtimestamp(int(timestamp)).date()
    except (OSError, OverflowError, TypeError, ValueError):
        return None
