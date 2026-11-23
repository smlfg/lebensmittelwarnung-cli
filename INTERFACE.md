# Schnittstelle: lmw

Konsolenbefehl: `lmw` (Python-Paket `lebensmittelwarnung_cli`, aufrufbar auch
mit `python3 -m lebensmittelwarnung_cli`). Python ≥ 3.10, Abhängigkeiten nur
`httpx` oder `requests`; HTML-Parsing mit der Standardbibliothek
(`html.parser`), optional `beautifulsoup4`.

```text
lmw [--version] [--help] {neu,suche,zeige,watch,config} ...
```

`lmw --version` und `lmw --help` sowie `lmw <unterkommando> --help` enden mit
Exit 0. Fehler nennen den nächsten Schritt und geben nie einen Traceback aus,
auch nicht bei Strg+C oder EOF.

## Gemeinsame Optionen

Diese Optionen gelten für `neu`, `suche`, `zeige` und `watch`, sofern unten
nicht anders beschrieben:

| Option | Bedeutung |
|---|---|
| `--json` | Ausgabe als genau ein JSON-Objekt auf stdout. Ohne TTY (Pipe/Agent) wird ebenfalls JSON ausgegeben, auch ohne Flag. |
| `--bundesland NAME\|KÜRZEL` | Bundesland-Filter; mehrfach oder kommagetrennt erlaubt. Namen und Kürzel sind tippfehler- und umlauttolerant (`BW`, `Baden-Württemberg`, `baden wuerttemberg`, `BaWü`). Ohne Angabe gilt der Wert aus `lmw config bundesland`, falls gesetzt. |
| `--grund GRUND` | Grund-Filter; mehrfach erlaubt. Slugs oder deutsche Anzeigenamen (`allergene`, `Allergene`, `krankheitserreger`, `Fremdkörper`, …). |
| `--typ TYP` | Produkttyp; mehrfach erlaubt (`lebensmittel`, `bedarfsgegenstaende`, `babyundkinderprodukte`, `kosmetischemittel`, `mittelzumtaetowieren`, auch Untertypen wie `lebensmittel/fleischundwurstwaren`). |
| `--tage N` | Zeitfenster in Tagen, positive ganze Zahl. `neu` nutzt 14, wenn nichts angegeben ist; `suche` und `watch` ohne Angabe unbegrenzt. Bezugstag ist `LMW_HEUTE`, sonst das lokale Datum. Ungültige Werte → Exit 2. |
| `--limit N` | Höchstens N Treffer ausgeben (positive ganze Zahl, Standard 20, Maximum 100). Weitere Seiten werden nur geladen, wenn nötig. |

Unbekannte Filterwerte werden nicht still ignoriert: `lmw` nennt den
unbekannten Wert, die erlaubten Werte und endet mit Exit 2.

## `lmw neu`

Neueste Warnungen, absteigend nach Datum.

```text
lmw neu [--bundesland NAME|KÜRZEL] [--grund GRUND] [--typ TYP]
        [--tage N] [--limit N] [--json]
```

Textausgabe (TTY):

```text
Neueste Warnungen (Baden-Württemberg, letzte 14 Tage): 10 Treffer
21.11.2026  Parmentine Speisekartoffeln rot,1,5 Kilogramm
Lebensmittel · Gesundheitsschädliche Substanz · ID 261121_22
...
```

## `lmw suche BEGRIFF`

Volltextsuche. `BEGRIFF` ist ein Pflicht-Positional und darf Leerzeichen
enthalten. Keine Treffer sind kein Fehler: Text „Keine Treffer für …“, Exit 0.

```text
lmw suche BEGRIFF [--bundesland NAME|KÜRZEL] [--grund GRUND] [--typ TYP]
                  [--tage N] [--limit N] [--json]
```

Textausgabe:

```text
4 Treffer für „Pinienkerne“
06.11.2026  dmBio Pinienkerne, 60 Gramm
...
```

## `lmw zeige AUSWAHL`

`AUSWAHL` ist eine Kurz-ID (`261105_02`) oder ein Suchbegriff. Eine Kurz-ID
wird zuerst gegen die Trefferliste geprüft; passt sie genau, wird direkt
geladen.

```text
lmw zeige AUSWAHL [--erster] [--json]
```

- Genau ein Treffer: Detailansicht sofort.
- Mehrere Treffer im TTY: nummerierte Liste und Frage `Auswahl [1-N]: ` auf
  stderr. Eingabe einer Nummer lädt die Detailseite. Leere Eingabe, EOF oder
  Strg+C beenden ohne Request mit Exit 2 bzw. 130.
