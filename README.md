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

## Was das Werkzeug kann

- `lmw neu`: neueste Warnungen, optional nach Bundesland, Grund, Typ und
  Zeitraum (`--tage`) gefiltert.
- `lmw suche BEGRIFF`: Volltextsuche nach Produkt, Marke oder Hersteller, mit
  denselben Filtern.
- `lmw zeige ID|BEGRIFF`: Detailansicht mit Produkt, Haltbarkeit, Charge,
  Hersteller, Grund, möglichen Folgen, betroffenen Bundesländern und Vertrieb.
- `lmw watch [BEGRIFF]`: meldet nur Warnungen, die seit dem letzten Aufruf neu
  sind; der Zustand liegt unter `~/.local/state/lebensmittelwarnung-cli` (0600).
- `lmw config bundesland NAME`: merkt sich ein Bundesland für spätere Aufrufe.

Die Basis-URL ist für Tests und eigene Gateways über `LMW_BASE_URL`
überschreibbar. Datumsabhängige Befehle akzeptieren `LMW_HEUTE=JJJJ-MM-TT` für
deterministische Läufe.

## Entwicklung

Die UX-Spec steht in [docs/UX.md](docs/UX.md), die Fixtures liegen unter
`tests/fixtures/ux/`.

```bash
python3 tests/harness/ux_check.py . --spec-only
```
