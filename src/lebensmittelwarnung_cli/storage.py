"""Lokale Konfiguration und Watch-Zustand (0600, atomar)."""

from __future__ import annotations

import json
import os
from pathlib import Path

from .errors import ConfigError

APP = "lebensmittelwarnung-cli"


def config_dir() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME")
    root = Path(base) if base else Path.home() / ".config"
    return root / APP


def state_dir() -> Path:
    base = os.environ.get("XDG_STATE_HOME")
    root = Path(base) if base else Path.home() / ".local" / "state"
    return root / APP


def config_path() -> Path:
    return config_dir() / "config.json"


def state_path() -> Path:
    return state_dir() / "state.json"


def _read_json(path: Path) -> dict:
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return {}
    except OSError as exc:
        raise ConfigError(
            f"{path} ist nicht lesbar: {exc}",
            hinweis="Prüfe die Dateirechte oder lösche die Datei.",
        ) from exc
    try:
        data = json.loads(raw)
    except ValueError as exc:
        raise ConfigError(
            f"{path} enthält kein gültiges JSON.",
            hinweis="Lösche die Datei und lege die Einstellung neu an.",
        ) from exc
    if not isinstance(data, dict):
        raise ConfigError(
            f"{path} enthält kein JSON-Objekt.",
            hinweis="Lösche die Datei und lege die Einstellung neu an.",
        )
    return data


def _write_json(path: Path, data: dict) -> None:
    directory = path.parent
    try:
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(directory, 0o700)
        tmp = path.with_name(path.name + ".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", "utf-8")
        os.chmod(tmp, 0o600)
        os.replace(tmp, path)
    except OSError as exc:
        raise ConfigError(
            f"{path} ist nicht schreibbar: {exc}",
            hinweis="Prüfe die Rechte des Verzeichnisses.",
        ) from exc


def load_config() -> dict:
    return _read_json(config_path())


def save_config(data: dict) -> None:
    _write_json(config_path(), data)


def load_state() -> dict:
    return _read_json(state_path())


def save_state(data: dict) -> None:
    _write_json(state_path(), data)