- Mehrere Treffer ohne TTY und ohne `--erster`: nummerierte Liste auf stderr,
  Hinweis auf `--erster`, Exit 2. Mit `--json` ist die Liste Teil des
  JSON-Fehlerobjekts.
- `--erster` wählt ohne Nachfrage den ersten Treffer (für Agenten).
- Ungültige Auswahl: erneut fragen, höchstens drei Mal, dann Exit 2.

Textausgabe der Detailansicht (fehlende Felder werden übersprungen):

```text
dennree Pinienkerne, 60 Gramm
Haltbarkeit: Mindesthaltbarkeitsdatum 03.06.2027 und 16.06.2027
Hersteller: dennree GmbH, Hofer Straße 11, 95183 Töpen
Grund: Krankheitserreger
Betroffene Bundesländer: Baden-Württemberg, Bayern, Berlin
Vertrieb über: Die Ware ist bei Denns BioMarkt ...
Empfehlung: Empfehlung der Firma dennree GmbH ...
```

## `lmw watch [BEGRIFF]`

Meldet nur Meldungs-IDs, die noch nicht im lokalen Zustand stehen. Der erste
Lauf legt den Zustand an und meldet die aktuellen Treffer als Ausgangsbasis
(Text: „Erster Lauf: N Warnungen gespeichert“). Spätere Läufe geben nur neue
IDs aus; ohne neue Treffer: „Keine neuen Warnungen.“ Exit 0.

```text
lmw watch [BEGRIFF] [--bundesland NAME|KÜRZEL] [--grund GRUND] [--typ TYP]
          [--tage N] [--limit N] [--json]
```

Der Zustand wird nach jeder erfolgreichen Abfrage atomar aktualisiert
(Tempdatei im selben Verzeichnis, dann `os.replace`). Schlägt die Abfrage fehl,
bleibt der alte Zustand erhalten.

## `lmw config`

```text
lmw config bundesland [NAME|KÜRZEL]   # ohne Argument: aktuellen Wert zeigen
lmw config pfad                      # Pfad der Konfigurationsdatei zeigen
```

`lmw config bundesland Baden-Württemberg` speichert Name und Slug. Namen und
Kürzel werden wie bei `--bundesland` normalisiert. Unbekannte Namen → Exit 2
mit Liste der erlaubten Bundesländer. Die Datei wird mit Rechten 0600
angelegt. Ohne gespeichertes Bundesland und ohne `--bundesland` arbeitet `neu`
bundesweit.

## Ausgabeformate

### Text

Für Menschen lesbar, eine Meldung pro Treffer mit Datum, Titel, Typ, Grund und
Kurz-ID. Kein JSON am Terminalanfang, keine Tracebacks. Farben sind optional
und werden bei `NO_COLOR` oder nicht-TTY abgeschaltet.

### JSON

Mit `--json` oder wenn stdout kein TTY ist, steht auf stdout genau ein
JSON-Objekt. Prompts und Hinweise gehen auf stderr. Datumsangaben sind
ISO-8601 (`JJJJ-MM-TT`) oder `null`.

Trefferobjekt:

```json
{
  "id": "261121_22",
  "datum": "2026-11-21",
  "titel": "Parmentine Speisekartoffeln rot,1,5 Kilogramm",
  "typ": "Lebensmittel",
  "gruende": ["Gesundheitsschädliche Substanz"],
  "bundeslaender": [],
  "url": "https://www.lebensmittelwarnung.de/___lebensmittelwarnung.de/..."
}
```

Liste (`neu`, `suche`):

```json
{
  "abfrage": {"begriff": null, "bundesland": ["Baden-Württemberg"], "tage": 14, "limit": 20},
  "anzahl": 10,
  "treffer": [ /* Trefferobjekte */ ]
}
```

Detail (`zeige`):

```json
{
  "id": "261105_02",
  "datum": "2026-11-05",
  "titel": "dennree Pinienkerne, 60 Gramm",
  "typ": "Lebensmittel",
  "produkt": "…",
  "haltbarkeit": "…",
  "verpackungseinheit": "…",
  "charge": "…",
  "hersteller": "…",
  "gruende": ["Krankheitserreger"],
  "weitere_informationen": "…",
  "moegliche_folgen": "…",
  "bundeslaender": ["Baden-Württemberg", "Bayern", "Berlin"],
  "vertrieb": "…",
  "empfehlung": "…",
  "erstveroeffentlichung": "2026-11-05",
  "aktualisiert": "2026-11-06",
  "url": "…"
}
```

