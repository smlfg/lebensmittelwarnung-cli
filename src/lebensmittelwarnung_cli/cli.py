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
