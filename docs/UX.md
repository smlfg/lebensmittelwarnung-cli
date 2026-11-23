# UX-Spec: lmw

`lmw` liest die offiziellen Lebensmittel- und Produktwarnungen von
lebensmittelwarnung.de (Bundesländer und BVL). Alle Abrufe sind lesende
GET-Requests. Es gibt keinen Login und keine schreibende Web-Aktion; deshalb
hat diese Spec keine `credential_env` und keine `ux-formsteps`. UX09 entfällt
damit als „keine schreibende Sitzung“ (SKIP ist zulässig).

Die Sitzungen sind am 23.11.2026 live gegen die echte Seite erkundet und für
den Fake-Server gekürzt. `LMW_HEUTE` macht die datumsabhängige Auswahl
(`--tage`) in Tests deterministisch.

## Meta

```ux-meta
{"tool": "lmw",
 "install": "pipx install git+https://github.com/smlfg/lebensmittelwarnung-cli",
 "base_url_env": "LMW_BASE_URL",
 "env": {"LMW_HEUTE": "2026-11-23"}}
```

## Sitzungen

### Installation und neueste Warnungen für ein Bundesland

Die erste Sitzung installiert das Werkzeug und zeigt die Warnungen der letzten
14 Tage, die Baden-Württemberg betreffen. Das Bundesland ist ein Name oder
Kürzel; die ID in der zweiten Zeile jedes Treffers ist die Kurz-ID für
`lmw zeige`.

```ux-session
$ pipx install git+https://github.com/smlfg/lebensmittelwarnung-cli
< lmw
$ lmw neu --bundesland BW
< Neueste Warnungen (Baden-Württemberg, letzte 14 Tage): 10 Treffer
< 21.11.2026  Parmentine Speisekartoffeln rot,1,5 Kilogramm
< Lebensmittel · Gesundheitsschädliche Substanz · ID 261121_22
< 19.11.2026  Appetiter Streichmettwurst fein
< Lebensmittel · Krankheitserreger · ID 261119_20
< Tipp: lmw zeige
! exit 0
```

### Nach einem Produkt suchen

Der Suchbegriff steht positional. Die Ausgabe nennt Datum, Produkt, Grund und
Kurz-ID, damit ein Mensch direkt mit `lmw zeige` weiterarbeiten kann.

```ux-session
$ lmw suche Pinienkerne
< 4 Treffer für „Pinienkerne“
< 06.11.2026  dmBio Pinienkerne, 60 Gramm
< 05.11.2026  Alnatura Pinienkerne und Alnatura Salatkerne-Mix
< 05.11.2026  dennree Pinienkerne, 60 Gramm
! exit 0
```

### Eine Meldung im Detail ansehen

Bei mehreren Treffern fragt `lmw zeige` im Terminal nach einer Nummer. Ohne TTY
gibt es stattdessen eine Liste und Exit 2; `--erster` wählt für Agenten den
ersten Treffer. Die Detailansicht zeigt die Felder der Meldungsseite lesbar
untereinander.

```ux-session
$ lmw zeige Pinienkerne
< Mehrere Treffer für „Pinienkerne“
< 3) 05.11.2026  dennree Pinienkerne, 60 Gramm
< Auswahl [1-4]:
> 3
< dennree Pinienkerne, 60 Gramm
< Haltbarkeit: Mindesthaltbarkeitsdatum 03.06.2027 und 16.06.2027
< Hersteller: dennree GmbH, Hofer Straße 11, 95183 Töpen
< Grund: Krankheitserreger
< Betroffene Bundesländer: Baden-Württemberg, Bayern, Berlin
< Vertrieb über: Die Ware ist bei Denns BioMarkt
< Empfehlung: Empfehlung der Firma dennree GmbH
! exit 0
```

## Lesende Routen

Die Liste für `lmw neu` nutzt die Expertensuche mit Bundesland- und
Datumsfilter. `lmw suche` nutzt dieselbe Route mit `templateQueryString`.
`lmw zeige` sucht zuerst und lädt danach die Meldungsseite. `path` wird ohne
Querystring verglichen; die Reihenfolge entscheidet bei gleichem Pfad.

```ux-routes
[{"method":"GET","path":"/SiteGlobals/Forms/Suche/Expertensuche/Expertensuche_Formular.html","query_contains":"lastChangeAfter=2026-11-09","response":"tests/fixtures/ux/liste_neu_bw.html","status":200,"content_type":"text/html; charset=utf-8"},
 {"method":"GET","path":"/SiteGlobals/Forms/Suche/Expertensuche/Expertensuche_Formular.html","query_contains":"Pinienkerne","response":"tests/fixtures/ux/suche_pinienkerne.html","status":200,"content_type":"text/html; charset=utf-8"},
 {"method":"GET","path":"/___lebensmittelwarnung.de/Meldungen/2026/11_November/261105_02_BY_Pinienkerne/261105_02_BY_Pinienkerne.html","response":"tests/fixtures/ux/detail_dennree.html","status":200,"content_type":"text/html; charset=utf-8"}]
```

## Keine schreibende Aktion

`lmw` verändert keine Daten auf der Website. Damit entfallen `ux-formsteps`,
`credential_env`, `login`, die `[j/N]`-Bestätigung und UX09. Watch speichert nur
lokal die zuletzt gesehenen IDs unter `~/.local/state/lebensmittelwarnung-cli`
(0600) und sendet ausschließlich lesende GET-Requests.
