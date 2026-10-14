#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
# Copyright (c) 2026 Angelo Vincenti, aVince Industrietechnik

# Schritt 4, V4 (P19, Lehre T0): die Spices-Huelle aus scripts/build-spices.py,
# gebaut in einen Wegwerfordner.
#  A. Zip: oben nur <uuid>/, Inhalt = versionierte Dateien unter Desklet/
#     (byte-gleich), kein __pycache__/.pyc/.mo, Rechte Dateien 644, Ordner 755
#     (Unix-Eintraege); Entpacken wie Cinnamons Spices.py (extract + chmod aus
#     external_attr) ergibt lesbare Dateien und betretbare Ordner.
#  B. Pull-Request-Ordner nach den Regeln von validate-spice aus
#     linuxmint/cinnamon-spices-desklets: Pflichtdateien, info.json mit
#     author ohne Leerraum, metadata.json (Pflichtfelder, keine verbotenen
#     Felder, UUID, NUR ASCII), icon.png quadratisch, kein icon.png oben,
#     files/ enthaelt nur <uuid>/, desklet.js da, po/ nur .po/.pot mit genau
#     einer .pot, keine .mo, msgfmt -c ohne Meldung.
#     screenshot.png kommt erst aus V5 (Tower) - fehlt sie, nur ein Hinweis.
#  C. Lizenzangaben stimmen ueberein (info.json, metadata.json, README).
# Den echten validate-spice-Lauf ersetzt das nicht (Pruefbericht V4).
# Aufruf im Repository-Wurzelverzeichnis:  python3 tests/v4-spices-test.py

import atexit
import json
import os
import shutil
import stat
import struct
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parent.parent
WORK = Path(tempfile.mkdtemp(prefix="avl-v4-test."))
atexit.register(shutil.rmtree, WORK, True)

checks = 0
failures = 0


def check(name, actual, expected):
    global checks, failures
    checks += 1
    if actual == expected:
        print("  ok      " + name)
    else:
        failures += 1
        print(f"  FEHLER  {name}\n          erwartet {expected!r}\n          erhalten {actual!r}")


def png_size(path):
    data = Path(path).read_bytes()[:24]
    if data[:8] != b"\x89PNG\r\n\x1a\n" or data[12:16] != b"IHDR":
        return None
    return struct.unpack(">II", data[16:24])


out = subprocess.run([sys.executable, str(ROOT / "scripts/build-spices.py"), str(WORK / "dist")],
                     capture_output=True, text=True)
check("build-spices.py laeuft", out.returncode, 0)
if out.returncode != 0:
    print(out.stderr)
    print(f"Geprueft: {checks}, Fehler: {failures + 1}")
    sys.exit(1)

uuid = json.loads((ROOT / "Desklet/metadata.json").read_text(encoding="utf-8"))["uuid"]
tracked = sorted(p[len("Desklet/"):] for p in subprocess.run(
    ["git", "-C", str(ROOT), "ls-files", "-z", "--", "Desklet"],
    capture_output=True, check=True).stdout.decode().split("\0") if p)

print("A. Zip:")
archive = WORK / "dist" / (uuid + ".zip")
check("Zip und .sha256 da", (archive.is_file(), (WORK / "dist" / (uuid + ".zip.sha256")).is_file()), (True, True))
with zipfile.ZipFile(archive) as z:
    infos = z.infolist()
    names = [i.filename for i in infos]
    check("alles unter <uuid>/", all(n.startswith(uuid + "/") for n in names), True)
    files = sorted(n[len(uuid) + 1:] for n in names if not n.endswith("/"))
    check("Inhalt = git ls-files Desklet", files, tracked)
    check("kein __pycache__/.pyc/.mo",
          [n for n in names if "__pycache__" in n or n.endswith((".pyc", ".mo"))], [])
    check("Unix-Eintraege", {i.create_system for i in infos}, {3})
    check("Dateien 644", sorted({oct(i.external_attr >> 16) for i in infos if not i.filename.endswith("/")}),
          [oct(0o100644)])
    check("Ordner 755", sorted({oct(i.external_attr >> 16) for i in infos if i.filename.endswith("/")}),
          [oct(0o040755)])
    check("byte-gleich mit Desklet/",
          [f for f in files if z.read(uuid + "/" + f) != (ROOT / "Desklet" / f).read_bytes()], [])
    # Entpacken wie Cinnamons Spices.py (_install)
    unpack = WORK / "entpackt"
    unpack.mkdir()
    for member in infos:
        z.extract(member, unpack)
        os.chmod(unpack / member.filename, member.external_attr >> 16)
