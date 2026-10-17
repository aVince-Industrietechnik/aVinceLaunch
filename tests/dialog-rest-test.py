#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
# Copyright (c) 2026 Angelo Vincenti, aVince Industrietechnik

# Prueft A4-4 (Pruefung Phase 2: P34, P36, P59, P60) ohne Cinnamon in einem
# Wegwerfordner:
#   P36  Dialog (orderFolderEditor.scan_directory) und Fence
#        (lib/linkScanner.js scanDirectoryAsync, per cjs) lesen denselben Ordner gleich;
#   P34  Navigieren in schreibgeschuetzte / fehlende Ordner ohne Abbruch;
#   P59  Meldung an den Fence faengt D-Bus-Fehler ab (absichtlich ungueltiger
#        Bus - das laufende Cinnamon wird NIE angesprochen);
#   P60  jede Dialogdatei einmal geladen, alle teilen orderFolderEditor,
#        safeJson, portalGuard; Knopfliste vergisst zerstoerte Knoepfe.
# Aufruf im Repository-Wurzelverzeichnis:  python3 tests/dialog-rest-test.py

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True

WORK = tempfile.mkdtemp(prefix="avl-dialog-rest-test.")
os.environ["XDG_CONFIG_HOME"] = os.path.join(WORK, "config")
os.environ["XDG_DATA_HOME"] = os.path.join(WORK, "data")
os.environ["LANGUAGE"] = "de"
# P59: nie den echten Sitzungsbus (Cinnamon) ansprechen.
os.environ["DBUS_SESSION_BUS_ADDRESS"] = "unix:path=" + os.path.join(WORK, "kein-bus")
os.makedirs(os.path.join(WORK, "config", "cinnamon", "spices", "avincelaunch-desklet@avince"))
REPO = os.getcwd()
DESKLET = os.path.join(REPO, "Desklet")

sys.path.insert(0, "/usr/share/cinnamon/cinnamon-settings")
sys.path.insert(0, "/usr/share/cinnamon/cinnamon-settings/bin")
import gi  # noqa: E402
gi.require_version("Gtk", "3.0")
from JsonSettingsWidgets import JSONSettingsHandler  # noqa: E402


def load(name, path):
    module = sys.modules.get(name)
    if module is not None:
        return module
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


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


def write(path, text, mode=None):
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)
    if mode is not None:
        os.chmod(path, mode)


# Wie im Dialog: settingsPageBuilder laedt die Bausteine als avincelaunch_<Datei>.
E = load("avincelaunch_orderFolderEditor", os.path.join(DESKLET, "orderFolderEditor.py"))

# --- P36: gleiche Regel wie der Fence ---------------------------------------
print("P36 Dialog und Fence lesen gleich:")
group = os.path.join(WORK, "data", "avincelaunch", "BUERO")
os.makedirs(os.path.join(group, "Unterordner"))
write(os.path.join(group, "kalender.desktop"),
      "[Desktop Entry]\nType=Application\nName=Calendar\nName[de]=Kalender\nExec=true\n")
write(os.path.join(group, "versteckt-mit-exec.desktop"),
      "[Desktop Entry]\nType=Application\nName=Versteckt\nExec=true\nNoDisplay=true\n")
write(os.path.join(group, "ohne-exec.desktop"),
      "[Desktop Entry]\nType=Application\nName=Ohne Exec\nNoDisplay=true\n")
write(os.path.join(group, "verweis-typ.desktop"),
      "[Desktop Entry]\nType=Link\nName=Webseite\nURL=https://example.org\n")
write(os.path.join(group, "bericht.final.pdf"), "pdf")
write(os.path.join(group, ".versteckt.txt"), "x")
write(os.path.join(group, "gesperrt.txt"), "x", 0o000)
os.symlink(os.path.join(group, "Unterordner"), os.path.join(group, "Verweis-Ordner"))
os.symlink(os.path.join(group, "gibt-es-nicht"), os.path.join(group, "kaputter-verweis.txt"))
root_reads_all = os.access(os.path.join(group, "gesperrt.txt"), os.R_OK)

