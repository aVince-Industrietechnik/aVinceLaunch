#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
# Copyright (c) 2026 Angelo Vincenti, aVince Industrietechnik

# Prueft die Dateiregeln des Einrichten-Dialogs (Pruefung Phase 2, A3-2:
# P4, P5, P11, P80) in einem Wegwerfordner: Desklet/safeJson.py und
# Desklet/orderFolderEditor.py (config.json, Sidecar-Dateien).
# Nichts im Live-System wird gelesen oder geschrieben.
# Aufruf im Repository-Wurzelverzeichnis:  python3 tests/dialog-files-test.py

import importlib.util
import json
import os
import shutil
import stat
import sys
import tempfile

sys.dont_write_bytecode = True

WORK = tempfile.mkdtemp(prefix="avl-dialog-files-test.")
os.environ["XDG_CONFIG_HOME"] = os.path.join(WORK, "config")
os.environ["XDG_DATA_HOME"] = os.path.join(WORK, "data")
os.makedirs(os.path.join(WORK, "config", "cinnamon", "spices", "avincelaunch-desklet@avince"))

spec = importlib.util.spec_from_file_location("orderFolderEditor", "Desklet/orderFolderEditor.py")
E = importlib.util.module_from_spec(spec)
spec.loader.exec_module(E)
J = E._SAFE_JSON

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


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)


def read(path):
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read()


def backups(path):
    directory = os.path.dirname(path)
    prefix = os.path.basename(path) + ".broken-"
    return sorted(n for n in os.listdir(directory) if n.startswith(prefix))


def temp_files(directory):
    return sorted(n for n in os.listdir(directory) if n.endswith(".tmp"))


DEFAULT_BASE = os.path.join(WORK, "data", "avincelaunch")
OWN = E.CONFIG_FILE
LEGACY = E.LEGACY_CONFIG_FILE

print("config.json - Rueckfallregel wie lib/config.js (P11):")
check("beide fehlen -> Standard", E.load_shared_base_directory(), DEFAULT_BASE)
write(LEGACY, json.dumps({"version": 1, "baseDirectory": "/alt/gruppen"}))
check("nur alte -> alte", E.load_shared_base_directory(), "/alt/gruppen")
write(OWN, json.dumps({"version": 1, "baseDirectory": "/neu/gruppen"}))
check("eigene gueltig -> eigene", E.load_shared_base_directory(), "/neu/gruppen")
broken_config = '{"version": 1, "baseDirectory": "/neu/gru'
write(OWN, broken_config)
J._reset_for_tests()
check("eigene kaputt -> alte (wie Desklet)", E.load_shared_base_directory(), "/alt/gruppen")
check("eigene kaputt: unveraendert", read(OWN), broken_config)
check("eigene kaputt: eine Kopie", len(backups(OWN)), 1)
os.remove(LEGACY)
check("eigene kaputt, keine alte -> Standard", E.load_shared_base_directory(), DEFAULT_BASE)
check("zweimal gelesen: weiter eine Kopie", len(backups(OWN)), 1)

print("\nconfig.json - Speichern (P5):")
os.chmod(OWN, 0o640)
E.save_shared_base_directory("/gewaehlt/gruppen")
check("bewusste Wahl ersetzt kaputte Datei", json.loads(read(OWN))["baseDirectory"], "/gewaehlt/gruppen")
check("Kopie der kaputten Datei bleibt", len(backups(OWN)), 1)
check("Rechte bleiben", stat.S_IMODE(os.stat(OWN).st_mode), 0o640)
check("Zeilenende wie bisher", read(OWN).endswith("}\n"), True)
check("keine Zwischendatei", temp_files(os.path.dirname(OWN)), [])

print("\nBasisordner nicht aufloesen (P11):")
real = os.path.join(WORK, "echt")
link = os.path.join(WORK, "verweis")
os.makedirs(real)
os.symlink(real, link)
E.save_shared_base_directory(link)
check("Verweis bleibt Verweis", E.resolve_shared_base(None), link)

print("\nSidecar - kaputte eigene Datei, gueltige alte (P4):")
group = os.path.join(WORK, "gruppen", "BUERO")
os.makedirs(group)
for name in ("a.desktop", "b.desktop", "c.desktop"):
    write(os.path.join(group, name), "[Desktop Entry]\nName=%s\nExec=true\n" % name)
own_sc = os.path.join(group, ".avincelaunch.json")
legacy_sc = os.path.join(group, ".thelauncher.json")
write(legacy_sc, json.dumps({"version": 1, "order": ["app:c.desktop", "app:a.desktop", "app:b.desktop"],
                             "disabled": ["app:b.desktop"], "itemStyles": {"folder:X": {"icon": "folder-red"}}}))
