#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
# Copyright (c) 2026 Angelo Vincenti, aVince Industrietechnik

# Schritt 4, V3b (K9, K2-3) ohne Cinnamon, in einem Wegwerfordner:
#  A. Uebersetzung der Helfer: Vorlage = frisch erzeugt, de.po vollstaendig,
#     keine deutschen Texte mehr im Code; zur Laufzeit englisch ohne und
#     deutsch mit Uebersetzung (Python ueber gettext, Bash ueber das Programm
#     gettext).
#  B. Regeln: "then" als Liste (erster vorhandener Fence gewinnt);
#     rules.example.json = Tabellen der Startaufstellung (appSort.py) mit
#     englischen und deutschen Ordnernamen, keine persoenlichen Namen.
# Aufruf im Repository-Wurzelverzeichnis:  python3 tests/v3b-test.py

import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True

WORK = tempfile.mkdtemp(prefix="avl-v3b-test.")
os.environ["HOME"] = os.path.join(WORK, "home")
os.environ["XDG_CONFIG_HOME"] = os.path.join(WORK, "home", ".config")
os.environ["XDG_DATA_HOME"] = os.path.join(WORK, "home", ".local", "share")
import umleitung  # noqa: E402 - A9/P70
umleitung.pruefe(WORK, "HOME", "XDG_CONFIG_HOME", "XDG_DATA_HOME")

import polib  # noqa: E402

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


SCRIPTS = ["launcher-watch", "launcher-add", "launcher-move", "desktop-clean-shortcut",
           "desktop-clean-toggle", "desktop-doubleclick", "avincelaunch_rules.py"]

# --- A. Uebersetzung -----------------------------------------------------------
print("A. Uebersetzung (Domaene avincelaunch-helfer):")
fresh = os.path.join(WORK, "frisch.pot")
subprocess.run(["bash", "scripts/po/makepot.sh", fresh], check=True)
pot = polib.pofile("scripts/po/avincelaunch-helfer.pot")
new = polib.pofile(fresh)
check("Vorlage = frisch erzeugt", sorted(e.msgid for e in new), sorted(e.msgid for e in pot))
de = polib.pofile("scripts/po/de.po")
check("de.po deckt die Vorlage ab", sorted(e.msgid for e in pot if not de.find(e.msgid)), [])
check("de.po ohne ueberzaehlige Eintraege", sorted(e.msgid for e in de if not pot.find(e.msgid)), [])
check("de.po: alles uebersetzt, nichts unscharf",
      [de.percent_translated(), [e.msgid for e in de.fuzzy_entries()]], [100, []])
check("Platzhalter gleich (Englisch/Deutsch)",
      [e.msgid for e in de if not e.msgid_plural
       and sorted(re.findall(r"%\(\w+\)[sd]|%[sd]", e.msgid)) != sorted(re.findall(r"%\(\w+\)[sd]|%[sd]", e.msgstr))],
      [])
out = subprocess.run(["msgfmt", "-c", "-o", "/dev/null", "scripts/po/de.po"], capture_output=True, text=True)
check("msgfmt -c", (out.returncode, out.stderr), (0, ""))


def visible_german(path):
    """Zeilen mit deutschen Zeichen ausserhalb von Kommentaren/Docstrings."""
    hits = []
    in_doc = False
    for number, line in enumerate(open(path, encoding="utf-8"), 1):
        stripped = line.strip()
        if stripped.count('"""') == 1:
            in_doc = not in_doc
            continue
        if in_doc or stripped.startswith("#") or stripped.startswith('"""'):
            continue
        code = line.split(" # ")[0]
        if re.search(r"[äöüÄÖÜß„]", code):
            hits.append("%s:%d" % (os.path.basename(path), number))
    return hits


check("keine deutschen Texte mehr im Code der Helfer",
      [h for s in SCRIPTS for h in visible_german(os.path.join("scripts", s))], [])

locale_dir = os.path.join(os.environ["XDG_DATA_HOME"], "locale", "de", "LC_MESSAGES")
os.makedirs(locale_dir)
subprocess.run(["msgfmt", "-o", os.path.join(locale_dir, "avincelaunch-helfer.mo"), "scripts/po/de.po"], check=True)
os.makedirs(os.path.join(os.environ["XDG_CONFIG_HOME"], "avincelaunch"))
GERMAN = dict(os.environ, LANGUAGE="de", LANG="de_DE.UTF-8", LC_ALL="de_DE.UTF-8")
ENGLISH = dict(os.environ, LANGUAGE="C", LANG="C.UTF-8", LC_ALL="C.UTF-8")


def run(argv, env):
    out = subprocess.run(argv, env=env, capture_output=True, text=True)
    return (out.stdout + out.stderr).strip().splitlines()[0] if (out.stdout + out.stderr).strip() else ""


