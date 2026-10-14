#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
# Copyright (c) 2026 Angelo Vincenti, aVince Industrietechnik

# Prueft Schritt 8, Paket S8-1 (Pruefung Phase 2) auf der Python-Seite in
# einem Wegwerfordner:
#   B10 orderFolderEditor.keep_missing_entries / ensure_sidecar (gleiche Faelle
#       wie tests/s8-1-test.js);
#   B11 Entfernen-Fenster der Liste: nur noch Abbrechen / In den Papierkorb,
#       Esc aendert nichts (ohne Fenster nachgebaut).
# Aufruf im Repository-Wurzelverzeichnis:  python3 tests/s8-1-test.py

import importlib.util
import json
import os
import re
import shutil
import sys
import tempfile

sys.dont_write_bytecode = True

WORK = tempfile.mkdtemp(prefix="avl-s8-1-test.")
os.environ["XDG_CONFIG_HOME"] = os.path.join(WORK, "config")
os.environ["XDG_DATA_HOME"] = os.path.join(WORK, "data")
import umleitung  # noqa: E402 - A9/P70: Abbruch, wenn die Umleitung nicht greift
umleitung.pruefe(WORK, "XDG_CONFIG_HOME", "XDG_DATA_HOME")
os.environ["LANGUAGE"] = "C"
os.makedirs(os.path.join(WORK, "config", "cinnamon", "spices", "avincelaunch-desklet@avince"))

spec = importlib.util.spec_from_file_location("avincelaunch_orderFolderEditor", "Desklet/orderFolderEditor.py")
E = importlib.util.module_from_spec(spec)
sys.modules["avincelaunch_orderFolderEditor"] = E
spec.loader.exec_module(E)

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


print("B10 fehlende Eintraege behalten ihren Platz (wie s8-1-test.js):")
DAY = 24 * 60 * 60
NOW = 1800000000
E._now_for_tests = NOW
CASES = [
    ("nichts fehlt", ["a", "b", "c"], ["a", "b", "c"], {}, ["a", "b", "c"], {}),
    ("b fehlt: bleibt an Platz 2", ["a", "b", "c"], ["a", "c"], {}, ["a", "b", "c"], {"b": NOW}),
    ("erster fehlt: bleibt vorn", ["a", "b", "c"], ["b", "c"], {}, ["a", "b", "c"], {"a": NOW}),
    ("zwei hintereinander fehlen", ["a", "b", "c", "d"], ["a", "d"], {}, ["a", "b", "c", "d"],
     {"b": NOW, "c": NOW}),
    ("Zeitstempel bleibt der erste", ["a", "b"], ["a"], {"b": NOW - 5 * DAY}, ["a", "b"],
     {"b": NOW - 5 * DAY}),
    ("nach 30 Tagen gestrichen", ["a", "b"], ["a"], {"b": NOW - 31 * DAY}, ["a"], {}),
    ("genau 30 Tage: noch da", ["a", "b"], ["a"], {"b": NOW - 30 * DAY}, ["a", "b"],
     {"b": NOW - 30 * DAY}),
    ("wieder da: Zeitstempel weg", ["a", "b"], ["a", "b"], {"b": NOW - DAY}, ["a", "b"], {}),
    ("neue Reihenfolge umsortiert, fehlender folgt Vorgaenger", ["a", "b", "c"], ["c", "a"], {},
     ["c", "a", "b"], {"b": NOW}),
    ("kaputter Zeitstempel = jetzt", ["a", "b"], ["a"], {"b": "x"}, ["a", "b"], {"b": NOW}),
]
for name, old, new, since, order, exp_since in CASES:
    got_order, got_since, _kept = E.keep_missing_entries(old, new, since)
    check(name, (got_order, got_since), (order, exp_since))

group = os.path.join(WORK, "TOOLS")
os.makedirs(group)
for item in ("a", "c"):
    with open(os.path.join(group, item + ".desktop"), "w") as handle:
        handle.write("[Desktop Entry]\nType=Application\nName=%s\nExec=true\n" % item.upper())
with open(os.path.join(group, ".avincelaunch.json"), "w") as handle:
    json.dump({"version": 1, "order": ["app:a.desktop", "app:b.desktop", "app:c.desktop"],
               "disabled": ["app:b.desktop"], "pinned": ["app:c.desktop"]}, handle)
items = E.scan_directory(group)
E.ensure_sidecar(group, items)
with open(os.path.join(group, ".avincelaunch.json")) as handle:
    data = json.load(handle)
check("Dialog-Einlesen: b behaelt Platz und Haken",
      (data["order"], data["disabled"], data.get("missingSince")),
      (["app:a.desktop", "app:b.desktop", "app:c.desktop"], ["app:b.desktop"], {"app:b.desktop": NOW}))
check("Angepinnt (vom Dialog nicht verwaltet) bleibt", data.get("pinned"), ["app:c.desktop"])
check("Liste zeigt nur Vorhandene", [i["id"] for i in items], ["app:a.desktop", "app:c.desktop"])
with open(os.path.join(group, "b.desktop"), "w") as handle:
    handle.write("[Desktop Entry]\nType=Application\nName=B\nExec=true\n")
E.ensure_sidecar(group, E.scan_directory(group))
with open(os.path.join(group, ".avincelaunch.json")) as handle:
    data = json.load(handle)
check("b wieder da: Platz 2, kein Zeitstempel", (data["order"], "missingSince" in data),
      (["app:a.desktop", "app:b.desktop", "app:c.desktop"], False))
check("b in der Liste wieder an Platz 2", [i["id"] for i in E.scan_directory(group)],
      ["app:a.desktop", "app:b.desktop", "app:c.desktop"])

print("B11 Entfernen-Fenster:")
source = open("Desklet/OrderListWidget.py", encoding="utf-8").read()
start = source.index("    def remove_item(")
end = source.index("    def list_changed(")
body = source[start:end]
check("kein Knopf \"Nur aus der Liste entfernen\"", "Remove from _list only" in body, False)
check("Knopf \"In den Papierkorb\" da", "Move to _trash" in body, True)
check("nur bei YES geht es weiter (Esc / Abbrechen aendern nichts)",
      bool(re.search(r"if response != Gtk\.ResponseType\.YES:\s*\n\s*return", body)), True)

shutil.rmtree(WORK)
print("")
print("Geprueft: %d, Fehler: %d" % (checks, failures))
sys.exit(1 if failures else 0)
