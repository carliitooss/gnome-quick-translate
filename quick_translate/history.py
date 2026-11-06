"""Append translations to a TSV file that Anki can import.

Each line is ``English<TAB>translation``. A new file starts with Anki's
header lines so that File → Import picks the tab separator and plain-text
fields by itself. A pair already in the file isn't added again.
"""

from __future__ import annotations

import os
from pathlib import Path

HEADER = "#separator:tab\n#html:false\n"


class SaveResult:
    SAVED = "saved"
    DUPLICATE = "duplicate"


def _clean(field: str) -> str:
    # Tabs and line breaks would split the card into extra fields or lines.
    return " ".join(field.replace("\t", " ").split())


def expand(path: str) -> Path:
    return Path(os.path.expandvars(os.path.expanduser(path)))


def append(path: str, source: str, translation: str) -> str:
    """Add the pair to ``path``. Returns a :class:`SaveResult` value.

    Raises ``OSError`` if the file can't be written.
    """
    file = expand(path)
    line = f"{_clean(source)}\t{_clean(translation)}"
    existing = ""
    if file.exists():
        existing = file.read_text(encoding="utf-8")
        if line in existing.splitlines():
            return SaveResult.DUPLICATE
    else:
        file.parent.mkdir(parents=True, exist_ok=True)
    with open(file, "a", encoding="utf-8", newline="\n") as fh:
        if not existing:
            fh.write(HEADER)
        elif not existing.endswith("\n"):
            fh.write("\n")
        fh.write(line + "\n")
    return SaveResult.SAVED


def display_path(path: str) -> str:
    """Show the path with ``~`` for the home folder, as in the design."""
    full = str(expand(path))
    home = os.path.expanduser("~")
    if full == home or full.startswith(home + os.sep):
        return "~" + full[len(home):]
    return full