bad = []
for p in (unpack / uuid).rglob("*"):
    mode = stat.S_IMODE(p.stat().st_mode)
    if mode != (0o755 if p.is_dir() else 0o644):
        bad.append((str(p.relative_to(unpack)), oct(mode)))
check("entpackt: Rechte 644/755", bad, [])
check("entpackt: metadata.json lesbar", json.loads((unpack / uuid / "metadata.json").read_text())["uuid"], uuid)

print("B. Pull-Request-Ordner (Regeln von validate-spice):")
pr = WORK / "dist" / uuid
inner = pr / "files" / uuid
for f in ["info.json", f"files/{uuid}/metadata.json", f"files/{uuid}/icon.png", "README.md"]:
    check("Pflichtdatei " + f, (pr / f).is_file(), True)
if (pr / "screenshot.png").is_file():
    size = png_size(pr / "screenshot.png")
    check("screenshot.png ist PNG", size is not None, True)
else:
    print("  hinweis screenshot.png fehlt noch (kommt aus V5, Tower avltest)")
check("kein icon.png oben", (pr / "icon.png").exists(), False)
check("keine .po/.pot oben", [p.name for p in pr.glob("*") if p.suffix in (".po", ".pot")], [])
check("files/ enthaelt nur <uuid>", sorted(os.listdir(pr / "files")), [uuid])
info = json.loads((pr / "info.json").read_text(encoding="utf-8"))
check("info.json author ohne Leerraum", bool(info.get("author")) and not any(c.isspace() for c in info["author"]), True)
meta = json.loads((inner / "metadata.json").read_text(encoding="utf-8"))
check("metadata Pflichtfelder", [f for f in ("uuid", "name", "description") if f not in meta], [])
check("metadata ohne verbotene Felder", [f for f in ("icon", "dangerous", "last-edited") if f in meta], [])
check("metadata uuid = Ordner", meta["uuid"], uuid)
check("metadata nur ASCII", [k for k, v in meta.items() if len(str(v).encode()) != len(str(v))], [])
w, h = png_size(inner / "icon.png") or (0, 1)
check("icon.png quadratisch", w == h and w > 0, True)
check("desklet.js da", (inner / "desklet.js").is_file(), True)
po = inner / "po"
check("po/ nur .po/.pot", [p.name for p in po.iterdir() if p.suffix not in (".po", ".pot")], [])
check("genau eine .pot", len(list(po.glob("*.pot"))), 1)
check("keine .mo", [str(p) for p in inner.rglob("*.mo")], [])
for p in sorted(po.glob("*.po")):
    r = subprocess.run(["msgfmt", "-c", str(p), "-o", "-"], stdout=subprocess.DEVNULL,
                       stderr=subprocess.PIPE, text=True)
    check("msgfmt -c ohne Meldung: " + p.name, r.stderr, "")

print("C. Lizenzangaben:")
check("info.json license", info.get("license"), "GPL-3.0-only")
check("metadata nennt GPL-3.0-only", "GPL-3.0-only" in meta.get("comments", ""), True)
readme = (pr / "README.md").read_text(encoding="utf-8")
for word in ("GPL-3.0-only", "MHK924", "NotSirius-A", "MIT"):
    check("README nennt " + word, word in readme, True)

print(f"Geprueft: {checks}, Fehler: {failures}")
sys.exit(1 if failures else 0)
