#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
# Copyright (c) 2026 Angelo Vincenti, aVince Industrietechnik

# Prueft den Abgleich vor dem Speichern im Einrichten-Dialog (Pruefung
# Phase 2, A4-3: P12) mit Cinnamons ECHTER Klasse JSONSettingsHandler
# (/usr/share/cinnamon/cinnamon-settings/bin/JsonSettingsWidgets.py) auf einer
# Wegwerfdatei: Desklet/settingsMerge.py und orderFolderEditor.set_values_bundled /
# navigate_to_path (ein Speichern statt bis zu sechs, kein leerer Zwischenstand).
# Nichts im Live-System wird gelesen oder geschrieben.
# Aufruf im Repository-Wurzelverzeichnis:  python3 tests/dialog-merge-test.py

import importlib.util
import json
import os
import shutil
import sys
import tempfile

sys.dont_write_bytecode = True

WORK = tempfile.mkdtemp(prefix="avl-dialog-merge-test.")
os.environ["XDG_CONFIG_HOME"] = os.path.join(WORK, "config")
os.environ["XDG_DATA_HOME"] = os.path.join(WORK, "data")
import umleitung  # noqa: E402 - A9/P70: Abbruch, wenn die Umleitung nicht greift
umleitung.pruefe(WORK, "XDG_CONFIG_HOME", "XDG_DATA_HOME")
os.makedirs(os.path.join(WORK, "config", "cinnamon", "spices", "avincelaunch-desklet@avince"))

sys.path.insert(0, "/usr/share/cinnamon/cinnamon-settings")
sys.path.insert(0, "/usr/share/cinnamon/cinnamon-settings/bin")
import gi  # noqa: E402
gi.require_version("Gtk", "3.0")
from gi.repository import GObject  # noqa: E402
from JsonSettingsWidgets import JSONSettingsHandler  # noqa: E402


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


M = load("settingsMerge", "Desklet/settingsMerge.py")
E = load("orderFolderEditor", "Desklet/orderFolderEditor.py")

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


class Toggle(GObject.Object):
    """Statt eines Schalters im Dialog: eine Eigenschaft, an die gebunden wird."""
    active = GObject.Property(type=bool, default=False)


SCHEMA = {
    "collapsed": {"type": "generic", "default": False, "value": False},
    "show-tooltips": {"type": "switch", "default": True, "value": True},
    "position-x": {"type": "generic", "default": 0, "value": 800},
    "link-order-list-data": {"type": "generic", "default": [], "value": [{"id": "a"}]},
    "order-folder-path": {"type": "generic", "default": "", "value": ""},
    "order-breadcrumb-display": {"type": "generic", "default": "", "value": ""},
    "order-in-subfolder": {"type": "generic", "default": False, "value": False},
    "order-open-folder-id": {"type": "generic", "default": "", "value": "x"},
    "subdirectory": {"type": "generic", "default": "default", "value": "TOOLS"},
    "folder-sort": {"type": "generic", "default": "mixed", "value": "mixed"},
}


def fresh(name):
    path = os.path.join(WORK, name + ".json")
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(SCHEMA, handle, indent=4)
    notes = []
    handler = JSONSettingsHandler(path, notify_callback=lambda h, k, v: notes.append(k))
    return path, handler, notes


def desklet_writes(path, **changes):
    """Wie Cinnamons settings.js: ganze Datei aus dem Speicher des Desklets."""
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    for key, value in changes.items():
        data[key.replace("_", "-")]["value"] = value
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=4)


def on_disk(path, key):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)[key]["value"]


# --- Kontrolle: der Fehler P12 ohne Abgleich --------------------------------
print("Kontrolle ohne Abgleich (so war es):")
path, handler, notes = fresh("ohne")
desklet_writes(path, collapsed=True)
handler.set_value("show-tooltips", False)
check("Einklappen des Fence ging verloren", on_disk(path, "collapsed"), False)

# --- mit Abgleich -----------------------------------------------------------
print("P12 mit Abgleich:")
path, handler, notes = fresh("mit")
toggle = Toggle()
handler.bind("collapsed", toggle, "active", 0)
heard = []
handler.listen("collapsed", lambda k, v: heard.append(v))
M.install(handler)
M.install(handler)
check("zweimal einrichten schadet nicht", handler.save_settings.__name__, "save_settings")
desklet_writes(path, collapsed=True)
handler.set_value("show-tooltips", False)
check("Einklappen bleibt erhalten", on_disk(path, "collapsed"), True)
check("Klick im Dialog gespeichert", on_disk(path, "show-tooltips"), False)
check("Dialog kennt den neuen Wert", handler.get_value("collapsed"), True)
check("Anzeige zeigt ihn", toggle.active, True)
# Cinnamon meldet gebundene Werte zweimal (Bindung + Zuhoerer), so auch in
# seinem eigenen check_settings - massgeblich ist der Wert.
check("Zuhoerer erfahren ihn", (len(heard) > 0, set(heard)), (True, {True}))
heard_after_merge = len(heard)
check("Fence benachrichtigt (nur der Klick)", notes, ["show-tooltips"])

