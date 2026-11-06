"""Translation backends.

Every backend translates text between two languages and raises
:class:`OfflineError` when the network can't be reached or
:class:`ServiceError` when the service answers with an error. They use only
the standard library so the app has no dependencies beyond PyGObject.
"""

from __future__ import annotations

import html
import json
import re
import socket
import ssl
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass

USER_AGENT = "QuickTranslate/1.0 (+https://github.com/)"
TIMEOUT = 12  # seconds


class TranslationError(Exception):
    """Base class for translation failures."""


class OfflineError(TranslationError):
    """The translation service couldn't be reached at all."""


class ServiceError(TranslationError):
    """The service was reached but returned an error."""


@dataclass
class Settings:
    """What a backend needs to know; built from the user's config."""

    api_key: str = ""
    url: str = ""
    email: str = ""


def _request(url: str, *, data: dict | None = None, headers: dict | None = None,
             method: str | None = None) -> dict:
    """Perform an HTTP request and decode the JSON reply."""
    hdrs = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    hdrs.update(headers or {})
    body = None
    if data is not None:
        body = json.dumps(data).encode("utf-8")
        hdrs["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=body, headers=hdrs, method=method)
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            raw = resp.read()
    except urllib.error.HTTPError as exc:
        detail = ""
        try:
            payload = json.loads(exc.read() or b"{}")
            detail = payload.get("error") or payload.get("message") or ""
            if isinstance(detail, dict):  # Google: {"error": {"message": ...}}
                detail = detail.get("message", "")
        except (ValueError, AttributeError):
            pass
        if exc.code in (401, 403):
            raise ServiceError(detail or "The API key was rejected.") from exc
        if exc.code in (429, 456):
            raise ServiceError(detail or "Translation quota exceeded. Try again later.") from exc
        raise ServiceError(detail or f"The service returned HTTP {exc.code}.") from exc
    except urllib.error.URLError as exc:
        reason = exc.reason
        if isinstance(reason, ssl.SSLError):
            raise ServiceError(f"Secure connection failed: {reason}") from exc
        raise OfflineError(str(reason)) from exc
    except (socket.timeout, TimeoutError, ConnectionError, OSError) as exc:
        raise OfflineError(str(exc)) from exc
    try:
        return json.loads(raw.decode("utf-8"))
    except ValueError as exc:
        raise ServiceError("The service sent an unreadable reply.") from exc


def split_text(text: str, limit: int) -> list[str]:
    """Split ``text`` into pieces of at most ``limit`` UTF-8 bytes.

    Splits on line breaks and sentence ends first, then on spaces, so each
    piece still reads naturally when translated on its own.
    """
    if len(text.encode("utf-8")) <= limit:
        return [text]
    pieces: list[str] = []
    current = ""
    for part in re.split(r"(?<=[.!?…\n])\s*", text):
        if not part:
            continue
        candidate = f"{current} {part}".strip() if current else part
        if len(candidate.encode("utf-8")) <= limit:
            current = candidate
            continue
        if current:
            pieces.append(current)
        current = ""
        while len(part.encode("utf-8")) > limit:
            cut = part[:limit]
            while len(cut.encode("utf-8")) > limit:
                cut = cut[:-1]
            space = cut.rfind(" ")
            if space > limit // 3:
                cut = cut[:space]
            pieces.append(cut.strip())
            part = part[len(cut):].strip()
        current = part
    if current:
        pieces.append(current)
    return pieces


class Translator:
    name = "base"

    def __init__(self, settings: Settings):
        self.settings = settings

    def translate(self, text: str, source: str, target: str) -> str:
        """Translate ``text`` between two ISO 639-1 codes."""
        raise NotImplementedError


class MyMemoryTranslator(Translator):
    """MyMemory (mymemory.translated.net): free and needs no key.

    Anonymous use allows about 5,000 characters a day; setting an email in
    the config raises that to 50,000.
    """

    name = "mymemory"
    endpoint = "https://api.mymemory.translated.net/get"

    def translate(self, text: str, source: str, target: str) -> str:
        out = []
        for piece in split_text(text, 480):
            params = {"q": piece, "langpair": f"{source}|{target}"}
            if self.settings.email:
                params["de"] = self.settings.email
            if self.settings.api_key:
                params["key"] = self.settings.api_key
            reply = _request(f"{self.endpoint}?{urllib.parse.urlencode(params)}")
            status = reply.get("responseStatus")
            translated = (reply.get("responseData") or {}).get("translatedText") or ""
            if str(status) != "200" or not translated:
                detail = reply.get("responseDetails") or translated
                if str(status) == "429" or "USED ALL AVAILABLE" in str(detail).upper():
                    raise ServiceError("Daily free translation limit reached. Try again tomorrow.")
                raise ServiceError(str(detail) or "The service couldn't translate this text.")
            out.append(html.unescape(translated))
        return " ".join(out)


class LibreTranslateTranslator(Translator):
    """LibreTranslate: self-hosted (no key) or a public instance with a key."""

    name = "libretranslate"
    default_url = "https://libretranslate.com"

    def translate(self, text: str, source: str, target: str) -> str:
        base = (self.settings.url or self.default_url).rstrip("/")
        payload = {"q": text, "source": source, "target": target, "format": "text"}
        if self.settings.api_key:
            payload["api_key"] = self.settings.api_key
        reply = _request(f"{base}/translate", data=payload)
        if "error" in reply:
            raise ServiceError(str(reply["error"]))
        translated = reply.get("translatedText")
        if not translated:
            raise ServiceError("The service couldn't translate this text.")
        return translated


class DeepLTranslator(Translator):
    """DeepL API (free or pro). Needs an API key."""

    name = "deepl"
    # DeepL wants regional variants for a few targets.
    _targets = {"en": "EN-US", "pt": "PT-PT", "zh": "ZH-HANS"}

    def translate(self, text: str, source: str, target: str) -> str:
        key = self.settings.api_key
        if not key:
            raise ServiceError("DeepL needs an API key. Add it in Settings.")
        host = "api-free.deepl.com" if key.endswith(":fx") else "api.deepl.com"
        url = self.settings.url.rstrip("/") + "/v2/translate" if self.settings.url else f"https://{host}/v2/translate"
        payload = {
            "text": [text],
            "source_lang": source.upper(),  # source codes have no regional variant
            "target_lang": self._targets.get(target, target.upper()),
        }
        reply = _request(url, data=payload, headers={"Authorization": f"DeepL-Auth-Key {key}"})
        try:
            return reply["translations"][0]["text"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ServiceError(reply.get("message") or "The service sent an unexpected reply.") from exc


class GoogleTranslator(Translator):
    """Google Cloud Translation (Basic, v2). Needs an API key."""

    name = "google"
    endpoint = "https://translation.googleapis.com/language/translate/v2"
    _targets = {"zh": "zh-CN", "he": "iw", "nb": "no"}

    def translate(self, text: str, source: str, target: str) -> str:
        key = self.settings.api_key
        if not key:
            raise ServiceError("Google Cloud Translation needs an API key. Add it in Settings.")
        payload = {"q": [text], "source": self._targets.get(source, source),
                   "target": self._targets.get(target, target),
                   "format": "text"}
        url = f"{self.endpoint}?{urllib.parse.urlencode({'key': key})}"
        reply = _request(url, data=payload)
        try:
            return reply["data"]["translations"][0]["translatedText"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ServiceError("The service sent an unexpected reply.") from exc


BACKENDS: dict[str, type[Translator]] = {
    cls.name: cls for cls in (MyMemoryTranslator, LibreTranslateTranslator, DeepLTranslator,
                              GoogleTranslator)
}


def make_translator(backend: str, settings: Settings) -> Translator:
    try:
        cls = BACKENDS[backend.lower()]
    except KeyError:
        raise ServiceError(
            f"Unknown backend “{backend}”. Use one of: {', '.join(BACKENDS)}."
        ) from None
    return cls(settings)
