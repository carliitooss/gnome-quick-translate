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
        self.assertEqual(cfg.problem, "")

    def test_language_by_code_and_env_key(self):
        self.path.parent.mkdir(parents=True)
        self.path.write_text('target_language = "ja"\nbackend = "deepl"\nshow_key_hints = false\n')
        with mock.patch.dict(os.environ, {"DEEPL_API_KEY": "k:fx"}, clear=False):
            os.environ.pop("QUICK_TRANSLATE_API_KEY", None)
            cfg = config.load(self.path)
        self.assertEqual((cfg.language_name, cfg.language_code), ("Japanese", "ja"))
        self.assertEqual(cfg.settings.api_key, "k:fx")
        self.assertFalse(cfg.show_key_hints)

    def test_bad_file_reports_problem(self):
        self.path.parent.mkdir(parents=True)
        self.path.write_text("target_language = ")
        self.assertIn("Config file error", config.load(self.path).problem)

    def test_unknown_language(self):
        self.path.parent.mkdir(parents=True)
        self.path.write_text('target_language = "Klingonese"\n')
        self.assertIn("Unknown target language", config.load(self.path).problem)


if __name__ == "__main__":
    unittest.main()
