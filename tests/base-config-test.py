#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
# Copyright (c) 2026 Angelo Vincenti, aVince Industrietechnik

# Prueft die Basisordner-Regel auf der Python-Seite und die Reihenfolge beim
# Wechsel im Dialog (Pruefung Phase 2, A4-2: P11, P32, P35) in einem
# Wegwerfordner: orderFolderEditor.py, portalGuard.py,
# scripts/avincelaunch_rules.py (gleiche Faelle wie tests/base-config-test.js),
# BaseDirectoryChooser.py und SubdirectoryChooser.py (ohne Fenster).
# Nichts im Live-System wird gelesen oder geschrieben.
# Aufruf im Repository-Wurzelverzeichnis:  python3 tests/base-config-test.py

import importlib.util
import json
import os
import shutil
import sys
import tempfile

sys.dont_write_bytecode = True

WORK = tempfile.mkdtemp(prefix="avl-base-config-test.")
# Meldungen unuebersetzt pruefen (sonst haengt der Test an der installierten de.mo).
os.environ["LANGUAGE"] = "C"
os.environ["XDG_CONFIG_HOME"] = os.path.join(WORK, "config")
os.environ["XDG_DATA_HOME"] = os.path.join(WORK, "data")
import umleitung  # noqa: E402 - A9/P70: Abbruch, wenn die Umleitung nicht greift
umleitung.pruefe(WORK, "XDG_CONFIG_HOME", "XDG_DATA_HOME")
OWN_DIR = os.path.join(WORK, "config", "avincelaunch")
LEGACY_DIR = os.path.join(WORK, "config", "thelauncher")
OWN = os.path.join(OWN_DIR, "config.json")
LEGACY = os.path.join(LEGACY_DIR, "config.json")
DEFAULT = os.path.join(WORK, "data", "avincelaunch")
HOME = os.path.expanduser("~")
for folder in (OWN_DIR, LEGACY_DIR):
    os.makedirs(folder)


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


E = load("orderFolderEditor", "Desklet/orderFolderEditor.py")
G = E._PORTAL_GUARD
R = load("avincelaunch_rules", "scripts/avincelaunch_rules.py")
# Pruefung Phase 3 Teil 2 (T1): die Pfade des Hilfsmoduls werden NICHT mehr
# von Hand umgebogen - es muss sie aus XDG_CONFIG_HOME/XDG_DATA_HOME selbst so
# finden wie Dialog und Portal-Schutz (Pruefung unten).

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


def put(path, text):
    if text is None:
        if os.path.exists(path):
            os.remove(path)
    else:
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)


def clear_broken():
    for folder in (OWN_DIR, LEGACY_DIR):
        for name in os.listdir(folder):
            if name.startswith("config.json.broken-"):
                os.remove(os.path.join(folder, name))


# --- T1: Hilfsskripte nehmen dieselben Benutzerordner -----------------------
print("T1 Pfade der Hilfsskripte (XDG wie Dialog):")
check("config.json", str(R.CONFIG_FILE), E.CONFIG_FILE)
check("alte config.json", str(R.LEGACY_CONFIG_FILE), E.LEGACY_CONFIG_FILE)
check("Standard-Basisordner", str(R.DEFAULT_BASE), DEFAULT)
check("Fence-Einstellungen wie Portal-Schutz", str(R.FENCE_SETTINGS_DIR), G._config_dir())
check("rules.json neben config.json", str(R.RULES_FILE), os.path.join(OWN_DIR, "rules.json"))
watch_code = open("scripts/launcher-watch", encoding="utf-8").read()
check("Waechter-Zustand unter XDG_DATA_HOME", "STATE_DIR = rules.DATA_HOME / " in watch_code, True)
check("Hilfsmodul ohne festes ~/.config", [l.strip() for l in open("scripts/avincelaunch_rules.py", encoding="utf-8")
      if '".config/' in l and not l.lstrip().startswith("#")], [])

