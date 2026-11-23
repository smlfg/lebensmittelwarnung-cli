# Anforderungen: lmw

## Zweck

`lmw` macht die offiziellen Lebensmittel- und Produktwarnungen der
Bundesländer und des Bundesamts für Verbraucherschutz und Lebensmittelsicherheit
(BVL) im Terminal lesbar. Das Werkzeug beantwortet die Fragen „Was ist gerade
neu?“, „Gibt es einen Rückruf zu Produkt X?“ und „Welche Warnungen betreffen
mein Bundesland?“ ohne Browser und ohne Konto.

Alle Abrufe sind lesende GET-Requests an lebensmittelwarnung.de. Es gibt keine
Anmeldung, keine Cookies und keine schreibende Aktion. `lmw` ist ein
inoffizielles Werkzeug und kein Angebot des BVL oder der Bundesländer.

## Nutzer-Aufgaben

- **Überblick:** Neueste Warnungen der letzten 14 Tage, optional auf ein
  Bundesland, einen Grund, einen Produkttyp und eine Trefferzahl begrenzt.
- **Suche:** Volltextsuche nach Produkt, Marke oder Hersteller („Pinienkerne“,
  „dennree“) mit denselben Filtern; die Trefferliste nennt Datum, Titel, Grund,
  Bundesländer soweit verfügbar und eine Kurz-ID.
- **Detail:** Eine Meldung vollständig lesen: Produktbezeichnung, Haltbarkeit,
  Verpackungseinheit, Charge, Hersteller/Inverkehrbringer, Grund, mögliche
  Folgen, betroffene Bundesländer, Vertrieb und Empfehlung.
- **Beobachten:** Nur Warnungen melden, die seit dem letzten Aufruf neu sind,
  optional gefiltert nach Suchbegriff oder Bundesland. Der Zustand liegt lokal.
- **Merken:** Ein Bundesland einmal konfigurieren, damit `lmw neu` und
  `lmw watch` es ohne erneute Option verwenden.
- **Agenten:** Dieselben Aufgaben nicht-interaktiv über `--json`, stabile
  Exit-Codes und `--erster` für die Detailauswahl.

## Nachfrage

Stand 23.11.2026, Demand-Gate aus dem Tool-Brief:

- GitHub-Suche „lebensmittelwarnung mcp“: 0 Treffer, kein bestehendes CLI.
- Viele Eigenbau-Notifier belegen den Bedarf:
  `bundesAPI/lebensmittelwarnung-api` (★21), `SBorg2014/ioB-Lebensmittelwarnung`
  (★4), `miggi92/hass-lebensmittelwarnung` (Push 15.11.2026),
  `TelegramTrainer/Lebensmittelwarnung` (Juli 2026),
  `svnee/FoodWarnApp` (Februar 2026).
- Die bei `bundesAPI` dokumentierte REST-API
  (`megov.bayern.de/…/warnings/merged`) liefert aktuell HTTP 200 mit leerem
  Body. Bestehende Clients, auch `bundesAPI/deutschland`, laufen dadurch ins
  Leere. Ein Terminal- und Agenten-Zugriff auf die öffentliche Website fehlt.

## Datenquelle

- Startseite/Liste: `GET /DE/Home/home_node.html`, Seiten über
  `?gtp=310780_list1%253D<N>`.
- Suche und Filter:
  `GET /SiteGlobals/Forms/Suche/Expertensuche/Expertensuche_Formular.html`
  mit `nn=310840`, `templateQueryString`, `cl2Taxonomies_Bundeslaender`,
  `cl2Taxonomies_Grund`, `cl2Taxonomies_Typ`, `lastChangeAfter`,
  `lastChangeBefore`, `resultsPerPage`.
- Detailseite: Link aus der Trefferliste folgen
  (`/___lebensmittelwarnung.de/Meldungen/<Jahr>/<Monat>/<ordner>/<datei>.html`).
  Felder stehen als Definitionsliste mit stabilen Klassen
  (`lmw-description-list__term`, `lmw-description-list__description`).
- Bundesländer-Slugs: baden-wuerttemberg, bayern, berlin, brandenburg, bremen,
  hamburg, hessen, mecklenburg-vorpommern, niedersachsen,
  nordrhein-westfalen, rheinland-pfalz, saarland, sachsen, sachsen-anhalt,
  schleswig-holstein, thueringen.
- Grund-Slugs: allergene, fremdkoerper, gesundheitsschaedlichesubstanz,
  irrefuehrungundtaeuschung, krankheitserreger, rueckstaendeundkontaminaten,
  sonstigegruende.
- Typ-Slugs: u. a. lebensmittel/<untertyp>, bedarfsgegenstaende/<untertyp>,
  babyundkinderprodukte, kosmetischemittel/<untertyp>, mittelzumtaetowieren.
- Die Basis-URL ist über `LMW_BASE_URL` überschreibbar (Fake-Server in Tests).
  Datumsabhängige Befehle lesen `LMW_HEUTE` (nur für Tests).

## Grenzen

- **Inoffiziell:** Die Website kann ihre Pfade, Klassen oder Parameter ohne
  Ankündigung ändern. `lmw` ist kein amtlicher Kanal; maßgeblich ist die
  Meldung auf lebensmittelwarnung.de.
- **Nur lesend live getestet:** Am 23.11.2026 wurden ausschließlich GET-Requests
  ohne Login, Cookies oder Captcha ausgeführt. Schreibende Web-Aktionen sind
  nicht Teil des Werkzeugs.
- **Filter sind nicht exakt:** Die Taxonomie-Filter der Website sind nicht
  disjunkt. Ein Bundesland-Filter kann bundesweite Meldungen einschließen, und
  Grund-Filter liefern Karten mit mehreren Badges. `lmw` filtert Grund, Typ und
  Datum clientseitig nach; ein Bundesland-Filter bleibt eine Quellfilterung,
  weil die Liste die betroffenen Länder nicht nennt. Die Detailansicht zeigt
  die tatsächlich genannten Bundesländer.
- **Keine Vollständigkeitsgarantie:** Es werden nur die Seiten geladen, die für
  `--limit` bzw. `--tage` nötig sind. Eine leere Antwort mit HTTP 200 ist
  möglich und bedeutet „keine Treffer“, nicht „Fehler“.
- **Höflichkeit:** Ein User-Agent mit Repo-URL, höchstens ein Request pro
  Sekunde, Cache für 10 Minuten und keine unnötigen Detailabrufe.
- **Keine Personendaten:** Das Werkzeug speichert nur Suchbegriffe,
  Einstellungen und zuletzt gesehene Meldungs-IDs lokal. Es werden keine
  Konten, Passwörter oder personenbezogenen Daten verarbeitet.
