#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
# Copyright (c) 2026 Angelo Vincenti, aVince Industrietechnik

# Prueft Desklet/linkImport.py (Pruefung Phase 2, A2: P1, P7, P53, P54) in
# einem Wegwerfordner. Nichts im Live-System wird geschrieben; Papierkorb
# wird nicht benutzt.
# Aufruf im Repository-Wurzelverzeichnis:
#   python3 tests/desktop-link-test.py          (eingebaute Beispieldatei)
#   python3 tests/desktop-link-test.py --live   (zusaetzlich KOPIEN der echten
#                                                Starter mit Aktionsabschnitten)

import glob
import errno
import importlib.util
import json
import os
import shutil
import stat
import sys
import tempfile

sys.dont_write_bytecode = True

WORK = tempfile.mkdtemp(prefix="avl-desktop-link-test.")
# Vor dem ersten GLib-Aufruf: deutsche Sprache, eigene Konfiguration
# (portalGuard liest dort die Instanzdateien).
os.environ["LANGUAGE"] = "de"
os.environ["LC_ALL"] = "C.UTF-8"
os.environ["XDG_CONFIG_HOME"] = os.path.join(WORK, "config")
# Teil 2 (BT2): Gio.DesktopAppInfo erkennt einen Starter nur an, wenn sein
# Programm im PATH liegt - sonst zeigt der Fence die unuebersetzte Name=-Zeile.
# Die Beispielprogramme gibt es deshalb als leere Schein-Programme.
FAKE_BIN = os.path.join(WORK, "bin")
os.makedirs(FAKE_BIN)
for _prog in ("drawtool", "plain", "linked"):
    with open(os.path.join(FAKE_BIN, _prog), "w") as _handle:
        _handle.write("#!/bin/sh\nexit 0\n")
    os.chmod(os.path.join(FAKE_BIN, _prog), 0o755)
os.environ["PATH"] = FAKE_BIN + os.pathsep + os.environ.get("PATH", "")
import umleitung  # noqa: E402 - A9/P70: Abbruch, wenn die Umleitung nicht greift
umleitung.pruefe(WORK, "XDG_CONFIG_HOME")
SPICES = os.path.join(WORK, "config", "cinnamon", "spices", "avincelaunch-desklet@avince")
os.makedirs(SPICES)

spec = importlib.util.spec_from_file_location("linkImport", "Desklet/linkImport.py")
L = importlib.util.module_from_spec(spec)
spec.loader.exec_module(L)

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


def read(path):
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read()


def changed_lines(before, after):
    a = before.splitlines()
    b = after.splitlines()
    if len(a) != len(b):
        return None
    return [(x, y) for x, y in zip(a, b) if x != y]


def leftovers(directory):
    return sorted(n for n in os.listdir(directory) if n.endswith(".tmp"))


SAMPLE = """[Desktop Entry]
# Kommentar bleibt erhalten
Version=1.0
Type=Application
Name=Drawing Tool
Name[de]=Zeichenprogramm
Name[fr]=Outil de dessin
GenericName=Drawing
Comment=Draw things
Comment[de]=Dinge zeichnen
Exec=drawtool --draw %U
Icon=drawtool
Terminal=false
MimeType=image/svg+xml;application/x-draw;
Categories=Graphics;
StartupWMClass=drawtool
Actions=NewDocument;

[Desktop Action NewDocument]
Name=New Drawing
Name[de]=Neue Zeichnung
Exec=drawtool --new
Icon=document-new
"""

group = os.path.join(WORK, "groups", "GRAFIK")
os.makedirs(group)
sample = os.path.join(group, "drawtool.desktop")
with open(sample, "w", encoding="utf-8") as handle:
    handle.write(SAMPLE)
os.chmod(sample, 0o644)

print("Lesen (P1: nur [Desktop Entry]):")
info = L.read_desktop_link(sample)
check("Name = deutscher Name des Programms, nicht der Aktion", info["name"], "Zeichenprogramm")
check("Exec aus [Desktop Entry] mit %U", info["command"], "drawtool --draw %U")
check("Icon aus [Desktop Entry]", info["icon"], "drawtool")
check("Terminal = false", info["terminal"], False)

