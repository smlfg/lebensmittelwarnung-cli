"""Unit-Tests für Parser und Datums-/ID-Helfer (ohne Netz)."""

from __future__ import annotations

from pathlib import Path

import pytest

from lebensmittelwarnung_cli.errors import SourceError
from lebensmittelwarnung_cli.parser import (
    german_date,
    iso_date,
    parse_detail,
    parse_list,
    short_id,
)

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "ux"


def _fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_parse_list_liefert_alle_treffer_der_suche():
    results, total = parse_list(_fixture("suche_pinienkerne.html"))

    assert total == 4
    assert len(results) == 4
    first = results[0]
    assert first["id"] == "261106_04"
    assert first["datum"] == "2026-11-06"
    assert first["titel"] == "dmBio Pinienkerne, 60 Gramm"
    assert first["typ"] == "Lebensmittel"
    assert first["gruende"] == ["Krankheitserreger"]
    assert first["_path"].endswith("/261106_04_BW_Pinienkerne_Meldung.html")


def test_parse_list_loest_html_entities_auf():
    results, _ = parse_list(_fixture("suche_pinienkerne.html"))

    assert results[-1]["titel"] == "„Tomate & Feta Aufstrich“"


def test_parse_list_liest_bundesland_liste():
    results, total = parse_list(_fixture("liste_neu_bw.html"))

    assert total == 10
    assert len(results) == 10
    assert results[0]["id"] == "261121_22"
    assert results[0]["datum"] == "2026-11-21"
    assert results[0]["gruende"] == ["Gesundheitsschädliche Substanz"]
    assert results[0]["titel"] == "Parmentine Speisekartoffeln rot,1,5 Kilogramm"


def test_parse_list_keine_treffer_ist_kein_fehler():
    html = (
        "<html><body><main>"
        "<p>Die Suche ergab leider keine Treffer.</p>"
        "</main></body></html>"
    )
    results, total = parse_list(html)

    assert results == []
    assert total == 0


def test_parse_list_unerwartete_struktur_ist_quellenfehler():
    with pytest.raises(SourceError):
        parse_list("<html><body><p>Ganz andere Seite</p></body></html>")


def test_parse_detail_liest_bekannte_felder():
    detail = parse_detail(_fixture("detail_dennree.html"))

    assert detail["titel"] == "dennree Pinienkerne, 60 Gramm"
    assert detail["typ"] == "Lebensmittel"
    assert detail["haltbarkeit"] == (
        "Mindesthaltbarkeitsdatum 03.06.2027 und 16.06.2027"
    )
    assert detail["hersteller"] == "dennree GmbH, Hofer Straße 11, 95183 Töpen"
    assert detail["gruende"] == ["Krankheitserreger"]
    assert detail["bundeslaender"][0] == "Baden-Württemberg"
    assert detail["bundeslaender"][1] == "Bayern"
    assert len(detail["bundeslaender"]) == 16
    assert detail["vertrieb"].startswith("Die Ware ist bei Denns BioMarkt")
    assert detail["empfehlung"].startswith("Empfehlung der Firma dennree GmbH")
    assert detail["erstveroeffentlichung"] == "2026-11-05"


def test_datum_und_id_helfer():
    assert iso_date("05.11.2026") == "2026-11-05"
    assert iso_date("2026-11-05") == "2026-11-05"
    assert iso_date("kein Datum") is None
    assert german_date("2026-11-05") == "05.11.2026"
    assert (
        short_id(
            "https://www.lebensmittelwarnung.de/___lebensmittelwarnung.de/"
            "Meldungen/2026/11_November/261105_02_BY_Pinienkerne/"
            "261105_02_BY_Pinienkerne.html"
        )
        == "261105_02"
    )
