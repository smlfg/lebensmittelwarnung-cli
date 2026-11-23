# UX-Gate-Bericht

- Datum: 23.11.2026
- Repo: `smlfg/lebensmittelwarnung-cli`
- Tool: `lmw`
- Ergebnis: PASS

## ux_check.py

`python3 tests/harness/ux_check.py . --report scratch/ux_check.md` — Exit-Code `0`.

| ID | Ergebnis | Befund |
|---|---|---|
| UX00 | PASS | 4 Request(s) am Fake-Server, keine Fremdverbindung |
| UX01 | PASS | docs/UX.md: 3 Sitzungen, 0 formsteps |
| UX02 | PASS | keine Credential-Env-Variablen gefunden |
| UX03 | PASS | --help, --version und 5 Unterkommandos mit Exit 0 |
| UX04 | PASS | 5 Unterkommandos ohne Pflicht-Option statt positional |
| UX05 | PASS | 3 Sitzungen ohne JSON/Traceback im TTY |
| UX06 | PASS | Schnellstart: 3 Tool-Befehle, Installation passt |
| UX07 | PASS | keine ux-formsteps, keine schreibende Aktion |
| UX08 | PASS | keine ux-formsteps, keine schreibende Aktion |
| UX09 | SKIP | keine schreibende Sitzung |

## ux_session.py

`python3 tests/harness/ux_session.py . --report scratch/ux_session.md` — Exit-Code `0`.

| Sitzung | Lauf | Ergebnis | Befund |
|---|---|---|---|
| Installation und neueste Warnungen für ein Bundesland | 1 | PASS | OK |
| Nach einem Produkt suchen | 1 | PASS | OK |
| Eine Meldung im Detail ansehen | 1 | PASS | OK |

## Fixes

- `fix(ux): Installationserwartung aus erster Sitzung entfernen` — die Zeile
  `< lmw` nach dem übersprungenen Installationsbefehl war keine Ausgabe eines
  laufenden Befehls und ließ `ux_session.py` scheitern.

Hinweis: Beide Gates legen ihr venv standardmäßig unter `scratch/ux-venv` an und
löschen es zu Beginn. Sie werden deshalb nacheinander ausgeführt; ein paralleler
Start führt zum Konflikt bei `ensurepip`.
