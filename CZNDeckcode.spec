# Build on the target OS; the Windows build includes Python, Tcl and Tk.
from pathlib import Path

project_root = Path(SPECPATH)
a = Analysis(
    [str(project_root / "scripts" / "desktop_entry.py")],
    pathex=[str(project_root / "src")],
    binaries=[],
    datas=[
        (str(project_root / "src" / "czn_deckcode" / "assets"), "czn_deckcode/assets"),
        (str(project_root / "LICENSE"), "licenses"),
        (str(project_root / "licenses" / "*.txt"), "licenses"),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["unittest", "http.server", "webbrowser"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="CZNDeckcode",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
)
