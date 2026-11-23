"""Fehlerklassen mit Exit-Code und nächstem Schritt."""

from __future__ import annotations

NEXT_NET = "Prüfe deine Internetverbindung oder versuche es später erneut."
NEXT_USAGE = "Nutze `lmw --help` für die erlaubten Optionen."


class LmwError(Exception):
    """Basisfehler; ``code`` ist der Prozess-Exit-Code."""

    code = 1
    art = "fehler"

    def __init__(self, meldung: str, *, hinweis: str | None = None) -> None:
        self.meldung = meldung
        self.hinweis = hinweis
        super().__init__(meldung)

    def text(self) -> str:
        if self.hinweis:
            return f"{self.meldung} {self.hinweis}"
        return self.meldung


class UsageError(LmwError):
    code = 2
    art = "usage"

    def __init__(self, meldung: str, *, hinweis: str | None = NEXT_USAGE) -> None:
        super().__init__(meldung, hinweis=hinweis)


class ConfigError(LmwError):
    code = 1
    art = "konfiguration"


class NetworkError(LmwError):
    code = 3
    art = "netz"

    def __init__(self, meldung: str, *, hinweis: str | None = NEXT_NET) -> None:
        super().__init__(meldung, hinweis=hinweis)


class SourceError(LmwError):
    code = 3
    art = "quelle"

    def __init__(self, meldung: str, *, hinweis: str | None = None) -> None:
        super().__init__(meldung, hinweis=hinweis)