print("\nSpeichern ohne Aenderung:")
before = read(sample)
mtime = os.stat(sample).st_mtime_ns
result = L.update_desktop_link(sample, info["name"], info["command"], info["icon"], info["terminal"])
check("ok", result.get("ok"), True)
check("Datei byte-gleich", read(sample), before)
check("nicht neu geschrieben (Zeitstempel)", os.stat(sample).st_mtime_ns, mtime)

print("\nNur den Namen aendern:")
result = L.update_desktop_link(sample, "Mein Zeichnen", info["command"], info["icon"], False)
after = read(sample)
check("ok", result.get("ok"), True)
check("genau eine Zeile anders: Name[de]", changed_lines(before, after),
      [("Name[de]=Zeichenprogramm", "Name[de]=Mein Zeichnen")])
check("Rechte bleiben 644", stat.S_IMODE(os.stat(sample).st_mode), 0o644)
check("keine Zwischendatei", leftovers(group), [])

print("\nBefehl, Symbol, Terminal aendern:")
before = after
L.update_desktop_link(sample, "Mein Zeichnen", "drawtool --draw --big %U", "gimp", True)
after = read(sample)
check("drei Zeilen anders (Exec, Icon, Terminal)", changed_lines(before, after), [
    ("Exec=drawtool --draw %U", "Exec=drawtool --draw --big %U"),
    ("Icon=drawtool", "Icon=gimp"),
    ("Terminal=false", "Terminal=true"),
])
check("Aktion unveraendert", "[Desktop Action NewDocument]\nName=New Drawing\nName[de]=Neue Zeichnung\n"
      "Exec=drawtool --new\nIcon=document-new\n" in after, True)
check("Kommentar, MimeType, Uebersetzungen da",
      all(x in after for x in ("# Kommentar bleibt erhalten", "MimeType=", "Name[fr]=", "Comment[de]=")), True)

print("\nDatei ohne Symbol und Terminal:")
plain = os.path.join(group, "plain.desktop")
with open(plain, "w", encoding="utf-8") as handle:
    handle.write("[Desktop Entry]\nType=Application\nName=Plain\nExec=plain\n")
info = L.read_desktop_link(plain)
before = read(plain)
L.update_desktop_link(plain, info["name"], info["command"], info["icon"], info["terminal"])
check("Vorgaben schreiben nichts dazu", read(plain), before)

print("\nSymlink (P1):")
outside = os.path.join(WORK, "applications")
os.makedirs(outside)
target = os.path.join(outside, "linked.desktop")
with open(target, "w", encoding="utf-8") as handle:
    handle.write("[Desktop Entry]\nType=Application\nName=Linked\nExec=linked\nIcon=linked\n")
link = os.path.join(group, "linked.desktop")
os.symlink(target, link)
target_before = read(target)
result = L.update_desktop_link(link, "Linked neu", "linked", "linked", False)
check("Teil 2 BT2: erst Rueckfrage (symlink), nichts geschrieben",
      (result.get("ok"), result.get("confirm"), os.path.islink(link)), (False, "symlink", True))
check("... nennt das Ziel", result.get("target"), target)
result = L.update_desktop_link(link, "Linked neu", "linked", "linked", False, confirmed=True)
check("nach Bestaetigung ok", result.get("ok"), True)
check("Ziel ausserhalb unveraendert", read(target), target_before)
check("Verweis durch bearbeitete Kopie ersetzt", os.path.islink(link), False)
check("Kopie traegt den neuen Namen", "Name=Linked neu" in read(link), True)

print("\nSchreibgeschuetzt (Teil 2, BT2):")
ro = os.path.join(group, "ro.desktop")
with open(ro, "w", encoding="utf-8") as handle:
    handle.write("[Desktop Entry]\nType=Application\nName=Geschuetzt\nExec=plain\n")
os.chmod(ro, 0o444)
ro_before = read(ro)
result = L.update_desktop_link(ro, "Geaendert", "plain", "", False)
check("erst Rueckfrage (readonly), nichts geschrieben",
      (result.get("confirm"), read(ro)), ("readonly", ro_before))
check("ohne Aenderung keine Rueckfrage", L.update_desktop_link(ro, "Geschuetzt", "plain", "", False).get("ok"), True)
result = L.update_desktop_link(ro, "Geaendert", "plain", "", False, confirmed=True)
check("nach Bestaetigung geaendert", (result.get("ok"), "Name=Geaendert" in read(ro)), (True, True))
check("bleibt schreibgeschuetzt (444)", stat.S_IMODE(os.stat(ro).st_mode), 0o444)

