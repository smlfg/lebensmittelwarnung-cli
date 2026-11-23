"""HTTP-Client für lebensmittelwarnung.de mit Cache und Rate-Limit."""

from __future__ import annotations

import hashlib
import json
import os
import time
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import urlencode, urlsplit

import httpx

from .errors import NetworkError, UsageError
from .filters import bundesland_slug, grund_slug, typ_slug, typ_source_slugs

DEFAULT_BASE_URL = "https://www.lebensmittelwarnung.de"
LIST_PATH = "/SiteGlobals/Forms/Suche/Expertensuche/Expertensuche_Formular.html"
CACHE_TTL = 600.0
RATE_LIMIT = 1.0
TIMEOUT = 15.0
USER_AGENT = (
    "lebensmittelwarnung-cli/0.1 "
    "(+https://github.com/smlfg/lebensmittelwarnung-cli)"
)


def _cache_dir() -> Path:
    base = os.environ.get("XDG_CACHE_HOME")
    root = Path(base) if base else Path.home() / ".cache"
    return root / "lebensmittelwarnung-cli"


def today() -> date:
    value = os.environ.get("LMW_HEUTE")
    if value:
        try:
            return date.fromisoformat(value)
        except ValueError as exc:
            raise UsageError(
                f"LMW_HEUTE ist kein Datum im Format JJJJ-MM-TT: {value!r}"
            ) from exc
    return date.today()


class Client:
    def __init__(self, base_url: str | None = None) -> None:
        raw = (base_url or os.environ.get("LMW_BASE_URL") or DEFAULT_BASE_URL).strip()
        parts = urlsplit(raw)
        if parts.scheme not in {"http", "https"} or not parts.netloc:
            raise UsageError(
                f"LMW_BASE_URL muss mit http:// oder https:// beginnen: {raw!r}"
            )
        self.base_url = f"{parts.scheme}://{parts.netloc}"
        self.prefix = parts.path.rstrip("/")
        self._last_request = 0.0
        self.cache_dir = _cache_dir()

    def _url(self, path: str) -> str:
        if "://" in path:
            path = urlsplit(path).path
        if not path.startswith("/"):
            path = "/" + path
        return self.base_url + self.prefix + path

    def _cache_path(self, url: str) -> Path:
        digest = hashlib.sha256(url.encode("utf-8")).hexdigest()
        return self.cache_dir / f"{digest}.json"

    def _read_cache(self, url: str) -> str | None:
        path = self._cache_path(url)
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        if payload.get("url") != url:
            return None
        try:
            age = time.time() - float(payload["ts"])
        except (KeyError, TypeError, ValueError):
            return None
        if age < 0 or age > CACHE_TTL:
            return None
        text = payload.get("text")
        return text if isinstance(text, str) else None

    def _write_cache(self, url: str, text: str) -> None:
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
            os.chmod(self.cache_dir, 0o700)
            path = self._cache_path(url)
            tmp = path.with_suffix(".tmp")
            tmp.write_text(
                json.dumps({"url": url, "ts": time.time(), "text": text}),
                encoding="utf-8",
            )
            os.chmod(tmp, 0o600)
            os.replace(tmp, path)
        except OSError:
            return

    def _throttle(self) -> None:
        wait = RATE_LIMIT - (time.monotonic() - self._last_request)
        if wait > 0:
            time.sleep(wait)

    def get(self, path: str) -> str:
        url = self._url(path)
        cached = self._read_cache(url)
        if cached is not None:
            return cached
        self._throttle()
        try:
            response = httpx.get(
                url,
                headers={"User-Agent": USER_AGENT},
                timeout=TIMEOUT,
                follow_redirects=True,
            )
        except httpx.TimeoutException as exc:
            raise NetworkError(
                "Zeitüberschreitung beim Abruf von lebensmittelwarnung.de."
            ) from exc
        except httpx.HTTPError as exc:
            raise NetworkError(
                f"Netzwerkfehler beim Abruf von lebensmittelwarnung.de: {exc}"
            ) from exc
        finally:
            self._last_request = time.monotonic()
        if response.status_code >= 400:
            raise NetworkError(
                f"lebensmittelwarnung.de antwortete mit HTTP {response.status_code}."
            )
        text = response.text
        self._write_cache(url, text)
        return text

    def search(
        self,
        *,
        begriff: str | None = None,
        bundeslaender: list[str] | None = None,
        gruende: list[str] | None = None,
        typen: list[str] | None = None,
        tage: int | None = None,
        limit: int | None = None,
        bezugstag: date | None = None,
    ) -> str:
        params: list[tuple[str, str]] = [
            ("nn", "310840"),
            ("templateQueryString", begriff or ""),
        ]
        if bundeslaender:
            slugs = [bundesland_slug(value) for value in bundeslaender]
            params.append(
                ("cl2Taxonomies_Bundeslaender", _taxonomy("bundeslaender", slugs))
            )
        if gruende:
            slugs = [grund_slug(value) for value in gruende]
            params.append(("cl2Taxonomies_Grund", _taxonomy("grund", slugs)))
        if typen:
            slugs = []
            for value in typen:
                slugs.extend(typ_source_slugs(typ_slug(value)))
            params.append(("cl2Taxonomies_Typ", _taxonomy("typ", slugs)))
        if tage is not None:
            day = bezugstag or today()
            params.append(("lastChangeAfter", (day - timedelta(days=tage)).isoformat()))
        if limit is not None:
            params.append(("resultsPerPage", str(limit)))
        return self.get(LIST_PATH + "?" + urlencode(params))

    def detail(self, path: str | None = None, *, url: str | None = None) -> str:
        target = path or url
        if not target:
            raise NetworkError("Kein Detail-Link vorhanden.")
        return self.get(target)


def _taxonomy(name: str, slugs: list[str]) -> str:
    return "+".join(f'"/c/{name}/{slug}"' for slug in slugs)
