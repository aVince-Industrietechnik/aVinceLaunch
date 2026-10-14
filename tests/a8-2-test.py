#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
# Copyright (c) 2026 Angelo Vincenti, aVince Industrietechnik

# Prueft Schritt 9, Paket A8-2 (Pruefung Phase 2) ohne Cinnamon, nur lesend:
#   Hilfe de/en: sauberes HTML, Inhaltsverzeichnis = 17 nummerierte Abschnitte (V3c: Zusatzpaket),
#   alle Sprungmarken vorhanden, de und en gleich gegliedert; Basisordner
#   ~/.local/share/avincelaunch (P20); Untermenue "Sperren" statt Schalter
#   "Position sperren" (P44); die neuen Funktionen mit ihren Namen genau wie
#   im Desklet bzw. in de.po (P45); Hinweis "Ordner bleibt" (B9);
#   Schnellstart: 7 Punkte inkl. "Weitere Fences", alle uebersetzt.
# Aufruf im Repository-Wurzelverzeichnis:  python3 tests/a8-2-test.py

import ast
import html
import re
import sys
from html.parser import HTMLParser

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


VOID = {"meta", "img", "br", "hr", "link", "input"}


class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack, self.errors, self.ids, self.hrefs = [], [], [], []
        self.nav, self.h2, self.in_nav, self.in_h2 = [], [], False, False
        self.text = []
        self.section_rows, self.section = [], -1

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag not in VOID:
            self.stack.append(tag)
        if "id" in a:
            self.ids.append(a["id"])
        if tag == "a" and a.get("href", "").startswith("#"):
            self.hrefs.append(a["href"][1:])
            if self.in_nav:
                self.nav.append(a["href"][1:])
        if tag == "nav":
            self.in_nav = True
        if tag == "h2":
            self.in_h2 = True
            self.h2.append([a.get("id"), ""])
            self.section += 1
            self.section_rows.append(0)
        if tag == "tr" and self.section >= 0:
            self.section_rows[self.section] += 1

    def handle_endtag(self, tag):
        if tag in VOID:
            return
        if not self.stack or self.stack[-1] != tag:
            self.errors.append("</%s> bei offen %s (Zeile %d)" % (tag, self.stack[-3:], self.getpos()[0]))
            if tag in self.stack:
                while self.stack and self.stack.pop() != tag:
                    pass
            return
        self.stack.pop()
        if tag == "nav":
            self.in_nav = False
        if tag == "h2":
            self.in_h2 = False

    def handle_data(self, data):
        self.text.append(data)
        if self.in_h2:
            self.h2[-1][1] += data


def load(lang):
    page = Page()
    with open("Desklet/help/%s.html" % lang, encoding="utf-8") as handle:
        page.feed(handle.read())
    page.close()
    page.plain = re.sub(r"\s+", " ", "".join(page.text))
    return page


po = polib.pofile("Desklet/po/de.po")
de_strings = {e.msgstr for e in po if e.msgstr}
en_strings = {e.msgid for e in po}

pages = {}
for lang in ("de", "en"):
    print("Hilfe %s:" % lang)
    p = load(lang)
    pages[lang] = p
    check("HTML ohne Verschachtelungsfehler", p.errors, [])
    check("alles geschlossen", [t for t in p.stack if t not in ("html", "body")], [])
    check("17 Abschnitte", len(p.h2), 17)
    check("nummeriert 1-17", [h[1].split(".")[0] for h in p.h2], [str(i) for i in range(1, 18)])
    check("Inhaltsverzeichnis = Abschnitte", p.nav, [h[0] for h in p.h2])
    check("alle Sprungmarken vorhanden", sorted(set(p.hrefs) - set(p.ids)), [])
    check("ids eindeutig", len(p.ids), len(set(p.ids)))
    check("Basisordner ~/.local/share/avincelaunch (P20)", "~/.local/share/avincelaunch" in p.plain, True)
    check("kein thelauncher-groups", "thelauncher-groups" in p.plain, False)

print("de/en gleich gegliedert:")
check("gleiche Tabellenzeilen je Abschnitt", pages["de"].section_rows, pages["en"].section_rows)

# --- P44: Untermenue statt Schalter ------------------------------------------
print("P44 Sperren:")
de_raw = open("Desklet/help/de.html", encoding="utf-8").read()
en_raw = open("Desklet/help/en.html", encoding="utf-8").read()
check("de: kein Menuepunkt \"Position sperren\"",
      re.findall(r"Rechtsklick → Position sperren|class=\"menu\">Position sperren<", de_raw), [])
check("en: kein Menuepunkt \"Lock position\"",
      re.findall(r"right-click → Lock position|class=\"menu\">Lock position<", en_raw, re.I), [])
check("de: Sperren ▸ Position", "Rechtsklick → Sperren ▸ Position" in pages["de"].plain, True)
check("en: Lock ▸ Position", "right-click → Lock ▸ Position" in pages["en"].plain, True)

