"""Akzeptanztests aus docs/UX.md gegen den Fake-Server.

Die Tests starten das noch zu bauende Werkzeug als Subprozess
(``python -m lebensmittelwarnung_cli``) mit ``LMW_BASE_URL`` auf den lokalen
Fake-Server. Bis der Code in S3 entsteht, sind sie absichtlich rot.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
HARNESS = REPO / "tests" / "harness"
SCRATCH_TMP = REPO / "scratch" / "tmp"
TIMEOUT = 25

sys.path.insert(0, str(HARNESS))

from fake_server import FakeServer  # noqa: E402
from ux_session import PtySession, strip_ansi  # noqa: E402
from ux_spec import parse  # noqa: E402

SPEC = parse(REPO / "docs" / "UX.md")


def _workspace() -> Path:
    SCRATCH_TMP.mkdir(parents=True, exist_ok=True)
    home = Path(tempfile.mkdtemp(prefix="lmw-acceptance-", dir=SCRATCH_TMP))
    for name in ("config", "state", "cache"):
        (home / name).mkdir()
    return home


def _environment(server: FakeServer, home: Path) -> dict[str, str]:
    env = dict(os.environ)
    env.update(
        {
            "LMW_BASE_URL": server.base_url,
            "LMW_HEUTE": "2026-11-23",
            "PYTHONPATH": os.pathsep.join(
                [str(REPO), str(HARNESS), env.get("PYTHONPATH", "")]
            ).strip(os.pathsep),
            "HOME": str(home),
            "XDG_CONFIG_HOME": str(home / "config"),
            "XDG_STATE_HOME": str(home / "state"),
            "XDG_CACHE_HOME": str(home / "cache"),
            "ACCEPTANCE_SANDBOX": "1",
            "ACCEPTANCE_NET_LOG": str(home / "net.log"),
            "NO_COLOR": "1",
            "PYTHONIOENCODING": "utf-8",
            "LC_ALL": "C.UTF-8",
        }
    )
    return env


def _command(*args: str) -> list[str]:
    return [sys.executable, "-m", "lebensmittelwarnung_cli", *args]


def _run_pty(
    *args: str, sends: tuple[tuple[str, str], ...] = ()
) -> tuple[int | None, str, list]:
    home = _workspace()
    try:
        with FakeServer(SPEC, REPO) as server:
            env = _environment(server, home)
            session = PtySession(_command(*args), env=env, cwd=str(REPO))
            try:
                for prompt, answer in sends:
                    found = session.expect(prompt, timeout=TIMEOUT)
                    assert found, (
                        f"Prompt {prompt!r} nicht gefunden.\n"
                        + strip_ansi(session.transcript)
                    )
                    session.send_line(answer)
                code = session.wait_exit(TIMEOUT)
                text = strip_ansi(session.transcript)
            finally:
                session.close()
            return code, text, list(server.requests)
    finally:
        shutil.rmtree(home, ignore_errors=True)


def _run_pipe(*args: str) -> tuple[int, str, str, list]:
    home = _workspace()
    try:
        with FakeServer(SPEC, REPO) as server:
            env = _environment(server, home)
            proc = subprocess.run(
                _command(*args),
                cwd=str(REPO),
                env=env,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=TIMEOUT,
            )
            return proc.returncode, proc.stdout, proc.stderr, list(server.requests)
    finally:
        shutil.rmtree(home, ignore_errors=True)


def test_sitzung_neu_zeigt_warnungen_fuer_baden_wuerttemberg():
    code, text, requests = _run_pty("neu", "--bundesland", "BW")

    assert code == 0, text
    assert "Neueste Warnungen" in text
    assert "Baden-Württemberg" in text
    assert "10 Treffer" in text
    assert "21.11.2026" in text
    assert "Parmentine Speisekartoffeln" in text
    assert "261121_22" in text
    assert any("lastChangeAfter=2026-11-09" in request.query for request in requests)
    assert any("baden-wuerttemberg" in request.query for request in requests)


def test_sitzung_suche_nach_pinienkerne():
    code, text, requests = _run_pty("suche", "Pinienkerne")

    assert code == 0, text
    assert "4 Treffer" in text
    assert "Pinienkerne" in text
    assert "06.11.2026" in text
    assert "dmBio Pinienkerne, 60 Gramm" in text
    assert "Alnatura Pinienkerne" in text
    assert "dennree Pinienkerne, 60 Gramm" in text
    assert any("Pinienkerne" in request.query for request in requests)


def test_sitzung_zeige_waehlt_dennree_im_terminal():
    code, text, requests = _run_pty(
        "zeige", "Pinienkerne", sends=(("Auswahl [1-", "3"),)
    )

    assert code == 0, text
    assert "Mehrere Treffer" in text
    assert "Auswahl [1-4]" in text
    assert "dennree Pinienkerne, 60 Gramm" in text
    assert "Haltbarkeit:" in text
    assert "Mindesthaltbarkeitsdatum 03.06.2027" in text
    assert "Hersteller:" in text
    assert "dennree GmbH" in text
    assert "Grund:" in text
    assert "Krankheitserreger" in text
    assert "Betroffene Bundesländer:" in text
    assert "Baden-Württemberg" in text
    assert "Vertrieb über:" in text
    assert "Empfehlung:" in text
    assert any(
        request.path.endswith("/261105_02_BY_Pinienkerne.html")
        for request in requests
    )


def test_zeige_ohne_tty_listet_kandidaten_und_endet_mit_2():
    code, stdout, stderr, _requests = _run_pipe("zeige", "Pinienkerne", "--json")

    assert code == 2, stderr
    payload = json.loads(stdout)
    assert payload["fehler"]["code"] == 2
    assert "dennree Pinienkerne, 60 Gramm" in stdout