print("\nName wie im Fence (Teil 2, BT2):")
E = None
try:
    espec = importlib.util.spec_from_file_location("orderFolderEditor_bt2", "Desklet/orderFolderEditor.py")
    E = importlib.util.module_from_spec(espec)
    espec.loader.exec_module(E)
except Exception as error:
    print("  (Vergleich mit dem Dialog-Scan uebersprungen: %s)" % error)


def same_as_fence(path):
    # Der Dialog-Scan (_desktop_entry_name) bildet lib/linkScanner.js nach (P36).
    return E is None or L.read_desktop_link(path)["name"] == E._desktop_entry_name(path, os.path.basename(path))


full = os.path.join(group, "full.desktop")
with open(full, "w", encoding="utf-8") as handle:
    handle.write("[Desktop Entry]\nType=Application\nName=Kurz\nX-GNOME-FullName=Langer Name\nExec=plain\n")
check("X-GNOME-FullName wird gezeigt und bearbeitet", L.read_desktop_link(full)["name"], "Langer Name")
check("... wie im Fence", same_as_fence(full), True)
L.update_desktop_link(full, "Neuer langer Name", "plain", "", False)
check("... X-GNOME-FullName geaendert, Name bleibt",
      ("X-GNOME-FullName=Neuer langer Name" in read(full), "Name=Kurz" in read(full)), (True, True))
hidden = os.path.join(group, "hidden.desktop")
with open(hidden, "w", encoding="utf-8") as handle:
    handle.write("[Desktop Entry]\nType=Application\nName=Roh\nName[de]=Uebersetzt\nNoDisplay=true\nExec=plain\n")
check("NoDisplay: unuebersetzte Name=-Zeile wie im Fence", L.read_desktop_link(hidden)["name"], "Roh")
check("... wie im Fence", same_as_fence(hidden), True)
L.update_desktop_link(hidden, "Roh neu", "plain", "", False)
check("... Name geaendert, Name[de] bleibt",
      ("Name=Roh neu" in read(hidden), "Name[de]=Uebersetzt" in read(hidden)), (True, True))
missing_prog = os.path.join(group, "fehlt.desktop")
with open(missing_prog, "w", encoding="utf-8") as handle:
    handle.write("[Desktop Entry]\nType=Application\nName=Fehlt\nName[de]=Fehlt-de\nExec=avl-gibt-es-nicht\n")
check("Programm nicht installiert: wie im Fence", (L.read_desktop_link(missing_prog)["name"], same_as_fence(missing_prog)),
      ("Fehlt", True))
check("installiertes Beispiel: Name[de] wie im Fence", same_as_fence(sample), True)

print("\nNeuer Starter (P53):")
created = L.create_desktop_link(group, "Datum", "date +%Y", "", False)
check("ok", created.get("ok"), True)
text = read(created["path"])
check("% als %% geschrieben", "Exec=date +%%Y" in text, True)
check("wieder gelesen = Eingabe (N2: %% wird als % gezeigt)", L.read_desktop_link(created["path"])["command"], "date +%Y")
second = L.create_desktop_link(group, "Datum", "date", "", False)
check("gleicher Name -> neue Datei", os.path.basename(second.get("path", "")), "Datum-1.desktop")
check("erste Datei nicht ueberschrieben", read(created["path"]), text)
check("keine Zwischendatei", leftovers(group), [])
check("leerer Name abgelehnt", L.create_desktop_link(group, " ", "x", "", False).get("ok"), False)

print("\nNeuer Starter, Sonderfaelle (Teil 2, T7):")
os.symlink(os.path.join(WORK, "gibt-es-nicht.desktop"), os.path.join(group, "Tot.desktop"))
result = L.create_desktop_link(group, "Tot", "true", "", False)
check("toter Verweis gleichen Namens: naechster Name", os.path.basename(result.get("path", "")), "Tot-1.desktop")
check("... Verweis unangetastet", (os.path.islink(os.path.join(group, "Tot.desktop")),
                                   os.path.exists(os.path.join(WORK, "gibt-es-nicht.desktop"))), (True, False))
real_link = os.link


def no_hardlinks(*args, **kwargs):
    raise OSError(errno.EPERM, "Operation not permitted")