broken_sc = '{"version": 1, "order": ["app:b.desktop", "app:a.de'
write(own_sc, broken_sc)
# Kopie, wie sie das Desklet (lib/safeJson.js) schon angelegt haette:
write(own_sc + ".broken-2026-10-07_16-48-50", broken_sc)
J._reset_for_tests()
sc = E.read_sidecar(group)
check("Reihenfolge aus der alten Datei", sc["order"], ["app:c.desktop", "app:a.desktop", "app:b.desktop"])
check("Aus-Haken aus der alten Datei", sc["disabled"], ["app:b.desktop"])
check("als kaputt markiert", sc.get("_broken"), True)
check("Kopie des Desklets wiederverwendet", len(backups(own_sc)), 1)
check("write_sidecar lehnt ab", E.write_sidecar(group, sc), False)
items = [{"id": "app:%s.desktop" % n, "enabled": True} for n in ("a", "b", "c", "neu")]
E.ensure_sidecar(group, items)
check("Navigieren/Aktualisieren schreibt nicht", read(own_sc), broken_sc)


class FakeSettings:
    def __init__(self, values):
        self.values = values

    def has_key(self, key):
        return key in self.values

    def get_value(self, key):
        return self.values[key]


E.save_shared_base_directory(os.path.join(WORK, "gruppen"))
settings = FakeSettings({"subdirectory": "BUERO"})
check("Ordnerstil wird abgelehnt (False)", E.save_folder_style(settings, "folder:X", "folder-blue", ""), False)
check("eigene Datei weiter unveraendert", read(own_sc), broken_sc)
check("alte Datei unveraendert", json.loads(read(legacy_sc))["order"][0], "app:c.desktop")
check("_broken nie geschrieben", "_broken" in read(legacy_sc), False)

print("\nSidecar - repariert:")
write(own_sc, json.dumps({"version": 1, "order": ["app:b.desktop"], "disabled": [], "pinned": ["app:b.desktop"]}))
os.chmod(own_sc, 0o664)
check("Ordnerstil gespeichert (True)", E.save_folder_style(settings, "folder:X", "folder-blue", ""), True)
data = json.loads(read(own_sc))
check("Stil geschrieben", data["itemStyles"]["folder:X"]["icon"], "folder-blue")
check("unbekanntes Feld (pinned) bleibt", data.get("pinned"), ["app:b.desktop"])
check("Rechte bleiben", stat.S_IMODE(os.stat(own_sc).st_mode), 0o664)
check("keine Zwischendatei", temp_files(group), [])

print("\nSidecar - nur kaputte alte Datei:")
group2 = os.path.join(WORK, "gruppen", "GRAFIK")
write(os.path.join(group2, "a.desktop"), "[Desktop Entry]\nName=a\nExec=true\n")
write(os.path.join(group2, ".thelauncher.json"), "{kaputt")
E.ensure_sidecar(group2, [{"id": "app:a.desktop", "enabled": True}])
check("keine neue .avincelaunch.json", os.path.exists(os.path.join(group2, ".avincelaunch.json")), False)
check("Kopie der alten Datei", len(backups(os.path.join(group2, ".thelauncher.json"))), 1)

print("\nSidecar - Normalfall:")
group3 = os.path.join(WORK, "gruppen", "TOOLS")
write(os.path.join(group3, "a.desktop"), "[Desktop Entry]\nName=a\nExec=true\n")
E.ensure_sidecar(group3, [{"id": "app:a.desktop", "enabled": True}])
check("fehlende Datei wird angelegt",
      json.loads(read(os.path.join(group3, ".avincelaunch.json")))["order"], ["app:a.desktop"])

print("\nTeil 2 (T13) - kaputte Datei entfernt, alte Datei gilt nicht mehr:")
group4 = os.path.join(WORK, "gruppen", "INTERNET")
write(os.path.join(group4, "a.desktop"), "[Desktop Entry]\nName=a\nExec=true\n")
legacy4 = os.path.join(group4, ".thelauncher.json")
write(legacy4, json.dumps({"version": 1, "order": ["app:alt.desktop"], "disabled": ["app:a.desktop"]}))
own4 = os.path.join(group4, ".avincelaunch.json")
write(own4 + ".broken-2026-10-10_12-00-00", "{kaputt")   # Kopie der entfernten Datei
check("has_broken_copy", J.has_broken_copy(own4), True)
sc4 = E.read_sidecar(group4)
check("NICHT die alte Datei, neu beginnen", (sc4["order"], sc4["disabled"], sc4.get("_broken")), ([], [], None))
check("Schreiben erlaubt", E.sidecar_source_broken(group4), False)
E.ensure_sidecar(group4, [{"id": "app:a.desktop", "enabled": True}])
check("neue .avincelaunch.json aus dem Ordner", json.loads(read(own4))["order"], ["app:a.desktop"])
check("alte Datei unveraendert", json.loads(read(legacy4))["order"], ["app:alt.desktop"])
group5 = os.path.join(WORK, "gruppen", "MEDIEN")
os.makedirs(group5)
write(os.path.join(group5, ".thelauncher.json"), json.dumps({"version": 1, "order": ["app:x.desktop"]}))
check("ohne Kopie: alte Datei wie bisher (Umstieg)", E.read_sidecar(group5)["order"], ["app:x.desktop"])

print("\nsafeJson - gleiche Sekunde, anderer Inhalt:")
target = os.path.join(WORK, "x.json")
write(target, "{1")
J.secure_broken(target)
write(target, "{2")
J.secure_broken(target)
check("zwei Kopien", len(backups(target)), 2)

shutil.rmtree(WORK)
print(f"\nGeprueft: {checks}, Fehler: {failures}")
sys.exit(1 if failures else 0)
