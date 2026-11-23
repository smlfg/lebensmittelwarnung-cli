"""Kommandozeile für lmw."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import timedelta

from . import __version__
from .client import Client, today
from .errors import LmwError, UsageError
from .filters import (
    BUNDESLAENDER,
    UnknownFilter,
    bundesland_slug,
    grund_display,
    grund_slug,
    typ_category,
    typ_display,
    typ_slug,
)
from .parser import german_date, parse_detail, parse_list
from .storage import (
    config_path,
    load_config,
    load_state,
    save_config,
    save_state,
)


_SHORT_ID_RE = re.compile(r"\d{6}_\d{2}")


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        raise UsageError(message)


def _positive_int(value: str) -> int:
    try:
        number = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"{value!r} ist keine ganze Zahl") from exc
    if number < 1:
        raise argparse.ArgumentTypeError("muss eine positive ganze Zahl sein")
    return number


def _limit(value: str) -> int:
    number = _positive_int(value)
    if number > 100:
        raise argparse.ArgumentTypeError("höchstens 100")
    return number


def _add_filters(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--bundesland", action="append", metavar="NAME|KÜRZEL")
    parser.add_argument("--grund", action="append", metavar="GRUND")
    parser.add_argument("--typ", action="append", metavar="TYP")
    parser.add_argument("--tage", type=_positive_int, metavar="N")
    parser.add_argument("--limit", type=_limit, default=20, metavar="N")
    parser.add_argument("--json", action="store_true")


def build_parser() -> argparse.ArgumentParser:
    parser = _Parser(
        prog="lmw",
        description="Lebensmittel- und Produktwarnungen von lebensmittelwarnung.de.",
    )
    parser.add_argument(
        "--version", action="version", version=f"lmw {__version__}"
    )
    subparsers = parser.add_subparsers(dest="kommando", required=True)

    neu = subparsers.add_parser("neu", help="neueste Warnungen anzeigen")
    _add_filters(neu)
    neu.set_defaults(func=_cmd_neu)

    suche = subparsers.add_parser("suche", help="nach Produkt oder Marke suchen")
    suche.add_argument("begriff", nargs="+", metavar="BEGRIFF")
    _add_filters(suche)
    suche.set_defaults(func=_cmd_suche)

    zeige = subparsers.add_parser("zeige", help="eine Meldung im Detail ansehen")
    zeige.add_argument("auswahl", nargs="+", metavar="AUSWAHL")
    zeige.add_argument("--erster", action="store_true")
    zeige.add_argument("--json", action="store_true")
    zeige.set_defaults(func=_cmd_zeige)

    watch = subparsers.add_parser("watch", help="neue Warnungen seit dem letzten Lauf")
    watch.add_argument("begriff", nargs="*", metavar="BEGRIFF")
    _add_filters(watch)
    watch.set_defaults(func=_cmd_watch)
    return parser


def _json_mode(args) -> bool:
    return bool(getattr(args, "json", False)) or not sys.stdout.isatty()


def _split_multi(values: list[str] | None) -> list[str]:
    result: list[str] = []
    for value in values or []:
        for part in str(value).split(","):
            part = part.strip()
            if part and part not in result:
                result.append(part)
    return result


def _resolve_bundeslaender(values: list[str] | None, *, use_config: bool) -> list[str]:
    raw = _split_multi(values)
    if not raw and use_config:
        gespeichert = load_config().get("slug")
        if gespeichert:
            raw = [str(gespeichert)]
    try:
        return [bundesland_slug(value) for value in raw]
    except UnknownFilter as exc:
        raise UsageError(str(exc)) from exc


def _resolve_gruende(values: list[str] | None) -> list[str]:
    try:
        return [grund_slug(value) for value in _split_multi(values)]
    except UnknownFilter as exc:
        raise UsageError(str(exc)) from exc


def _resolve_typen(values: list[str] | None) -> list[str]:
    try:
        return [typ_slug(value) for value in _split_multi(values)]
    except UnknownFilter as exc:
        raise UsageError(str(exc)) from exc


def _apply_filters(
    items: list[dict],
    *,
    gruende: list[str],
    typen: list[str],
    tage: int | None,
    heute,
) -> list[dict]:
    result = items
    if gruende:
        wanted = {grund_display(slug) for slug in gruende}
        result = [
            item
            for item in result
            if wanted.intersection(item.get("gruende") or [])
        ]
    if typen:
        wanted = {typ_display(slug).casefold() for slug in typen}
        result = [
            item
            for item in result
            if str(item.get("typ") or "").casefold() in wanted
        ]
    if tage is not None:
        earliest = (heute - timedelta(days=tage)).isoformat()
        latest = heute.isoformat()
        result = [
            item
            for item in result
            if item.get("datum") is None
            or earliest <= str(item["datum"]) <= latest
        ]
    return result


def _public_item(item: dict) -> dict:
    return {
        "id": item.get("id"),
        "datum": item.get("datum"),
        "titel": item.get("titel"),
        "typ": item.get("typ"),
        "gruende": list(item.get("gruende") or []),
        "bundeslaender": list(item.get("bundeslaender") or []),
        "url": item.get("url"),
    }


def _print_list(text: str, results: list[dict], *, json_mode: bool, abfrage: dict) -> None:
    if json_mode:
        payload = {
            "abfrage": abfrage,
            "anzahl": len(results),
            "treffer": [_public_item(item) for item in results],
        }
        print(json.dumps(payload, ensure_ascii=False))
        return
    print(text)
    for item in results:
        datum = german_date(item.get("datum"))
        print(f"{datum}  {item.get('titel')}")
        teile = []
        if item.get("typ"):
            teile.append(str(item["typ"]))
        if item.get("gruende"):
            teile.append(", ".join(item["gruende"]))
        teile.append(f"ID {item.get('id')}")
        print(" · ".join(teile))
    if results:
        print(f"Tipp: lmw zeige {results[0].get('id')} zeigt Details.")


def _fetch(
    client: Client,
    *,
    begriff: str | None,
    bundeslaender: list[str],
    gruende: list[str],
    typen: list[str],
    tage: int | None,
    limit: int,
    heute,
) -> tuple[list[dict], int | None]:
    html = client.search(
        begriff=begriff,
        bundeslaender=bundeslaender,
        gruende=gruende,
        typen=typen,
        tage=tage,
        limit=limit,
        bezugstag=heute,
    )
    results, total = parse_list(html)
    results = _apply_filters(
        results, gruende=gruende, typen=typen, tage=tage, heute=heute
    )
    return results[:limit], total


def _cmd_neu(args) -> int:
    heute = today()
    bundeslaender = _resolve_bundeslaender(args.bundesland, use_config=True)
    gruende = _resolve_gruende(args.grund)
    typen = _resolve_typen(args.typ)
    tage = args.tage or 14
    client = Client()
    results, _total = _fetch(
        client,
        begriff=None,
        bundeslaender=bundeslaender,
        gruende=gruende,
        typen=typen,
        tage=tage,
        limit=args.limit,
        heute=heute,
    )
    if _json_mode(args):
        abfrage = {
            "begriff": None,
            "bundesland": [BUNDESLAENDER[slug] for slug in bundeslaender],
            "tage": tage,
            "limit": args.limit,
        }
        _print_list("", results, json_mode=True, abfrage=abfrage)
        return 0
    scope = []
    if bundeslaender:
        scope.append(", ".join(BUNDESLAENDER[slug] for slug in bundeslaender))
    scope.append(f"letzte {tage} Tage")
    if results:
        text = f"Neueste Warnungen ({', '.join(scope)}): {len(results)} Treffer"
    else:
        text = f"Keine Warnungen ({', '.join(scope)})."
    _print_list(text, results, json_mode=False, abfrage={})
    return 0


def _cmd_suche(args) -> int:
    begriff = " ".join(args.begriff).strip()
    if not begriff:
        raise UsageError("Bitte einen Suchbegriff angeben.")
    heute = today()
    bundeslaender = _resolve_bundeslaender(args.bundesland, use_config=True)
    gruende = _resolve_gruende(args.grund)
    typen = _resolve_typen(args.typ)
    client = Client()
    results, _total = _fetch(
        client,
        begriff=begriff,
        bundeslaender=bundeslaender,
        gruende=gruende,
        typen=typen,
        tage=args.tage,
        limit=args.limit,
        heute=heute,
    )
    if _json_mode(args):
        abfrage = {
            "begriff": begriff,
            "bundesland": [BUNDESLAENDER[slug] for slug in bundeslaender],
            "tage": args.tage,
            "limit": args.limit,
        }
        _print_list("", results, json_mode=True, abfrage=abfrage)
        return 0
    if not results:
        print(f"Keine Treffer für „{begriff}“.")
        return 0
    text = f"{len(results)} Treffer für „{begriff}“"
    _print_list(text, results, json_mode=False, abfrage={})
    return 0


def _detail_url(item: dict) -> str:
    return item.get("_path") or item.get("url") or ""


def _build_detail(item: dict, parsed: dict) -> dict:
    datum = parsed.get("erstveroeffentlichung") or item.get("datum")
    detail = {
        "id": item.get("id"),
        "datum": datum,
        "titel": parsed.get("titel") or item.get("titel"),
        "typ": parsed.get("typ") or item.get("typ"),
    }
    for key in (
        "produkt",
        "haltbarkeit",
        "verpackungseinheit",
        "charge",
        "hersteller",
        "gruende",
        "weitere_informationen",
        "moegliche_folgen",
        "bundeslaender",
        "vertrieb",
        "empfehlung",
        "erstveroeffentlichung",
        "aktualisiert",
    ):
        if key in parsed:
            detail[key] = parsed[key]
    detail.setdefault("gruende", list(item.get("gruende") or []))
    detail.setdefault("bundeslaender", [])
    detail["url"] = item.get("url")
    return detail


def _print_detail(detail: dict) -> None:
    print(detail.get("titel") or detail.get("id"))
    labels = [
        ("haltbarkeit", "Haltbarkeit"),
        ("verpackungseinheit", "Verpackungseinheit"),
        ("charge", "Charge"),
        ("hersteller", "Hersteller"),
        ("gruende", "Grund"),
        ("weitere_informationen", "Weitere Informationen"),
        ("moegliche_folgen", "Mögliche Folgen"),
        ("bundeslaender", "Betroffene Bundesländer"),
        ("vertrieb", "Vertrieb über"),
        ("empfehlung", "Empfehlung"),
    ]
    for key, label in labels:
        value = detail.get(key)
        if isinstance(value, list):
            value = ", ".join(str(part) for part in value if part)
        if value:
            print(f"{label}: {value}")


def _ask_selection(items: list[dict], begriff: str) -> dict | None:
    print(f"Mehrere Treffer für „{begriff}“", file=sys.stderr)
    for index, item in enumerate(items, start=1):
        print(
            f"{index}) {german_date(item.get('datum'))}  {item.get('titel')}",
            file=sys.stderr,
        )
    for _attempt in range(3):
        print(f"Auswahl [1-{len(items)}]: ", end="", file=sys.stderr, flush=True)
        line = sys.stdin.readline()
        if line == "":
            raise UsageError("Keine Auswahl getroffen.")
        value = line.strip()
        if not value:
            raise UsageError("Keine Auswahl getroffen.")
        if value.isdigit() and 1 <= int(value) <= len(items):
            return items[int(value) - 1]
        print(f"Ungültige Auswahl. Bitte 1-{len(items)} eingeben.", file=sys.stderr)
    raise UsageError("Keine gültige Auswahl getroffen.")


def _cmd_zeige(args) -> int:
    begriff = " ".join(args.auswahl).strip()
    if not begriff:
        raise UsageError("Bitte eine Kurz-ID oder einen Suchbegriff angeben.")
    client = Client()
    html = client.search(begriff=begriff, limit=100)
    results, _total = parse_list(html)
    for item in results:
        item["_begriff"] = begriff
    if _SHORT_ID_RE.fullmatch(begriff):
        candidates = [item for item in results if item.get("id") == begriff]
        if not candidates:
            raise UsageError(
                f"Keine Meldung mit der Kurz-ID {begriff} gefunden.",
                hinweis="Suche mit `lmw suche BEGRIFF` nach der Meldung.",
            )
    else:
        candidates = results
    if not candidates:
        raise UsageError(
            f"Keine Meldung für „{begriff}“ gefunden.",
            hinweis="Prüfe den Suchbegriff mit `lmw suche BEGRIFF`.",
        )
    if len(candidates) > 1 and not args.erster:
        if sys.stdin.isatty():
            selected = _ask_selection(candidates, begriff)
        else:
            if _json_mode(args):
                payload = {
                    "fehler": {
                        "code": 2,
                        "art": "usage",
                        "meldung": f"Mehrere Treffer für „{begriff}“",
                        "hinweis": "Wähle mit --erster den ersten Treffer "
                        "oder starte den Befehl im Terminal.",
                        "kandidaten": [_public_item(item) for item in candidates],
                    }
                }
                print(json.dumps(payload, ensure_ascii=False))
            else:
                for index, item in enumerate(candidates, start=1):
                    print(
                        f"{index}) {german_date(item.get('datum'))}  "
                        f"{item.get('titel')}",
                        file=sys.stderr,
                    )
                print("Hinweis: --erster wählt den ersten Treffer.", file=sys.stderr)
            return 2
    else:
        selected = candidates[0]
    if selected is None:
        return 2
    parsed = parse_detail(client.detail(_detail_url(selected)))
    detail = _build_detail(selected, parsed)
    if _json_mode(args):
        print(json.dumps(detail, ensure_ascii=False))
    else:
        _print_detail(detail)
    return 0


def _cmd_watch(args) -> int:
    begriff = " ".join(args.begriff).strip() or None
    heute = today()
    bundeslaender = _resolve_bundeslaender(args.bundesland, use_config=True)
    gruende = _resolve_gruende(args.grund)
    typen = _resolve_typen(args.typ)
    client = Client()
    results, _total = _fetch(
        client,
        begriff=begriff,
        bundeslaender=bundeslaender,
        gruende=gruende,
        typen=typen,
        tage=args.tage,
        limit=args.limit,
        heute=heute,
    )
    state = load_state()
    seen = state.get("ids")
    seen = [str(item) for item in seen] if isinstance(seen, list) else []
    first = "ids" not in state
    current = [str(item["id"]) for item in results if item.get("id")]
    if first:
        neue = []
    else:
        neue = [item for item in results if str(item.get("id")) not in set(seen)]
    seen_after = sorted(set(seen) | set(current))
    save_state({"ids": seen_after})
    if _json_mode(args):
        payload = {
            "neu": [_public_item(item) for item in neue],
            "anzahl_neu": len(neue),
            "gesehen": len(seen_after),
            "erster_lauf": first,
        }
        print(json.dumps(payload, ensure_ascii=False))
        return 0
    if first:
        print(f"Erster Lauf: {len(current)} Warnungen gespeichert")
        return 0
    if not neue:
        print("Keine neuen Warnungen.")
        return 0
    print(f"{len(neue)} neue Warnungen")
    for item in neue:
        print(f"{german_date(item.get('datum'))}  {item.get('titel')}")
        teile = []
        if item.get("typ"):
            teile.append(str(item["typ"]))
        if item.get("gruende"):
            teile.append(", ".join(item["gruende"]))
        teile.append(f"ID {item.get('id')}")
        print(" · ".join(teile))
    return 0


def _emit_error(exc: LmwError, json_mode: bool) -> None:
    if json_mode:
        payload = {
            "fehler": {
                "code": exc.code,
                "art": exc.art,
                "meldung": exc.meldung,
            }
        }
        if exc.hinweis:
            payload["fehler"]["hinweis"] = exc.hinweis
        print(json.dumps(payload, ensure_ascii=False))
    else:
        print(f"Fehler: {exc.text()}", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    args_list = list(sys.argv[1:] if argv is None else argv)
    json_mode = "--json" in args_list or not sys.stdout.isatty()
    try:
        parser = build_parser()
        args = parser.parse_args(args_list)
        return int(args.func(args))
    except SystemExit:
        raise
    except KeyboardInterrupt:
        try:
            print("Abgebrochen.", file=sys.stderr)
        except OSError:
            pass
        return 130
    except BrokenPipeError:
        return 0
    except EOFError:
        _emit_error(UsageError("Keine Eingabe erhalten."), json_mode)
        return 2
    except LmwError as exc:
        try:
            _emit_error(exc, json_mode)
        except OSError:
            pass
        return exc.code
    except Exception as exc:  # noqa: BLE001 - kein Traceback nach außen
        try:
            _emit_error(
                LmwError(
                    f"Unerwarteter Fehler: {exc}",
                    hinweis="Bitte erneut versuchen oder das Problem melden.",
                ),
                json_mode,
            )
        except OSError:
            pass
        return 1
