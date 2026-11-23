# Pflicht-QA: lmw

- Datum: 2026-11-23
- Version: `lmw 0.1.0`
- Commit: `e3cb3b6` (docs(ux): UX-Gate-Bericht)
- Prüfer: separate QA-Iteration (nicht der Entwickler), keine Code-Fixes
- Nachprüfung S6: F1-F3 behoben und live erneut geprüft (siehe Ergebnis-Tabelle)
- Installation: `pipx install git+https://github.com/smlfg/lebensmittelwarnung-cli`
  in `./scratch/pipx` (Protokoll `scratch/qa/pipx-install.log`), Aufruf nur über
  `PATH=$PWD/scratch/pipx/bin:$PATH`
- Live-Zugriffe: ausschließlich lesende GET-Requests gegen
  `https://www.lebensmittelwarnung.de`; HOME/XDG lagen unter `scratch/qa/`
- Fake-Server: `tests/harness/fake_server.py` mit den `ux-routes` aus
  `docs/UX.md`, Sitzungen im Pseudo-Terminal (`script -e -qc`)

## Ergebnisse

| # | Prüfung | Befehl | Erwartet | Ergebnis | Beleg (gekürzt) |
|---|---|---|---|---|---|
| Q01 | Frische pipx-Installation | `cat scratch/qa/pipx-install.log` | Erfolg, `lmw` im PATH | OK | `installed package lebensmittelwarnung-cli 0.1.0 ... - lmw` |
| Q02 | README-Installationszeile im pty | `script -e -qc "pipx install git+https://github.com/smlfg/lebensmittelwarnung-cli"` | Exit 0 | OK | 1. Versuch transienter Git-Fetch (`curl 92`), 2. Versuch `done!` Exit 0 |
| Q03 | Version | `lmw --version` | Exit 0, Version | OK | `lmw 0.1.0`, Exit 0 |
| Q04 | Haupt-Hilfe | `lmw --help` | Exit 0, Befehle sichtbar | OK | `{neu,suche,zeige,watch,config}`, Exit 0 |
| Q05 | Hilfe aller Unterkommandos | `lmw <sub> --help` | Exit 0 | OK | alle fünf Exit 0 |
| Q06 | Verständliche Optionshilfe | `lmw neu --help` | Bedeutung der Flags erklärt | OK (nach Fix eb042b3) | `--bundesland`, `--grund`, `--typ`, `--tage`, `--limit`, `--json` mit Bedeutung, Werten und Defaults (`Standard: 14`, `1-100`), Exit 0 |
| Q07 | README `neu` live im pty | `script -e -qc "lmw neu --bundesland BW"` | Text, 10 Treffer, Exit 0 | OK | `Neueste Warnungen (Baden-Württemberg, letzte 14 Tage): 10 Treffer` |
| Q08 | README `suche` live im pty | `script -e -qc "lmw suche Pinienkerne"` | Text, 4 Treffer, Exit 0 | OK | `4 Treffer für „Pinienkerne“`, IDs 261106_04, 261105_03, 261105_02, 260130_18 |
| Q09 | README `zeige` live im pty | `printf '3\n' \| script -e -qc "lmw zeige Pinienkerne"` | Auswahl per Nummer, Details, Exit 0 | OK | Liste, `Auswahl [1-4]:`, dennree-Details, Exit 0 |
| Q10 | Sortierung `neu` | `lmw neu --bundesland BW` | absteigend nach Datum | OK | 23.11., 21.11., 19.11., 18.11., … 09.11. |
| Q11 | Suchplausibilität | `lmw suche Pinienkerne` | Produkte zum Begriff | OK | drei Pinienkern-Produkte plus ein Treffer der Quelle (Tomate & Feta) |
| Q12 | Detailfelder und Entities | `lmw zeige 261105_02` | Produkt, MHD, Charge, Hersteller, Grund, Folgen, Länder, Vertrieb | OK | `Hofer Straße`, `Töpen`, `Mögliche Folgen`, `Betroffene Bundesländer` korrekt |
| Q13 | Mehrdeutig ohne TTY | `lmw zeige Pinienkerne` | Liste + `--erster`-Hinweis, Exit 2 | OK | JSON-Fehler `code 2`, `hinweis: Wähle mit --erster ...` |
| Q14 | Agentenauswahl | `lmw zeige Pinienkerne --erster --json` | genau ein JSON-Objekt, Exit 0 | OK | valides Detailobjekt, Exit 0 |
| Q15 | Ungültige Auswahl | `printf '9\nfoo\n3\n' \| script -e -qc "lmw zeige Pinienkerne"` | erneut fragen, dann Details | OK | zweimal `Ungültige Auswahl. Bitte 1-4 eingeben.`, dann dennree |
| Q16 | EOF bei Auswahl | `printf '' \| script -e -qc "lmw zeige Pinienkerne"` | Exit 2, kein Traceback | OK | `Fehler: Keine Auswahl getroffen...`, Exit 2 |
| Q17 | Strg+C bei Auswahl | pty-Harness sendet `SIGINT` | Exit 130, kein Traceback | OK | `Abgebrochen.`, Exit 130 |
| Q18 | Suche ohne Treffer | `script -e -qc "lmw suche zzzqqqxyz"` | Exit 0, Meldung | OK | `Keine Treffer für „zzzqqqxyz“.`, Exit 0 |
| Q19 | Detail ohne Treffer | `script -e -qc "lmw zeige zzzqqqxyz"` | Exit 2, nächster Schritt | OK | `Prüfe den Suchbegriff mit lmw suche BEGRIFF`, Exit 2 |
| Q20 | Leere Filterliste | `lmw neu --bundesland Bremen --grund irrefuehrungundtaeuschung --tage 2 --json` | Exit 0, leere Liste | OK | `{"anzahl": 0, "treffer": []}`, Exit 0 |
| Q21 | Datumsfilter | `lmw neu --tage 3 --limit 100 --json` | alle Einträge im Fenster | OK | Bezug 2026-11-23, Grenze 2026-11-20, 3 Treffer, 0 Ausreißer |
| Q22 | Limit | `lmw neu --bundesland BW --tage 7 --limit 3` | höchstens 3 | OK | `3 Treffer` |
| Q23 | Grund-Filter über alle Treffer | `lmw neu --grund G --tage 3650 --limit 100 --json` für alle sechs Gründe | jeder Treffer passt | OK | krankheitserreger 62, fremdkoerper 44, gesundheitsschaedlichesubstanz 75, irrefuehrungundtaeuschung 1, rueckstaendeundkontaminaten 44, sonstigegruende 31; je 0 Ausreißer |
| Q24 | Typ-Filter Blatt/Leaf | `lmw neu --typ babyundkinderprodukte` bzw. `.../lebensmittel/fleischundwurstwaren` | Treffer, Typ passt | OK | 3 Baby-Treffer; 14 Fleisch-/Wursttreffer (Anzeige `Lebensmittel`) |
| Q25 | Typ-Filter Elternkategorie | `lmw neu --typ lebensmittel --tage 3650 --limit 100 --json` (auch `bedarfsgegenstaende`, `kosmetischemittel`) | Treffer aller Untertypen | OK (nach Fix 2c6b1fe, 45e395c) | `lebensmittel` 97, `bedarfsgegenstaende` 34, `kosmetischemittel` 5 Treffer; Blatt `lebensmittel/fleischundwurstwaren` 14, `bedarfsgegenstaende/spielwaren` 17; alle Typen passend |
| Q26 | Bundesland-Schreibvarianten | `--bundesland BW, "Baden-Württemberg", "baden wuerttemberg", "BaWü", bawue` | gleiche Treffer | OK | je 3 Treffer, IDs `261112_13, 261121_22, 261119_20` |
| Q27 | Bundesland-Quellfilter wirksam | `lmw neu --tage 3650 --limit 100` vs. `--bundesland Bremen` | unterschiedliche Mengen | OK | ungefiltert 98, Bremen 98, aber 34 IDs nur in je einer Menge |
| Q28 | Bundesland semantisch | `lmw zeige ID` für 8 Bremer Treffer | `Bremen` in betroffenen Ländern | OK | 8/8 enthalten `Bremen` |
| Q29 | Mehrfachfilter | `lmw neu --bundesland "BW,Bayern" ...`; `--grund allergene --grund fremdkoerper`; `--grund allergene,fremdkoerper` | Vereinigung der Treffer | OK (nach Fix dbaeeb8, 45e395c) | Grund mehrfach 69 = Vereinigung 25 (`allergene`) + 44 (`fremdkoerper`); kommagetrennt ebenfalls 69; `BW,Bayern` 5 = Vereinigung 5 + 5 |
| Q30 | Umlaute/Tippvarianten bei Grund/Typ | `--grund Fremdkörper`, `fremdkoerper`, `Baby`, `Baby- und Kinderprodukte` | gleiche Treffer | OK | jeweils Exit 0 und passende Treffer |
| Q31 | Unbekannte Filterwerte | `lmw neu --grund quatsch`, `--bundesland Atlantis`, `--typ raumschiff` | Exit 2, erlaubte Werte | OK | `Unbekanntes ... Erlaubt: ...`, Exit 2 |
| Q32 | Ungültige Zahlen | `lmw neu --limit 0`, `--tage -1` | Exit 2 | OK | `muss eine positive ganze Zahl sein`, Exit 2 |
| Q33 | Netzfehler | `LMW_BASE_URL=http://127.0.0.1:1 script -e -qc "lmw neu ..."` | Exit 3, Text, nächster Schritt, kein Traceback | OK | `Fehler: Netzwerkfehler ... Prüfe deine Internetverbindung ...`, Exit 3 |
| Q34 | Basis-URL ohne Schema | `LMW_BASE_URL=example.invalid lmw neu` | Exit 2, kein Request | OK | `muss mit http:// oder https:// beginnen`, Exit 2 |
| Q35 | Ungültiges `LMW_HEUTE` | `LMW_HEUTE=2026-13-99 lmw neu` | Exit 2, kein Traceback | OK | `LMW_HEUTE ist kein Datum im Format JJJJ-MM-TT`, Exit 2 |
| Q36 | JSON Liste | `lmw neu --limit 2 --json` | genau ein valides Objekt | OK | `json.load` erfolgreich, Schlüssel `abfrage, anzahl, treffer` |
| Q37 | JSON Detail | `lmw zeige 261105_02 --json` | valides Detailobjekt | OK | Pflichtfelder inkl. `charge`, `vertrieb`, `bundeslaender` |
| Q38 | JSON Watch/Config | `lmw watch ... --json`, `lmw config bundesland --json` | valide Objekte | OK | Watch `neu, anzahl_neu, gesehen, erster_lauf`; Config `bundesland, slug, pfad` |
| Q39 | JSON Fehlerobjekt | `LMW_BASE_URL=http://127.0.0.1:1 lmw neu` | genau ein JSON-Objekt | OK | `{"fehler": {"code": 3, "art": "netz", ...}}` |
| Q40 | TTY Text statt JSON | `script -e -qc "lmw config bundesland"` | Klartext | OK | `Bundesland: Baden-Württemberg (baden-wuerttemberg)` |
| Q41 | Fake-Server Sitzungen | `neu`, `suche`, `zeige` mit `LMW_BASE_URL` | dokumentierte Ausgaben | OK | 10 Treffer, 4 Treffer, Auswahl 3 → dennree; alle Requests am Fake-Server |
| Q42 | Fake-Server Watch/Config | `watch`, `config bundesland`, `neu` | erster Lauf, keine neuen, Config genutzt | OK | `Erster Lauf: 4 Warnungen gespeichert`, `Keine neuen Warnungen.`, `Bundesland gespeichert: Bayern` |
| Q43 | Watch-Zustand | zwei Läufe, dann Netzfehler | 0600, atomar, Fehler erhält Zustand | OK | `600 .../state.json`; nach Fehlerlauf identische Prüfsumme |
| Q44 | Config Datei | `lmw config bundesland ...`, `config pfad` | 0600, von `neu` genutzt | OK | `600 .../config.json`; `neu` zeigt `(Baden-Württemberg, letzte 7 Tage)` |
| Q45 | HTTP-Cache | nach Live-Aufrufen | Dateien 0600, Verzeichnis 0700 | OK | `700 lebensmittelwarnung-cli`, Einträge `600 ...json` |
| Q46 | Schnellstart = UX-Sessions | `python3 tests/harness/ux_check.py . --spec-only` | UX01/UX06/UX07 PASS | OK | Bericht PASS |
| Q47 | Testsuite | `scratch/venv/bin/pytest -q` | grün | OK | `75 passed` (nach den Fix-Tests; vorher 69) |
| Q48 | Keine Secrets/PII in QA-Ausgaben | Sichtprüfung der Logs | keine Zugangsdaten/Personendaten | OK | nur öffentliche Meldungs- und Firmendaten |

## Zählung

- OK: 48
- FAIL: 0
- Gesamt: 48

## Offene FAILs

Keine. F1-F3 wurden behoben und am 2026-11-23 live erneut geprüft (Belege in
den Zeilen Q06, Q25 und Q29).

## Hinweise (kein FAIL)

- Der erste erneute `pipx install`-Lauf scheiterte an einem transienten
  Git-Fetch (`curl 92`, HTTP/2-CANCEL); der zweite Lauf war grün.
- `--bundesland` ist laut INTERFACE ein Quellfilter (Bundesland der Meldung),
  nicht der Filter „Betroffene Bundesländer“. Die Stichprobe (8/8 Bremen)
  passt; einzelne Meldungen können laut Quelle abweichen.
- `--typ mittelzumtaetowieren` liefert aktuell 0; auch die Quelle hat dafür
  keine Meldungen, daher kein Fehler.
- Das UX-Gate (`tests/harness/`) wurde nicht verändert.