check("Python englisch ohne Uebersetzung", run([sys.executable, "scripts/launcher-add"], ENGLISH),
      'Usage: launcher-add "Program name" [GROUP]')
check("Python deutsch mit Uebersetzung", run([sys.executable, "scripts/launcher-add"], GERMAN),
      'Verwendung: launcher-add "Programmname" [GRUPPE]')
check("Bash englisch", run(["bash", "scripts/desktop-clean-toggle", "--egal"], ENGLISH),
      "Usage: desktop-clean-toggle [--hide | --show | --status]")
check("Bash deutsch (Programm gettext)", run(["bash", "scripts/desktop-clean-toggle", "--egal"], GERMAN),
      "Verwendung: desktop-clean-toggle [--hide | --show | --status]")
probe = ("import sys; sys.path.insert(0, 'scripts'); import avincelaunch_rules as R; "
         "print(R._reason('categories', 'Office'), '|', R._reason('exec', 'gimp'))")
check("Gruende im Dialog deutsch", run([sys.executable, "-c", probe], GERMAN),
      "Kategorie Office | Programmaufruf enthält „gimp“")
check("Gruende im Dialog englisch", run([sys.executable, "-c", probe], ENGLISH),
      "category Office | command contains “gimp”")
check("Statusausgabe bleibt maschinenlesbar (nicht uebersetzt)",
      run(["bash", "scripts/desktop-clean-toggle", "--status"], GERMAN), "shown")

# --- B. Regeln ------------------------------------------------------------------
print("B. Regeln:")
sys.path.insert(0, "scripts")
import avincelaunch_rules as R  # noqa: E402

groups = [("Office", "Office"), ("Spiele", "Spiele"), ("Werkzeuge", "Werkzeuge")]
check("Ziel als Text", R.rule_targets({"then": "BUERO"}), ["BUERO"])
check("Ziel als Liste", R.rule_targets({"then": ["Games", "Spiele"]}), ["Games", "Spiele"])
check("ungueltige Ziele", [R.rule_targets({"then": x}) for x in ([], [1], "", None)], [[], [], [], []])
check("Regel mit leerer Liste ungueltig", R._valid_rule({"if": {"categories": "Game"}, "then": []}), False)
check("Regel mit Liste gueltig", R._valid_rule({"if": {"categories": "Game"}, "then": ["Games", "Spiele"]}), True)
rules = [{"if": {"categories": "Game"}, "then": ["Games", "Spiele"]},
         {"if": {"categories": "Utility"}, "then": ["Tools", "Werkzeuge"]},
         {"if": {"categories": "Graphics"}, "then": ["Graphics_Photos", "Grafik_Fotos"]}]
check("Liste: erster vorhandener Fence (deutsche Startaufstellung)",
      R.suggest({"Categories": "Game;"}, "x.desktop", rules, groups)[0], "Spiele")
check("Liste: Gross/klein egal", R.suggest({"Categories": "Utility"}, "x.desktop", rules,
                                           [("werkzeuge", "W")])[0], "werkzeuge")
check("fehlende Ziele fuer das Protokoll", R.missing_targets(rules, groups), ["Graphics_Photos / Grafik_Fotos"])

spec = importlib.util.spec_from_file_location("appSort", "Desklet/appSort.py")
A = importlib.util.module_from_spec(spec)
spec.loader.exec_module(A)
desklet_po = polib.pofile("Desklet/po/de.po")
titles = dict(A.FENCES)


def folders(key):
    en = A.folder_name(titles[key])
    de_name = A.folder_name(desklet_po.find(titles[key]).msgstr)
    return [en] if en == de_name else [en, de_name]


expected = ([{"if": {"exec": sorted(e)}, "then": folders(k)} for k, e in A.EXEC_RULES]
            + [{"if": {"categories": sorted(c)}, "then": folders(k)} for k, c in A.CATEGORY_RULES])
example = json.load(open("scripts/rules.example.json", encoding="utf-8"))
check("rules.example.json = Tabellen der Startaufstellung (en/de)", example["rules"], expected)
check("Beispiel vollstaendig gueltig", R.example_rules() == example["rules"], True)
starter = {f for k in titles for f in folders(k)}
check("nur Ordner der Startaufstellung als Ziel",
      sorted({t for r in example["rules"] for t in R.rule_targets(r)} - starter), [])
check("Startaufstellung deutsch: Vorschlag ohne eigene Regeln",
      R.suggest({"Categories": "Graphics;2DGraphics;", "Exec": "gimp %U"}, "gimp.desktop", example["rules"],
                [(folders(k)[-1], folders(k)[-1]) for k in titles])[0], "Grafik_Fotos")

subprocess.run(["rm", "-rf", WORK])
print("")
print("Geprueft: %d, Fehler: %d" % (checks, failures))
sys.exit(1 if failures else 0)
