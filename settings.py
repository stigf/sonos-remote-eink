# settings.py — Persistent user settings (JSON file on disk)

import json
import logging
import os

logger = logging.getLogger(__name__)

_SETTINGS_PATH = os.environ.get(
    'SONOS_REMOTE_SETTINGS',
    '/opt/sonos-remote/settings.json',
)

_DEFAULTS = {
    'show_album_art': False,
}


def _load() -> dict:
    """Load settings from disk, falling back to defaults."""
    try:
        with open(_SETTINGS_PATH, 'r') as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        data = {}
    # Merge with defaults so new keys are always present
    merged = dict(_DEFAULTS)
    merged.update(data)
    return merged


def _save(data: dict) -> None:
    """Persist settings to disk."""
    try:
        os.makedirs(os.path.dirname(_SETTINGS_PATH) or '.', exist_ok=True)
        with open(_SETTINGS_PATH, 'w') as f:
            json.dump(data, f, indent=2)
    except OSError as exc:
        logger.error('Failed to save settings: %s', exc)


def get(key: str):
    """Read a single setting value."""
    return _load().get(key, _DEFAULTS.get(key))


def set(key: str, value) -> None:
    """Write a single setting value and persist."""
    data = _load()
    data[key] = value
    _save(data)


def get_all() -> dict:
    """Return all settings as a dict."""
    return _load()
