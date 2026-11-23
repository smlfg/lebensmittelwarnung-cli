"""Normalisierung von Bundesländern, Gründen und Produkttypen."""

from __future__ import annotations

import difflib
import re
import unicodedata

BUNDESLAENDER: dict[str, str] = {
    "baden-wuerttemberg": "Baden-Württemberg",
    "bayern": "Bayern",
    "berlin": "Berlin",
    "brandenburg": "Brandenburg",
    "bremen": "Bremen",
    "hamburg": "Hamburg",
    "hessen": "Hessen",
    "mecklenburg-vorpommern": "Mecklenburg-Vorpommern",
    "niedersachsen": "Niedersachsen",
    "nordrhein-westfalen": "Nordrhein-Westfalen",
    "rheinland-pfalz": "Rheinland-Pfalz",
    "saarland": "Saarland",
    "sachsen": "Sachsen",
    "sachsen-anhalt": "Sachsen-Anhalt",
    "schleswig-holstein": "Schleswig-Holstein",
    "thueringen": "Thüringen",
}

BUNDESLAND_ABKUERZUNGEN: dict[str, str] = {
    "bw": "baden-wuerttemberg",
    "by": "bayern",
    "be": "berlin",
    "bb": "brandenburg",
    "hb": "bremen",
    "hh": "hamburg",
    "he": "hessen",
    "mv": "mecklenburg-vorpommern",
    "ni": "niedersachsen",
    "nw": "nordrhein-westfalen",
    "rp": "rheinland-pfalz",
    "sl": "saarland",
    "sn": "sachsen",
    "st": "sachsen-anhalt",
    "sh": "schleswig-holstein",
    "th": "thueringen",
}

BUNDESLAND_ALIASES: dict[str, str] = {
    "badenwuerttemberg": "baden-wuerttemberg",
    "bawue": "baden-wuerttemberg",
    "badenwurttemberg": "baden-wuerttemberg",
    "mecklenburgvorpommern": "mecklenburg-vorpommern",
    "nordrheinwestfalen": "nordrhein-westfalen",
    "rheinlandpfalz": "rheinland-pfalz",
    "sachsenanhalt": "sachsen-anhalt",
    "schleswigholstein": "schleswig-holstein",
}

GRUENDE: dict[str, str] = {
    "allergene": "Allergene",
    "fremdkoerper": "Fremdkörper",
    "gesundheitsschaedlichesubstanz": "Gesundheitsschädliche Substanz",
    "irrefuehrungundtaeuschung": "Irreführung und Täuschung",
    "krankheitserreger": "Krankheitserreger",
    "rueckstaendeundkontaminaten": "Rückstände und Kontaminanten",
    "sonstigegruende": "Sonstige Gründe",
}

GRUND_ALIASES: dict[str, str] = {
    "gesundheitsschaedlich": "gesundheitsschaedlichesubstanz",
    "gesundheitsschaedlichesubst": "gesundheitsschaedlichesubstanz",
    "irrefuehrung": "irrefuehrungundtaeuschung",
    "tauschung": "irrefuehrungundtaeuschung",
    "rueckstaende": "rueckstaendeundkontaminaten",
    "kontaminanten": "rueckstaendeundkontaminaten",
    "rueckstaendeundkontaminanten": "rueckstaendeundkontaminaten",
    "sonstige": "sonstigegruende",
}

TYPEN: dict[str, str] = {
    "lebensmittel": "Lebensmittel",
    "bedarfsgegenstaende": "Bedarfsgegenstände",
    "babyundkinderprodukte": "Baby- und Kinderprodukte",
    "kosmetischemittel": "Kosmetische Mittel",
    "mittelzumtaetowieren": "Mittel zum Tätowieren",
}

TYP_ALIASES: dict[str, str] = {
    "lebensmitteln": "lebensmittel",
    "bedarfsgegenstand": "bedarfsgegenstaende",
    "bedarfsgegenstaenden": "bedarfsgegenstaende",
    "babyundkinder": "babyundkinderprodukte",
    "babys": "babyundkinderprodukte",
    "kinderprodukte": "babyundkinderprodukte",
    "kosmetik": "kosmetischemittel",
    "kosmetika": "kosmetischemittel",
    "taetowierung": "mittelzumtaetowieren",
    "taetowieren": "mittelzumtaetowieren",
}

_UMLAUF = str.maketrans(
    {"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss", "Ä": "ae", "Ö": "oe", "Ü": "ue"}
)


class UnknownFilter(ValueError):
    """Ein Filterwert ist unbekannt."""

    def __init__(self, kind: str, value: str, erlaubte: list[str]) -> None:
        self.kind = kind
        self.value = value
        self.erlaubte = erlaubte
        super().__init__(
            f"Unbekanntes {kind}: {value!r}. Erlaubt: {', '.join(erlaubte)}"
        )


def _fold(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).translate(_UMLAUF)
    return re.sub(r"[^a-z0-9]", "", text.lower())


def _match(kind: str, value: str, table: dict[str, str], aliases: dict[str, str]) -> str:
    folded = _fold(value)
    if not folded:
        raise UnknownFilter(kind, value, sorted(table))
    if folded in table:
        return folded
    if folded in aliases:
        return aliases[folded]
    candidates = {**{_fold(key): slug for key, slug in table.items()}, **aliases}
    close = difflib.get_close_matches(folded, list(candidates), n=1, cutoff=0.82)
    if close:
        return candidates[close[0]]
    raise UnknownFilter(kind, value, sorted(table))


def bundesland_slug(value: str) -> str:
    """Name, Kürzel oder Slug -> Slug; tippfehler- und umlauttolerant."""
    folded = _fold(value)
    if folded in BUNDESLAND_ABKUERZUNGEN:
        return BUNDESLAND_ABKUERZUNGEN[folded]
    candidates = {
        **{_fold(key): slug for key, slug in BUNDESLAENDER.items()},
        **{_fold(name): slug for slug, name in BUNDESLAENDER.items()},
        **BUNDESLAND_ALIASES,
    }
    if folded in candidates:
        return candidates[folded]
    close = difflib.get_close_matches(folded, list(candidates), n=1, cutoff=0.82)
    if close:
        return candidates[close[0]]
    raise UnknownFilter("Bundesland", value, sorted(BUNDESLAENDER.values()))


def grund_slug(value: str) -> str:
    return _match("Grund", value, GRUENDE, GRUND_ALIASES)


def typ_slug(value: str) -> str:
    """Produkttyp -> Slug; Untertypen wie ``lebensmittel/fleisch`` bleiben erhalten."""
    if "/" in value:
        head, rest = value.split("/", 1)
        slug_head = typ_slug(head)
        rest = re.sub(r"[^a-z0-9_-]", "", rest.strip().lower())
        return f"{slug_head}/{rest}" if rest else slug_head
    return _match("Typ", value, TYPEN, TYP_ALIASES)


def grund_display(slug: str) -> str:
    return GRUENDE.get(slug, slug)


def typ_display(slug: str) -> str:
    head = slug.split("/", 1)[0]
    return TYPEN.get(head, slug)


def typ_category(slug: str) -> str:
    return slug.split("/", 1)[0]