# --- P11: eine Regel in allen drei Python-Stellen ---------------------------
print("P11 Regel (gleiche Faelle wie base-config-test.js):")
CASES = [
    ("beide fehlen -> Standard", None, None, DEFAULT),
    ("eigene Datei", '{"baseDirectory": "/srv/gruppen"}', None, "/srv/gruppen"),
    ("/ am Ende und .. bereinigt", '{"baseDirectory": "/srv/a/../gruppen/"}', None, "/srv/gruppen"),
    ("~ erweitert", '{"baseDirectory": "~/Gruppen"}', None, HOME + "/Gruppen"),
    ("Leerzeichen am Rand", '{"baseDirectory": "  /srv/g  "}', None, "/srv/g"),
    ("relativer Pfad -> Standard", '{"baseDirectory": "gruppen"}', '{"baseDirectory": "/alt"}', DEFAULT),
    ("ohne Wert -> Standard, nicht die alte Datei", '{"version": 1}', '{"baseDirectory": "/alt"}', DEFAULT),
    ("eigene fehlt -> alte Datei", None, '{"baseDirectory": "/alt"}', "/alt"),
    ("eigene kaputt -> alte Datei", '{"baseDirectory": "/neu"', '{"baseDirectory": "/alt"}', "/alt"),
    ("eigene ist Liste (kaputt) -> alte Datei", '["/neu"]', '{"baseDirectory": "/alt"}', "/alt"),
    ("beide kaputt -> Standard", "{", "{", DEFAULT),
    ("kein Text -> Standard", '{"baseDirectory": 5}', None, DEFAULT),
]
for name, own, legacy, expected in CASES:
    put(OWN, own)
    put(LEGACY, legacy)
    results = (E.resolve_shared_base(None), G.base_directory(), str(R.base_directory()))
    check(name, results, (expected, expected, expected))
clear_broken()

real = os.path.join(WORK, "echt")
link = os.path.join(WORK, "verweis")
os.makedirs(real)
os.symlink(real, link)
put(OWN, json.dumps({"baseDirectory": link}))
put(LEGACY, None)
check("Verweis wird nirgends aufgeloest",
      (E.resolve_shared_base(None), G.base_directory(), str(R.base_directory())), (link, link, link))

# --- P32/P35: Reihenfolge im Basisordner-Dialog -----------------------------
print("P32 Basisordner wechseln (ohne Fenster):")
try:
    B = load("BaseDirectoryChooser", "Desklet/BaseDirectoryChooser.py")
    S = load("SubdirectoryChooser", "Desklet/SubdirectoryChooser.py")
    have_gtk = True
except Exception as error:
    have_gtk = False
    print("  (Dialog-Teil uebersprungen: %s)" % error)


class Label:
    def __init__(self):
        self.text = ""

    def set_text(self, text):
        self.text = text


class Button:
    def __init__(self, log):
        self.log = log

    def set_sensitive(self, value):
        self.log.append(("Knopf", value))


class FakeSettings:
    def __init__(self, values, log):
        self.values = dict(values)
        self.log = log
        self.instance_id = "5"

    def has_key(self, key):
        return key in self.values

    def get_value(self, key):
        return self.values.get(key)


class FakeChooser:
    """Nur was _apply_chosen_path(_locked) braucht."""

    def __init__(self, module, settings, log, key):
        self.settings = settings
        self.key = key
        self.log = log
        self.status = Label()
        self.path_label = Label()
        self.browse_button = Button(log)
        self._updating = False
        self.errors = []
        self._module = module
        cls = module.BaseDirectoryChooser if key == "base-directory" else module.SubdirectoryChooser
        self._apply_chosen_path_locked = lambda path: cls._apply_chosen_path_locked(self, path)

    def _configured_base(self):
        return self.settings.get_value("base-directory") or ""

    def _current_subdirectory(self):
        return (self.settings.get_value("subdirectory") or "").strip()

    def _set_display(self, text):
        self.path_label.set_text(text)

    def _show_error(self, text):
        self.errors.append(text)
        self.status.set_text(text)

    def _clear_error(self):
        pass

    def _refresh_display(self):
        pass

    def _warn_outside_base(self, base):
        self.errors.append("ausserhalb")

    def _notify_desklet(self, name):
        self.log.append(("Desklet", name))

    def get_toplevel(self):
        return None


