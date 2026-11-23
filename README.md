# lebensmittelwarnung-cli

Offizielle Lebensmittel- und Produktwarnungen der Bundesländer und des BVL im
Terminal. `lmw` liest die Meldungen von [lebensmittelwarnung.de](https://www.lebensmittelwarnung.de),
sucht nach Produkt oder Marke, filtert nach Bundesland, Grund und Typ und zeigt
die vollständige Meldung. Alle Abrufe sind lesend; ein Konto ist nicht nötig.

## Schnellstart

```bash
pipx install git+https://github.com/smlfg/lebensmittelwarnung-cli
lmw neu --bundesland BW
lmw suche Pinienkerne
lmw zeige Pinienkerne
```

Bei mehreren Treffern fragt `lmw zeige` nach einer Nummer. Für Skripte und
Agenten gibt es `--json` und `--erster`.

## Befehle

```bash
lmw neu --bundesland BW --tage 7
lmw neu --grund allergene --typ lebensmittel
lmw suche dennree --bundesland Bayern
lmw zeige 261105_02
lmw zeige Pinienkerne --erster --json
lmw watch "Pinienkerne" --bundesland BW
lmw config bundesland Baden-Württemberg
```

- `lmw neu`: neueste Warnungen, optional nach Bundesland, Grund, Typ und
  Zeitraum (`--tage`) gefiltert.
- `lmw suche BEGRIFF`: Volltextsuche nach Produkt, Marke oder Hersteller, mit
  denselben Filtern.
- `lmw zeige ID|BEGRIFF`: Detailansicht mit Produkt, Haltbarkeit, Charge,
  Hersteller, Grund, möglichen Folgen, betroffenen Bundesländern und Vertrieb.
  Ohne TTY und ohne `--erster` gibt es eine Liste und Exit 2.
- `lmw watch [BEGRIFF]`: meldet nur Warnungen, die seit dem letzten Aufruf neu
  sind; der Zustand liegt unter `~/.local/state/lebensmittelwarnung-cli` (0600).
- `lmw config bundesland NAME|KÜRZEL`: merkt sich ein Bundesland für spätere
  Aufrufe; `lmw config pfad` zeigt die Konfigurationsdatei.

Ausgabe ist im Terminal für Menschen lesbar. Mit `--json` oder wenn stdout
kein Terminal ist, kommt genau ein JSON-Objekt. Details zu Flags, JSON-Feldern
und Pfaden stehen in [INTERFACE.md](INTERFACE.md).

## Konfiguration

| Einstellung | Standard | Zweck |
|---|---|---|
| `LMW_BASE_URL` | `https://www.lebensmittelwarnung.de` | Basis-URL, z. B. für einen Fake-Server. |
| `LMW_HEUTE` | lokales Datum | Testdatum `JJJJ-MM-TT` für `--tage`. |
| Konfiguration | `~/.config/lebensmittelwarnung-cli/config.json` (0600) | gemerktes Bundesland. |
| Watch-Zustand | `~/.local/state/lebensmittelwarnung-cli/state.json` (0600) | zuletzt gesehene IDs. |
| Cache | `~/.cache/lebensmittelwarnung-cli/` | Antworten für 10 Minuten. |

`XDG_CONFIG_HOME`, `XDG_STATE_HOME` und `XDG_CACHE_HOME` werden respektiert.

## Exit-Codes

| Code | Bedeutung |
|---|---|
| 0 | Erfolg, auch bei „keine Treffer“. |
| 1 | Allgemeiner Fehler (Konfiguration, Zustand, unerwartet). |
| 2 | Aufruffehler, unbekannter Filter oder mehrdeutige Auswahl ohne TTY. |
| 3 | Netz- oder Quellenfehler. |
| 4 | Login erforderlich (für `lmw` derzeit unbenutzt). |
| 130 | Abbruch mit Strg+C/EOF. |

## Hinweis

`lmw` ist ein inoffizielles Werkzeug und kein Angebot des BVL oder der
Bundesländer. Maßgeblich ist immer die Meldung auf lebensmittelwarnung.de.
Die Website kann sich ändern; Abrufe sind höflich (ein Request pro Sekunde,
Cache, User-Agent mit Repo-URL).

## Entwicklung

Die UX-Spec steht in [docs/UX.md](docs/UX.md), die Anforderungen in
[ANFORDERUNGEN.md](ANFORDERUNGEN.md), die Schnittstelle in
[INTERFACE.md](INTERFACE.md). Fixtures liegen unter `tests/fixtures/ux/`.

```bash
python3 tests/harness/ux_check.py . --spec-only
python3 -m pytest -q tests/harness
```

## Lizenz

MIT, Copyright (c) 2026 smlfg. Siehe [LICENSE](LICENSE).
