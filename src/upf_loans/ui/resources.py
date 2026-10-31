"""Small SVG images used by the style sheet (drop-down arrow, check mark).

They are written to a folder in the data directory and registered under the
``upf:`` search prefix, so the style sheet can say ``url(upf:chevron.svg)``.
"""

from __future__ import annotations

from PySide6.QtCore import QDir

from .. import config

_FILES = {
    "chevron.svg": '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#C9CED8" '
                   'stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="m6 9 6 6 6-6"/></svg>',
    "check-dark.svg": '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#10140A" '
                      'stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="m5 12.5 4.5 4.5L19 7.5"/></svg>',
}


def register() -> None:
    folder = config.data_dir() / "theme"
    folder.mkdir(parents=True, exist_ok=True)
    for name, svg in _FILES.items():
        path = folder / name
        try:
            if not path.exists() or path.read_text(encoding="utf-8") != svg:
                path.write_text(svg, encoding="utf-8")
        except OSError:
            pass
    QDir.addSearchPath("upf", str(folder))
