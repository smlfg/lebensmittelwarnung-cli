"""CLI-Tests mit Fixtures statt Netzwerk (keine echten Requests)."""

from __future__ import annotations

import json
import os
import shutil
import stat
import tempfile
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest

from lebensmittelwarnung_cli import cli, client

REPO = Path(__file__).resolve().parents[1]
SCRATCH = REPO / "scratch" / "tmp"
FIXTURES = Path(__file__).resolve().parent / "fixtures" / "ux"


def _fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


@pytest.fixture()
def workspace(monkeypatch):
    SCRATCH.mkdir(parents=True, exist_ok=True)
    home = Path(tempfile.mkdtemp(prefix="lmw-unit-", dir=SCRATCH))
    for name in ("config", "state", "cache"):
        (home / name).mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(home / "config"))
    monkeypatch.setenv("XDG_STATE_HOME", str(home / "state"))
    monkeypatch.setenv("XDG_CACHE_HOME", str(home / "cache"))
    monkeypatch.setenv("LMW_HEUTE", "2026-11-23")
    monkeypatch.setenv("LMW_BASE_URL", "http://127.0.0.1:1")

    def no_network(*_args, **_kwargs):
        raise AssertionError("Netzwerk ist in Unit-Tests verboten")

    monkeypatch.setattr(client.httpx, "get", no_network)
    try:
        yield home
    finally:
        shutil.rmtree(home, ignore_errors=True)


def _fake_search(html: str):
    def search(self, **_kwargs):
        return html

    return search


def _capture_search_query(monkeypatch) -> dict:
    seen: dict[str, str] = {}

    def fake_get(self, path):
        seen["path"] = path
        return ""

    monkeypatch.setattr(cli.Client, "get", fake_get)
    return seen


def _query_value(path: str, key: str) -> str:
    query = parse_qs(urlsplit(path).query)
    return query[key][0]


def test_elternkategorie_typ_wird_zu_blaettern_erweitert(workspace, monkeypatch):
    seen = _capture_search_query(monkeypatch)

    cli.Client().search(typen=["lebensmittel"], limit=100)

    value = _query_value(seen["path"], "cl2Taxonomies_Typ")
    assert "/c/typ/lebensmittel/fleischundwurstwaren" in value
    assert "/c/typ/lebensmittel " not in value + " "
    assert not value.endswith("/c/typ/lebensmittel\"")


def test_blattslug_typ_bleibt_einzeln(workspace, monkeypatch):
    seen = _capture_search_query(monkeypatch)

    cli.Client().search(typen=["lebensmittel/fleischundwurstwaren"], limit=100)

    value = _query_value(seen["path"], "cl2Taxonomies_Typ")
    assert value == '"/c/typ/lebensmittel/fleischundwurstwaren"'


def test_neu_json_gegen_fixture(workspace, monkeypatch, capsys):
    monkeypatch.setattr(
        cli.Client, "search", _fake_search(_fixture("liste_neu_bw.html"))
    )

    code = cli.main(["neu", "--bundesland", "BW", "--json"])

    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["anzahl"] == 10
    assert payload["abfrage"]["tage"] == 14
    assert payload["abfrage"]["bundesland"] == ["Baden-Württemberg"]
    assert payload["treffer"][0]["id"] == "261121_22"


def test_neu_unbekanntes_bundesland_ist_exit_2(workspace, capsys):
    code = cli.main(["neu", "--bundesland", "Atlantis", "--json"])

    assert code == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload["fehler"]["code"] == 2
    assert "Atlantis" in payload["fehler"]["meldung"]


def test_suche_json_gegen_fixture(workspace, monkeypatch, capsys):
    monkeypatch.setattr(
        cli.Client, "search", _fake_search(_fixture("suche_pinienkerne.html"))
    )

    code = cli.main(["suche", "Pinienkerne", "--json"])

    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["anzahl"] == 4
    assert {item["titel"] for item in payload["treffer"]} >= {
        "dmBio Pinienkerne, 60 Gramm",
        "dennree Pinienkerne, 60 Gramm",
    }


def test_zeige_mehrdeutig_ohne_tty_ist_exit_2_mit_kandidaten(
    workspace, monkeypatch, capsys
):
    monkeypatch.setattr(
        cli.Client, "search", _fake_search(_fixture("suche_pinienkerne.html"))
    )

    code = cli.main(["zeige", "Pinienkerne", "--json"])

    assert code == 2
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert payload["fehler"]["code"] == 2
    assert len(payload["fehler"]["kandidaten"]) == 4
    assert "dennree Pinienkerne, 60 Gramm" in out