# --- P45: Namen wie im Desklet ------------------------------------------------
print("P45 Namen wie im Desklet (de.po):")
DE_TERMS = [
    "Fence einklappen", "Eingeklappt beim Überfahren aufklappen", "Alle Fences durchsuchen …",
    "Fence umbenennen …", "Fence duplizieren", "Sperren", "Vorherige Größe wiederherstellen",
    "Ursprüngliche Größe wiederherstellen", "Anordnung wiederherstellen", "Alle Fences ausrichten",
    "Titel aller Fences ausblenden", "Titel aller Fences einblenden", "Darstellung zurücksetzen …",
    "Verknüpfungsordner öffnen", "Schnellstart …", "Verschieben nach", "Vorn anpinnen", "Lösen",
    "Aus dem Fence entfernen …", "Titelzeile anzeigen", "Lage der Titelzeile",
    "Such-Knopf in der Titelzeile", "Reihenfolge im Fence", "Manuell (Liste unter „Inhalte“)",
    "Im Fence – nur unter der Maus", "Im Fence – immer", "Über dem Fence – als Lasche unter der Maus",
    "Wie die Position", "Startverhalten", "Klick auf einen Ordner", "Ordner-Portal (nur Ansicht)",
    "Auswählen …", "FREI (Strg)", "Ursprüngliche Anordnung", "Inhalt", "Größe", "Position",
]
EN_TERMS = [
    "Collapse fence", "Expand on hover when collapsed", "Search all fences…", "Rename fence…",
    "Duplicate fence", "Lock", "Restore previous size", "Restore original size",
    "Restore arrangement", "Align all fences", "Hide titles of all fences",
    "Show titles of all fences", "Reset appearance…", "Open link folder", "Quick start…",
    "Move to", "Pin to the front", "Unpin", "Remove from fence…", "Show title row",
    "Title row position", "Search button in the title row", "Order in the fence",
    "Manual (Items list)", "Inside the fence – only under the pointer", "Inside the fence – always",
    "Above the fence – as a tab under the pointer", "Like the position", "Launch mode",
    "Folder click action", "Folder portal (view only)", "Choose…", "FREE (Ctrl)",
    "Original arrangement", "Content", "Size", "Position",
]
check("de: Begriffe stehen so in de.po", [t for t in DE_TERMS if t not in de_strings], [])
check("de: Begriffe stehen in der Hilfe", [t for t in DE_TERMS if t not in pages["de"].plain], [])
check("en: Begriffe sind Texte des Desklets", [t for t in EN_TERMS if t not in en_strings], [])
check("en: Begriffe stehen in der Hilfe", [t for t in EN_TERMS if t not in pages["en"].plain], [])

# --- B9 und weitere Hinweise -----------------------------------------------------
print("B9 und Hinweise:")
check("de: Ordner bleibt nach dem Entfernen", "bleibt der Ordner des Fence mit allen Dateien" in pages["de"].plain, True)
check("en: folder kept after removing", "its folder and all files in it are kept" in pages["en"].plain, True)
check("de: 30 Tage", "30 Tage" in pages["de"].plain, True)
check("en: 30 days", "30 days" in pages["en"].plain, True)
check("de: Einstellungssicherung", "~/.config/avincelaunch/backups/" in pages["de"].plain, True)
check("en: settings backup", "~/.config/avincelaunch/backups/" in pages["en"].plain, True)
check("de: Strg bleibt nach Neustart", "nach einem Neustart genau dort" in pages["de"].plain, True)
check("en: Ctrl stays after restart", "stays exactly there after a restart" in pages["en"].plain, True)

# --- Schnellstart ------------------------------------------------------------------
print("Schnellstart:")
src = open("Desklet/quickstart-dialog.py", encoding="utf-8").read()
block = src[src.index("POINTS = ["):src.index("]\n\n\ndef help_page")]
texts = [ast.literal_eval("(" + raw + ")") for raw in re.findall(r'_\(((?:"[^"]*"\s*)+)\)', block)]
check("7 Punkte (je Ueberschrift + Text)", len(texts), 14)
check("zweiter Punkt \"More fences\"", texts[2], "More fences")
check("Text nennt Duplicate fence", "Duplicate fence" in texts[3], True)
check("Lock ▸ Position statt Lock position", ["Lock position" in t for t in texts], [False] * 14)
translated = {e.msgid: e.msgstr for e in po if not e.obsolete}
check("alle Schnellstart-Texte uebersetzt", [t[:30] for t in texts if not translated.get(t)], [])
check("de: Weitere Fences", translated.get("More fences"), "Weitere Fences")
check("de.po: nichts unscharf", len(po.fuzzy_entries()), 0)
check("de.po: nichts leer", len(po.untranslated_entries()), 0)

print("")
print("Geprueft: %d, Fehler: %d" % (checks, failures))
sys.exit(1 if failures else 0)
