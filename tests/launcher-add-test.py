#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
# Copyright (c) 2026 Angelo Vincenti, aVince Industrietechnik

# Prueft scripts/launcher-add (Pruefung Phase 2, A7: P23, P24) vollstaendig im
# Wegwerfordner: HOME, XDG_CONFIG_HOME und XDG_DATA_HOME zeigen dorthin, auch
# die Liste enabled-desklets kommt aus einer eigenen dconf-Datenbank
# (dconf compile) - kein Zugriff auf die echten Einstellungen.
# V5f / N30: auch der uebersetzte Name (Name[de]) wird gefunden.
# Pruefung Phase 3 Teil 2 (T11): vorher reichte der Test das echte
# XDG_CONFIG_HOME durch (fuer die echte enabled-desklets) und war nur sicher,
# weil die Skripte XDG_CONFIG_HOME ignorierten (T1); mit weniger als zwei
# Fences endete er still "bestanden".
# Aufruf im Repository-Wurzelverzeichnis:  python3 tests/launcher-add-test.py

import ast
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True

WORK = Path(tempfile.mkdtemp(prefix="avl-launcher-add-test."))
UUID = "avincelaunch-desklet@avince"
os.environ["HOME"] = str(WORK)
os.environ["XDG_CONFIG_HOME"] = str(WORK / ".config")
os.environ["XDG_DATA_HOME"] = str(WORK / ".local/share")
import umleitung  # noqa: E402 - A9/P70: Abbruch, wenn die Umleitung nicht greift
umleitung.pruefe(str(WORK), "HOME", "XDG_CONFIG_HOME", "XDG_DATA_HOME")

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


def run(*args, env=None):
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", **(env or {}))
    return subprocess.run([sys.executable, "scripts/launcher-add", *args],
                          capture_output=True, text=True, env=env, timeout=30)


# Zwei Schein-Fences in einer eigenen dconf-Datenbank unter dem umgebogenen
# XDG_CONFIG_HOME: gsettings liest sie ohne D-Bus (Schreiben braeuchte den
# dconf-Dienst - es wird nichts geschrieben).
ids = ["901", "902"]
keyfiles = WORK / "dconf-quelle"
keyfiles.mkdir()
(keyfiles / "00-test").write_text(
    "[org/cinnamon]\nenabled-desklets=['%s:%s:50:50', '%s:%s:425:50']\n"
    % (UUID, ids[0], UUID, ids[1]))
(WORK / ".config/dconf").mkdir(parents=True)
compiled = subprocess.run(["dconf", "compile", str(WORK / ".config/dconf/user"), str(keyfiles)],
                          capture_output=True, text=True)
check("eigene dconf-Datenbank angelegt", compiled.returncode, 0)
seen = subprocess.run(["gsettings", "get", "org.cinnamon", "enabled-desklets"],
                      capture_output=True, text=True).stdout.strip()
check("gsettings liest die Schein-Fences",
      [e.split(":")[1] for e in ast.literal_eval(seen.removeprefix("@as ")) if e.startswith(UUID + ":")],
      ids)

spices = WORK / ".config/cinnamon/spices" / UUID
spices.mkdir(parents=True)
base = WORK / "gruppen"
(WORK / ".config/avincelaunch").mkdir(parents=True)
(WORK / ".config/avincelaunch/config.json").write_text(json.dumps({"baseDirectory": str(base)}))


def fence(fence_id, subdirectory, locked):
    (spices / f"{fence_id}.json").write_text(json.dumps({
        "source-mode": {"value": "group"},
        "subdirectory": {"value": subdirectory},
        "fence-title": {"value": subdirectory},
        "lock-content": {"value": locked},
    }))
    (base / subdirectory).mkdir(parents=True, exist_ok=True)


fence(ids[0], "OFFEN", False)
fence(ids[1], "GESPERRT", True)

apps = WORK / ".local/share/applications"
apps.mkdir(parents=True)
(apps / "avl-testprogramm.desktop").write_text(
    "[Desktop Entry]\nType=Application\nName=AVL Testprogramm\nExec=true\n")

print("Gesperrter Fence ist kein Ziel (P24):")
r = run("AVL Testprogramm", "GESPERRT")
check("abgelehnt (Exit 1)", r.returncode, 1)
check("Meldung nennt die Sperre", "Content locked" in r.stdout, True)
check("nichts kopiert", list((base / "GESPERRT").iterdir()), [])
r = run()
check("Gruppenliste ohne gesperrten Fence", "GESPERRT" in r.stdout, False)

print("\nNie ueberschreiben (P23):")
r = run("AVL Testprogramm", "OFFEN")
target = base / "OFFEN" / "avl-testprogramm.desktop"
check("erstes Mal kopiert", (r.returncode, target.exists()), (0, True))
target.write_text("[Desktop Entry]\nType=Application\nName=Mein angepasster Name\nExec=true --x\n")
r = run("AVL Testprogramm", "OFFEN")
check("zweites Mal abgelehnt (Exit 1)", r.returncode, 1)
check("Meldung", "not overwritten" in r.stdout, True)
check("angepasste Kopie erhalten", "Mein angepasster Name" in target.read_text(), True)

print("\nUebersetzter Name wie im Startmenue (V5f / N30):")
(apps / "avl-testrechner.desktop").write_text(
    "[Desktop Entry]\nType=Application\nName=AVL Calc Probe\nName[de]=AVL Taschenrechner Probe\nExec=true\n")
deutsch = dict(LANGUAGE="", LC_ALL="", LC_MESSAGES="", LANG="de_DE.UTF-8")
r = run("Taschenrechner Probe", "OFFEN", env=deutsch)
copied = base / "OFFEN/avl-testrechner.desktop"
check("deutscher Name gefunden und kopiert", (r.returncode, copied.exists()), (0, True))
check("Ausgabe mit deutschem Namen", r.stdout.strip().endswith("AVL Taschenrechner Probe -> OFFEN"), True)
copied.unlink(missing_ok=True)
r = run("AVL Calc Probe", "OFFEN", env=deutsch)
check("englischer Name geht weiter", (r.returncode, copied.exists()), (0, True))
copied.unlink(missing_ok=True)
r = run("Taschenrechner Probe", "OFFEN", env=dict(LANGUAGE="C", LC_ALL="", LC_MESSAGES="", LANG=""))
check("ohne deutsche Sprache nur der englische Name", (r.returncode, copied.exists()), (1, False))

shutil.rmtree(WORK)
print(f"\nGeprueft: {checks}, Fehler: {failures}")
sys.exit(1 if failures else 0)
