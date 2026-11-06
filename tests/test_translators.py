import io
import json
import unittest
import urllib.error
from unittest import mock

from quick_translate import translators as t


def reply(payload):
    resp = mock.MagicMock()
    resp.read.return_value = json.dumps(payload).encode()
    resp.__enter__.return_value = resp
    return resp


class SplitTextTests(unittest.TestCase):
    def test_short_text_is_one_piece(self):
        self.assertEqual(t.split_text("Hello there.", 480), ["Hello there."])

    def test_long_text_respects_limit(self):
        text = "This is a sentence. " * 60
        pieces = t.split_text(text, 100)
        self.assertTrue(all(len(p.encode()) <= 100 for p in pieces))
        self.assertEqual(" ".join(pieces).split(), text.split())

    def test_word_longer_than_limit(self):
        pieces = t.split_text("a" * 250, 100)
        self.assertTrue(all(len(p) <= 100 for p in pieces))
        self.assertEqual("".join(pieces), "a" * 250)


class MyMemoryTests(unittest.TestCase):
    def test_translates_and_unescapes(self):
        payload = {"responseStatus": 200, "responseData": {"translatedText": "l&#39;eau"}}
        with mock.patch("urllib.request.urlopen", return_value=reply(payload)) as op:
            out = t.MyMemoryTranslator(t.Settings(email="a@b.c")).translate("water", "fr")
        self.assertEqual(out, "l'eau")
        url = op.call_args[0][0].full_url
        self.assertIn("langpair=en%7Cfr", url)
        self.assertIn("de=a%40b.c", url)

    def test_quota_error(self):
        payload = {"responseStatus": 429, "responseData": {"translatedText": "MYMEMORY WARNING: YOU USED ALL AVAILABLE FREE TRANSLATIONS"}}
        with mock.patch("urllib.request.urlopen", return_value=reply(payload)):
            with self.assertRaises(t.ServiceError):
                t.MyMemoryTranslator(t.Settings()).translate("hi", "es")

    def test_offline(self):
        with mock.patch("urllib.request.urlopen", side_effect=urllib.error.URLError(OSError("Name or service not known"))):
            with self.assertRaises(t.OfflineError):
                t.MyMemoryTranslator(t.Settings()).translate("hi", "es")

    def test_http_error_is_service_error(self):
        err = urllib.error.HTTPError("u", 403, "Forbidden", {}, io.BytesIO(b'{"error":"bad key"}'))
        with mock.patch("urllib.request.urlopen", side_effect=err):
            with self.assertRaisesRegex(t.ServiceError, "bad key"):
                t.MyMemoryTranslator(t.Settings()).translate("hi", "es")


class LibreTranslateTests(unittest.TestCase):
    def test_posts_json(self):
        with mock.patch("urllib.request.urlopen", return_value=reply({"translatedText": "Hola"})) as op:
            out = t.LibreTranslateTranslator(t.Settings(url="http://localhost:5000/", api_key="k")).translate("Hi", "es")
        self.assertEqual(out, "Hola")
        req = op.call_args[0][0]
        self.assertEqual(req.full_url, "http://localhost:5000/translate")
        self.assertEqual(json.loads(req.data), {"q": "Hi", "source": "en", "target": "es", "format": "text", "api_key": "k"})


class DeepLTests(unittest.TestCase):
    def test_free_key_uses_free_host(self):
        with mock.patch("urllib.request.urlopen", return_value=reply({"translations": [{"text": "Hallo"}]})) as op:
            out = t.DeepLTranslator(t.Settings(api_key="abc:fx")).translate("Hello", "de")
        self.assertEqual(out, "Hallo")
        req = op.call_args[0][0]
        self.assertEqual(req.full_url, "https://api-free.deepl.com/v2/translate")
        self.assertEqual(req.get_header("Authorization"), "DeepL-Auth-Key abc:fx")
        self.assertEqual(json.loads(req.data)["target_lang"], "DE")

    def test_needs_key(self):
        with self.assertRaises(t.ServiceError):
            t.DeepLTranslator(t.Settings()).translate("Hello", "de")


class GoogleTests(unittest.TestCase):
    def test_translates(self):
        payload = {"data": {"translations": [{"translatedText": "Bonjour"}]}}
        with mock.patch("urllib.request.urlopen", return_value=reply(payload)) as op:
            out = t.GoogleTranslator(t.Settings(api_key="AIza")).translate("Hello", "fr")
        self.assertEqual(out, "Bonjour")
        req = op.call_args[0][0]
        self.assertTrue(req.full_url.endswith("/v2?key=AIza"))
        self.assertEqual(json.loads(req.data), {"q": ["Hello"], "source": "en", "target": "fr", "format": "text"})

    def test_error_message_from_nested_error(self):
        err = urllib.error.HTTPError("u", 400, "Bad", {}, io.BytesIO(b'{"error":{"code":400,"message":"API key not valid."}}'))
        with mock.patch("urllib.request.urlopen", side_effect=err):
            with self.assertRaisesRegex(t.ServiceError, "API key not valid"):
                t.GoogleTranslator(t.Settings(api_key="x")).translate("Hello", "fr")


class FactoryTests(unittest.TestCase):
    def test_unknown_backend(self):
        with self.assertRaises(t.ServiceError):
            t.make_translator("nope", t.Settings())


if __name__ == "__main__":
    unittest.main()
