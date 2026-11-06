import tempfile
import unittest
from pathlib import Path

from quick_translate import history


class HistoryTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.path = str(Path(self.dir.name) / "sub" / "translations.tsv")

    def tearDown(self):
        self.dir.cleanup()

    def test_creates_file_with_anki_header(self):
        self.assertEqual(history.append(self.path, "Hello", "Hola"), history.SaveResult.SAVED)
        self.assertEqual(Path(self.path).read_text(), "#separator:tab\n#html:false\nHello\tHola\n")

    def test_skips_duplicates(self):
        history.append(self.path, "Hello", "Hola")
        self.assertEqual(history.append(self.path, "Hello", "Hola"), history.SaveResult.DUPLICATE)
        history.append(self.path, "Bye", "Adiós")
        self.assertEqual(Path(self.path).read_text().count("\n"), 4)

    def test_tabs_and_newlines_stay_in_one_field(self):
        history.append(self.path, "Line one\nline\ttwo", "Uno\ndos")
        self.assertTrue(Path(self.path).read_text().endswith("Line one line two\tUno dos\n"))

    def test_display_path_uses_tilde(self):
        self.assertEqual(history.display_path(str(Path.home() / "Documents" / "a.tsv")),
                         "~/Documents/a.tsv")


if __name__ == "__main__":
    unittest.main()
