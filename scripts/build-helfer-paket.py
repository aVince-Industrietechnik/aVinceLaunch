#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
# Copyright (c) 2026 Angelo Vincenti, aVince Industrietechnik

"""Baut das Zusatzpaket aVinceLaunch-Helfer-<Version>.tar.gz (Schritt 4, V3c, E5).

Aufruf im Repository-Wurzelverzeichnis:
    python3 scripts/build-helfer-paket.py [ZIELORDNER]      (Standard: dist/)

Das Archiv wird selbst gebaut (nicht git archive): feste Rechte 755/644 und
ohne Besitzer (Lehre T0 - git archive --format=zip speicherte keine Rechte),
die .mo frisch aus scripts/po/de.po. Zeitstempel = Zeit des letzten Commits.
"""

import io
import os
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent.parent
S = ROOT / "scripts"


def version():
    for line in (S / "avincelaunch-helfer").read_text(encoding="utf-8").splitlines():
        if line.startswith("VERSION = "):
            return line.split('"')[1]
    raise SystemExit("VERSION fehlt in scripts/avincelaunch-helfer")


EXECUTABLE = ["launcher-watch", "launcher-add", "launcher-move", "desktop-clean-toggle",
              "desktop-clean-shortcut", "desktop-doubleclick"]
DATA = ["avincelaunch_rules.py", "rules.example.json"]

INSTALL_SH = '#!/bin/sh\n# aVinceLaunch helpers - install (see README.md)\nexec python3 "$(dirname "$0")/avincelaunch-helfer" install "$@"\n'
UNINSTALL_SH = '#!/bin/sh\n# aVinceLaunch helpers - remove (see README.md)\nexec python3 "$(dirname "$0")/avincelaunch-helfer" uninstall "$@"\n'


def contents(mo_bytes):
    """[(Pfad im Archiv, Bytes, Rechte)]."""
    def read(path):
        return path.read_bytes()
    items = [
        ("install.sh", INSTALL_SH.encode(), 0o755),
        ("uninstall.sh", UNINSTALL_SH.encode(), 0o755),
        ("avincelaunch-helfer", read(S / "avincelaunch-helfer"), 0o755),
        ("README.md", read(S / "README.md"), 0o644),
        ("README.de.md", read(S / "README.de.md"), 0o644),
        ("LICENSE", read(ROOT / "LICENSE"), 0o644),
        ("nemo/avincelaunch-move-to-fence.nemo_action", read(S / "avincelaunch-move-to-fence.nemo_action"), 0o644),
        ("autostart/avincelaunch-watcher.desktop.in", read(S / "avincelaunch-watcher.desktop.in"), 0o644),
        ("autostart/avincelaunch-doubleclick.desktop.in", read(S / "avincelaunch-doubleclick.desktop.in"), 0o644),
        ("locale/de/LC_MESSAGES/avincelaunch-helfer.mo", mo_bytes, 0o644),
    ]
    items += [("bin/" + name, read(S / name), 0o755) for name in EXECUTABLE]
    items += [("bin/" + name, read(S / name), 0o644) for name in DATA]
    return items


def build(target_dir):
    name = "aVinceLaunch-Helfer-" + version()
    with tempfile.TemporaryDirectory() as tmp:
        mo = Path(tmp) / "de.mo"
        subprocess.run(["msgfmt", "-c", "-o", str(mo), str(S / "po/de.po")], check=True)
        mo_bytes = mo.read_bytes()
    try:
        mtime = int(subprocess.run(["git", "-C", str(ROOT), "log", "-1", "--format=%ct"],
                                   capture_output=True, text=True, check=True).stdout.strip())
    except (subprocess.CalledProcessError, ValueError):
        mtime = 0
    target_dir.mkdir(parents=True, exist_ok=True)
    archive = target_dir / (name + ".tar.gz")
    dirs = set()
    with tarfile.open(archive, "w:gz", format=tarfile.PAX_FORMAT) as tar:
        def add_dir(path):
            if path in dirs:
                return
            parent = os.path.dirname(path)
            if parent:
                add_dir(parent)
            info = tarfile.TarInfo(path)
            info.type, info.mode, info.mtime = tarfile.DIRTYPE, 0o755, mtime
            tar.addfile(info)
            dirs.add(path)
        add_dir(name)
        for path, data, mode in contents(mo_bytes):
            full = name + "/" + path
            add_dir(os.path.dirname(full))
            info = tarfile.TarInfo(full)
            info.size, info.mode, info.mtime = len(data), mode, mtime
            tar.addfile(info, io.BytesIO(data))
    return archive


if __name__ == "__main__":
    out = build(Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "dist")
    print(out)