os.link = no_hardlinks
result = L.create_desktop_link(group, "Ohne Hardlink", "true", "", False)
check("ohne harte Verweise (vfat): trotzdem angelegt", result.get("ok"), True)
check("... Inhalt vollstaendig, 755", ("Name=Ohne Hardlink" in read(result["path"]),
                                       stat.S_IMODE(os.stat(result["path"]).st_mode)), (True, 0o755))
again = L.create_desktop_link(group, "Ohne Hardlink", "true", "", False)
check("... gleicher Name -> naechste Datei", os.path.basename(again.get("path", "")), "Ohne-Hardlink-1.desktop")
real_fsync = os.fsync
calls = []


def disk_full(fd):
    calls.append(fd)
    if len(calls) >= 2:
        raise OSError(errno.ENOSPC, "No space left on device")
    return real_fsync(fd)


os.fsync = disk_full
result = L.create_desktop_link(group, "Voll", "true", "", False)
os.fsync = real_fsync
os.link = real_link
check("Platte voll: Fehler", result.get("ok"), False)
check("... keine halbe Datei", os.path.lexists(os.path.join(group, "Voll.desktop")), False)
check("... keine Zwischendatei", leftovers(group), [])

print("\nPfad aus der Liste (P7):")
check("normaler Name", L.entry_path(group, "a.desktop"), os.path.join(group, "a.desktop"))
check("../x abgelehnt", L.entry_path(group, "../x"), None)
check("a/b abgelehnt", L.entry_path(group, "a/b"), None)
check(".. abgelehnt", L.entry_path(group, ".."), None)
check("leer abgelehnt", L.entry_path(group, ""), None)

print("\nPortal-Schutz fuer Eintraege (P54):")
portal = os.path.join(WORK, "portal")
os.makedirs(os.path.join(portal, "sub"))
with open(os.path.join(SPICES, "99.json"), "w", encoding="utf-8") as handle:
    json.dump({"source-mode": {"value": "portal"}, "portal-path": {"value": portal}}, handle)
# A6/P28: Es zaehlen nur eingeschaltete Fences (enabled-desklets) - im Test
# gilt Instanz 99 als eingeschaltet, statt Cinnamon zu fragen.
L._PORTAL_GUARD._enabled_for_tests = ["99"]
os.symlink(os.path.join(portal, "sub"), os.path.join(group, "verweis"))
check("Verweis in der Gruppe auf ein Portal: erlaubt",
      L._refuse_entry(os.path.join(group, "verweis"), "Test"), False)
check("Eintrag im Portal: verweigert", L._refuse_entry(os.path.join(portal, "sub"), "Test"), True)
check("Portal selbst: verweigert", L._refuse_entry(portal, "Test"), True)

if "--live" in sys.argv:
    print("\nKopien der echten Starter mit Aktionsabschnitten (--live):")
    live_dir = os.path.join(WORK, "live")
    os.makedirs(live_dir)
    sources = sorted(glob.glob(os.path.expanduser("~/.local/share/thelauncher-groups/**/*.desktop"),
                               recursive=True))
    count = 0
    for source in sources:
        with open(source, "r", encoding="utf-8", errors="ignore") as handle:
            if "[Desktop Action" not in handle.read():
                continue
        count += 1
        copy = os.path.join(live_dir, "%02d-%s" % (count, os.path.basename(source)))
        shutil.copyfile(source, copy)
        name = os.path.relpath(source, os.path.expanduser("~/.local/share/thelauncher-groups"))
        info = L.read_desktop_link(copy)
        from gi.repository import Gio
        app = Gio.DesktopAppInfo.new_from_filename(copy)
        check(name + ": Name wie das Desklet ihn zeigt", info["name"], app.get_name() if app else info["name"])
        before = read(copy)
        L.update_desktop_link(copy, info["name"], info["command"], info["icon"], info["terminal"])
        check(name + ": Speichern ohne Aenderung = byte-gleich", read(copy), before)
        L.update_desktop_link(copy, info["name"] + " X", info["command"], info["icon"], info["terminal"])
        diff = changed_lines(before, read(copy))
        check(name + ": nur eine Namenszeile anders", diff is not None and len(diff) == 1
              and diff[0][0].startswith("Name"), True)
    check("Starter mit Aktionsabschnitten gefunden", count > 0, True)
    print("  (%d Starter, nur Kopien in %s)" % (count, live_dir))

shutil.rmtree(WORK)
print(f"\nGeprueft: {checks}, Fehler: {failures}")
sys.exit(1 if failures else 0)
