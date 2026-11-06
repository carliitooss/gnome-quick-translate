"""User configuration in ``~/.config/quick-translate/config.toml``.

The Settings page writes this file whenever something changes, so choices
survive closing the app and restarting the computer. API keys go to the
GNOME keyring instead (see :mod:`keystore`); only when no keyring is
available are they kept here, under ``[api_keys]``.
"""

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
    "Czech": "cs", "Danish": "da", "Dutch": "nl", "English": "en", "Estonian": "et",
    "Finnish": "fi", "French": "fr", "German": "de", "Greek": "el",
    "Hebrew": "he", "Hindi": "hi", "Hungarian": "hu", "Indonesian": "id",
    "Italian": "it", "Japanese": "ja", "Korean": "ko", "Latvian": "lv",
    "Lithuanian": "lt", "Norwegian": "nb", "Polish": "pl", "Portuguese": "pt",
    "Romanian": "ro", "Russian": "ru", "Slovak": "sk", "Slovenian": "sl",
    "Spanish": "es", "Swedish": "sv", "Thai": "th", "Turkish": "tr",
    "Ukrainian": "uk", "Vietnamese": "vi",
}

# Backend id -> name shown in Settings, in the order the design lists them.
SERVICES: dict[str, str] = {
    "deepl": "DeepL",
    "google": "Google Cloud Translation",
    "libretranslate": "LibreTranslate",
    "mymemory": "MyMemory (free, no key)",
}
KEY_REQUIRED = {"deepl", "google"}
NO_KEY = {"mymemory"}  # the Settings page hides the API key row for these


def config_path() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    return Path(base) / "quick-translate" / "config.toml"


def default_anki_file() -> str:
    try:
        from gi.repository import GLib
        docs = GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_DOCUMENTS)
    except (ImportError, AttributeError):
        docs = None
    docs = docs or os.path.expanduser("~/Documents")
    return os.path.join(docs, "Anki", "translations.tsv")


@dataclass
class Config:
    source_name: str = "English"
    source_code: str = "en"
    language_name: str = "Spanish"  # the target language
    language_code: str = "es"
    backend: str = "mymemory"
    url: str = ""
    email: str = ""
    show_key_hints: bool = True
    close_on_focus_loss: bool = True
    close_after_copy: bool = False
    anki_export: bool = False
    anki_file: str = field(default_factory=default_anki_file)
    file_keys: dict[str, str] = field(default_factory=dict)  # only without a keyring
    problem: str = ""  # a config error to show instead of translating
    path: Path | None = None

    def settings(self, api_key: str) -> Settings:
        url = self.url if self.backend == "libretranslate" else ""
        return Settings(api_key=api_key, url=url, email=self.email)

    def save(self) -> None:
        """Write the config file atomically."""
        path = self.path or config_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".toml.tmp")
        text = render(self)
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
        os.replace(tmp, path)


def _toml_str(value: str) -> str:
    out = value.replace("\\", "\\\\").replace('"', '\\"')
    out = out.replace("\n", "\\n").replace("\t", "\\t").replace("\r", "\\r")
    return f'"{out}"'


def _toml_bool(value: bool) -> str:
    return "true" if value else "false"


def render(cfg: Config) -> str:
    lines = [
        "# Quick Translate settings. The app's Settings page rewrites this file;",
        "# you can also edit it by hand. Changes apply the next time the popup opens.",
        "",
        "# Languages to translate from and into: a name (\"Spanish\") or code (\"es\").",
        f"source_language = {_toml_str(cfg.source_name)}",
        f"target_language = {_toml_str(cfg.language_name)}",
        "",
        "# Translation service: " + ", ".join(f'"{k}"' for k in SERVICES) + ".",
        f"backend = {_toml_str(cfg.backend)}",
        "",
        "# Server address for a self-hosted LibreTranslate (e.g. \"http://localhost:5000\").",
        f"url = {_toml_str(cfg.url)}",
        "",
        "# MyMemory only: an email raises the free daily limit from 5,000 to 50,000 characters.",
        f"email = {_toml_str(cfg.email)}",
        "",
        "# Anki: add every translation as a line (original<TAB>translation) to a TSV file.",
        f"anki_export = {_toml_bool(cfg.anki_export)}",
        f"anki_file = {_toml_str(cfg.anki_file)}",
        "",
        "# Show the Enter / Esc hints at the bottom of the popup.",
        f"show_key_hints = {_toml_bool(cfg.show_key_hints)}",
        "",
        "# Close the popup when it loses focus, like a launcher.",
        f"close_on_focus_loss = {_toml_bool(cfg.close_on_focus_loss)}",
        "",
        "# Close the popup after Enter copies a translation.",
        f"close_after_copy = {_toml_bool(cfg.close_after_copy)}",
        "",
    ]
    keys = {k: v for k, v in cfg.file_keys.items() if v}
    if keys:
        lines += ["# API keys, kept here only because no keyring was available.",
                  "[api_keys]"]
        lines += [f"{k} = {_toml_str(v)}" for k, v in sorted(keys.items())]
        lines.append("")
    return "\n".join(lines)


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
    cfg = Config(path=path)
    if not path.exists():
        try:
            cfg.save()
        except OSError:
            pass
        return cfg
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        cfg.problem = f"Config file error: {exc}"
        return cfg
    except OSError:
        return cfg

    for key, default, attrs in (("source_language", "English", ("source_name", "source_code")),
                                ("target_language", "Spanish", ("language_name", "language_code"))):
        lang = resolve_language(str(data.get(key, default)))
        if lang is None:
            kind = key.split("_")[0]
            cfg.problem = f"Unknown {kind} language “{data.get(key)}” in config."
        else:
            setattr(cfg, attrs[0], lang[0])
            setattr(cfg, attrs[1], lang[1])

    backend = str(data.get("backend", "mymemory")).strip().lower() or "mymemory"
    cfg.backend = backend
    cfg.url = str(data.get("url", "")).strip()
    cfg.email = str(data.get("email", "")).strip()
    cfg.show_key_hints = bool(data.get("show_key_hints", True))
    cfg.close_on_focus_loss = bool(data.get("close_on_focus_loss", True))
    cfg.close_after_copy = bool(data.get("close_after_copy", False))
    cfg.anki_export = bool(data.get("anki_export", False))
    cfg.anki_file = str(data.get("anki_file", "")).strip() or default_anki_file()

    keys = data.get("api_keys")
    if isinstance(keys, dict):
        cfg.file_keys = {str(k): str(v) for k, v in keys.items()}
    legacy = str(data.get("api_key", "")).strip()  # version 1 kept one key at the top
    if legacy and backend not in cfg.file_keys:
        cfg.file_keys[backend] = legacy
    return cfg
