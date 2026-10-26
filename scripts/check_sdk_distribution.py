"""Reject demo files or artwork in the SDK release artifacts."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import tarfile
import zipfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("directory", type=Path, nargs="?", default=Path("dist/pypi"))
args = parser.parse_args()
files = sorted([*args.directory.glob("*.whl"), *args.directory.glob("*.tar.gz")])
assert len(files) == 2, "Expected exactly one SDK wheel and one source distribution"
expected = {"__init__.py", "__main__.py", "_compression.py", "_obfuscation.py", "_serialization.py", "cli.py", "codec.py", "errors.py", "models.py", "py.typed"}
result = []
for path in files:
    assert path.stat().st_size < 1024 * 1024, "SDK artifact unexpectedly large"
    if path.suffix == ".whl":
        with zipfile.ZipFile(path) as archive:
            assert archive.testzip() is None
            names = archive.namelist()
            content = {n.split("/", 1)[1] for n in names if n.startswith("czn_deckcode/")}
            assert content == expected, content
    else:
        with tarfile.open(path, "r:gz") as archive:
            names = archive.getnames()
    assert not any("/demo/" in n or "/assets/" in n or "/user_data/" in n for n in names)
    assert not any(n.endswith((".png", ".gif", ".jpg", ".svg", ".html", ".exe", ".pyc")) for n in names)
    result.append({"file": path.name, "bytes": path.stat().st_size, "demo_included": False})
print(json.dumps(result))
