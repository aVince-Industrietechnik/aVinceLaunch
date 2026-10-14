#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
# Copyright (c) 2026 Angelo Vincenti, aVince Industrietechnik

# Prueft Schritt 9, Paket A9 (Pruefung Phase 2, P70) - die Testwerkzeuge selbst:
#   - tests/syntax-check.sh schreibt nichts (Lauf in einer Wegwerfkopie des
#     Repositorys: keine neue Datei, kein __pycache__, nichts unter TMPDIR)
#     und prueft auch tests/*.py und tests/*.js;
#   - jeder Test mit umgebogenen Benutzerordnern bricht mit Code 2 und
#     "ABBRUCH" ab, wenn die Umleitung nicht greift. Nachgestellt wird das,
#     indem GLib die Ordner schon VOR dem Test festhaelt - auf einen
#     Wegwerf-"Aussenordner", nie die echten; der muss danach leer sein;
#   - tests/alle-tests.sh --liste nennt genau alle Tests;
#   - tests/PRUEFLISTE.md nennt jeden Test.
# Alles laeuft unter einem eigenen TMPDIR, der am Ende geloescht wird.
# Aufruf im Repository-Wurzelverzeichnis:  python3 tests/a9-test.py

import glob
import os
import re
import shutil
import subprocess
import sys
import tempfile

checks = 0
failures = 0


def check(name, actual, expected):
    global checks, failures
    checks += 1
    if actual == expected:
        print("  ok      " + name)
    else:
        failures += 1
        print("  FEHLER  %s\n          erwartet %r\n          erhalten %r" % (name, expected, actual))


def snapshot(root):
    found = {}
    for base, dirs, files in os.walk(root):
        for name in dirs + files:
            path = os.path.join(base, name)
            st = os.lstat(path)
            found[os.path.relpath(path, root)] = (st.st_size, st.st_mtime_ns)
    return found


WORK = tempfile.mkdtemp(prefix="avl-a9-test.")
TMP = os.path.join(WORK, "tmp")
os.makedirs(TMP)
BASE_ENV = dict(os.environ, TMPDIR=TMP, LANGUAGE="C", PYTHONDONTWRITEBYTECODE="1",
                DBUS_SESSION_BUS_ADDRESS="unix:path=/nonexistent/avl-test")

try:
    # --- syntax-check.sh schreibt nichts -------------------------------------
    print("syntax-check.sh:")
    copy = os.path.join(WORK, "repo")
    shutil.copytree(".", copy, ignore=shutil.ignore_patterns(".git", "__pycache__", "Claude outputs"))
    before, tmp_before = snapshot(copy), snapshot(TMP)
    run = subprocess.run(["bash", "tests/syntax-check.sh"], cwd=copy, env=dict(BASE_ENV, PYTHONDONTWRITEBYTECODE=""),
                         capture_output=True, text=True)
    check("laeuft ohne Fehler", run.returncode, 0)
    after = snapshot(copy)
    check("keine neue oder geaenderte Datei in der Kopie",
          sorted(k for k in after if k not in before or after[k] != before[k]), [])
    check("kein __pycache__", [k for k in after if "__pycache__" in k], [])
    check("nichts unter TMPDIR", sorted(set(snapshot(TMP)) - set(tmp_before)), [])
    check("prueft auch tests/*.py", "ok      tests/a9-test.py" in run.stdout, True)
    check("prueft auch tests/*.js", "ok      tests/n1-position-test.js" in run.stdout, True)
    check("prueft scripts/rules.example.json", "ok      scripts/rules.example.json" in run.stdout, True)

    # --- Abbruch bei nicht greifender Umleitung ----------------------------------
    print("Abbruch bei falscher Umleitung (Code 2):")
    outer = os.path.join(WORK, "aussen")
    for sub in ("config", "data", "home"):
        os.makedirs(os.path.join(outer, sub))
    outer_env = dict(BASE_ENV, XDG_CONFIG_HOME=os.path.join(outer, "config"),
                     XDG_DATA_HOME=os.path.join(outer, "data"), HOME=os.path.join(outer, "home"))

    PY_WRAPPER = (
        "import sys, runpy\n"
        "from gi.repository import GLib\n"
        "GLib.get_user_config_dir(); GLib.get_user_data_dir(); GLib.get_home_dir()\n"
        "sys.path.insert(0, 'tests')\n"
        "sys.argv = [sys.argv[1]]\n"
        "runpy.run_path(sys.argv[0], run_name='__main__')\n"
    )
    JS_WRAPPER = (
        "imports.gi.GLib.get_user_config_dir(); imports.gi.GLib.get_user_data_dir();\n"
        "(0, eval)(new TextDecoder().decode(imports.gi.GLib.file_get_contents(ARGV[0])[1]));\n"
    )
    # Nur echte Aufrufzeilen am Zeilenanfang - dieser Test nennt die Namen
    # selbst und darf sich nie selbst aufrufen (endlose Kette).
    call = re.compile(r"(?m)^(umleitung\.pruefe\(|requireRedirect\(\[)")
    guarded = sorted(f for f in glob.glob("tests/*-test.py") + glob.glob("tests/*-test.js")
                     if f != "tests/a9-test.py" and call.search(open(f, encoding="utf-8").read()))
    check("mindestens 10 Tests mit Umleitungs-Sicherung", len(guarded) >= 10, True)
    for test in guarded:
        if test.endswith(".py"):
            cmd = [sys.executable, "-c", PY_WRAPPER, test]
        else:
            cmd = ["cjs", "-c", JS_WRAPPER, test]
        run = subprocess.run(cmd, env=outer_env, capture_output=True, text=True, timeout=120)
        check("%s: Code 2 + ABBRUCH" % os.path.basename(test),
              (run.returncode, "ABBRUCH" in run.stderr), (2, True))
    check("Aussenordner unberuehrt (nichts geschrieben)", snapshot(outer),
          {"config": snapshot(outer).get("config"), "data": snapshot(outer).get("data"),
           "home": snapshot(outer).get("home")})

    # --- Uebersicht --------------------------------------------------------------
    print("alle-tests.sh und PRUEFLISTE.md:")
    listed = subprocess.run(["bash", "tests/alle-tests.sh", "--liste"], capture_output=True,
                            text=True).stdout.split()
    present = sorted(glob.glob("tests/*-test.js") + glob.glob("tests/*-test.py"))
    check("--liste = alle Testdateien", listed, present)
    check("a9-test.py selbst dabei", "tests/a9-test.py" in listed, True)
    with open("tests/PRUEFLISTE.md", encoding="utf-8") as handle:
        checklist = handle.read()
    check("PRUEFLISTE nennt jeden Test",
          [t for t in present + ["tests/syntax-check.sh"] if "`%s`" % os.path.basename(t) not in checklist], [])
    check("PRUEFLISTE 1.2 nennt alle-tests.sh", "`bash tests/alle-tests.sh`" in checklist, True)
    check("PRUEFLISTE ohne alte englische Menuetexte",
          [w for w in ("Restore previous size", "Restore original size", "Original arrangement",
                       "free (Ctrl)", "TheLauncher-Daten") if w in checklist], [])
finally:
    shutil.rmtree(WORK, ignore_errors=True)

print("")
print("Geprueft: %d, Fehler: %d" % (checks, failures))
sys.exit(1 if failures else 0)
