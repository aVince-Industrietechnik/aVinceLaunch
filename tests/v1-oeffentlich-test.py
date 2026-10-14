#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
# Copyright (c) 2026 Angelo Vincenti, aVince Industrietechnik

# Schritt 4, V1 (13.10.2026): Alles im Repository wird oeffentlich. Dieser
# Test sucht in jeder versionierten Datei nach Spuren, die nicht hinaus
# gehoeren: Pfade und Ordner der privaten Ablage, persoenliche Gruppennamen,
# feste Pfade eines Benutzers, Hinweise auf ein privates Repository.
# Seit E2 (14.10.2026, neues oeffentliches Repository mit sauberem Anfang)
# gelten dieselben Muster auch fuer alle Commit-Texte.
# Nichts wird geschrieben.
# Aufruf im Repository-Wurzelverzeichnis:  python3 tests/v1-oeffentlich-test.py

import os
import re
import subprocess
import sys

sys.dont_write_bytecode = True

# (Name, Muster). Die Muster sind zerlegt, damit diese Datei sich nicht
# selbst findet; sie wird zusaetzlich ausgenommen.
VERBOTEN = [
    ("private Ablage (Pfad)", re.compile("LX" + "-NAS|/mnt/" + "LX|60" + "_SETUP")),
    ("private Ablage (Ordner wie 01_DOKUMENTATION)", re.compile(r"\b(0[1-9]|1[01])_[A-Z][A-Z_]{3,}\b")),
    ("persoenliche Gruppe", re.compile("WA" + "WI|VM" + "_JTL|NETZWERK" + "_NAS")),
    ("fester Benutzerpfad", re.compile("/home/" + "angelo")),
    ("private E-Mail", re.compile("sang" + "io")),
    ("privates Repository", re.compile(r"stays private|\(privat\)")),
]

DIESE = "tests/v1-oeffentlich-test.py"
# Bekannte Ausnahmen - jede mit Grund und Ende.
AUSNAHMEN = {
    # Prueft, dass der Fence keine persoenlichen Gruppennamen mehr kennt -
    # nennt sie dafuer als Suchbegriffe.
    "tests/s8-2-test.py": {"persoenliche Gruppe"},
}

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


def dateien():
    try:
        out = subprocess.run(["git", "ls-files", "-z"], capture_output=True, check=True).stdout
        return [p for p in out.decode().split("\0") if p]
    except Exception:
        liste = []
        for wurzel, ordner, namen in os.walk("."):
            ordner[:] = [o for o in ordner if o not in (".git", "__pycache__")]
            liste += [os.path.relpath(os.path.join(wurzel, n)) for n in namen]
        return liste


funde = []
geprueft = 0
for pfad in sorted(dateien()):
    if pfad == DIESE or not os.path.isfile(pfad):
        continue
    with open(pfad, "rb") as handle:
        daten = handle.read()
    if b"\0" in daten[:4096]:
        continue  # Bild o. ae.
    text = daten.decode("utf-8", errors="replace")
    geprueft += 1
    erlaubt = AUSNAHMEN.get(pfad, set())
    for name, muster in VERBOTEN:
        if name in erlaubt:
            continue
        for nr, zeile in enumerate(text.splitlines(), 1):
            if muster.search(zeile):
                funde.append(f"{pfad}:{nr} [{name}] {zeile.strip()[:90]}")

check(f"{geprueft} Textdateien ohne interne Spuren", funde, [])
# E2: Commit-Texte (Betreff und Text) - sie werden mit dem Repository
# oeffentlich. Ohne git (z. B. entpacktes Archiv) wird nur gemeldet.
try:
    log = subprocess.run(["git", "log", "--all", "--format=%h%x00%B%x1e"],
                         capture_output=True, check=True).stdout.decode("utf-8", "replace")
except Exception:
    log = None
if log is None:
    print("  info    kein git-Verlauf - Commit-Texte nicht geprueft")
else:
    commit_funde = []
    eintraege = [e.strip("\n") for e in log.split("\x1e") if e.strip()]
    for eintrag in eintraege:
        kennung, _, text = eintrag.partition("\0")
        for name, muster in VERBOTEN:
            for zeile in text.splitlines():
                if muster.search(zeile):
                    commit_funde.append(f"{kennung} [{name}] {zeile.strip()[:90]}")
    check(f"{len(eintraege)} Commit-Texte ohne interne Spuren", commit_funde, [])

check("Ausnahmen zeigen auf vorhandene Dateien", [p for p in AUSNAHMEN if not os.path.isfile(p)], [])
check("Selbstpruefung: Muster greifen",
      [name for name, m in VERBOTEN if not m.search({
          "private Ablage (Pfad)": "/mnt/" + "LX" + "-NAS-linux",
          "private Ablage (Ordner wie 01_DOKUMENTATION)": "07_" + "PRUEFPROTOKOLLE",
          "persoenliche Gruppe": "VM" + "_JTL",
          "fester Benutzerpfad": "/home/" + "angelo/.local",
          "private E-Mail": "sang" + "io.av",
          "privates Repository": "(privat)",
      }[name])], [])

print("")
print(f"Geprueft: {checks}, Fehler: {failures}")
sys.exit(1 if failures else 0)
