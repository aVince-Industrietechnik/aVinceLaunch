#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
# Copyright (c) 2026 Angelo Vincenti, aVince Industrietechnik

# Schritt 4, V5f / N30 - Programmnamen der Helfer wie im Startmenue.
# launcher-add verglich nur die Zeile "Name=" (englisch): "Rechner" wurde nicht
# gefunden, obwohl Startmenue und Fences "Taschenrechner" zeigen (W6, 4.3).
# Geprueft wird avincelaunch_rules.desktop_names: uebersetzter Name nach den
# Sprachvariablen wie gettext (erste gesetzte, bis "C"), Land vor Sprache,
# Uebersetzung ueber X-Ubuntu-Gettext-Domain (so liefert Mint die meisten),
# nur der Abschnitt [Desktop Entry], unlesbare Datei; launcher-add und
# launcher-move nutzen die Funktion. launcher-add selbst: tests/launcher-add-test.py.
# Aufruf im Repository-Wurzelverzeichnis:  python3 tests/v5f-test.py

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True

WORK = Path(tempfile.mkdtemp(prefix="avl-v5f-test."))
os.environ["HOME"] = str(WORK)
os.environ["XDG_CONFIG_HOME"] = str(WORK / ".config")
os.environ["XDG_DATA_HOME"] = str(WORK / ".local/share")
import umleitung  # noqa: E402 - A9/P70: Abbruch, wenn die Umleitung nicht greift
umleitung.pruefe(str(WORK), "HOME", "XDG_CONFIG_HOME", "XDG_DATA_HOME")

sys.path.insert(0, str(Path.cwd() / "scripts"))
import avincelaunch_rules as rules  # noqa: E402

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


def sprache(**werte):
    for var in ("LANGUAGE", "LC_ALL", "LC_MESSAGES", "LANG"):
        os.environ.pop(var, None)
    os.environ.update(werte)


calc = WORK / "calc.desktop"
calc.write_text("[Desktop Entry]\nType=Application\nName=Calculator\nName[de]=Taschenrechner\n"
                "Name[de_AT]=Rechner AT\nName[fr]=Calculatrice\nExec=true\n"
                "[Desktop Action new]\nName=New Window\nName[de]=Neues Fenster\n")
plain = WORK / "plain.desktop"
plain.write_text("[Desktop Entry]\nType=Application\nName=Rechner\nExec=true\n")
action_first = WORK / "action.desktop"
action_first.write_text("[Desktop Action x]\nName=Falsch\n[Desktop Entry]\nName=Richtig\nName[de]=Richtig DE\n")

print("Uebersetzter Name nach Sprache (wie gettext):")
sprache(LANG="de_DE.UTF-8")
check("LANG=de_DE.UTF-8 -> Name[de]", rules.desktop_names(calc), ("Taschenrechner", ["Taschenrechner", "Calculator"]))
sprache(LANG="de_AT.UTF-8")
check("Land vor Sprache (de_AT)", rules.desktop_names(calc)[0], "Rechner AT")
sprache(LANGUAGE="fr:de", LANG="de_DE.UTF-8")
check("LANGUAGE hat Vorrang, Reihenfolge fr vor de", rules.desktop_names(calc)[0], "Calculatrice")
sprache(LANGUAGE="C", LANG="de_DE.UTF-8")
check("LANGUAGE=C -> englischer Name (wie die Meldungen)", rules.desktop_names(calc), ("Calculator", ["Calculator"]))
sprache(LC_ALL="de_DE.UTF-8@euro")
check("LC_ALL mit @-Zusatz", rules.desktop_names(calc)[0], "Taschenrechner")
sprache()
check("keine Sprachvariable -> Name=", rules.desktop_names(calc)[0], "Calculator")

print("\nDatei-Aufbau:")
sprache(LANG="de_DE.UTF-8")
check("nur Name= vorhanden", rules.desktop_names(plain), ("Rechner", ["Rechner"]))
check("nur [Desktop Entry], nicht [Desktop Action]", rules.desktop_names(action_first),
      ("Richtig DE", ["Richtig DE", "Richtig"]))
check("Aktion 'Neues Fenster' nicht als Name", "Neues Fenster" in rules.desktop_names(calc)[1], False)
check("unlesbar -> leer", rules.desktop_names(WORK / "fehlt.desktop"), ("", []))

print("\nUebersetzung ueber X-Ubuntu-Gettext-Domain (Mint/Ubuntu):")
mo_dir = WORK / "locale/de/LC_MESSAGES"
mo_dir.mkdir(parents=True)
(WORK / "avltest.po").write_text('msgid ""\nmsgstr "Content-Type: text/plain; charset=UTF-8\\n"\n\n'
                                 'msgid "AVL Calculator"\nmsgstr "AVL Taschenrechner"\n', encoding="utf-8")
built = subprocess.run(["msgfmt", "-o", str(mo_dir / "avltest.mo"), str(WORK / "avltest.po")],
                       capture_output=True, text=True)
check("Test-.mo gebaut", built.returncode, 0)
rules.SYSTEM_LOCALE_DIR = str(WORK / "locale")
domain = WORK / "domain.desktop"
domain.write_text("[Desktop Entry]\nType=Application\nName=AVL Calculator\nExec=true\n"
                  "X-Ubuntu-Gettext-Domain=avltest\n")
sprache(LANG="de_DE.UTF-8")
check("deutsch: Name ueber die Domaene uebersetzt", rules.desktop_names(domain),
      ("AVL Taschenrechner", ["AVL Taschenrechner", "AVL Calculator"]))
sprache(LANGUAGE="C", LANG="de_DE.UTF-8")
check("LANGUAGE=C: englisch", rules.desktop_names(domain), ("AVL Calculator", ["AVL Calculator"]))
sprache(LANG="de_DE.UTF-8")
domain.write_text(domain.read_text() + "Name[de]=Eigener Name\n")
check("Name[de] in der Datei geht vor", rules.desktop_names(domain)[0], "Eigener Name")
domain.write_text("[Desktop Entry]\nName=AVL Unbekannt\nX-Ubuntu-Gettext-Domain=gibt-es-nicht\n")
check("Domaene ohne .mo: englisch", rules.desktop_names(domain), ("AVL Unbekannt", ["AVL Unbekannt"]))
rules.SYSTEM_LOCALE_DIR = None

print("\nHelfer nutzen die Funktion:")
add = Path("scripts/launcher-add").read_text(encoding="utf-8")
move = Path("scripts/launcher-move").read_text(encoding="utf-8")
check("launcher-add vergleicht alle Namen", "rules.desktop_names(path)" in add and "for n in names" in add, True)
check("launcher-add: kein eigener Name=-Leser mehr", 'startswith("Name=")' in add, False)
check("launcher-move zeigt den uebersetzten Namen", "rules.desktop_names(path)[0]" in move, True)

shutil.rmtree(WORK)
print(f"\nGeprueft: {checks}, Fehler: {failures}")
sys.exit(1 if failures else 0)