python_items = sorted((i["id"], i["name"]) for i in E.scan_directory(group))

shim = tempfile.mkdtemp(prefix="avl-shim-", dir=WORK)
os.makedirs(os.path.join(shim, "desklets"))
os.symlink(DESKLET, os.path.join(shim, "desklets", "avincelaunch-desklet@avince"))
script = os.path.join(WORK, "scan.js")
write(script, """
imports.searchPath.unshift(%s);
const L = imports.desklets["avincelaunch-desklet@avince"].lib.linkScanner;
const GLib = imports.gi.GLib;
const loop = new GLib.MainLoop(null, false);
let r = null;
L.scanDirectoryAsync(%s, { persistOrder: false }, result => { r = result; loop.quit(); });
loop.run();
print(JSON.stringify(r.manualItems.map(i => [i.id, i.name])));
""" % (json.dumps(shim), json.dumps(group)))
run = subprocess.run(["cjs", script], capture_output=True, text=True, timeout=60)
try:
    js_items = sorted(tuple(x) for x in json.loads(run.stdout.strip().splitlines()[-1]))
except Exception:
    js_items = None
    print("  (cjs: %s)" % (run.stderr.strip()[:300]))

check("Fence-Scan lief", js_items is not None, True)
check("Dialog zeigt dieselben Eintraege mit denselben Namen wie der Fence", python_items, js_items)
names = dict(python_items)
check("uebersetzter Name (Kalender statt Calendar)", names.get("app:kalender.desktop"), "Kalender")
check("ausgeblendeter Starter mit Exec: wie im Fence gezeigt",
      names.get("app:versteckt-mit-exec.desktop"), "Versteckt")
check("nicht startbarer Starter weggelassen", "app:ohne-exec.desktop" in names, False)
check("Typ Link ohne Exec weggelassen", "app:verweis-typ.desktop" in names, False)
check("Dokument ohne letzte Endung", names.get("document:bericht.final.pdf"), "bericht.final")
check("Verweis auf Ordner als Ordner", names.get("folder:Verweis-Ordner"), "Verweis-Ordner")
check("kaputter Verweis weggelassen", "document:kaputter-verweis.txt" in names, False)
check("versteckte Datei weggelassen", "document:.versteckt.txt" in names, False)
if not root_reads_all:
    check("unlesbare Datei weggelassen", "document:gesperrt.txt" in names, False)
os.chmod(os.path.join(group, "gesperrt.txt"), 0o644)

# --- P34: Navigieren ohne Abbruch -------------------------------------------
print("P34 Navigieren bei Schreib-/Lesefehlern:")
SCHEMA = {
    "link-order-list-data": {"type": "generic", "default": [], "value": []},
    "order-folder-path": {"type": "generic", "default": "", "value": ""},
    "order-breadcrumb-display": {"type": "generic", "default": "", "value": ""},
    "order-in-subfolder": {"type": "generic", "default": False, "value": False},
    "order-open-folder-id": {"type": "generic", "default": "", "value": ""},
    "subdirectory": {"type": "generic", "default": "default", "value": "BUERO"},
    "folder-sort": {"type": "generic", "default": "mixed", "value": "mixed"},
}
settings_file = os.path.join(WORK, "5.json")
write(settings_file, json.dumps(SCHEMA, indent=4))
handler = JSONSettingsHandler(settings_file, notify_callback=None)
handler.instance_id = "5"

readonly = os.path.join(group, "Nurlesen")
os.makedirs(readonly)
write(os.path.join(readonly, "a.desktop"), "[Desktop Entry]\nType=Application\nName=A\nExec=true\n")
os.chmod(readonly, 0o555)
try:
    result = E.navigate_to_path(handler, readonly)
    error = None
except Exception as exc:
    result, error = None, repr(exc)
