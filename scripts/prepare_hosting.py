"""Rebuild and stage only the public page for Firebase Hosting."""

import shutil
from pathlib import Path

from build_maren_page import build

ROOT = Path(__file__).resolve().parents[1]


if __name__ == "__main__":
    build()
    target = ROOT / "dist"
    if target.exists():
        shutil.rmtree(target)
    target.mkdir()
    shutil.copy2(ROOT / "index.html", target / "index.html")
    print("Firebase Hosting ready: dist/index.html")
