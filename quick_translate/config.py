"""User configuration, read from ``~/.config/quick-translate/config.toml``."""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from .translators import Settings

# English display name -> ISO 639-1 code. The title and card label use the
# English name, as in the design ("English → Spanish").
LANGUAGES: dict[str, str] = {
    "Arabic": "ar", "Bulgarian": "bg", "Catalan": "ca", "Chinese": "zh",
    "Czech": "cs", "Danish": "da", "Dutch": "nl", "Estonian": "et",
    "Finnish": "fi", "French": "fr", "German": "de", "Greek": "el",
    "Hebrew": "he", "Hindi": "hi", "Hungarian": "hu", "Indonesian": "id",
    "Italian": "it", "Japanese": "ja", "Korean": "ko", "Latvian": "lv",
    "Lithuanian": "lt", "Norwegian": "nb", "Polish": "pl", "Portuguese": "pt",
    "Romanian": "ro", "Russian": "ru", "Slovak": "sk", "Slovenian": "sl",
    "Spanish": "es", "Swedish": "sv", "Thai": "th", "Turkish": "tr",
    "Ukrainian": "uk", "Vietnamese": "vi",
}

DEFAULT_CONFIG = """\
# Quick Translate settings. Changes apply the next time the popup opens.

# Language to translate English into: a name ("Spanish") or code ("es").
target_language = "Spanish"

# Translation service: "mymemory" (free, no key), "libretranslate" or "deepl".
backend = "mymemory"

# API key for the backend, if it needs one. You can also set the
# QUICK_TRANSLATE_API_KEY environment variable (or DEEPL_API_KEY).
api_key = ""

# Server address, for a self-hosted LibreTranslate (e.g. "http://localhost:5000").
url = ""

# MyMemory only: an email raises the free daily limit from 5,000 to 50,000 characters.
email = ""

# Show the Enter / Esc hints at the bottom of the popup.
show_key_hints = true

# Close the popup when it loses focus, like a launcher.
close_on_focus_loss = true

# Close the popup after Enter copies a translation.
close_after_copy = false
"""


def config_path() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    return Path(base) / "quick-translate" / "config.toml"


@dataclass
class Config:
    language_name: str = "Spanish"
    language_code: str = "es"
    backend: str = "mymemory"
    settings: Settings = field(default_factory=Settings)
    show_key_hints: bool = True
    close_on_focus_loss: bool = True
    close_after_copy: bool = False
    problem: str = ""  # a config error to show instead of translating


def resolve_language(value: str) -> tuple[str, str] | None:
    value = value.strip()
    for name, code in LANGUAGES.items():
        if value.lower() in (name.lower(), code):
            return name, code
    if 2 <= len(value) <= 3 and value.isalpha():  # an unlisted ISO code
        return value.upper(), value.lower()
    return None


def load(path: Path | None = None) -> Config:
    """Read the config file, creating it with defaults on first run."""
    path = path or config_path()
    cfg = Config()
    try:
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(DEFAULT_CONFIG, encoding="utf-8")
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        cfg.problem = f"Config file error: {exc}"
        data = {}
    except OSError:
        data = {}

    lang = resolve_language(str(data.get("target_language", "Spanish")))
    if lang is None:
        cfg.problem = f"Unknown target language “{data.get('target_language')}” in config."
    else:
        cfg.language_name, cfg.language_code = lang

    cfg.backend = str(data.get("backend", "mymemory")).strip().lower() or "mymemory"
    key = (str(data.get("api_key", "")).strip()
           or os.environ.get("QUICK_TRANSLATE_API_KEY", "")
           or (os.environ.get("DEEPL_API_KEY", "") if cfg.backend == "deepl" else ""))
    cfg.settings = Settings(api_key=key, url=str(data.get("url", "")).strip(),
                            email=str(data.get("email", "")).strip())
    cfg.show_key_hints = bool(data.get("show_key_hints", True))
    cfg.close_on_focus_loss = bool(data.get("close_on_focus_loss", True))
    cfg.close_after_copy = bool(data.get("close_after_copy", False))
    return cfg
