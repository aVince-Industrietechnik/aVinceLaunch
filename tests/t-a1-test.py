#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
# Copyright (c) 2026 Angelo Vincenti, aVince Industrietechnik

# Prueft Paket T-A1 der Pruefung Phase 3 Teil 2 an den Hilfsskripten, ganz im
# Wegwerfordner (HOME, XDG_CONFIG_HOME, XDG_DATA_HOME):
#   T3  Verknuepfungen werden nur NEU angelegt (rules.install_desktop_file,
#       genutzt von launcher-watch und launcher-add): nie ueberschreiben, auch
#       keinen toten Verweis, nie eine halbe Datei - auch auf Dateisystemen
#       ohne harte Verweise; already_in_launcher zaehlt tote Verweise mit.
#   N7  kaputte config.json/<ID>.json: gemeldet (einmal je Inhalt), nicht
#       still wie fehlend; rules.json wird exklusiv und atomar angelegt.
# Aufruf im Repository-Wurzelverzeichnis:  python3 tests/t-a1-test.py

import errno
import importlib.machinery
import importlib.util
import json
import os
import shutil
import stat
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True

WORK = tempfile.mkdtemp(prefix="avl-t-a1-test.")
os.environ["HOME"] = WORK
os.environ["XDG_CONFIG_HOME"] = os.path.join(WORK, ".config")
os.environ["XDG_DATA_HOME"] = os.path.join(WORK, ".local", "share")
import umleitung  # noqa: E402 - A9/P70: Abbruch, wenn die Umleitung nicht greift
umleitung.pruefe(WORK, "HOME", "XDG_CONFIG_HOME", "XDG_DATA_HOME")
sys.path.insert(0, os.path.abspath("scripts"))

import avincelaunch_rules as R  # noqa: E402

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


def leftovers(folder):
    return sorted(n for n in os.listdir(folder) if n.endswith(".tmp"))


ENTRY = b"[Desktop Entry]\nType=Application\nName=AVL Test\nExec=true\n"
src_dir = Path(WORK) / "quelle"
src_dir.mkdir()
(src_dir / "avl-test.desktop").write_bytes(ENTRY)
(src_dir / "verweis.desktop").symlink_to(src_dir / "avl-test.desktop")
group = Path(WORK) / "gruppen" / "OFFEN"

print("T3 neu anlegen:")
target, problem = R.install_desktop_file(src_dir / "avl-test.desktop", group)
check("angelegt", (target, problem), (group / "avl-test.desktop", None))
check("Inhalt", target.read_bytes(), ENTRY)
check("ausfuehrbar 755", stat.S_IMODE(target.stat().st_mode), 0o755)
check("keine Zwischendatei", leftovers(group), [])
target, problem = R.install_desktop_file(src_dir / "verweis.desktop", group)
check("Verweis als Quelle: Inhalt des Ziels", (problem, target.read_bytes()), (None, ENTRY))
check("... als echte Datei, kein Verweis", target.is_symlink(), False)

print("T3 nie ueberschreiben:")
(group / "avl-test.desktop").write_bytes(b"[Desktop Entry]\nName=Von Hand angepasst\n")
target, problem = R.install_desktop_file(src_dir / "avl-test.desktop", group)
check("vorhanden -> exists", (target, problem), (None, "exists"))
check("angepasste Kopie erhalten", b"Von Hand" in (group / "avl-test.desktop").read_bytes(), True)
dead_target = Path(WORK) / "woanders" / "ziel.desktop"
(group / "tot.desktop").symlink_to(dead_target)
(src_dir / "tot.desktop").write_bytes(ENTRY)
target, problem = R.install_desktop_file(src_dir / "tot.desktop", group)
check("toter Verweis gleichen Namens -> exists", (target, problem), (None, "exists"))
check("... nicht durch den Verweis geschrieben", dead_target.exists(), False)
check("keine Zwischendatei", leftovers(group), [])

print("T3 ohne harte Verweise (z. B. vfat):")
real_link = os.link


def no_link(*args, **kwargs):
    raise OSError(errno.EPERM, "Operation not permitted")


os.link = no_link
(src_dir / "fat.desktop").write_bytes(ENTRY)
target, problem = R.install_desktop_file(src_dir / "fat.desktop", group)
check("Rueckfall: exklusiv angelegt", (problem, target.read_bytes() if target else None), (None, ENTRY))
check("... 755", stat.S_IMODE(target.stat().st_mode), 0o755)
target, problem = R.install_desktop_file(src_dir / "fat.desktop", group)
check("... zweites Mal exists", problem, "exists")
real_fsync = os.fsync
calls = []


