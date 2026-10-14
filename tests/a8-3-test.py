#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
# Copyright (c) 2026 Angelo Vincenti, aVince Industrietechnik

# Prueft Schritt 9, Paket A8-3 (Pruefung Phase 2) ohne Cinnamon, nur lesend
# (die .pot-Probe laeuft in einem Wegwerfordner):
#   P46 READMEs en/de: kein veralteter UUID-Satz, kein Master-Backup, "Noch
#       offen" statt "Geplant" (AP13d, AP14), Eval-Grenze (B6), Ko-fi-Abschnitt,
#       gleiche Gliederung; .github/FUNDING.yml;
#   P47 CHANGELOG [0.1.0] (seit V1 Kurzfassung); ROADMAP-Stand;
#   metadata.json-Beschreibung ohne "drag handle"/"position lock";
#   P68 .pot = frisch erzeugte (cinnamon-xlet-makepot), de.po vollstaendig,
#       "…" im Deutschen mit Leerzeichen (ausser in Pfaden).
# Aufruf im Repository-Wurzelverzeichnis:  python3 tests/a8-3-test.py

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

import polib

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
    # Fehlende Datei = leer: der Test meldet das als Fehler statt abzubrechen.
    try:
        with open(path, encoding="utf-8") as handle:
            return handle.read()
    except FileNotFoundError:
        return ""


UUID = "avincelaunch-desklet@avince"

# --- P46 READMEs ----------------------------------------------------------------
print("P46 READMEs:")
en, de = read("README.md"), read("README.de.md")
check("en: kein UUID-Satz", "has **not** been carried out" in en, False)
check("de: kein UUID-Satz", "**noch nicht** durchgeführt" in de, False)
check("en: kein Master-Backup", "master backup" in en.lower(), False)
check("de: kein Master-Backup", "master-backup" in de.lower(), False)
check("en: Status 0.1.0", "version 0.1.0, published on 14 October 2026" in en, True)
check("de: Stand 0.1.0", "Version 0.1.0, veröffentlicht am 14. Oktober 2026" in de, True)
en_heads = re.findall(r"(?m)^## (.+)$", en)
de_heads = re.findall(r"(?m)^## (.+)$", de)
check("en: kein Abschnitt Planned", "Planned" in en_heads, False)
check("de: kein Abschnitt Geplant", "Geplant" in de_heads, False)
check("gleich viele Abschnitte", len(en_heads), len(de_heads))
for name, text, head in (("en", en, "Still open"), ("de", de, "Noch offen")):
    part = text.split("## " + head, 1)[1].split("\n## ", 1)[0] if ("## " + head) in text else ""
    # V1 (13.10.): ohne interne Paketnummern - Layoutprofile und Tabs.
    rows = re.findall(r"(?m)^\| ([^|]+?) \|", part)
    check(name + ": offen genau Layoutprofile und Tabs", len(rows) == 2 and "Tabs" in rows[1]
          and ("Layout" in rows[0]), True)
    # V3a (B6): Eval ist weg - statt der Grenze steht das Zusatzpaket im README.
    check(name + ": keine Eval-Grenze mehr, Zusatzpaket genannt",
          ("org.Cinnamon.Eval" in text, "aVinceLaunch-Helfer-0.1.0.tar.gz" in text), (False, True))
    check(name + ": Ko-fi-Link", "(https://ko-fi.com/avince)" in text, True)
    check(name + ": Satz zu MHK924 im Unterstuetzungsabschnitt",
          "MHK924" in text.split("ko-fi.com/avince")[0].rsplit("\n## ", 1)[-1], True)
check("FUNDING.yml ko_fi: avince",
      re.findall(r"(?m)^ko_fi:\s*(\S+)\s*$", read(".github/FUNDING.yml")), ["avince"])