print("P12 beide aendern denselben Wert:")
desklet_writes(path, position_x=900)
handler.set_value("position-x", 100)
check("Dialog gilt", on_disk(path, "position-x"), 100)

print("P12 nach regulaerem Einlesen (2 s):")
desklet_writes(path, position_x=50)
handler.check_settings()
check("eingelesen", handler.get_value("position-x"), 50)
handler.set_value("show-tooltips", True)
check("danach nichts Altes zurueckgeschrieben", on_disk(path, "position-x"), 50)
check("... und keine falsche Uebernahme", len(heard), heard_after_merge)

print("P12 Datei gerade unlesbar:")
with open(path, "w", encoding="utf-8") as handle:
    handle.write("{")
try:
    handler.set_value("show-tooltips", False)
    raised = False
except Exception:
    raised = True
check("Speichern wie bisher, keine Ausnahme", raised, False)
check("Datei wieder vollstaendig", on_disk(path, "show-tooltips"), False)

# --- Navigation in einem Speichern -----------------------------------------
print("P12 Navigation in einem Speichern:")
path, handler, notes = fresh("navigation")
M.install(handler)
saves = []
inner = handler.save_settings


def counting_save(*args, **kwargs):
    saves.append(json.loads(json.dumps(handler.settings["link-order-list-data"]["value"])))
    return inner(*args, **kwargs)


handler.save_settings = counting_save
order = []
for key in ("link-order-list-data", "order-folder-path", "order-breadcrumb-display",
            "order-in-subfolder", "order-open-folder-id"):
    handler.listen(key, lambda k, v, key=key: order.append(k))
desklet_writes(path, collapsed=True)
E.set_values_bundled(handler, [
    ("link-order-list-data", [{"id": "b"}]),
    ("order-folder-path", "/x/TOOLS/Sub"),
    ("order-breadcrumb-display", "Sub"),
    ("order-in-subfolder", True),
    ("order-open-folder-id", ""),
], force_keys=("link-order-list-data",))
check("genau ein Speichern", len(saves), 1)
check("kein leerer Zwischenstand", [] in saves, False)
check("alle Werte in der Datei",
      [on_disk(path, k) for k in ("link-order-list-data", "order-folder-path",
                                   "order-in-subfolder", "order-open-folder-id")],
      [[{"id": "b"}], "/x/TOOLS/Sub", True, ""])
check("Zuhoerer in der alten Reihenfolge", order, [
    "link-order-list-data", "order-folder-path", "order-breadcrumb-display",
    "order-in-subfolder", "order-open-folder-id"])
check("Fence einmal benachrichtigt", notes, ["link-order-list-data"])
check("Aenderung des Fence dabei erhalten", on_disk(path, "collapsed"), True)

saves.clear()
order.clear()
notes.clear()
E.set_values_bundled(handler, [
    ("link-order-list-data", [{"id": "b"}]),
    ("order-folder-path", "/x/TOOLS/Sub"),
], force_keys=("link-order-list-data",))
check("nichts geaendert: kein Speichern, keine Meldung", (saves, notes), ([], []))
check("... die Liste meldet sich trotzdem", order, ["link-order-list-data"])

print("P12 navigate_to_path an einem echten Gruppenordner:")
base = os.path.join(WORK, "data", "avincelaunch")
tools = os.path.join(base, "TOOLS")
os.makedirs(os.path.join(tools, "Unterordner"))
with open(os.path.join(tools, "a.desktop"), "w") as handle:
    handle.write("[Desktop Entry]\nType=Application\nName=A\nExec=true\n")
saves.clear()
check("navigiert", E.navigate_to_path(handler, os.path.join(tools, "Unterordner")), True)
check("ein Speichern", len(saves), 1)
check("Ordner in der Datei", on_disk(path, "order-folder-path"), os.path.join(tools, "Unterordner"))
saves.clear()
check("zurueck nach oben", E.navigate_to_path(handler, tools), True)
check("ein Speichern, Liste mit Eintraegen",
      (len(saves), len(on_disk(path, "link-order-list-data")) >= 2), (1, True))

shutil.rmtree(WORK)
print("")
print("Geprueft: %d, Fehler: %d" % (checks, failures))
sys.exit(1 if failures else 0)
