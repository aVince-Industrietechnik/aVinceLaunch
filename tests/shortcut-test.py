#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
# Copyright (c) 2026 Angelo Vincenti, aVince Industrietechnik

# Prueft scripts/desktop-clean-shortcut (AP15b), ohne etwas zu aendern:
# Kuerzel-Vergleich und Erkennung belegter Kuerzel an Cinnamons echten
# Tastenschemata (nur lesend).
# Aufruf im Repository-Wurzelverzeichnis:  python3 tests/shortcut-test.py

import importlib.machinery
import importlib.util
import sys

sys.dont_write_bytecode = True
# Das Skript laedt avincelaunch_rules aus seinem Ordner (V3b, Uebersetzung).
sys.path.insert(0, "scripts")

loader = importlib.machinery.SourceFileLoader("shortcut", "scripts/desktop-clean-shortcut")
spec = importlib.util.spec_from_loader("shortcut", loader)
S = importlib.util.module_from_spec(spec)
loader.exec_module(S)

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


print("Kuerzel vergleichen:")
target = S.normalize("<Super><Shift>d")
check("Reihenfolge egal", S.normalize("<Shift><Super>d"), target)
check("Gross/klein egal", S.normalize("<SUPER><shift>D"), target)
check("Mod4 = Super", S.normalize("<Mod4><Shift>d"), target)
check("Primary = Control", S.normalize("<Primary>c"), S.normalize("<Control>c"))
check("ohne Umschalt verschieden", S.normalize("<Super>d") == target, False)
check("leer -> None", S.normalize(""), None)
check("nur Modifikator -> None", S.normalize("<Super>"), None)

check("Anzeige: Kuerzel als Text, nicht als Liste",
      S.readable({"entry": "custom0", "binding": ["<Super><Shift>d"]})["binding"], "<Super><Shift>d")
print("\nBelegte Kuerzel (Cinnamon, nur lesend):")
down = S.builtin_owners(S.normalize("<Super><Shift>Down"))
check("<Super><Shift>Down gehoert move-to-monitor-down",
      any("move-to-monitor-down" in o for o in down), True)
check("<Super><Shift>d ist nicht fest belegt", S.builtin_owners(target), [])

print("\nListe anstossen wie Cinnamon:")
check("Platzhalter hinein", S.touch_list(["custom0"]), ["custom0", "__dummy__"])
check("Platzhalter heraus", S.touch_list(["custom0", "__dummy__"]), ["custom0"])
check("naechster freier Eintrag", S.next_free_entry(["custom0", "custom2", "__dummy__"]), "custom1")
check("leer -> custom0", S.next_free_entry([]), "custom0")

print(f"\nGeprueft: {checks}, Fehler: {failures}")
sys.exit(1 if failures else 0)
