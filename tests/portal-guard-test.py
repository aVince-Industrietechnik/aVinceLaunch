#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
# Copyright (c) 2026 Angelo Vincenti, aVince Industrietechnik

# Prueft den Portal-Schutz der Dialogseite (Pruefung Phase 2, A6: P10, P26,
# P27, P28, P29) in einem Wegwerfordner: Desklet/portalGuard.py und
# Desklet/orderFolderEditor.py (Sidecar, Ordnerstil).
# Nichts im Live-System wird gelesen oder geschrieben.
# Aufruf im Repository-Wurzelverzeichnis:  python3 tests/portal-guard-test.py

import importlib.util
import json
import os
import shutil
import sys
import tempfile

sys.dont_write_bytecode = True

WORK = tempfile.mkdtemp(prefix="avl-portal-guard-test.")
os.environ["XDG_CONFIG_HOME"] = os.path.join(WORK, "config")
os.environ["XDG_DATA_HOME"] = os.path.join(WORK, "data")
import umleitung  # noqa: E402 - A9/P70: Abbruch, wenn die Umleitung nicht greift
umleitung.pruefe(WORK, "XDG_CONFIG_HOME", "XDG_DATA_HOME")
SPICES = os.path.join(WORK, "config", "cinnamon", "spices", "avincelaunch-desklet@avince")
os.makedirs(SPICES)

spec = importlib.util.spec_from_file_location("orderFolderEditor", "Desklet/orderFolderEditor.py")
E = importlib.util.module_from_spec(spec)
spec.loader.exec_module(E)
G = E._PORTAL_GUARD

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


def instance(iid, mode="group", portal=""):
    data = {"source-mode": {"type": "generic", "value": mode},
            "portal-path": {"type": "generic", "value": portal}}
    with open(os.path.join(SPICES, "%s.json" % iid), "w", encoding="utf-8") as handle:
        json.dump(data, handle)


def set_base(path):
    os.makedirs(os.path.join(WORK, "config", "avincelaunch"), exist_ok=True)
    with open(os.path.join(WORK, "config", "avincelaunch", "config.json"), "w") as handle:
        json.dump({"version": 1, "baseDirectory": path}, handle)


HOME = os.path.join(WORK, "home")
BASE = os.path.join(HOME, ".local", "share", "thelauncher-groups")
GROUP = os.path.join(BASE, "BUERO")
OTHER = os.path.join(HOME, "Downloads")
for folder in (GROUP, OTHER):
    os.makedirs(folder)
set_base(BASE)

# --- P10: Basisordner nie gesperrt ------------------------------------------
print("P10 Basisordner:")
G._enabled_for_tests = ["4", "40"]
instance(4, "group")
instance(40, "portal", HOME)
check("Basisordner aus config.json", G.base_directory(), BASE)
check("Portal auf ~ sperrt Gruppenordner nicht", G.is_portal_path(GROUP), False)
check("Basisordner selbst frei", G.is_portal_path(BASE), False)
check("uebriger Inhalt gesperrt", G.is_portal_path(OTHER), True)
check(".. aus dem Basisordner hinaus gesperrt", G.is_portal_path(BASE + "/../x"), True)
check("refuse im Gruppenordner = nein", G.refuse(GROUP, "Test"), False)
check("Portal enthaelt Basisordner (Warnung P27)", G.contains_base_directory(HOME), True)
check("Portal / enthaelt Basisordner", G.contains_base_directory("/"), True)
check("Portal Downloads enthaelt ihn nicht", G.contains_base_directory(OTHER), False)
check("Portal auf Gruppenordner enthaelt Basis nicht", G.contains_base_directory(GROUP), False)

# --- P28: nur eingeschaltete Fences, unlesbar = ablehnen, kein realpath -----
print("P28 Instanzdateien:")
instance(40, "portal", OTHER)
instance(112, "portal", os.path.join(HOME, "Alt"))
check("ausgeschalteter Fence 112 zaehlt nicht",
      G.is_portal_path(os.path.join(HOME, "Alt", "x")), False)
check("eingeschaltetes Portal zaehlt", G.is_portal_path(os.path.join(OTHER, "y")), True)
G._enabled_for_tests = ["4", "40", "112"]
check("nach Einschalten zaehlt 112", G.is_portal_path(os.path.join(HOME, "Alt", "x")), True)
G._enabled_for_tests = ["4", "40", "77"]
check("fehlende Datei eines Fence: kein Portal, keine Sperre",
      G.is_portal_path(os.path.join(HOME, "Bilder")), False)
with open(os.path.join(SPICES, "4.json"), "w") as handle:
    handle.write('{"source-mode": {"value": "group"')