Watch:

```json
{"neu": [ /* Trefferobjekte */ ], "anzahl_neu": 0, "gesehen": 42, "erster_lauf": false}
```

Config:

```json
{"bundesland": "Baden-Württemberg", "slug": "baden-wuerttemberg", "pfad": "/home/…/config.json"}
```

Fehlerobjekt (Exit-Code wie unten):

```json
{"fehler": {"code": 2, "art": "usage", "meldung": "Unbekanntes Bundesland: …"}}
```

## Exit-Codes

| Code | Bedeutung |
|---|---|
| 0 | Erfolg, auch bei „keine Treffer“ oder „keine neuen Warnungen“. |
| 1 | Allgemeiner Fehler: Konfiguration/Zustand nicht lesbar oder schreibbar, unerwarteter interner Fehler (ohne Traceback). |
| 2 | Aufruffehler: unbekanntes Argument/Filter, ungültige Zahl, fehlender Suchbegriff, mehrdeutige Auswahl ohne TTY, abgebrochene Auswahl. |
| 3 | Netz- oder Quellenfehler: Timeout, DNS, HTTP ≥ 400, unerwartete/leere Antwort, Parserfehler. |
| 4 | Login erforderlich. Für `lmw` derzeit unbenutzt (die Quelle ist ohne Login lesbar); reserviert für künftige Quellen. |
| 130 | Abbruch durch Strg+C/EOF, ohne Traceback. |

## Umgebungsvariablen

| Variable | Bedeutung |
|---|---|
| `LMW_BASE_URL` | Basis-URL, Standard `https://www.lebensmittelwarnung.de`. Für Tests/Fake-Server überschreiben. Ohne Schema → Exit 2, kein Request. |
| `LMW_HEUTE` | Testdatum `JJJJ-MM-TT` für `--tage` und „neu seit“. Nur für deterministische Tests; menschen nutzen das lokale Datum. |
| `NO_COLOR` | Deaktiviert Farben. |
| `XDG_CONFIG_HOME`, `XDG_STATE_HOME`, `XDG_CACHE_HOME` | Überschreiben die Basisverzeichnisse für Konfiguration, Zustand und Cache. |

`LMW_BASE_URL` ist die einzige URL-Quelle; es gibt keine hartcodierte
Produktions-URL in Tests. Zugangsdaten werden nicht benötigt und nicht gelesen.

## Lokale Pfade und Rechte

| Zweck | Standardpfad | Rechte |
|---|---|---|
| Konfiguration | `$XDG_CONFIG_HOME/lebensmittelwarnung-cli/config.json`, sonst `~/.config/lebensmittelwarnung-cli/config.json` | Datei 0600, Verzeichnis 0700 |
| Watch-Zustand | `$XDG_STATE_HOME/lebensmittelwarnung-cli/state.json`, sonst `~/.local/state/lebensmittelwarnung-cli/state.json` | Datei 0600, Verzeichnis 0700 |
| HTTP-Cache | `$XDG_CACHE_HOME/lebensmittelwarnung-cli/`, sonst `~/.cache/lebensmittelwarnung-cli/` | Verzeichnis 0700, Einträge max. 10 Minuten gültig |

Die Pfade werden nur bei Bedarf angelegt. Nichts davon liegt im
Arbeitsverzeichnis oder im Repo.

## Netzverhalten

- Ausschließlich GET; ein User-Agent mit Repo-URL
  (`lebensmittelwarnung-cli/0.1 (+https://github.com/smlfg/lebensmittelwarnung-cli)`).
- Höchstens ein Request pro Sekunde, Cache 10 Minuten. Fehlgeschlagene
  Antworten werden nicht gecacht.
- Vor dem Parsen wird der HTTP-Status geprüft. Eine 200-Antwort ohne
  Trefferliste ist „keine Treffer“, eine 200-Antwort mit unerwarteter Struktur
  ist Exit 3.
- Bundesländer stehen in der Liste nicht zur Verfügung; `--bundesland` wirkt
  deshalb als Quellfilter. Grund, Typ und Datum werden zusätzlich clientseitig
  gegen jeden Treffer geprüft.
- HTML-Entities werden korrekt aufgelöst (`&amp;`, `&szlig;`, Umlaute,
  `&#8222;`).
