"""API keys, stored in the GNOME keyring through libsecret.

Each translation service has its own entry, so switching service keeps the
other keys. If libsecret or a keyring isn't available, keys fall back to the
config file (which is then readable only by the user).
"""

from __future__ import annotations

import os

try:
    import gi

    gi.require_version("Secret", "1")
    from gi.repository import GLib, Secret
except (ImportError, ValueError):  # libsecret's typelib isn't installed
    Secret = None

SCHEMA_NAME = "io.github.QuickTranslate.ApiKey"
_schema = None


def _get_schema():
    global _schema
    if _schema is None and Secret is not None:
        _schema = Secret.Schema.new(SCHEMA_NAME, Secret.SchemaFlags.NONE,
                                    {"service": Secret.SchemaAttributeType.STRING})
    return _schema


class KeyringUnavailable(Exception):
    pass


def keyring_available() -> bool:
    """Whether a Secret Service (GNOME keyring, KWallet…) answers."""
    if Secret is None:
        return False
    try:
        Secret.Service.get_sync(Secret.ServiceFlags.NONE, None)
        return True
    except GLib.Error:
        return False


def lookup(service: str) -> str:
    """Return the stored key for ``service``, or "" if none or unavailable."""
    if Secret is None:
        return ""
    try:
        return Secret.password_lookup_sync(_get_schema(), {"service": service}, None) or ""
    except GLib.Error:
        return ""


def store(service: str, key: str, label: str) -> None:
    """Save (or, for an empty key, delete) the key for ``service``."""
    if Secret is None:
        raise KeyringUnavailable("libsecret is not installed")
    try:
        if key:
            Secret.password_store_sync(_get_schema(), {"service": service},
                                       Secret.COLLECTION_DEFAULT, label, key, None)
        else:
            Secret.password_clear_sync(_get_schema(), {"service": service}, None)
    except GLib.Error as exc:
        raise KeyringUnavailable(exc.message) from exc


def env_key(service: str) -> str:
    """A key given through the environment, which overrides stored keys."""
    specific = {"deepl": "DEEPL_API_KEY", "google": "GOOGLE_TRANSLATE_API_KEY"}.get(service)
    return os.environ.get("QUICK_TRANSLATE_API_KEY", "") or (os.environ.get(specific, "") if specific else "")
