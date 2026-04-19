"""Heuristic grocery filter for Slovenian catalog text.

We don't have clean category tags from the PDFs, so we classify by keyword.
Approach: reject rows that are obviously non-food or pure template noise;
accept everything else. Tuned permissively — better to let a condiment
slip through than to drop real food.
"""
from __future__ import annotations

import re

NON_FOOD = {
    # clothing & textile
    "natikač", "copat", "čevelj", "majica", "hlače", "nogavic", "oblačil",
    "brisač", "rjuh", "odej", "posteljnin", "srajc", "pulover", "jopic",
    "pižam", "kopalk", "bundi", "jakn",
    # home / appliances / tools
    "sesaln", "pralni stroj", "pomivaln", "mikrovalov", "hladiln", "pečic",
    "likaln", "tostrer", "kuhinjsk aparat", "orodj", "vrtalnik", "kosilnic",
    "škarje", "nož set", "posod", "lonec", "ponev", "krožnik", "skodelic",
    # garden / pets / diy
    "cvet", "sadik", "lonček za rože", "vrtn", "bazen", "ležalnik",
    "pesek", "hran za pse", "hran za mačke", "pesja", "mačja", "ptič",
    # cosmetics / hygiene / baby
    "šampon", "balzam za lase", "tuš gel", "gel za tušir", "krem za obraz",
    "zobn", "parfum", "deodorant", "vatiran", "plenič", "tamponi", "vložki",
    "maskar", "šmink", "lak za nohte", "britvic", "brivnik",
    # electronics / toys / media
    "televizor", " tv ", "telefon", "kabel", "baterij", "žarnic", "usb",
    "slušalk", "zvočnik", "igrač", "lego", "kolo ", "skiro",
    # misc
    "sveč", "dežnik", "nakit", "uhan", "prstan", "verižic", "parket",
    "barv za ", "lak za les", "plošč s premaz", "premaz", "gobic",
    "čistil", "detergent", "mehčalec", "osvežilec",
    "cedilo", "ponev", "kozic", "lonec", "skleda", "krožnik", "pribor",
    "rezalnik", "lupilec", "strgalo", "pekač", "podstavek", "servet",
    "vrečk za smeti", "folij za živila", "alu folij",
}

TEMPLATE_NOISE_RE = re.compile(
    r"^(?:pc\s*30|ceneje|cena za|redna cena|znižan|od od|različn|izbran)",
    re.I,
)
# rows like "189", "1449", "od od"
MOSTLY_JUNK_RE = re.compile(r"^[\d\s.,:€%/\-]+$")


def is_grocery(product: str) -> bool:
    if not product or len(product.strip()) < 3:
        return False
    p = product.lower().strip()
    if MOSTLY_JUNK_RE.match(p):
        return False
    if TEMPLATE_NOISE_RE.match(p):
        return False
    for kw in NON_FOOD:
        if kw in p:
            return False
    return True
