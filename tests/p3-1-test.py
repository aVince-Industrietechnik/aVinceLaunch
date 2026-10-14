#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
# Copyright (c) 2026 Angelo Vincenti, aVince Industrietechnik

# Prueft Paket P3-1 (Pruefung Phase 3: N2, N4, N5) ohne Cinnamon in einem
# Wegwerfordner:
#   N2  eine Regel fuer "%" beim Anlegen und Bearbeiten von Startern
#       (linkImport.command_to_exec / exec_to_command): Platzhalter bleiben,
#       Prozentzeichen als "%%", unveraenderter Befehl wird nie neu geschrieben;
#   N4  Ueber-Dialog: Uebersetzung fest unter ~/.local/share/locale, Desklet
#       unter $XDG_DATA_HOME und ~/.local/share, dann Systemordner;
#   N5  Beschreibung nennt GPL-3.0-only (en/de).
# N3 prueft tests/p3-1-test.js.
# Aufruf im Repository-Wurzelverzeichnis:  python3 tests/p3-1-test.py

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True

WORK = tempfile.mkdtemp(prefix="avl-p3-1-test.")
os.environ["LANGUAGE"] = "C"
os.environ["XDG_CONFIG_HOME"] = os.path.join(WORK, "config")
import umleitung  # noqa: E402 - A9/P70: Abbruch, wenn die Umleitung nicht greift
umleitung.pruefe(WORK, "XDG_CONFIG_HOME")
os.makedirs(os.path.join(WORK, "config", "cinnamon", "spices", "avincelaunch-desklet@avince"))

spec = importlib.util.spec_from_file_location("linkImport", "Desklet/linkImport.py")
L = importlib.util.module_from_spec(spec)
spec.loader.exec_module(L)

UUID = "avincelaunch-desklet@avince"
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