def full_disk(fd):
    calls.append(fd)
    if len(calls) >= 2:            # 1. Zwischendatei ok, 2. Zieldatei: Platte voll
        raise OSError(errno.ENOSPC, "No space left on device")
    return real_fsync(fd)


os.fsync = full_disk
(src_dir / "voll.desktop").write_bytes(ENTRY)
target, problem = R.install_desktop_file(src_dir / "voll.desktop", group)
os.fsync = real_fsync
os.link = real_link
check("Platte voll: Fehler gemeldet", (target, "No space" in (problem or "")), (None, True))
check("... keine halbe Datei", os.path.lexists(group / "voll.desktop"), False)
check("... keine Zwischendatei", leftovers(group), [])

print("T3 already_in_launcher:")
base = Path(R.base_directory())
(base / "GRUPPE").mkdir(parents=True)
(base / "GRUPPE" / "nur-verweis.desktop").symlink_to(Path(WORK) / "gibt-es-nicht.desktop")
check("toter Verweis gilt als einsortiert", R.already_in_launcher("nur-verweis.desktop"), True)
check("fehlender Name nicht", R.already_in_launcher("fehlt.desktop"), False)

print("N7 kaputte Dateien melden:")
reports = []
R.REPORT = reports.append
os.makedirs(R.CONFIG_FILE.parent, exist_ok=True)
R.CONFIG_FILE.write_text('{"baseDirectory": "/srv/x"')
check("kaputte config.json -> Standard", str(R.base_directory()), str(R.DEFAULT_BASE))
check("gemeldet", len(reports) == 1 and "config.json" in reports[0] and "damaged" in reports[0], True)
R.base_directory()
R.base_directory()
check("gleicher Inhalt: nur einmal gemeldet", len(reports), 1)
check("nichts kopiert oder geaendert", sorted(os.listdir(R.CONFIG_FILE.parent)), ["config.json"])
R.CONFIG_FILE.write_text("[kaputt")
R.base_directory()
check("neuer kaputter Inhalt: neue Meldung", len(reports), 2)
R.CONFIG_FILE.unlink()
R.base_directory()
check("fehlende Datei: keine Meldung", len(reports), 2)
R.REPORT = None

print("N7 rules.json exklusiv und atomar:")
check("angelegt", R.write_default_rules(), True)
check("gueltiges JSON", json.loads(R.RULES_FILE.read_text())["mode"], "suggest")
check("keine Zwischendatei", leftovers(R.RULES_FILE.parent), [])
R.RULES_FILE.write_text('{"version": 1, "mode": "off", "rules": []}')
check("vorhandene nie ueberschrieben", (R.write_default_rules(), json.loads(R.RULES_FILE.read_text())["mode"]),
      (False, "off"))

print("Waechter: install_launcher (T3) und Protokoll (N7):")
loader = importlib.machinery.SourceFileLoader("launcher_watch", "scripts/launcher-watch")
spec = importlib.util.spec_from_loader("launcher_watch", loader)
W = importlib.util.module_from_spec(spec)
loader.exec_module(W)
check("Waechter-Zustand im Wegwerfordner", str(W.STATE_DIR).startswith(WORK), True)
check("Meldungen ins Protokoll", R.REPORT is W.log, True)
(src_dir / "neu.desktop").write_bytes(ENTRY)
first = W.install_launcher(src_dir / "neu.desktop", "GRUPPE")
check("eingeordnet", first, base / "GRUPPE" / "neu.desktop")
first.write_bytes(b"[Desktop Entry]\nName=Inzwischen von Hand\n")
check("zweites Mal: None", W.install_launcher(src_dir / "neu.desktop", "GRUPPE"), None)
check("von Hand angelegte Datei erhalten", b"von Hand" in first.read_bytes(), True)
check("im Protokoll", "Already there, not overwritten" in W.LOG_FILE.read_text(), True)
R.CONFIG_FILE.write_text("{kaputt")
R.base_directory()
check("kaputte config.json im Waechter-Protokoll", "config.json is damaged" in W.LOG_FILE.read_text(), True)

shutil.rmtree(WORK)
print(f"\nGeprueft: {checks}, Fehler: {failures}")
sys.exit(1 if failures else 0)
