# -*- coding: utf-8 -*-
"""
Build a ready-to-upload copy of the app in the `publish/` folder.

Static hosts (Netlify Drop, GitHub Pages, ...) serve the file named `index.html`
when someone opens the site root, so this script copies the whole app and also
adds `index.html` next to `apartment-charge.html`.

Usage:
    python build_publish.py

Then upload the contents of the `publish/` folder.
"""
from __future__ import annotations

import os
import shutil
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "publish")

FILES = [
    "apartment-charge.html",
    "manifest.webmanifest",
    "sw.js",
]
DIRS = ["icons"]


def _all(base):
    out = []
    for root, _dirs, files in os.walk(base):
        for f in files:
            out.append(os.path.join(root, f))
    return out


def main():
    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)

    for name in FILES:
        src = os.path.join(HERE, name)
        if not os.path.exists(src):
            print("!! missing file: %s" % name)
            return 1
        shutil.copy2(src, os.path.join(OUT, name))

    for name in DIRS:
        src = os.path.join(HERE, name)
        if os.path.isdir(src):
            shutil.copytree(src, os.path.join(OUT, name))

    shutil.copy2(
        os.path.join(HERE, "apartment-charge.html"),
        os.path.join(OUT, "index.html"),
    )

    files = _all(OUT)
    total = sum(os.path.getsize(f) for f in files)
    print("\npublish/ آماده شد  (%d فایل، %.0f کیلوبایت)" % (len(files), total / 1024.0))
    print("محتوای پوشه publish را روی هر هاست https آپلود کنید.")
    print("آدرس نهایی را روی گوشی باز کنید و از منوی کروم «نصب برنامه» را بزنید.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
