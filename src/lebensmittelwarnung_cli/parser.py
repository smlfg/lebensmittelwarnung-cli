"""HTML-Parser für Trefferlisten und Meldungsdetails (nur Standardbibliothek)."""

from __future__ import annotations

import re
from datetime import date
from html.parser import HTMLParser
from urllib.parse import urlsplit

from .errors import SourceError

_DATE_DMY = re.compile(r"^(\d{2})\.(\d{2})\.(\d{4})$")
_DATE_ISO = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")
_SHORT_ID = re.compile(r"(\d{6}_\d{2})")
_TOTAL = re.compile(r"von\s+insgesamt\s+(\d+)", re.I)


def iso_date(text: str | None) -> str | None:
    if not text:
        return None
    value = text.strip()
    match = _DATE_DMY.match(value)
    if match:
        day, month, year = match.groups()
        return f"{year}-{month}-{day}"
    match = _DATE_ISO.match(value)
    if match:
        return value
    return None


def german_date(iso: str | None) -> str:
    if not iso:
        return ""
    try:
        value = date.fromisoformat(iso)
    except ValueError:
        return iso
    return value.strftime("%d.%m.%Y")


def short_id(url: str) -> str | None:
    path = urlsplit(url).path
    match = _SHORT_ID.search(path)
    return match.group(1) if match else None


def _classes(attrs) -> str:
    for name, value in attrs:
        if name == "class" and value:
            return value
    return ""


def _attr(attrs, wanted: str) -> str:
    for name, value in attrs:
        if name == wanted:
            return value or ""
    return ""


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


class _ListParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[str] = []
        self.items: list[dict] = []
        self.item: dict | None = None
        self.item_depth: int | None = None
        self.captures: list[dict] = []
        self.header = ""
        self.all_text: list[str] = []

    def _push_capture(self, tag: str, depth: int, key: str) -> None:
        self.captures.append(
            {"tag": tag, "depth": depth, "key": key, "buf": []}
        )

    def handle_starttag(self, tag, attrs):
        classes = _classes(attrs)
        depth = len(self.stack)
        if tag == "br":
            for capture in self.captures:
                capture["buf"].append(" ")
            return
        self.stack.append(tag)
        if tag == "li" and "lmw-search__results-element" in classes:
            self.item = {
                "titel": "",
                "datum": None,
                "typ": "",
                "gruende": [],
                "href": "",
            }
            self.item_depth = depth
            self.items.append(self.item)
            return
        if self.item is None:
            if tag == "span" and "lmw-search__results-hits" in classes:
                self._push_capture(tag, depth, "header")
            return
        if tag == "time" and "lmw-card__datetime" in classes:
            self._push_capture(tag, depth, "datum")
        elif tag == "h4" and "lmw-card__heading" in classes:
            self._push_capture(tag, depth, "titel")
        elif tag == "a" and "lmw-card__link" in classes:
            if not self.item["href"]:
                self.item["href"] = _attr(attrs, "href")
        elif tag == "span" and "lmw-producttype__label" in classes:
            self._push_capture(tag, depth, "typ")
        elif tag == "span" and "lmw-badge" in classes and "lmw-card__badge" in classes:
            self._push_capture(tag, depth, "badge")

    def handle_endtag(self, tag):
        if not self.stack:
            return
        depth = len(self.stack) - 1
        if self.stack[-1] == tag:
            self.stack.pop()
        else:
            if tag in self.stack:
                while self.stack and self.stack[-1] != tag:
                    self.stack.pop()
                if self.stack:
                    depth = len(self.stack) - 1
                    self.stack.pop()
            else:
                return
        for index in range(len(self.captures) - 1, -1, -1):
            capture = self.captures[index]
            if capture["tag"] == tag and capture["depth"] == depth:
                del self.captures[index]
                text = _clean("".join(capture["buf"]))
                self._finish(capture["key"], text)
                break
        if tag == "li" and self.item_depth == depth:
            self.item = None
            self.item_depth = None

    def _finish(self, key: str, text: str) -> None:
        if key == "header":
            self.header = text
        elif self.item is None:
            return
        elif key == "datum":
            self.item["datum"] = iso_date(text)
        elif key == "titel":
            if not self.item["titel"]:
                self.item["titel"] = text
        elif key == "typ":
            if not self.item["typ"]:
                self.item["typ"] = text
        elif key == "badge":
            if text:
                self.item["gruende"].append(text)

    def handle_data(self, data):
        self.all_text.append(data)
        for capture in self.captures:
            capture["buf"].append(data)


def parse_list(html: str) -> tuple[list[dict], int | None]:
    parser = _ListParser()
    parser.feed(html)
    parser.close()
    text = _clean("".join(parser.all_text))
    total_match = _TOTAL.search(parser.header or text)
    total = int(total_match.group(1)) if total_match else None
    if not parser.items:
        lowered = text.lower()
        if "keine treffer" in lowered or "keine meldungen" in lowered:
            return [], 0
        raise SourceError(
            "Die Antwort der Quelle enthielt keine bekannte Trefferliste. "
            "Vielleicht hat sich die Seite geändert.",
            hinweis="Prüfe `lmw suche` erneut oder melde das Problem im Repo.",
        )
    results = []
    for item in parser.items:
        if not item["href"] or not item["titel"]:
            continue
        item["id"] = short_id(item["href"])
        if not item["id"]:
            continue
        item["url"] = item["href"]
        item["_path"] = urlsplit(item["href"]).path
        item["gruende"] = [value for value in item["gruende"] if value]
        results.append(item)
    return results, total