# --- P47 CHANGELOG, ROADMAP --------------------------------------------------------
print("P47 CHANGELOG / ROADMAP:")
log = read("CHANGELOG.md")
# V1 (Angelo 13.10.): oeffentlich eine Kurzfassung; die Entwicklungsgeschichte
# liegt im privaten Archiv.
check("Abschnitt [0.1.0] mit Datum", "## [0.1.0] – 2026-10-14" in log, True)
check("Kurzfassung (unter 120 Zeilen)", len(log.splitlines()) < 120, True)
check("nennt Fork, Startaufstellung, Hilfsskripte",
      ("TheLauncher 1.0.3" in log, "**Starter layout**" in log, "### Helper scripts" in log), (True, True, True))
road = read("docs/ROADMAP.md")
check("ROADMAP Stand 2026-10-13", road.startswith("# Roadmap\n\nAs of 2026-10-13"), True)
check("ROADMAP: Layoutprofile erstes Update, Tabs spaeter",
      ("first update after 0.1.0" in road, "**Tabs**" in road), (True, True))

# --- metadata.json ------------------------------------------------------------------
print("metadata.json:")
meta = json.loads(read("Desklet/metadata.json"))
check("Beschreibung ohne drag handle/position lock",
      [w for w in ("drag handle", "position lock") if w in meta["comments"]], [])
check("Beschreibung nennt die Sperren", "locks for position, size and content" in meta["comments"], True)

# --- P68 Uebersetzung ---------------------------------------------------------------
print("P68 Uebersetzung:")
pot = polib.pofile("Desklet/po/%s.pot" % UUID)
po = polib.pofile("Desklet/po/de.po")
active = {(e.msgctxt, e.msgid): e for e in po if not e.obsolete}
pot_ids = {(e.msgctxt, e.msgid) for e in pot}
check("de.po deckt die .pot ab", sorted(k[1][:40] for k in pot_ids - set(active)), [])
check("de.po ohne Eintraege ausserhalb der .pot (aktiv)", sorted(k[1][:40] for k in set(active) - pot_ids), [])
check("alles uebersetzt", [k[1][:40] for k, e in active.items() if not e.msgstr], [])
check("nichts unscharf", [e.msgid[:40] for e in po if "fuzzy" in e.flags and e.msgid], [])
check("Beschreibung (comments) uebersetzt", bool(active.get((None, meta["comments"])) and
                                                   active[(None, meta["comments"])].msgstr), True)
tight = [e.msgstr for e in active.values() if re.search(r"[^\s/]…", e.msgstr)]
check("deutsches „…“ mit Leerzeichen (ausser Pfade)", tight, [])
check("Hilfe de ohne „…“ direkt am Wort", re.findall(r"\w…", read("Desklet/help/de.html")), [])
fmt = subprocess.run(["msgfmt", "-c", "-o", os.devnull, "Desklet/po/de.po"], capture_output=True, text=True)
check("msgfmt -c ohne Fehler", (fmt.returncode, fmt.stderr.strip()), (0, ""))

makepot = shutil.which("cinnamon-xlet-makepot")
if makepot:
    with tempfile.TemporaryDirectory(prefix="avl-a8-3-") as work:
        copy = os.path.join(work, UUID)
        shutil.copytree("Desklet", copy, ignore=shutil.ignore_patterns("__pycache__"))
        os.remove(os.path.join(copy, "po", UUID + ".pot"))
        subprocess.run([makepot, UUID], cwd=work, capture_output=True, text=True, check=True)
        fresh = polib.pofile(os.path.join(copy, "po", UUID + ".pot"))
        check(".pot = frisch erzeugte (Texte)", sorted((e.msgctxt or "", e.msgid) for e in fresh),
              sorted((e.msgctxt or "", e.msgid) for e in pot))
        check(".pot = frisch erzeugte (Fundstellen)",
              {e.msgid: e.occurrences for e in fresh} == {e.msgid: e.occurrences for e in pot}, True)
else:
    print("  (cinnamon-xlet-makepot fehlt - .pot-Abgleich uebersprungen)")

print("")
print("Geprueft: %d, Fehler: %d" % (checks, failures))
sys.exit(1 if failures else 0)