def test_zeige_kurz_id_laedt_detail(workspace, monkeypatch, capsys):
    monkeypatch.setattr(
        cli.Client, "search", _fake_search(_fixture("suche_pinienkerne.html"))
    )
    monkeypatch.setattr(
        cli.Client,
        "detail",
        lambda self, path=None, url=None: _fixture("detail_dennree.html"),
    )

    code = cli.main(["zeige", "261105_02", "--erster", "--json"])

    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["id"] == "261105_02"
    assert payload["haltbarkeit"].startswith("Mindesthaltbarkeitsdatum")
    assert payload["bundeslaender"][0] == "Baden-Württemberg"


def test_config_speichert_bundesland_mit_0600(workspace, capsys):
    code = cli.main(["config", "bundesland", "BW", "--json"])

    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    path = Path(payload["pfad"])
    assert payload["bundesland"] == "Baden-Württemberg"
    assert payload["slug"] == "baden-wuerttemberg"
    assert path.exists()
    assert stat.S_IMODE(os.stat(path).st_mode) == 0o600

    code = cli.main(["config", "bundesland", "--json"])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["slug"] == "baden-wuerttemberg"


def test_version_und_help_enden_mit_0():
    for argv in (["--version"], ["--help"], ["neu", "--help"]):
        with pytest.raises(SystemExit) as excinfo:
            cli.main(argv)
        assert excinfo.value.code == 0


def test_netzfehler_ist_exit_3_ohne_traceback(workspace, monkeypatch, capsys):
    def boom(*_args, **_kwargs):
        raise client.httpx.ConnectError("Verbindung fehlgeschlagen")

    monkeypatch.setattr(client.httpx, "get", boom)

    code = cli.main(["neu", "--json"])

    assert code == 3
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert payload["fehler"]["code"] == 3
    assert "Traceback" not in out


def test_watch_zustand_0600_und_neue_ids(workspace, monkeypatch, capsys):
    from lebensmittelwarnung_cli.storage import state_path

    monkeypatch.setattr(
        cli.Client, "search", _fake_search(_fixture("liste_neu_bw.html"))
    )

    code = cli.main(["watch", "--json"])
    assert code == 0
    first = json.loads(capsys.readouterr().out)
    assert first["erster_lauf"] is True
    assert first["anzahl_neu"] == 0
    assert first["gesehen"] == 10
    path = state_path()
    assert stat.S_IMODE(os.stat(path).st_mode) == 0o600

    state = json.loads(path.read_text(encoding="utf-8"))
    state["ids"] = [value for value in state["ids"] if value != "261121_22"]
    path.write_text(json.dumps(state), encoding="utf-8")

    code = cli.main(["watch", "--json"])
    assert code == 0
    second = json.loads(capsys.readouterr().out)
    assert second["erster_lauf"] is False
    assert second["anzahl_neu"] == 1
    assert second["neu"][0]["id"] == "261121_22"


def test_auswahl_eof_ist_exit_2_ohne_traceback(workspace, monkeypatch, capsys):
    class FakeStdin:
        def isatty(self):
            return True

        def readline(self):
            return ""

    monkeypatch.setattr(
        cli.Client, "search", _fake_search(_fixture("suche_pinienkerne.html"))
    )
    monkeypatch.setattr(cli.sys, "stdin", FakeStdin())

    code = cli.main(["zeige", "Pinienkerne", "--json"])

    assert code in {2, 130}
    out = capsys.readouterr().out
    assert "Traceback" not in out


def test_strg_c_ist_exit_130_ohne_traceback(workspace, monkeypatch, capsys):
    def interrupt(self, **_kwargs):
        raise KeyboardInterrupt

    monkeypatch.setattr(cli.Client, "search", interrupt)

    code = cli.main(["neu", "--json"])

    assert code == 130
    captured = capsys.readouterr()
    assert "Traceback" not in captured.out
    assert "Traceback" not in captured.err


def test_hilfe_erklaert_optionen(capsys):
    with pytest.raises(SystemExit) as excinfo:
        cli.main(["neu", "--help"])

    assert excinfo.value.code == 0
    out = capsys.readouterr().out
    assert "Bundesland-Filter" in out
    assert "Zeitfenster in Tagen" in out
    assert "Standard: 14" in out
    assert "1-100" in out