if have_gtk:
    log = []

    def fake_save(path):
        log.append(("config.json", path))
        put(OWN, json.dumps({"version": 1, "baseDirectory": path}))
        return path

    def fake_set(settings, key, value):
        log.append(("Instanz", key, value))
        settings.values[key] = value
        return True

    B.save_shared_base_directory = fake_save
    B.set_value_safe = fake_set
    B.navigate_to_path = lambda settings, path: log.append(("Liste", path)) or True

    new_base = os.path.join(WORK, "neu")
    old_base = os.path.join(WORK, "alt")
    os.makedirs(old_base)
    put(OWN, json.dumps({"baseDirectory": old_base}))
    settings = FakeSettings({"base-directory": old_base, "subdirectory": "BUERO"}, log)
    chooser = FakeChooser(B, settings, log, "base-directory")
    result = B.BaseDirectoryChooser._apply_chosen_path(chooser, new_base + "/")
    check("Wechsel gelingt", result, True)
    check("Reihenfolge: config.json, Instanz, Liste, Desklet; Knopf gesperrt", log, [
        ("Knopf", False),
        ("config.json", new_base),
        ("Instanz", "base-directory", new_base),
        ("Liste", os.path.join(new_base, "BUERO")),
        ("Desklet", "on_base_directory_selected_callback"),
        ("Knopf", True),
    ])
    check("kein leerer Zwischenwert", any(e[0] == "Instanz" and e[2] == "" for e in log), False)

    log.clear()
    result = B.BaseDirectoryChooser._apply_chosen_path(chooser, new_base)
    check("gleicher Ordner: Instanz nicht neu geschrieben, Desklet benachrichtigt",
          [e[0] for e in log], ["Knopf", "config.json", "Liste", "Desklet", "Knopf"])

    log.clear()

    def failing_save(path):
        log.append(("config.json", path))
        raise OSError("Datentraeger voll")

    B.save_shared_base_directory = failing_save
    put(OWN, json.dumps({"baseDirectory": new_base}))
    settings.values["base-directory"] = new_base
    other = os.path.join(WORK, "anders")
    result = B.BaseDirectoryChooser._apply_chosen_path(chooser, other)
    check("config.json scheitert: Rueckgabe False", result, False)
    check("... nichts weiter getan, Knopf wieder frei",
          log, [("Knopf", False), ("config.json", other), ("Knopf", True)])
    check("... Instanzkopie unveraendert", settings.values["base-directory"], new_base)
    check("... rote Zeile", len(chooser.errors) == 1 and "Nothing was changed" in chooser.errors[0], True)

    check("Basisordner-Dialog loest Verweise nicht auf", B._normalize_dir(link + "/"), link)

    print("T15 Basisordner-Wechsel fragt vor dem Neuladen (Teil 2):")
    B.save_shared_base_directory = fake_save
    asked = []
    real_confirm = B._EDITOR.confirm_unapplied_changes
    B._EDITOR.confirm_unapplied_changes = lambda s, parent=None: asked.append("Rueckfrage") or False
    log.clear()
    with open(OWN, encoding="utf-8") as handle:
        own_before = handle.read()
    target15 = os.path.join(WORK, "noch-neuer")
    result = B.BaseDirectoryChooser._apply_chosen_path(chooser, target15)
    check("Abbrechen: kein Wechsel", result, False)
    check("... gefragt", asked, ["Rueckfrage"])
    with open(OWN, encoding="utf-8") as handle:
        check("... config.json unveraendert", handle.read(), own_before)
    check("... nichts geschrieben oder geladen", [e for e in log if e[0] != "Knopf"], [])
    check("... kein Ordner angelegt", os.path.exists(target15), False)
    B._EDITOR.confirm_unapplied_changes = lambda s, parent=None: asked.append("weiter") or True
    result = B.BaseDirectoryChooser._apply_chosen_path(chooser, target15)
    check("Weiter: Wechsel gelingt", (result, asked[-1]), (True, "weiter"))
    check("... config.json zuerst", [e for e in log if e[0] != "Knopf"][0], ("config.json", target15))
    B._EDITOR.confirm_unapplied_changes = real_confirm

    print("P32 Unterordner ohne Zwischenwert:")
    log.clear()
    S.set_value_safe = fake_set
    S.navigate_to_path = lambda settings, path: log.append(("Liste", path)) or True
    S._EDITOR.confirm_unapplied_changes = lambda settings, parent=None: True
    S._resolve_base = lambda settings: new_base
    os.makedirs(os.path.join(new_base, "BUERO"), exist_ok=True)
    sub_settings = FakeSettings({"subdirectory": "BUERO"}, log)
    sub_chooser = FakeChooser(S, sub_settings, log, "subdirectory")
    result = S.SubdirectoryChooser._apply_chosen_path(sub_chooser, os.path.join(new_base, "BUERO"))
    check("gleicher Unterordner: kein \"\" und kein neues Schreiben",
          [e for e in log if e[0] == "Instanz"], [])
    check("... trotzdem neu geladen und benachrichtigt",
          [e[0] for e in log], ["Knopf", "Liste", "Desklet", "Knopf"])
    log.clear()
    os.makedirs(os.path.join(new_base, "TOOLS"), exist_ok=True)
    S.SubdirectoryChooser._apply_chosen_path(sub_chooser, os.path.join(new_base, "TOOLS"))
    check("anderer Unterordner: genau ein Schreiben",
          [e for e in log if e[0] == "Instanz"], [("Instanz", "subdirectory", "TOOLS")])

shutil.rmtree(WORK)
print("")
print("Geprueft: %d, Fehler: %d" % (checks, failures))
sys.exit(1 if failures else 0)
