#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
# Copyright (c) 2026 Angelo Vincenti, aVince Industrietechnik

# Prueft scripts/launcher-watch (Pruefung Phase 2, A3-3: P14) mit einem
# Wegwerf-HOME: fehlende und kaputte state.json, atomares Schreiben.
# Es wird kein Dialog (zenity) geoeffnet und nichts im echten HOME geschrieben;
# gelesen werden nur die Programmordner unter /usr/share/applications usw.
# Aufruf im Repository-Wurzelverzeichnis:  python3 tests/watcher-state-test.py

import importlib.machinery
import importlib.util
import json
import os
import shutil
import stat
import sys
import tempfile

sys.dont_write_bytecode = True

WORK = tempfile.mkdtemp(prefix="avl-watcher-state-test.")
os.environ["HOME"] = WORK
# Teil 2 (T1/T12): die Skripte folgen jetzt XDG_* - beide in den Wegwerfordner,
# und Abbruch, wenn die Umleitung nicht greift.
os.environ["XDG_CONFIG_HOME"] = os.path.join(WORK, ".config")
os.environ["XDG_DATA_HOME"] = os.path.join(WORK, ".local", "share")
import umleitung  # noqa: E402 - A9/P70: Abbruch, wenn die Umleitung nicht greift
umleitung.pruefe(WORK, "HOME", "XDG_CONFIG_HOME", "XDG_DATA_HOME")
sys.path.insert(0, os.path.abspath("scripts"))

loader = importlib.machinery.SourceFileLoader("launcher_watch", "scripts/launcher-watch")
spec = importlib.util.spec_from_loader("launcher_watch", loader)
W = importlib.util.module_from_spec(spec)
loader.exec_module(W)

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


def listing():
    return sorted(os.listdir(W.STATE_DIR))


def log_text():
    try:
        return W.LOG_FILE.read_text()
    except FileNotFoundError:
        return ""


check("Wegwerf-HOME benutzt", str(W.STATE_DIR).startswith(WORK), True)
inventory = W.current_inventory()
print("  (heutiger Bestand: %d Programme, %d Desklets)" % (len(inventory["apps"]), len(inventory["desklets"])))

print("\nstate.json fehlt (P14):")
state = W.load_state()
check("Grundlinie = heutiger Bestand", state, inventory)
check("Datei angelegt", W.STATE_FILE.exists(), True)
check("nichts gilt als neu", set(W.get_apps()) - set(state["apps"]), set())
check("im Protokoll vermerkt", "baseline" in log_text(), True)

print("\nstate.json gueltig:")
own = {"apps": ["/x/a.desktop"], "desklets": [], "zukunft": 1}
W.save_state(own)
check("unveraendert gelesen", W.load_state(), own)
check("keine Kopie", [n for n in listing() if "broken" in n], [])

print("\nstate.json kaputt (P14):")
broken = b'{"apps": ["/x/a.desktop", "/x/b.desk'
W.STATE_FILE.write_bytes(broken)
os.chmod(W.STATE_FILE, 0o640)
state = W.load_state()
copies = [n for n in listing() if n.startswith("state.json.broken-")]
check("eine Kopie", len(copies), 1)
check("Kopie = kaputter Inhalt", (W.STATE_DIR / copies[0]).read_bytes(), broken)
check("Grundlinie = heutiger Bestand", state, inventory)
check("Datei jetzt gueltig", json.loads(W.STATE_FILE.read_text()), inventory)
check("Rechte bleiben", stat.S_IMODE(W.STATE_FILE.stat().st_mode), 0o640)
check("im Protokoll vermerkt", "not readable" in log_text(), True)

print("\nFalsche Form (Liste statt Objekt):")
W.STATE_FILE.write_text("[1, 2]")
W.load_state()
check("zweite Kopie", len([n for n in listing() if n.startswith("state.json.broken-")]), 2)

print("\nGueltiges JSON ohne apps (Teil 2, T4):")
before = len([n for n in listing() if n.startswith("state.json.broken-")])
W.STATE_FILE.write_text("{}")
check("{} -> Grundlinie statt Rueckfrageflut", W.load_state(), inventory)
check("{} gesichert", len([n for n in listing() if n.startswith("state.json.broken-")]), before + 1)
W.STATE_FILE.write_text('{"desklets": []}')
check("ohne apps -> Grundlinie", W.load_state(), inventory)
W.STATE_FILE.write_text('{"apps": "kein-array", "desklets": []}')
check("apps keine Liste -> Grundlinie", W.load_state(), inventory)
W.STATE_FILE.write_text('{"apps": []}')
check("ohne desklets bleibt gueltig", W.load_state(), {"apps": []})

print("\nJe Inhalt nur eine Kopie (Teil 2, T4):")
count = len([n for n in listing() if n.startswith("state.json.broken-")])
W.STATE_FILE.write_text("{}")
W.load_state()
check("gleicher kaputter Inhalt: keine weitere Kopie",
      len([n for n in listing() if n.startswith("state.json.broken-")]), count)
W.STATE_FILE.write_text("{nochmal kaputt")
W.load_state()
check("neuer kaputter Inhalt: eine weitere Kopie",
      len([n for n in listing() if n.startswith("state.json.broken-")]), count + 1)

print("\nAtomar:")
W.save_state({"apps": [], "desklets": []})
check("keine Zwischendatei", [n for n in listing() if n.endswith(".tmp")], [])

print("\n--baseline wie bisher:")
W.STATE_FILE.unlink()
W.baseline()
check("Bestand gespeichert", json.loads(W.STATE_FILE.read_text()), inventory)

shutil.rmtree(WORK)
print(f"\nGeprueft: {checks}, Fehler: {failures}")
sys.exit(1 if failures else 0)
