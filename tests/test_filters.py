"""Unit-Tests für Filter-Normalisierung (ohne Netz)."""

from __future__ import annotations

import pytest

from lebensmittelwarnung_cli.filters import (
    UnknownFilter,
    bundesland_slug,
    grund_display,
    grund_slug,
    typ_category,
    typ_display,
    typ_slug,
    typ_source_slugs,
)


@pytest.mark.parametrize(
    "value",
    ["BW", "Baden-Württemberg", "baden wuerttemberg", "BaWü", "baden-wuerttemberg"],
)
def test_bundesland_namen_und_kuerzel(value):
    assert bundesland_slug(value) == "baden-wuerttemberg"


def test_bundesland_tippfehler_tolerant():
    assert bundesland_slug("Baden-Wuerttemberq") == "baden-wuerttemberg"
    assert bundesland_slug("Nordrhein Westfalen") == "nordrhein-westfalen"


def test_unbekanntes_bundesland_nennt_erlaubte_werte():
    with pytest.raises(UnknownFilter) as excinfo:
        bundesland_slug("Atlantis")

    assert "Baden-Württemberg" in str(excinfo.value)


@pytest.mark.parametrize(
    ("value", "slug"),
    [
        ("Allergene", "allergene"),
        ("Fremdkörper", "fremdkoerper"),
        ("Krankheitserreger", "krankheitserreger"),
        ("gesundheitsschaedlichesubstanz", "gesundheitsschaedlichesubstanz"),
        ("Rückstände und Kontaminanten", "rueckstaendeundkontaminaten"),
        ("Sonstige Gründe", "sonstigegruende"),
    ],
)
def test_grund_normalisierung(value, slug):
    assert grund_slug(value) == slug
    assert grund_display(slug)


@pytest.mark.parametrize(
    ("value", "slug"),
    [
        ("Lebensmittel", "lebensmittel"),
        ("Bedarfsgegenstände", "bedarfsgegenstaende"),
        ("Baby- und Kinderprodukte", "babyundkinderprodukte"),
        ("Kosmetische Mittel", "kosmetischemittel"),
        ("Mittel zum Tätowieren", "mittelzumtaetowieren"),
        ("lebensmittel/fleischundwurstwaren", "lebensmittel/fleischundwurstwaren"),
    ],
)
def test_typ_normalisierung(value, slug):
    assert typ_slug(value) == slug


def test_typ_hilfen():
    assert typ_display("babyundkinderprodukte") == "Baby- und Kinderprodukte"
    assert typ_display("lebensmittel/fleischundwurstwaren") == "Lebensmittel"
    assert typ_category("lebensmittel/fleischundwurstwaren") == "lebensmittel"


def test_unbekannter_typ_ist_usage_fehler():
    with pytest.raises(UnknownFilter):
        typ_slug("Raumschiff")


def test_elternkategorie_wird_zu_blaettern():
    slugs = typ_source_slugs("lebensmittel")

    assert "lebensmittel/fleischundwurstwaren" in slugs
    assert "lebensmittel/obstundgemuese" in slugs
    assert "lebensmittel" not in slugs
    assert len(slugs) == 15


def test_blattslug_bleibt_unveraendert():
    assert typ_source_slugs("lebensmittel/fleischundwurstwaren") == [
        "lebensmittel/fleischundwurstwaren"
    ]
    assert typ_source_slugs("babyundkinderprodukte") == ["babyundkinderprodukte"]
