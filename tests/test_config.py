import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from quick_translate import config


class ConfigTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.path = Path(self.dir.name) / "quick-translate" / "config.toml"

    def tearDown(self):
        self.dir.cleanup()

    def test_creates_default_file(self):
        cfg = config.load(self.path)
        self.assertTrue(self.path.exists())
        self.assertEqual((cfg.language_name, cfg.language_code, cfg.backend), ("Spanish", "es", "mymemory"))
        self.assertEqual((cfg.source_name, cfg.source_code), ("English", "en"))
        self.assertEqual(cfg.problem, "")

    def test_language_by_code(self):
        self.path.parent.mkdir(parents=True)
        self.path.write_text('target_language = "ja"\nbackend = "deepl"\nshow_key_hints = false\n')
        cfg = config.load(self.path)
        self.assertEqual((cfg.language_name, cfg.language_code, cfg.backend), ("Japanese", "ja", "deepl"))
        self.assertFalse(cfg.show_key_hints)

    def test_save_and_reload_round_trip(self):
        cfg = config.load(self.path)
        cfg.language_name, cfg.language_code, cfg.backend = "German", "de", "libretranslate"
        cfg.source_name, cfg.source_code = "French", "fr"
        cfg.url = "http://localhost:5000"
        cfg.anki_export, cfg.anki_file = True, '/tmp/my "words".tsv'
        cfg.file_keys = {"libretranslate": "k\\ey"}
        cfg.save()
        again = config.load(self.path)
        for attr in ("source_name", "source_code", "language_name", "language_code", "backend", "url", "anki_export", "anki_file", "file_keys"):
            self.assertEqual(getattr(again, attr), getattr(cfg, attr), attr)
        self.assertEqual(self.path.stat().st_mode & 0o777, 0o600)

    def test_legacy_single_api_key(self):
        self.path.parent.mkdir(parents=True)
        self.path.write_text('backend = "deepl"\napi_key = "old:fx"\n')
        self.assertEqual(config.load(self.path).file_keys, {"deepl": "old:fx"})

    def test_env_key(self):
        from quick_translate import keystore
        with mock.patch.dict(os.environ, {"DEEPL_API_KEY": "k:fx"}, clear=False):
            os.environ.pop("QUICK_TRANSLATE_API_KEY", None)
            self.assertEqual(keystore.env_key("deepl"), "k:fx")
            self.assertEqual(keystore.env_key("mymemory"), "")

    def test_bad_file_reports_problem(self):
        self.path.parent.mkdir(parents=True)
        self.path.write_text("target_language = ")
        self.assertIn("Config file error", config.load(self.path).problem)

    def test_old_config_without_source_defaults_to_english(self):
        self.path.parent.mkdir(parents=True)
        self.path.write_text('target_language = "fr"\n')
        cfg = config.load(self.path)
        self.assertEqual((cfg.source_code, cfg.language_code, cfg.problem), ("en", "fr", ""))

    def test_unknown_language(self):
        self.path.parent.mkdir(parents=True)
        self.path.write_text('target_language = "Klingonese"\n')
        self.assertIn("Unknown target language", config.load(self.path).problem)


if __name__ == "__main__":
    unittest.main()
