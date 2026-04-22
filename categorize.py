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
# Order matters: first match wins in a single pass, so narrower keywords go
# first. Lowercased; matched with plain `in` against lowered product name.
#
# Prefer stems ("čokolad") over full words ("čokolada") to cover declensions.
# Where a bare word would have false positives elsewhere (e.g. "med" inside
# "medicin"), the pattern is padded with a space or comma.
_CATEGORY_RULES: list[tuple[str, tuple[str, ...]]] = [
    # Kids-specific BEFORE hygiene so "otroška zobna pasta" goes to "otroka".
    ("VSE ZA OTROKA", (
        "otroška", "otroški ", "otroška zobn", "otroško ",
        "becutan", "violeta ",
        "plišasta igrač", "plišast igrač", "igrač,", "igrač ", "igrač",
        "lego,", "lego ",
        "presenečenje v škatli", "skrivnostna škatl",
        "avtomobil za", "dinozaver", "robot,", "robot ",
        "tic tac toe", "komplet kock", "škatla s sestav", "sestavljank",
        "žoga za stiska", "voziček za lutk", "lutka,", "lutka ",
        "steklenica za lutko",
    )),
    # Cosmetics / hygiene FIRST after kids — "toaletna voda" (perfume) must
    # not hit "voda" in the drinks rule, "gel za prhanje" must not hit "gel"
    # elsewhere, etc.
    ("HIGIENA IN LEPOTA", (
        "toaletna voda", "eau de", "parfum", "kolonjska voda",
        "meglica za telo", "body mist", "darilni set",
        "gel za prhanje", "gel za tuširanje", "tuš gel", "šampon", "balzam za lase",
        "balzam za ustnice", "maska za lase", "krema za obraz", "krema za roke",
        "krema za telo", "krema za noge", "balzam za noge",
        "telesno mleko", "serum", "piling", "losjon",
        "roll-on", "deodorant", "antiperspirant", "aftershave", "after shave",
        "zobna past", "zobna krtač", "zobna nitk", "ustna voda", "zobna",
        "britvic", "brivnik", "brivn gel", "pena za britje",
        "šminka", "maskara", "puder", "rdečilo", "senčil", "korektor",
        "svinčnik za obrvi", "črtalo za obrvi", "gel za obrvi",
        "set za oblikovanje obrvi", "obrvi",
        "lak za nohte", "odstranjevalec laka", "pilnic za nohte",
        "barva za lase", "lak za lase", "pena za lase", "vosek za lase",
        "milo,", "milo ", "tekoče milo",
        "vlažiln robček", "vlažilni robček", "vlažni robč", "čist robček",
        "razkužil",
        "vložki", "tamponi", "dnevni vložki", "intimna higijena", "intimna nega",
        "plenic", "plenice", "pampers", "huggies",
        "papirnat robč", "papirnat brisač", "toaletni papir", "wc papir",
        "sončna krema", "sunscreen",
        "serviete", "prtički za",
    )),
    ("ČISTILA", (
        "tablete za pomivaln", "tablet za pomival", "kapsul za pralni",
        "tekočina za odmaš", "gel za strojno pomivanje",
        "sredstv za pomivan", "sredstvo za pomivanje posode",
        "pralni prašek", "prašek za perilo", "mehčalec", "detergent",
        "belo perilo", "kapsul za perilo", "čistil",
        "osvežilec", "bref", "glorix", "cif", "ajax", "pronto",
        "ariel", "persil", "lenor", "vanish", "sidol", "ata",
        "milo za pomivanje", "gobic za posod", "pomivaln gobic",
        "abrazivne gobic", "gospodinj gobic", "krpe za čiščenje",
        "wc ", "za wc", "za kopalnico", "za kuhinjo",
        "čistilne krpe", "talne krpe", "gobic",
    )),
    # Bread & baked goods
    ("SVEŽ KRUH IN PECIVO", (
        "kruh", "štručk", "pecivo", "žemlj", "rogljič", "bageta", "burek",
        "pita", "tortilj", "pizza testo", "testo za", "krof",
        "lepinja", "pletenka", "toast", "drobtine", "krušne drobtine",
        "listnato testo", "vlečeno testo",
    )),
    # Dairy & eggs (note: ovsen napitek routed to PIJAČE above)
    ("MLEKO, JAJCA IN MLEČNI IZDELKI", (
        "mleko", "sojin napitek", "mandljev napitek",
        "jogurt", "kefir", "skuta", "maslo", "margarin",
        "smetana", "krema za stepanje", "kajmak", "sirni namaz",
        "sir,", "sir ", "sirov narezek", "nizozemska gavda",
        "edamec", "gauda", "gavda", "gouda", "mozzarella", "feta", "parmezan",
        "mascarpone", "ricotta", "čedar", "emental", "topljen sir",
        "maasdamer", "skyr",
        "jajca", "jajčk",
        "puding", "mlečn",
    )),
    # Meat & fish
    ("MESO, MESNI IZDELKI IN RIBE", (
        "piščanec", "piščančj", "piščančj", "puranj", "puran", "račk",
        "govedin", "goved", "svinjsk", "teletin", "jagnj",
        "mleto meso", "mleto mešano", "čevapčič", "pleskavic", "mesni pripravek",
        "klobas", "hrenovk", "salam", "paštet", "šunk", "pršut",
        "slanin", "panceta", "špeh",
        "ribje palčk", "ribji file", "ribje", "tunin zrezek",
        "tuna", "losos", "skuš", "sardin",
        "inčun", "škamp", "kozic", "hobotnic", "lignji", "polž",
        "fileti",
    )),
    # Fruit & vegetables (fresh produce, not canned)
    ("SADJE IN ZELENJAVA", (
        "jabolk", "jabolčna kaša", "banan", "pomaranč", "citron", "limone",
        "mandarin",
        "grenivk", "ananas", "grozdj", "jagode", "borovnic", "maline",
        "češnje", "hruške", "breskv", "marelice", "slive", "kivi", "lubenic",
        "melone", "mango", "papaja", "granatno jabolk",
        "paradižnik", "kumar", "solat", "špinač", "korenček",
        "krompir", "čebul", "česen", "paprik", "zelje", "bučke", "cvetača",
        "brokoli", "gob ", "gobe", "šampinjoni", "avokad", "ingver", "rukola",
        "radič", "koleraba", "redkvice", "rdeč repa",
        "beluš", "šparglj",
    )),
    # Drinks
    ("PIJAČE", (
        "pivo", "radler", "ale", "stout", "lager",
        "vino", "cviček", "teran", "refošk", "šampanj", "prosek", "prosecco",
        "penina", "frizzante", "fruitysecco", "secco",
        "viski", "whiskey", "gin", "vodka", "tequila", "rum", "liker",
        "brinjevec", "šnops", "šnopc", "žganje", "cider", "aperitiv",
        "hugo", "aperol", "campari", "borovničevec",
        "sok", "nektar", "limonada", "gazirana", "cola", "coca", "cocka", "fanta", "sprite",
        "pepsi", "schweppes", "tonic", "tonik", "bitter lemon",
        "ledeni čaj", "ice tea", "cedevita", "energijska pijača", "energy drink",
        "red bull", "monster",
        "mineralna voda", "gazirana voda", "negazirana voda", "slatina",
        "radenska", "jamnica", "pfanner", "malt",
        "pijača,", "pijača ", "napitek,", "napitek ", "napitek",
        "ovsen napitek", "ovseni napitek",
        "cocktail", "koktejl", "koktajl", "cocta",
        "rioja", "toscana", "amarone", "chianti", "merlot", "cabernet",
        "riesling", "sauvignon", "chardonnay", "grande", "cremant",
    )),
    # Breakfast — coffee, tea, cereal, spreads
    ("VSE ZA ZAJTRK", (
        "kava,", "kava ", "kave ", "kave,", "kavne kapsul", "kavni napitek",
        "mleta kava", "instant kava", "nescafe", "nespresso", "tassimo",
        "čaj,", "čaj ", "čajn", "čajna mešan",
        "kosmič", "ovseni kosmič", "musli", "granola", "corn flakes",
        "čokolino", "čokoladni namaz", "nutella", "lešnikov namaz",
        "arašidov maslo", "med,", "med ", "medi ",
        "marmelad", "džem", "konfitur",
    )),
    # Sweets, chocolate, ice cream, cookies
    ("ČOKOLADA IN DRUGI SLADKI PROGRAM", (
        "čokolad", "milka", "toblerone", "kinder", "m&m", "snickers", "twix",
        "mars,", "bounty",
        "bonbon", "bombonjer", "lizik", "gumijasti bonbon", "žele bonbon", "karamele",
        "piškot", "keks", "oblat", "napolitank", "wafer", "biskvit",
        "čoko ", "praline", "truffle", "sladoled", "čokoladno jajc",
        "rezine farciti", "rezine s kakav", "kakavov krem", "kakav,",
        "benquick", "cacao",
        "bigne",
    )),
    # Savoury snacks
    ("SLANI PRIGRIZKI IN APERITIVI (JEDI)", (
        "čips", "smoki", "flips", "palčk slanin", "krekerj", "pretzel", "prestec",
        "pokovk", "popcorn", "oreščki", "arašid", "mandlji", "lešnik", "orehi",
        "orehova jedrc", "indijski oreh", "pistacij",
        "sončnič seme", "sončnična sem", "bučnic", "bučn seme",
        "sezam", "lan seme", "chia seme",
        "slan prigrizek", "slani prigrizek", "aperitiv",
        "prigrizek iz", "ploščic", "energijska ploščic", "proteinsk ploščic",
    )),
    # Pasta, rice, sauces, soups
    ("TESTENINE, JUHE, RIŽ IN OMAKE", (
        "testenin", "špageti", "makaron", "penne", "peresniki", "fusili",
        "tagliatelle", "lazanj", "njoki", "polžki", "rigatoni",
        "riž,", "riž ", "riževi rezanci", "kus kus", "bulgur", "kvinoja", "quinoa",
        "juha,", "juha ", "instant juha", "goveja juha", "piščančja juha",
        "omak", "paradižnikova omak", "pesto", "kečap", "majonez", "gorčic",
        "dresing", "bešamel",
    )),
    # Canned / preserved
    ("KONZERVIRANA HRANA", (
        "konzerv", "pločevink",
        "tunin filet", "sardin v olj", "olj v plo",
        "kisl kumaric", "vložen", "ajvar", "lutenica", "mariniran",
        "oliv", "kaper",
        "fižol v pločevink", "koruza v pločevink", "čičerika v pločevink",
        "tunin", "tunina z", "tunina s",
        "fižol,", "fižol ", "čičerika", "leča,", "leča ",
        "grah,", "grah ", "grah droben", "grah ",
        "koruza v zrnju", "koruza,", "koruza ",
    )),
    # Frozen
    ("ZAMRZNJENA HRANA", (
        "zamrzn", "zamrznjen", "globoko zmrzn", "pomfri", "pomfrit",
        "ledene kocke", "zmrzn zelenjav", "zmrzn sadje",
        "fileji aljaškega", "panirani filej", "paniran file",
        "file polak", "alaškega polak",
    )),
    # Pantry staples
    ("OSNOVNA ŽIVILA / SHRAMBA", (
        "moka", "zdrob", "sladkor,", "sladkor ", "kokosov sladkor",
        "kvas", "pecilni prašek",
        "olje", "repično olje", "sončnično olje", "bučno olje",
        "kokosovo olje", "olivno olje", "arašidovo olje",
        "ocet", "kis,", "kis ", "balzamič",
        "sol,", "sol ", "morska sol",
        "začimb", "popr,", "poper ", "cimet", "vanilij", "muškatni orešč",
        "kurkum", "paprika začimb", "bazilika", "origano", "timijan", "rožmarin",
        "koper,", "koper ", "peteršilj", "kumin", "janež",
        "vanilin sladkor", "sladka smetana za kuhanje",
        "kaša,", "kaša ", "ajdova kaša", "ovsena kaša", "prosena kaša",
        "ješprenj", "polnozrnati prepečen", "prepečen",
        "rezan", "rezanci", "gnezda", "jušne krogl",
        "ketchup", "kečap",
        "medenjak", "namaz mastni",
        "mak,", "mak ", "mleti mak",
        "datl", "rozin", "posušen", "suhi", "suho sadje",
        "makadam",
        "le gusto",  # Hofer spice brand, uses "le gusto" + spice name
        "krušne drobtine",
    )),
    # Deli / ready meals
    ("DELIKATESNI IZDELKI IN PRIPRAVLJENE JEDI", (
        "pizza,", "pizza ", "pica ", "pica,", "lazanje pripravlj",
        "gotove jedi", "ready meal",
        "burito", "tortilja napolnjen", "salate pripravlj", "narezek",
        "gibanica", "tlačenk", "pletenka s sirom",
        "tofu",
        "namaz hummus", "hummus", "namaz,", "namaz ", "zelenjavni namaz",
        "kremni namaz", "vegansk", "rastlinski pripravek",
        "jabolčni zavitek", "zavitek",
        "kuhana plečk", "dimljeno suš", "speck",
    )),
    # Home / household (appliances, kitchenware, decor, candles, batteries,
    # plants, outdoor, travel goods)
    ("VSE ZA DOM IN GOSPODINJSTVO", (
        "folij", "vrečk za smeti", "vrečk za zmrzovan", "alu folij", "folija",
        "servet", "prtič", "prt,", "prt ", "papirnati prt",
        "svečk", "sveč,", "sveč ", "sveča", "dišeča sveč", "nagrobn sveč",
        "polnilo za sveč", "vžigalne kocke", "vžigalnik",
        "baterij", "žarnic", "led žarnic", "razpršilnik arom",
        "aparat", "sesalnik", "pralni stroj", "pomivalni stroj", "mikrovaln",
        "hladilnik", "pečic", "likalnik", "likaln", "kuhalnik vode",
        "cvrtnik", "aparat za kav", "kavni aparat",
        "mešalnik", "paličn mešal", "smoothie", "sekljaln",
        "grelnik", "ledomat", "stojalo za suš", "plinska peč",
        "kuhinjski aparat", "ventilator", "klimatska naprava",
        "kovček", "zaboj", "kompostnik", "žar,", "žar ", "bbq",
        "vaza", "cvetlični lonč", "lonček za rože", "dekorativna figuric",
        "figuric", "okrasn", "dekoracij", "obesek za ključ",
        "skodelic", "krožnik", "kozarc,", "kozarc ", "lončk", "skleda",
        "pekač", "kuhinjski pripomoč", "nož,", "rezalnik", "lupilec",
        "ponev", "lonec", "kozic", "set posod",
        "kopalniška omara", "kopalniški predalnik", "kopalniški",
        "lasna sponka", "sponka za lase", "obesek,", "obesek ",
        "brisača,", "brisača ", "brisač",
        # plants / garden
        "pelargonij", "sivka", "hortenzija", "potonik", "rastlin", "sadik",
        "bugenvilej", "nagelj", "rezano cvetje", "jagodičevje", "lončnic",
        "balkonsk rož", "okrasn rastl", "vrtna", "vrtni",
    )),
    # Pets
    ("VSE ZA MALE DOMAČE ŽIVALI", (
        "hrana za pse", "hrana za mačke", "pasja hrana", "mačja hrana",
        "pesja hrana", "pesji pri", "mačji pri", "pasji", "mačji",
        "pesek za mačk", "posip za mačk",
        "mačja igrač", "mačja žoga", "praskalna plošč", "mačja meta",
        "obesek za mačk", "povodec", "ovratnica",
    )),
    # Office / school / gift program
    ("VSE ZA ŠOLO IN PISARNO, DARILNI PROGRAM", (
        "beležka", "ravnil", "svinčnik,", "svinčnik ", "svinčnikov", "šilček",
        "komplet za risanje", "začetni komplet", "barvic,", "barvic ",
        "jumbo barvic", "voščenk", "flomaster", "fotokopirni papir",
        "šolski etui", "zvezek", "mapa,", "mapa ", "radirka", "peresnic",
        "ruksak", "nahrbtnik",
        "dekorativna figuric", "figuric,", "figuric ", "vaza,", "vaza ",
        "cvetlični lonč", "lonček za rože", "okrasn", "dekoracij",
        "obesek za ključ",
        "presenečenje v škatli", "skrivnostna škatl", "zbirna šk",
        "živalski kostum", "kostum,", "kostum ",
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