os.chmod(readonly, 0o755)
check("schreibgeschuetzter Ordner: kein Abbruch", error, None)
check("... wird angezeigt", (result, [r.get("id-short") or r.get("id") for r in handler.get_value("link-order-list-data")] != []),
      (True, True))
if not root_reads_all:
    check("... keine Sidecar-Datei (nicht schreibbar)",
          os.path.exists(os.path.join(readonly, ".avincelaunch.json")), False)
try:
    result = E.navigate_to_path(handler, os.path.join(group, "gibt-es-nicht"))
    error = None
except Exception as exc:
    result, error = None, repr(exc)
check("fehlender Ordner: kein Abbruch, False", (error, result), (None, False))

# --- P59: Meldung an den Fence ----------------------------------------------
print("P59 Meldung an den Fence ohne erreichbares Cinnamon:")
try:
    ok = E.notify_desklet(handler, "on_items_changed_callback")
    error = None
except Exception as exc:
    ok, error = None, repr(exc)
check("kein Abbruch, Rueckgabe False", (error, ok), (None, False))
check("auch mit Instanz-ID als Text", E.notify_desklet("5", "x"), False)


class Recorder:
    def __init__(self):
        self.values = {}
        self.instance_id = "5"
        self.notify_callback = None

    def has_key(self, key):
        return True

    def set_value(self, key, value):
        self.values[key] = value


rec = Recorder()
check("set_value_safe schreibt", (E.set_value_safe(rec, "order-list-stale", False), rec.values),
      (True, {"order-list-stale": False}))

# --- P60: jede Datei einmal -------------------------------------------------
print("P60 Module einmal je Dialog:")
loaded = {}
for name in ("OrderListWidget", "ItemsActionBar", "BaseDirectoryChooser", "SubdirectoryChooser",
             "PortalPathChooser", "OrderFolderHeader", "BackHomeButton", "ScrollableCollapsiblePage",
             "settingsPageBuilder"):
    try:
        loaded[name] = load("avincelaunch_" + name, os.path.join(DESKLET, name + ".py"))
    except Exception as exc:
        loaded[name] = None
        print("  (%s nicht ladbar: %s)" % (name, exc))
editors = {id(getattr(m, "_EDITOR", None)) for n, m in loaded.items()
           if m is not None and hasattr(m, "_EDITOR")}
check("alle Bausteine teilen EIN orderFolderEditor", editors, {id(E)})
check("safeJson einmal", E._SAFE_JSON is sys.modules.get("avincelaunch_safeJson"), True)
check("portalGuard einmal (Dialog und Starter-Import)",
      E._PORTAL_GUARD is sys.modules.get("avincelaunch_linkImport")._PORTAL_GUARD, True)
check("kein Modul mehr unter altem Namen",
      sorted(k for k in sys.modules if k.startswith("thelauncher")), [])
builder = loaded.get("settingsPageBuilder")
if builder is not None:
    first = builder._load_custom_widget.__globals__["sys"].modules.get("avincelaunch_BaseDirectoryChooser")
    check("Seitenbauer nutzt dieselben Bausteine", first is loaded["BaseDirectoryChooser"], True)

bar = load("avincelaunch_itemsBarButtons", os.path.join(DESKLET, "itemsBarButtons.py"))


class FakeButton:
    def __init__(self):
        self.handlers = {}

    def connect(self, signal, callback):
        self.handlers.setdefault(signal, []).append(callback)

    def get_realized(self):
        return False


button = FakeButton()
bar.apply_bar_button_width(button)
bar.apply_bar_button_width(button)
check("Knopf einmal in der Liste", bar._BAR_BUTTONS.count(button), 1)
for callback in button.handlers.get("destroy", []):
    callback(button)
check("zerstoerter Knopf vergessen", button in bar._BAR_BUTTONS, False)

shutil.rmtree(WORK, ignore_errors=True)
print("")
print("Geprueft: %d, Fehler: %d" % (checks, failures))
sys.exit(1 if failures else 0)
