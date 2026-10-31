# PyInstaller spec: build with  pyinstaller packaging/upf_loans.spec
from pathlib import Path

ROOT = Path(SPECPATH).parent
SRC = ROOT / "src"

a = Analysis(
    [str(ROOT / "packaging" / "launch.py")],
    pathex=[str(SRC)],
    datas=[(str(SRC / "upf_loans" / "db" / "migrations"), "upf_loans/db/migrations"),
           (str(SRC / "upf_loans" / "assets"), "upf_loans/assets")],
    hiddenimports=["upf_loans.db.models", "sqlalchemy.dialects.sqlite", "alembic.runtime.migration",
                   "alembic.ddl.sqlite", "PySide6.QtSvg"],
    excludes=["tkinter", "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets", "PySide6.Qt3DCore",
              "PySide6.QtQuick", "PySide6.QtQml", "PySide6.QtMultimedia"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name="UPFLoanManager",
    console=False,
    icon=None,
)
coll = COLLECT(exe, a.binaries, a.datas, name="UPFLoanManager")