_LABELS = {
    "produktbezeichnungbeschreibung": "produkt",
    "haltbarkeit": "haltbarkeit",
    "verpackungseinheit": "verpackungseinheit",
    "chargennummerloskennzeichnung": "charge",
    "herstellerinverkehrbringer": "hersteller",
    "grunddermeldung": "grund_label",
    "weitereinformationen": "weitere_informationen",
    "moeglichefolgen": "moegliche_folgen",
    "betroffenebundeslaendernachderzeitigemstand": "bundeslaender_label",
    "vertriebueber": "vertrieb",
    "empfehlung": "empfehlung",
    "datumdererstveroeffentlichung": "erstveroeffentlichung_label",
    "letzteaktualisierung": "aktualisiert_label",
}


def _label_key(text: str) -> str:
    lowered = text.lower().replace("ä", "ae").replace("ö", "oe").replace("ü", "ue")
    return re.sub(r"[^a-z0-9]", "", lowered)


class _DetailParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[str] = []
        self.captures: list[dict] = []
        self.title = ""
        self.typ = ""
        self.entries: list[dict] = []
        self.entry: dict | None = None

    def _push(self, tag: str, depth: int, key: str) -> None:
        self.captures.append({"tag": tag, "depth": depth, "key": key, "buf": []})

    def handle_starttag(self, tag, attrs):
        classes = _classes(attrs)
        depth = len(self.stack)
        if tag == "br":
            for capture in self.captures:
                capture["buf"].append(" ")
            return
        self.stack.append(tag)
        if tag == "h1" and "lmw-intro__heading" in classes:
            self._push(tag, depth, "title")
        elif tag == "span" and "lmw-producttype__label" in classes:
            self._push(tag, depth, "typ")
        elif tag == "dt" and "lmw-description-list__term" in classes:
            self.entry = {"label": "", "text": [], "badges": []}
            self.entries.append(self.entry)
            self._push(tag, depth, "label")
        elif tag == "dd" and "lmw-description-list__description" in classes:
            if self.entry is not None:
                self._push(tag, depth, "description")
        elif tag == "span" and "lmw-badge" in classes:
            if self.entry is not None:
                self._push(tag, depth, "badge")

    def handle_endtag(self, tag):
        if not self.stack:
            return
        depth = len(self.stack) - 1
        if self.stack[-1] == tag:
            self.stack.pop()
        elif tag in self.stack:
            while self.stack and self.stack[-1] != tag:
                self.stack.pop()
            if self.stack:
                depth = len(self.stack) - 1
                self.stack.pop()
        else:
            return
        for index in range(len(self.captures) - 1, -1, -1):
            capture = self.captures[index]
            if capture["tag"] == tag and capture["depth"] == depth:
                del self.captures[index]
                text = _clean("".join(capture["buf"]))
                self._finish(capture["key"], text)
                break

    def _finish(self, key: str, text: str) -> None:
        if key == "title":
            if not self.title:
                self.title = text
        elif key == "typ":
            if not self.typ:
                self.typ = text
        elif key == "label":
            if self.entry is not None:
                self.entry["label"] = text
        elif key == "description":
            if self.entry is not None:
                self.entry["text"].append(text)
        elif key == "badge":
            if self.entry is not None and text:
                self.entry["badges"].append(text)

    def handle_data(self, data):
        for capture in self.captures:
            capture["buf"].append(data)


def parse_detail(html: str) -> dict:
    parser = _DetailParser()
    parser.feed(html)
    parser.close()
    fields: dict[str, object] = {}
    for entry in parser.entries:
        label = entry["label"]
        key = _LABELS.get(_label_key(label))
        if key is None:
            continue
        text = _clean(" ".join(entry["text"]))
        badges = [value for value in entry["badges"] if value]
        if key == "grund_label":
            fields["gruende"] = badges or ([text] if text else [])
        elif key == "bundeslaender_label":
            fields["bundeslaender"] = badges or (
                [part.strip() for part in text.split(",") if part.strip()]
                if text
                else []
            )
        elif key == "erstveroeffentlichung_label":
            value = iso_date(text)
            if value:
                fields["erstveroeffentlichung"] = value
        elif key == "aktualisiert_label":
            value = iso_date(text)
            if value:
                fields["aktualisiert"] = value
        elif text:
            fields[key] = text
    if not parser.title and not fields:
        raise SourceError(
            "Die Detailseite enthielt keine bekannten Felder. "
            "Vielleicht hat sich die Seite geändert.",
            hinweis="Prüfe die Meldung im Browser auf lebensmittelwarnung.de.",
        )
    result: dict[str, object] = {
        "titel": parser.title,
        "typ": parser.typ,
    }
    result.update(fields)
    result.setdefault("gruende", [])
    result.setdefault("bundeslaender", [])
    return result
