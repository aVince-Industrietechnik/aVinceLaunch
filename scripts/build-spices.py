#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
# Copyright (c) 2026 Angelo Vincenti, aVince Industrietechnik

"""Baut die Spices-Huelle des Desklets (Schritt 4, V4).

Aufruf im Repository-Wurzelverzeichnis:
    python3 scripts/build-spices.py [ZIELORDNER]      (Standard: dist/spices/)

Ergebnis im Zielordner:
  avincelaunch-desklet@avince/        Ordner fuer den Pull Request in
                                      linuxmint/cinnamon-spices-desklets:
                                      info.json, README.md, screenshot.png
                                      (aus spices/) und files/<uuid>/ = Desklet/
  avincelaunch-desklet@avince.zip     so, wie die Spices-Seite es ausliefert:
                                      oben der Ordner <uuid>/, darin Desklet/
  avincelaunch-desklet@avince.zip.sha256

Inhalt = versionierte Dateien unter Desklet/ (git ls-files), also kein
__pycache__ und keine .mo. Rechte werden ausdruecklich gesetzt: Dateien 644,
Ordner 755 - Cinnamons Spices.py uebernimmt sie beim Entpacken aus dem Zip
(Lehre T0: git archive --format=zip speicherte keine Rechte).
Zeitstempel = Zeit des letzten Commits.
"""

import hashlib
import json
import shutil
import subprocess
import sys
import time
import zipfile
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent.parent
DESKLET = ROOT / "Desklet"
SPICES = ROOT / "spices"
UUID = json.loads((DESKLET / "metadata.json").read_text(encoding="utf-8"))["uuid"]
EXTRA = ["info.json", "README.md", "screenshot.png"]


def desklet_files():
    """Versionierte Dateien unter Desklet/, relativ dazu, sortiert."""
    out = subprocess.run(["git", "-C", str(ROOT), "ls-files", "-z", "--", "Desklet"],
                         capture_output=True, check=True).stdout.decode()
    return sorted(p[len("Desklet/"):] for p in out.split("\0") if p)


def commit_time():
    try:
        return int(subprocess.run(["git", "-C", str(ROOT), "log", "-1", "--format=%ct"],
                                  capture_output=True, text=True, check=True).stdout.strip())
    except (subprocess.CalledProcessError, ValueError):
        return 315532800  # 1980-01-01, fruehestes Datum im Zip


def build_folder(target_dir, files):
    folder = target_dir / UUID
    if folder.exists():
        shutil.rmtree(folder)
    inner = folder / "files" / UUID
    for rel in files:
        dest = inner / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(DESKLET / rel, dest)
        dest.chmod(0o644)
    missing = []
    for name in EXTRA:
        if (SPICES / name).is_file():
            shutil.copyfile(SPICES / name, folder / name)
            (folder / name).chmod(0o644)
        else:
            missing.append(name)
    for d in [folder, *[p for p in folder.rglob("*") if p.is_dir()]]:
        d.chmod(0o755)
    return folder, missing


def build_zip(target_dir, files):
    archive = target_dir / (UUID + ".zip")
    stamp = time.localtime(max(commit_time(), 315532800))[:6]
    dirs = set()

    def add_dir(z, path):
        if not path or path in dirs:
            return
        add_dir(z, path.rpartition("/")[0])
        info = zipfile.ZipInfo(path + "/", stamp)
        info.create_system = 3  # Unix: Rechte stehen in external_attr
        info.external_attr = (0o040755 << 16) | 0x10
        z.writestr(info, b"")
        dirs.add(path)

    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as z:
        add_dir(z, UUID)
        for rel in files:
            full = UUID + "/" + rel
            add_dir(z, full.rpartition("/")[0])
            info = zipfile.ZipInfo(full, stamp)
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, (DESKLET / rel).read_bytes())
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    (target_dir / (archive.name + ".sha256")).write_text(f"{digest}  {archive.name}\n", encoding="utf-8")
    return archive


def build(target_dir):
    target_dir.mkdir(parents=True, exist_ok=True)
    files = desklet_files()
    folder, missing = build_folder(target_dir, files)
    archive = build_zip(target_dir, files)
    return folder, archive, missing


if __name__ == "__main__":
    folder, archive, missing = build(Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "dist" / "spices")
    print(folder)
    print(archive)
    for name in missing:
        print(f"HINWEIS: spices/{name} fehlt - der Pull-Request-Ordner ist ohne diese Datei unvollstaendig.")