check("kaputte Datei: ausserhalb des Basisordners abgelehnt",
      G.is_portal_path(os.path.join(HOME, "Bilder")), True)
check("kaputte Datei: Basisordner bleibt frei", G.is_portal_path(GROUP), False)
with open(os.path.join(SPICES, "4.json"), "w") as handle:
    handle.write("[1, 2]")
check("kein Objekt: abgelehnt", G.is_portal_path(os.path.join(HOME, "Bilder")), True)
instance(4, "group")

link = os.path.join(HOME, "zu-downloads")
os.symlink(OTHER, link)
real_realpath = os.path.realpath


def no_realpath(*args, **kwargs):
    raise AssertionError("realpath aufgerufen")


os.path.realpath = no_realpath
try:
    result = G.is_portal_path(os.path.join(OTHER, "z"))
    called = False
except AssertionError:
    result, called = None, True
os.path.realpath = real_realpath
check("kein realpath beim Pruefen", called, False)
check("... und richtig gesperrt", result, True)
check("Verweis wird wie im Desklet nicht aufgeloest", G.is_portal_path(os.path.join(link, "z")), False)

# --- P26: Netzlaufwerk ------------------------------------------------------
print("P26 Netzlaufwerk:")
G._tables_for_tests = {
    "/proc/self/mountinfo": "61 22 0:51 / /mnt/nas-share rw - autofs systemd-1 rw\n"
                            "91 22 0:61 / /media/Mit\\040Leer rw - nfs4 srv:/x rw\n",
    "/etc/fstab": "# Kommentar\nUUID=a / ext4 defaults 0 1\n"
                  "//nas/Backup /mnt/nas-backup cifs noauto 0 0\n"
                  "sshfs#me@h:/ /mnt/ssh fuse defaults 0 0\n",
}
check("autofs", G.is_network_path("/mnt/nas-share/60"), True)
check("cifs nur in fstab", G.is_network_path("/mnt/nas-backup/a"), True)
check("sshfs#", G.is_network_path("/mnt/ssh"), True)
check("\\040", G.is_network_path("/media/Mit Leer/b"), True)
check("lokal", G.is_network_path("/home/u"), False)
check("aehnlicher Name", G.is_network_path("/mnt/nas-backupX"), False)
G._tables_for_tests = None

# --- P29: Ordnerstil meldet Misserfolg --------------------------------------
print("P29 Ordnerstil:")


class FakeSettings:
    def __init__(self, values):
        self.values = values

    def has_key(self, key):
        return key in self.values

    def get_value(self, key):
        return self.values.get(key)


G._enabled_for_tests = ["4", "40"]
instance(40, "portal", OTHER)
settings = FakeSettings({"subdirectory": "BUERO", "order-folder-path": GROUP})
check("Ordnerstil im Gruppenordner gespeichert",
      E.save_folder_style(settings, "folder:Sub", "folder-blue", ""), True)
with open(os.path.join(GROUP, ".avincelaunch.json")) as handle:
    check("Stil steht in der Datei", json.load(handle)["itemStyles"]["folder:Sub"], {"icon": "folder-blue"})

check("im Portal (ausserhalb Basis): nicht gespeichert",
      E.write_sidecar(OTHER, {"order": [], "disabled": []}), False)
check("keine Datei im Portal", os.path.exists(os.path.join(OTHER, ".avincelaunch.json")), False)

readonly = os.path.join(BASE, "NURLESEN")
os.makedirs(readonly)
os.chmod(readonly, 0o555)
can_test_rights = not os.access(readonly, os.W_OK)
if can_test_rights:
    check("Schreibfehler: False statt Ausnahme",
          E.write_sidecar(readonly, {"order": [], "disabled": []}), False)
    ro_settings = FakeSettings({"subdirectory": "NURLESEN", "order-folder-path": readonly})
    check("Ordnerstil bei Schreibfehler: False",
          E.save_folder_style(ro_settings, "folder:X", "folder-red", ""), False)
else:
    print("  (Schreibrechte-Test uebersprungen: laeuft als root)")
os.chmod(readonly, 0o755)

with open(os.path.join(GROUP, ".avincelaunch.json"), "w") as handle:
    handle.write('{"order": [')
check("kaputte Sidecar: Ordnerstil nicht gespeichert",
      E.save_folder_style(settings, "folder:Sub", "folder-red", ""), False)
with open(os.path.join(GROUP, ".avincelaunch.json")) as handle:
    check("kaputte Datei unveraendert", handle.read(), '{"order": [')

shutil.rmtree(WORK)
print("")
print("Geprueft: %d, Fehler: %d" % (checks, failures))
sys.exit(1 if failures else 0)
