#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
# Copyright (c) 2026 Angelo Vincenti, aVince Industrietechnik

# Prueft den Einrichten-Dialog (Pruefung Phase 2, A4-1: P8, P30, P31) in
# einem Wegwerfordner: Speicherfunktion je Fence, Erkennung nicht
# uebernommener Listenaenderungen, Ordnerpruefung im Unterordner-Dialog.
# Nichts im Live-System wird gelesen oder geschrieben.
# Aufruf im Repository-Wurzelverzeichnis:  python3 tests/dialog-list-test.py

import importlib.util
import json
import os
import shutil
import sys
import tempfile

sys.dont_write_bytecode = True

WORK = tempfile.mkdtemp(prefix="avl-dialog-list-test.")
os.environ["XDG_CONFIG_HOME"] = os.path.join(WORK, "config")
os.environ["XDG_DATA_HOME"] = os.path.join(WORK, "data")
import umleitung  # noqa: E402 - A9/P70: Abbruch, wenn die Umleitung nicht greift
umleitung.pruefe(WORK, "XDG_CONFIG_HOME", "XDG_DATA_HOME")
os.makedirs(os.path.join(WORK, "config", "cinnamon", "spices", "avincelaunch-desklet@avince"))


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


# Wie im Dialog: alle Bausteine teilen sich die Module unter diesen Namen.
P = load("avincelaunch_orderListPending", "Desklet/orderListPending.py")
E = load("avincelaunch_orderFolderEditor", "Desklet/orderFolderEditor.py")

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


print("Speicherfunktion je Fence (P30):")
calls = []
cb4 = lambda: calls.append("4")
cb5 = lambda: calls.append("5")
P.set_order_list_flush_callback(cb4, "4")
P.set_order_list_flush_callback(cb5, "5")
P.flush_order_list_now("4")
check("nur die Liste von Fence 4", calls, ["4"])
P.clear_order_list_flush_callback(cb5, "4")
P.flush_order_list_now("4")
check("fremde Abmeldung loescht nichts", calls, ["4", "4"])
P.clear_order_list_flush_callback(cb4, "4")
check("eigene Abmeldung", P.flush_order_list_now("4"), False)
P.flush_order_list_now("5")
check("Fence 5 unberuehrt", calls, ["4", "4", "5"])

print("\nOffene Aenderungen erkennen (P31):")
base = os.path.join(WORK, "gruppen")
group = os.path.join(base, "BUERO")
os.makedirs(group)
for name in ("a", "b", "c"):
    with open(os.path.join(group, name + ".desktop"), "w") as handle:
        handle.write("[Desktop Entry]\nName=%s\nExec=true\n" % name)
with open(os.path.join(group, ".avincelaunch.json"), "w") as handle:
    json.dump({"version": 1, "order": ["app:c.desktop", "app:a.desktop", "app:b.desktop"],
               "disabled": ["app:b.desktop"]}, handle)
E.save_shared_base_directory(base)


class FakeSettings:
    def __init__(self, values):
        self.values = values
        self.instance_id = "4"

    def has_key(self, key):
        return key in self.values

    def get_value(self, key):
        return self.values[key]

    def set_value(self, key, value):
        self.values[key] = value


def row(name, enabled=True):
    return {"id-short": name + ".desktop", "name": name, "enabled": enabled,
            "type-icon": "application-x-executable-symbolic"}


saved_rows = [row("c"), row("a"), row("b", False)]
settings = FakeSettings({"subdirectory": "BUERO", "folder-sort": "mixed",
                         E.DATA_KEY: list(saved_rows)})
check("Liste = Ordner -> keine offenen Aenderungen", E.list_has_unapplied_changes(settings), False)
settings.values[E.DATA_KEY] = [row("a"), row("c"), row("b", False)]
check("umsortiert -> offen", E.list_has_unapplied_changes(settings), True)
settings.values[E.DATA_KEY] = [row("c"), row("a", False), row("b", False)]
check("Haken geaendert -> offen", E.list_has_unapplied_changes(settings), True)
with open(os.path.join(group, "neu.desktop"), "w") as handle:
    handle.write("[Desktop Entry]\nName=neu\nExec=true\n")
settings.values[E.DATA_KEY] = list(saved_rows)
check("neuer Eintrag nur im Ordner -> nicht offen", E.list_has_unapplied_changes(settings), False)
settings.values[E.DATA_KEY] = list(saved_rows) + [row("weg")]
check("Eintrag nur in der Liste -> nicht offen", E.list_has_unapplied_changes(settings), False)
settings.values[E.DATA_KEY] = []
check("leere Liste -> nicht offen", E.list_has_unapplied_changes(settings), False)
settings.values[E.DATA_KEY] = [row("a"), row("c"), row("b", False)]
check("ohne offene Aenderungen keine Rueckfrage noetig",
      E.confirm_unapplied_changes(FakeSettings({"subdirectory": "BUERO", E.DATA_KEY: list(saved_rows)})), True)

print("\nUnterordner-Dialog: Ordnerpruefung (P8):")
try:
    S = load("avl_SubdirectoryChooser", "Desklet/SubdirectoryChooser.py")
except Exception as error:
    S = None
    print("  (uebersprungen, Dialogbausteine nicht ladbar: %s)" % error)
if S is not None:
    outside = os.path.join(WORK, "woanders", "PROJEKT")
    os.makedirs(outside)
    os.symlink(outside, os.path.join(base, "PROJEKT"))
    check("Gruppenordner", S._relative_subdirectory(base, group), "BUERO")
    check("Gruppenordner als Verweis bleibt waehlbar",
          S._relative_subdirectory(base, os.path.join(base, "PROJEKT")), "PROJEKT")
    check("Basisordner selbst -> ungueltig", S._relative_subdirectory(base, base), None)
    check("ausserhalb -> ungueltig", S._relative_subdirectory(base, outside), None)
    check("keine Methode leert mehr die Auswahl",
          hasattr(S.SubdirectoryChooser, "_clear_selection"), False)

shutil.rmtree(WORK)
print(f"\nGeprueft: {checks}, Fehler: {failures}")
sys.exit(1 if failures else 0)
