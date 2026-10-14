#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
# Copyright (c) 2026 Angelo Vincenti, aVince Industrietechnik

# Prueft Schritt 8, Paket S8-3 (Pruefung Phase 2: B14 / P51) mit einem
# Wegwerf-HOME und eigenen Programmordnern: Programmordner aus
# XDG_DATA_HOME / XDG_DATA_DIRS (+ Snap, + bisherige vier), neue Ordner still
# als gesehen, fehlende Ordner nur vorgemerkt, alte state.json ohne "dirs",
# launcher-add mit derselben Ordnerliste. Kein Dialog, nichts im echten HOME.
# Aufruf im Repository-Wurzelverzeichnis:  python3 tests/s8-3-test.py

import importlib.machinery
import importlib.util
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True

WORK = tempfile.mkdtemp(prefix="avl-s8-3-test.")
os.environ["HOME"] = WORK
os.environ["XDG_CONFIG_HOME"] = os.path.join(WORK, ".config")
DATA_HOME = os.path.join(WORK, "data-home")
SYS_A = os.path.join(WORK, "sys-a")
SYS_B = os.path.join(WORK, "sys-b")
os.environ["XDG_DATA_HOME"] = DATA_HOME
os.environ["XDG_DATA_DIRS"] = SYS_A + ":" + SYS_B + "::" + SYS_A + "/"
import umleitung  # noqa: E402 - A9/P70: Abbruch, wenn die Umleitung nicht greift
umleitung.pruefe(WORK, "HOME", "XDG_CONFIG_HOME", "XDG_DATA_HOME")
sys.path.insert(0, os.path.abspath("scripts"))


def load(name, path):
    loader = importlib.machinery.SourceFileLoader(name, path)
    spec = importlib.util.spec_from_loader(name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


W = load("launcher_watch", "scripts/launcher-watch")
R = W.rules
messages = []
W.log = lambda text: messages.append(text)

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


def app(directory, name, label):
    os.makedirs(directory, exist_ok=True)
    with open(os.path.join(directory, name), "w") as handle:
        handle.write("[Desktop Entry]\nType=Application\nName=%s\nExec=true\n" % label)


print("B14 Ordnerliste:")
dirs = [str(d) for d in R.app_dirs()]
check("eigener Ordner zuerst", dirs[0], DATA_HOME + "/applications")
check("dann XDG_DATA_DIRS in Reihenfolge, doppelte und leere weg",
      dirs[1:3], [SYS_A + "/applications", SYS_B + "/applications"])
check("Snap dabei", str(R.SNAP_APP_DIR) in dirs, True)
check("bisherige vier dabei", all(str(d) in dirs for d in R.LEGACY_APP_DIRS), True)
check("keine doppelten", len(dirs), len(set(dirs)))
saved = os.environ.pop("XDG_DATA_DIRS")
check("ohne XDG_DATA_DIRS: /usr/local/share, /usr/share",
      [str(d) for d in R.app_dirs()][1:3], ["/usr/local/share/applications", "/usr/share/applications"])
os.environ["XDG_DATA_DIRS"] = saved

print("B14 neue Ordner:")
legacy_home = os.path.join(WORK, ".local/share/applications")
app(legacy_home, "alt.desktop", "Alt")
old_state = {"apps": [legacy_home + "/alt.desktop"], "desklets": []}
app(SYS_A + "/applications", "a1.desktop", "A1")
app(SYS_A + "/applications", "a2.desktop", "A2")
directories = [Path(legacy_home), Path(SYS_A + "/applications"), Path(SYS_B + "/applications")]
state = json.loads(json.dumps(old_state))
check("alte state.json wird ergaenzt", W.sync_app_dirs(state, directories), True)
check("bisherige vier gelten als bekannt", all(str(d) in state["dirs"] for d in R.LEGACY_APP_DIRS), True)
check("vorhandener neuer Ordner: Programme still gesehen",
      sorted(p for p in state["apps"] if p.startswith(SYS_A)),
      [SYS_A + "/applications/a1.desktop", SYS_A + "/applications/a2.desktop"])
check("fehlender Ordner nur vorgemerkt",
      (SYS_B + "/applications" in state["dirs"], any(p.startswith(SYS_B) for p in state["apps"])), (True, False))
check("Protokoll: eine Zeile je neuem Ordner",
      [m.split(":")[0] for m in messages], ["New program folder", "Program folder noted (does not exist yet)"])
check("alter Eintrag bleibt", legacy_home + "/alt.desktop" in state["apps"], True)
messages.clear()
check("zweiter Lauf: nichts mehr zu tun", (W.sync_app_dirs(state, directories), messages), (False, []))

app(SYS_B + "/applications", "neu.desktop", "Neu")
found = set(W.get_apps(directories).keys()) - set(state["apps"])
check("spaeter auftauchender Ordner: Programm gilt als NEU (wird gefragt)",
      sorted(found), [SYS_B + "/applications/neu.desktop"])
app(SYS_A + "/applications", "a3.desktop", "A3")
found = set(W.get_apps(directories).keys()) - set(state["apps"])
check("neues Programm im uebernommenen Ordner wird gefragt",
      sorted(found), [SYS_A + "/applications/a3.desktop", SYS_B + "/applications/neu.desktop"])

print("B14 Grundlinie und launcher-add:")
inventory = W.current_inventory()
check("Grundlinie kennt alle Ordner", sorted(inventory["dirs"]), sorted(str(d) for d in R.app_dirs()))
# launcher-add fuehrt beim Laden sein Hauptprogramm aus - darum am Quelltext.
add_source = open("scripts/launcher-add", encoding="utf-8").read()
check("launcher-add nutzt dieselben Ordner (rules.app_dirs, keine eigene Liste)",
      ("APPDIRS = rules.app_dirs()" in add_source, "/usr/share/applications" in add_source), (True, False))

shutil.rmtree(WORK)
print("")
print("Geprueft: %d, Fehler: %d" % (checks, failures))
sys.exit(1 if failures else 0)