def read(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()


try:
    # --- N2 Regel ------------------------------------------------------------
    print("N2 Regel fuer %:")
    check("date +%Y -> %%Y", L.command_to_exec("date +%Y"), "date +%%Y")
    check("firefox %u bleibt", L.command_to_exec("firefox %u"), "firefox %u")
    check("Platzhalter %F %U %f %i %c %k bleiben",
          L.command_to_exec("app %F %U %f %i %c %k"), "app %F %U %f %i %c %k")
    check("echo 100% -> 100%%", L.command_to_exec("echo 100%"), "echo 100%%")
    check("%d/%m (veraltete Codes) sind Prozentzeichen", L.command_to_exec("date +%d.%m"), "date +%%d.%%m")
    check("anzeigen: %%Y -> %Y", L.exec_to_command("date +%%Y"), "date +%Y")
    check("anzeigen: %u bleibt", L.exec_to_command("firefox %u"), "firefox %u")
    EXECS = ["firefox %u", "code --new-window %F", "gimp-2.10 %U", "sh -c 'date +%%Y'",
             "libreoffice --writer %U", "nemo %U", "chromium --app=https://x.de %U",
             "bash -c \"echo 100%%\"", "env A=1 app %f", "app --icon %i --name %c --file %k",
             "date +%%d.%%m.%%Y"]
    check("Rundlauf typischer Exec-Werte", [e for e in EXECS if L.command_to_exec(L.exec_to_command(e)) != e], [])

    # --- N2 Dateien -----------------------------------------------------------
    print("N2 Anlegen und Bearbeiten:")
    group = os.path.join(WORK, "gruppe")
    os.makedirs(group)
    made = L.create_desktop_link(group, "Datum", "date +%Y", "", False)
    check("anlegen ok", made.get("ok"), True)
    check("Datei: Exec=date +%%Y", "Exec=date +%%Y\n" in read(made["path"]), True)
    check("Bearbeiten zeigt dieselbe Eingabe", L.read_desktop_link(made["path"])["command"], "date +%Y")
    fx = L.create_desktop_link(group, "Firefox", "firefox %u", "", False)
    check("anlegen mit Platzhalter: Exec=firefox %u", "Exec=firefox %u\n" in read(fx["path"]), True)

    literal = os.path.join(group, "literal.desktop")
    with open(literal, "w", encoding="utf-8") as handle:
        handle.write("[Desktop Entry]\nType=Application\nName=Woche\nExec=date +%%u\nIcon=x\nTerminal=false\n")
    before = read(literal)
    shown = L.read_desktop_link(literal)
    check("%%u wird als %u gezeigt", shown["command"], "date +%u")
    r = L.update_desktop_link(literal, "Woche neu", shown["command"], "x", False)
    check("nur Name geaendert: ok", r.get("ok"), True)
    check("Exec bleibt byte-gleich (%%u nicht zu %u)", "Exec=date +%%u\n" in read(literal), True)
    check("nur die Name-Zeile anders", [a for a, b in zip(before.splitlines(), read(literal).splitlines()) if a != b],
          ["Name=Woche"])
    r = L.update_desktop_link(literal, "Woche neu", "date +%Y", "x", False)
    check("Befehl geaendert: Exec=date +%%Y", "Exec=date +%%Y\n" in read(literal), True)

    # --- N4 Ueber-Dialog --------------------------------------------------------
    print("N4 Ueber-Dialog:")
    home = os.path.join(WORK, "home")
    data = os.path.join(WORK, "data")
    sysdir = os.path.join(WORK, "sys")
    for d in (home, data, sysdir):
        os.makedirs(d)
    env = dict(os.environ, HOME=home, XDG_DATA_HOME=data, XDG_DATA_DIRS=sysdir, LANGUAGE="de",
               DBUS_SESSION_BUS_ADDRESS="unix:path=/nonexistent/avl-test")
    probe = (
        "import importlib.util, sys\n"
        "spec = importlib.util.spec_from_file_location('about', sys.argv[1])\n"
        "a = importlib.util.module_from_spec(spec); spec.loader.exec_module(a)\n"
        "print(a.find_desklet_path('desklets', a.UUID) or '-')\n"
        "print(a.translate(a.UUID, 'P3-1 Probe'))\n"
    )

    def run():
        out = subprocess.run([sys.executable, "-c", probe, "Desklet/about-dialog.py"], env=env,
                             capture_output=True, text=True).stdout.strip().split("\n")
        return out[-2:] if len(out) >= 2 else out

    check("nichts vorhanden", run()[0], "-")
    home_desklet = os.path.join(home, ".local", "share", "cinnamon", "desklets", UUID)
    os.makedirs(home_desklet)
    check("nur ~/.local/share (Spices) -> gefunden", run()[0], home_desklet)
    xdg_desklet = os.path.join(data, "cinnamon", "desklets", UUID)
    os.makedirs(xdg_desklet)
    check("$XDG_DATA_HOME geht vor", run()[0], xdg_desklet)

    def mo(base, text):
        target = os.path.join(base, "de", "LC_MESSAGES")
        os.makedirs(target, exist_ok=True)
        po = os.path.join(WORK, "probe.po")
        with open(po, "w", encoding="utf-8") as handle:
            handle.write('msgid ""\nmsgstr "Content-Type: text/plain; charset=UTF-8\\n"\n\n'
                         'msgid "P3-1 Probe"\nmsgstr "%s"\n' % text)
        subprocess.run(["msgfmt", "-o", os.path.join(target, UUID + ".mo"), po], check=True)

    mo(os.path.join(data, "locale"), "falscher Ort")
    check("Uebersetzung nicht aus $XDG_DATA_HOME/locale", run()[1], "P3-1 Probe")
    mo(os.path.join(home, ".local", "share", "locale"), "richtiger Ort")
    check("Uebersetzung aus ~/.local/share/locale", run()[1], "richtiger Ort")

    # --- N5 Beschreibung -----------------------------------------------------------
    print("N5 Lizenz in der Beschreibung:")
    import polib
    comments = json.loads(read("Desklet/metadata.json"))["comments"]
    last = comments.split("\n\n")[-1]
    check("en: GPL-3.0-only im letzten Absatz", "licensed under GPL-3.0-only" in last, True)
    check("en: MIT nur fuer uebernommene Teile", "inherited parts remain under the MIT licence" in last, True)
    de = {e.msgid: e.msgstr for e in polib.pofile("Desklet/po/de.po") if not e.obsolete}.get(comments, "")
    check("de: GPL-3.0-only im letzten Absatz", "steht unter GPL-3.0-only" in de.split("\n\n")[-1], True)
finally:
    shutil.rmtree(WORK, ignore_errors=True)

print("")
print("Geprueft: %d, Fehler: %d" % (checks, failures))
sys.exit(1 if failures else 0)
