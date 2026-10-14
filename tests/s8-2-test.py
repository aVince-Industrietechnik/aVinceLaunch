#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
# Copyright (c) 2026 Angelo Vincenti, aVince Industrietechnik

# Prueft Schritt 8, Paket S8-2 (Pruefung Phase 2: B7, B15) ohne Live-Dateien
# (eigenes HOME in einem Wegwerfordner):
#   B7  Titel ohne eingebaute Namenstabelle (Fence und Hilfsskripte gleich),
#       keine eingebauten Regeln, Beispielregeln = bisherige Standardregeln,
#       --write-rules nimmt das Beispiel und ueberschreibt nie;
#   B15 kein "Fences alternative" mehr in Beschreibung und READMEs.
# Aufruf im Repository-Wurzelverzeichnis:  python3 tests/s8-2-test.py

import ast
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True

WORK = tempfile.mkdtemp(prefix="avl-s8-2-test.")
os.environ["HOME"] = WORK
os.environ["XDG_CONFIG_HOME"] = os.path.join(WORK, ".config")
os.environ["XDG_DATA_HOME"] = os.path.join(WORK, ".local", "share")
import umleitung  # noqa: E402 - A9/P70: Abbruch, wenn die Umleitung nicht greift
# Teil 2 (T12): vorher nur geprueft, nicht abgebrochen - der Test schreibt
# rules.json und danach "{kaputt" hinein.
umleitung.pruefe(WORK, "HOME", "XDG_CONFIG_HOME", "XDG_DATA_HOME")

spec = importlib.util.spec_from_file_location("avincelaunch_rules", "scripts/avincelaunch_rules.py")
R = importlib.util.module_from_spec(spec)
spec.loader.exec_module(R)

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


print("B7 Titel:")
check("Test-HOME aktiv", str(R.RULES_FILE).startswith(WORK), True)
check("Ordnername mit Leerzeichen", R.default_title("INTERNET_KOMMUNIKATION"), "INTERNET KOMMUNIKATION")
check("keine Tabelle mehr (BUERO bleibt BUERO)", R.default_title("BUERO"), "BUERO")
check("ohne Ordner: aVinceLaunch", R.default_title(""), "aVinceLaunch")
check("kein LEGACY_TITLES mehr", hasattr(R, "LEGACY_TITLES"), False)
desklet = open("Desklet/desklet.js", encoding="utf-8").read()
fn = desklet[desklet.index("    _getHoverWindowTitle: function()"):desklet.index("    _showHoverWindowTitle: function()")]
check("Fence: keine Namenstabelle", "const names" in fn or "VM & WAWI" in fn, False)
check("Fence: gleiche Regel (Ordnername, _ -> Leerzeichen)", 'folder.replace(/_/g, " ")' in fn, True)
check("Fence: Rueckfall aVinceLaunch statt THELAUNCHER",
      ('"aVinceLaunch"' in fn, "THELAUNCHER" in fn), (True, False))

print("B7 Regeln:")
mode, rules, notes = R.load_rules()
check("ohne rules.json: keine Regeln", (mode, rules), ("suggest", []))
# Teil 2 (T12): Vergleich mit dem Stand vor S8-2 (acb41c4 = erste Pruefung);
# "main~0" war nach dem Merge schon der neue Stand - der Vergleich entfiel immer.
old_source = subprocess.run(["git", "show", "acb41c4:scripts/avincelaunch_rules.py"],
                            capture_output=True, text=True).stdout
check("Vergleichsstand acb41c4 lesbar", bool(old_source), True)
old_rules = None
for node in ast.parse(old_source).body:
    if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == "DEFAULT_RULES":
        old_rules = ast.literal_eval(node.value)
example = json.load(open("scripts/rules.example.json", encoding="utf-8"))
check("acb41c4 hatte eingebaute Regeln", bool(old_rules), True)
# Schritt 4, V3b (K2-3): Das Beispiel folgt jetzt der Startaufstellung (en/de,
# tests/v3b-test.py) - keines der alten persoenlichen Ziele mehr.
# Persoenlich waren die Sammelordner VM_JTL und INTERNET_KOMMUNIKATION;
# BUERO/GRAFIK/TOOLS/SYSTEM/MULTIMEDIA sind allgemeine Namen (Buero ist heute
# der deutsche Ordner "Buero" der Startaufstellung).
check("Beispiel ohne die alten persoenlichen Ziele (K2-3)",
      sorted({t.casefold() for r in example["rules"] for t in R.rule_targets(r)}
             & {"vm_jtl", "internet_kommunikation"}), [])
check("Beispiel nicht mehr = alte eingebaute Regeln", example["rules"] != old_rules, True)
check("alle Beispielregeln gueltig", all(R._valid_rule(r) for r in example["rules"]), True)
check("example_rules liest das Beispiel", R.example_rules(), example["rules"])
check("--write-rules legt an", R.write_default_rules(), True)
written = json.load(open(R.RULES_FILE, encoding="utf-8"))
check("... mit den Beispielregeln", (written["mode"], written["rules"]), ("suggest", example["rules"]))
check("... ueberschreibt nie", R.write_default_rules(), False)
mode, rules, notes = R.load_rules()
check("mit rules.json gelten deren Regeln", rules, example["rules"])
with open(R.RULES_FILE, "w") as handle:
    handle.write("{kaputt")
mode, rules, notes = R.load_rules()
check("kaputte rules.json: keine Regeln + Hinweis",
      (rules, any("no rules" in n for n in notes)), ([], True))

code = re.sub(r"(?m)#.*$", "", open("scripts/avincelaunch_rules.py", encoding="utf-8").read())
check("Hilfsmodul ohne persoenliche Ordnernamen",
      [n for n in ("BUERO", "VM_JTL", "INTERNET_KOMMUNIKATION", "GRAFIK", "NETZWERK") if n in code], [])

print("B15 Beschreibung:")
for path in ("Desklet/metadata.json", "README.md", "README.de.md"):
    text = open(path, encoding="utf-8").read()
    check(path + " ohne \"Fences alternative\"",
          bool(re.search(r"Fences[ -]alternative|Fences-Alternative", text, re.IGNORECASE)), False)
meta = json.load(open("Desklet/metadata.json", encoding="utf-8"))
check("neue Beschreibung", "with fences and launcher groups" in meta["description"], True)

shutil.rmtree(WORK)
print("")
print("Geprueft: %d, Fehler: %d" % (checks, failures))
sys.exit(1 if failures else 0)
