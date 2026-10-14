#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
# Copyright (c) 2026 Angelo Vincenti, aVince Industrietechnik

# Prueft Schritt 9, Paket A8-1 (Pruefung Phase 2) ohne Cinnamon, nur lesend:
#   B3  jede Quelldatei hat genau einen SPDX-Kopf (nach dem Shebang); die aus
#       TheLauncher 1.0.3 (Commit 3845912) uebernommenen tragen
#       "GPL-3.0-only AND MIT" + "Portions copyright (c) MHK924", die eigenen
#       "GPL-3.0-only" ohne;
#   P43 keine Protokollmeldung "TheLauncher:" mehr, Autostart-Texte ohne den
#       alten Namen;
#   P40 metadata.json ohne last-edited;
#   P41 ausfuehrbar (git) nur die Skripte;
#   P61 Ueber-Dialog findet das Desklet unter $XDG_DATA_HOME bzw.
#       $XDG_DATA_DIRS (Wegwerfordner, eigener Prozess).
# Aufruf im Repository-Wurzelverzeichnis:  python3 tests/a8-1-test.py

import json
import os
import re
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


def git(*args):
    return subprocess.run(["git"] + list(args), check=True, capture_output=True, text=True).stdout


SOURCE = re.compile(r"^(Desklet/.*\.(js|py|css)|scripts/[^/]+|tests/[^/]+\.(js|py|sh)|branding/build-branding\.py)$")
NOT_SOURCE = re.compile(r"\.(md|json|desktop|desktop\.in|nemo_action)$|__pycache__")
# Nur Kommentarzeilen zaehlen (dieser Test nennt den Text auch in Zeichenketten).
SPDX_LINE = re.compile(r"^(#|//|/\*)\s*SPDX-License-Identifier:")

tracked = git("ls-files").split()
if not os.path.exists("tests/a8-1-test.py") or "tests/a8-1-test.py" not in tracked:
    # Vor dem ersten Commit zaehlt die Datei trotzdem mit.
    tracked.append("tests/a8-1-test.py")
sources = sorted(f for f in tracked if SOURCE.match(f) and not NOT_SOURCE.search(f))
upstream = set(git("ls-tree", "-r", "--name-only", "3845912").split())

# --- B3 ---------------------------------------------------------------------
print("B3 SPDX-Koepfe:")
check("mindestens 69 Quelldateien", len(sources) >= 69, True)
inherited = [f for f in sources if f in upstream]
check("24 geerbte Dateien", len(inherited), 24)
bad_count, bad_place, bad_expr, bad_portions, bad_shebang = [], [], [], [], []
for path in sources:
    with open(path, encoding="utf-8") as handle:
        lines = handle.read().split("\n")
    spdx = [i for i, line in enumerate(lines) if SPDX_LINE.match(line)]
    if len(spdx) != 1:
        bad_count.append(path)
        continue
    index = spdx[0]
    shebang = lines[0].startswith("#!")
    if index != (1 if shebang else 0):
        bad_place.append(path)
    expected = "GPL-3.0-only AND MIT" if path in inherited else "GPL-3.0-only"
    if not lines[index].rstrip().endswith("SPDX-License-Identifier: " + expected):
        bad_expr.append(path)
    head = "\n".join(lines[index:index + 5])
    has_portions = "Portions copyright (c) MHK924 (TheLauncher), MIT" in head
    if has_portions != (path in inherited) or "Copyright (c) 2026 Angelo Vincenti, aVince Industrietechnik" not in head:
        bad_portions.append(path)
    try:
        before = git("show", "main:" + path).split("\n", 1)[0]
    except subprocess.CalledProcessError:
        before = lines[0]
    if before.startswith("#!") and lines[0] != before:
        bad_shebang.append(path)
check("genau ein SPDX-Kopf je Datei", bad_count, [])
check("Kopf am Anfang bzw. direkt nach dem Shebang", bad_place, [])
check("Ausdruck passt zur Herkunft (3845912)", bad_expr, [])
check("Copyright-Zeilen passen zur Herkunft", bad_portions, [])
check("Shebang unveraendert in Zeile 1", bad_shebang, [])
with open("Desklet/about-dialog.py", encoding="utf-8") as handle:
    about = handle.read()
check("Ueber-Dialog nennt xlet-about-dialog (GPL-2.0-or-later)",
      "xlet-about-dialog (Linux Mint, GPL-2.0-or-later)" in about.split("import", 1)[0], True)

# --- P43 --------------------------------------------------------------------
print("P43 alte Namen:")
hits = []
for path in sources:
    if not path.startswith("Desklet/"):
        continue
    with open(path, encoding="utf-8") as handle:
        for number, line in enumerate(handle, 1):
            if '"TheLauncher:' in line or "'TheLauncher:" in line:
                hits.append("%s:%d" % (path, number))
check("keine Meldung \"TheLauncher:\" im Desklet", hits, [])
check("Ueber-Dialog ohne TheLauncher-Rueckfall/-Klasse",
      [w for w in ('"TheLauncher"', "TheLauncherAboutDialog", "for TheLauncher") if w in about], [])
