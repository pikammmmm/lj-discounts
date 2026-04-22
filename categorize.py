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


# Keyword -> Mercator-style category1 key (matches run.py CATEGORY_LABELS).
# Order matters: first match wins, so narrower keywords go first.
_CATEGORY_RULES: list[tuple[str, tuple[str, ...]]] = [
    ("SVEŽ KRUH IN PECIVO", (
        "kruh", "štručk", "pecivo", "žemlj", "rogljič", "bageta", "burek",
        "pita", "tortilj", "pizza testo", "testo za", "krof",
    )),
    ("MLEKO, JAJCA IN MLEČNI IZDELKI", (
        "mleko", "jogurt", "kefir", "skuta", "maslo", "margarin",
        "smetana", "kajmak", "sirni namaz", "sir,", "sir ", "edamec", "gauda",
        "gouda", "mozzarella", "feta", "parmezan", "jajca", "jajčk", "puding",
        "mlečn", "mascarpone",
    )),
    ("MESO, MESNI IZDELKI IN RIBE", (
        "piščanec", "piščančj", "puranj", "govedin", "goved", "svinjsk",
        "mleto meso", "klobas", "hrenovk", "salam", "paštet", "šunk",
        "pršut", "slanin", "file ", "ocvrt", "tuna", "riba", "losos",
        "skuš", "sardin", "inčun", "škamp", "kozic", "hobotnic",
    )),
    ("SADJE IN ZELENJAVA", (
        "jabolk", "banan", "pomarančn", "citron", "limone", "mandarin",
        "grenivk", "ananas", "grozdj", "jagode", "borovnic", "maline",
        "češnje", "hruške", "breskv", "marelice", "slive", "kivi", "lubenic",
        "melone", "paradižnik", "kumar", "solat", "špinač", "korenček",
        "krompir", "čebul", "česen", "paprik", "zelje", "bučke", "cvetača",
        "brokoli", "gob ", "gobe", "avokad", "ingver",
    )),
    ("PIJAČE", (
        "pivo", "radler", "vino", "cviček", "šampanj", "prosek", "prosecco",
        "viski", "whiskey", "gin", "vodka", "tequila", "rum", "liker",
        "brinjevec", "šnops", "šnopc", "cider", "aperitiv",
        "sok", "nektar", "limonada", "gazirana", "cola", "fanta", "sprite",
        "tonic", "ledeni čaj", "energijska pijača", "energy drink",
        "mineralna voda", "voda,", "negazirana", "slatina",
    )),
    ("VSE ZA ZAJTRK", (
        "kav ", "kava,", "kave ", "kava", "nescafe", "nespresso", "čaj ", "čaj,",
        "čajn", "čokolino", "kosmič", "musli", "granola", "čokoladni namaz",
        "nutella", "medi ", "med ", "marmelad", "džem",
    )),
    ("ČOKOLADA IN DRUGI SLADKI PROGRAM", (
        "čokolad", "milka", "toblerone", "kinder", "m&m", "snickers",
        "bonbon", "lizik", "gumijasti bonbon", "žele bonbon", "bonboni",
        "piškot", "keks", "rogljič čokoladn", "oblat", "napolitank",
        "čoko ", "praline", "sladoled",
    )),
    ("SLANI PRIGRIZKI IN APERITIVI (JEDI)", (
        "čips", "smoki", "krekerj", "slanin krekerj", "prestec", "pokovk",
        "popcorn", "oreščki", "arašid", "mandlji", "lešnik", "orehi",
        "indijski oreh", "pistacij", "sončnič seme",
    )),
    ("TESTENINE, JUHE, RIŽ IN OMAKE", (
        "testenin", "špageti", "makaron", "penne", "fusili", "tagliatelle",
        "lazanj", "njoki", "riž ", "riž,", "riževi rezanci", "kus kus",
        "juha", "instant juha", "omak", "paradižnikova omak", "pesto",
        "kečap", "majonez", "gorčic", "dresing",
    )),
    ("KONZERVIRANA HRANA", (
        "konzerv", "fižol v pločevink", "koruza v pločevink",
        "tunin filet", "olj v plo", "pašteta v pl", "kisle kumaric",
        "vložen", "ajvar", "mariniran", "oliv",
    )),
    ("ZAMRZNJENA HRANA", (
        "zamrzn", "zamrznjen", "globoko zmrzn", "pomfri", "rib v testen",
        "sladoled", "ledene kocke",
    )),
    ("OSNOVNA ŽIVILA / SHRAMBA", (
        "moka", "sladkor", "sol,", "sol ", "kvas", "olje", "kis",
        "začimb", "popr,", "poper ", "cimet", "vanilija", "pecilni prašek",
    )),
    ("DELIKATESNI IZDELKI IN PRIPRAVLJENE JEDI", (
        "pizza", "lazanje pripravlj", "gotove jedi", "ready meal",
        "burito", "tortilja napolnjen", "salate pripravlj",
    )),
    ("ČISTILA", (
        "detergent", "pralni prašek", "mehčalec", "belo perilo",
        "čistil", "osvežilec zraka", "zob sredstv", "sredstv za pomivanje",
        "wc ", "ariel", "persil", "lenor", "cif", "pronto", "glorix",
    )),
    ("HIGIENA IN LEPOTA", (
        "šampon", "balzam za lase", "tuš gel", "gel za tuširanje",
        "milo,", "milo ", "krem ", "krema za", "telesno mleko", "deodorant",
        "zobna past", "zobna krtač", "ustna voda", "antibakter",
        "britvic", "brivnik", "parfum", "lak za nohte", "šminka", "maskara",
        "papirnat brisač", "toaletni papir", "papirnat robč", "robček",
        "tamponi", "vložki", "plenic", "plenice",
    )),
    ("VSE ZA DOM IN GOSPODINJSTVO", (
        "folij", "vrečke za", "alu folij", "servet", "svečk", "baterij",
        "žarnic", "krpe", "gobic za posod", "pomivaln gobic",
        "pripomočk", "kozarc", "lončk", "pekač", "skleda",
    )),
]


def infer_category1(product: str, fallback: str | None = None) -> str | None:
    """Guess a Mercator-style category1 key from product name.

    Returns the first matching category key, or ``fallback`` if nothing
    matches. Case-insensitive Slovenian keyword match.
    """
    if not product:
        return fallback
    p = product.lower()
    for cat, keywords in _CATEGORY_RULES:
        for kw in keywords:
            if kw in p:
                return cat
    return fallback