visible = []
for path in ("scripts/avincelaunch-watcher.desktop.in", "scripts/avincelaunch-doubleclick.desktop.in"):
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            if line.startswith(("Name", "Comment")) and "TheLauncher" in line:
                visible.append(path + ": " + line.strip())
check("Autostart-Texte ohne TheLauncher", visible, [])
with open("scripts/avincelaunch-watcher.desktop.in", encoding="utf-8") as handle:
    check("Waechter heisst aVinceLaunch Programm-Waechter (de) / program watcher (en)",
          [l in handle.read().split("\n") for l in ("Name[de]=aVinceLaunch Programm-Wächter",)], [True])

# --- P40 --------------------------------------------------------------------
print("P40 metadata.json:")
with open("Desklet/metadata.json", encoding="utf-8") as handle:
    metadata = json.load(handle)
check("kein last-edited", "last-edited" in metadata, False)
check("Version 0.1.0", metadata.get("version"), "0.1.0")

# --- P41 --------------------------------------------------------------------
print("P41 Dateirechte (git):")
executable = sorted(line.split()[3] for line in git("ls-files", "-s").splitlines()
                    if line.startswith("100755"))
check("ausfuehrbar nur die Skripte", executable, sorted([
    "branding/build-branding.py",
    "scripts/avincelaunch-helfer",
    "scripts/desktop-clean-shortcut",
    "scripts/desktop-clean-toggle",
    "scripts/desktop-doubleclick",
    "scripts/launcher-add",
    "scripts/launcher-move",
    "scripts/launcher-watch",
    "tests/alle-tests.sh",
    "tests/syntax-check.sh",
]))
check("icon.png nicht ausfuehrbar (Platte)", os.access("Desklet/icon.png", os.X_OK), False)

# --- P61 --------------------------------------------------------------------
print("P61 Ueber-Dialog sucht nach XDG:")
PROBE = r"""
import importlib.util, sys
spec = importlib.util.spec_from_file_location("about", sys.argv[1])
about = importlib.util.module_from_spec(spec)
spec.loader.exec_module(about)
print(about.find_desklet_path("desklets", "avincelaunch-desklet@avince") or "-")
"""
uuid = "avincelaunch-desklet@avince"
with tempfile.TemporaryDirectory(prefix="avl-a8-1-") as work:
    home_data = os.path.join(work, "daten")
    system_data = os.path.join(work, "system")
    # HOME mit umbiegen: seit P3-1 (N4) sucht der Dialog auch ~/.local/share.
    env = dict(os.environ, XDG_DATA_HOME=home_data, XDG_DATA_DIRS=system_data,
               HOME=os.path.join(work, "home"),
               DBUS_SESSION_BUS_ADDRESS="unix:path=/nonexistent/avl-test", LANGUAGE="C")

    def probe():
        result = subprocess.run([sys.executable, "-c", PROBE, "Desklet/about-dialog.py"],
                                env=env, capture_output=True, text=True)
        return result.stdout.strip().split("\n")[-1]

    check("nichts vorhanden -> nicht gefunden", probe(), "-")
    os.makedirs(os.path.join(system_data, "cinnamon", "desklets", uuid))
    check("Systemordner aus XDG_DATA_DIRS", probe(), os.path.join(system_data, "cinnamon", "desklets", uuid))
    os.makedirs(os.path.join(home_data, "cinnamon", "desklets", uuid))
    check("XDG_DATA_HOME geht vor", probe(), os.path.join(home_data, "cinnamon", "desklets", uuid))

# --- Schritt 4, V2: Ko-fi im Ueber-Dialog ------------------------------------
print("V2 Ko-fi-Knopf im Ueber-Dialog:")
KOFI = "https://ko-fi.com/avince"
about_lines = about.split("\n")
check("KOFI_URL = Ko-fi-Seite", 'KOFI_URL = "%s"' % KOFI in about_lines, True)
for path in ("README.md", "README.de.md"):
    with open(path, encoding="utf-8") as handle:
        check("%s nennt dieselbe Seite" % path, "(%s)" % KOFI in handle.read(), True)
with open(".github/FUNDING.yml", encoding="utf-8") as handle:
    check("FUNDING.yml nennt dasselbe Konto", "ko_fi: avince" in handle.read(), True)
check("schlichter Verweis (Gtk.LinkButton), kein eigenes Fenster/keine Nachfrage",
      ["Gtk.LinkButton.new_with_label(" in about,
       [w for w in ("MessageDialog", "Gtk.Window(", "Gtk.Dialog(", "run()") if w in about]],
      [True, []])
check("Beschriftung uebersetzbar (translate + _ fuer makepot)",
      'translate(metadata.get("uuid", UUID), _("Support aVinceLaunch on Ko-fi"))' in about, True)
import polib
de = polib.pofile("Desklet/po/de.po").find("Support aVinceLaunch on Ko-fi")
check("deutsche Beschriftung", de.msgstr if de else None, "aVinceLaunch auf Ko-fi unterstützen")

print("")
print("Geprueft: %d, Fehler: %d" % (checks, failures))
sys.exit(1 if failures else 0)
