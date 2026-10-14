#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
# Copyright (c) 2026 Angelo Vincenti, aVince Industrietechnik

# N17 - Startaufstellung: Desklet/appSort.py in einem Wegwerfordner.
#   1. Zuordnung nach Kategorie und Programmname (Vorrang bei Mehrfachangaben)
#   2. Cinnamon-Einstellungsseiten erkannt, versteckte Eintraege nicht gelistet
#   3. Ordnernamen aus Titeln, eindeutig
#   4. Verknuepfung kopieren: neu, ausfuehrbar, nie ueberschreiben
#   5. create_layout: Standardbasis wird angelegt, eigene fehlende nie;
#      Auftrag vollstaendig
# Dazu die Stellen in startaufstellung-dialog.py, quickstart-dialog.py und
# desklet.js, die den Ablauf verbinden.
# Nichts im Live-System wird gelesen oder geschrieben.
# Aufruf im Repository-Wurzelverzeichnis:  python3 tests/n17-sort-test.py

import importlib.util
import json
import os
import shutil
import stat
import sys
import tempfile

sys.dont_write_bytecode = True

WORK = tempfile.mkdtemp(prefix="avl-n17-sort-test.")
os.environ["XDG_CONFIG_HOME"] = os.path.join(WORK, "config")
os.environ["XDG_DATA_HOME"] = os.path.join(WORK, "data")
import umleitung  # noqa: E402 - A9/P70: Abbruch, wenn die Umleitung nicht greift
umleitung.pruefe(WORK, "XDG_CONFIG_HOME", "XDG_DATA_HOME")

spec = importlib.util.spec_from_file_location("appSort", "Desklet/appSort.py")
S = importlib.util.module_from_spec(spec)
spec.loader.exec_module(S)

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


# --- 1. Zuordnung -------------------------------------------------------------
F = S.fence_for
check("neun Fences in Rasterreihenfolge", S.FENCE_KEYS,
      ["internet", "communication", "office", "graphics", "multimedia", "games", "development", "tools", "system"])
check("Firefox -> Internet", F("Network;WebBrowser;"), "internet")
check("Thunderbird (Office;Network;Email) -> Kommunikation", F("Office;Network;Email;"), "communication")
check("LibreOffice Writer -> Buero", F("Office;WordProcessor;"), "office")
check("GIMP -> Grafik", F("Graphics;2DGraphics;RasterGraphics;GTK;"), "graphics")
check("VLC -> Multimedia", F("AudioVideo;Player;Recorder;"), "multimedia")
check("Spiel -> Spiele", F("Game;ArcadeGame;"), "games")
check("VS Code (Development;TextEditor) -> Entwicklung", F("Utility;TextEditor;Development;IDE;"), "development")
check("Texteditor (Utility;TextEditor) -> Werkzeuge", F("GTK;Utility;TextEditor;"), "tools")
check("Terminal (Utility;TerminalEmulator;System) -> System", F("GTK;Utility;TerminalEmulator;System;"), "system")
check("Mint-Webapp (GTK;WebApps) -> Internet", F("GTK;WebApps;"), "internet")
check("Bildbetrachter (Utility;Viewer) -> Werkzeuge", F("GNOME;GTK;Utility;Viewer;"), "tools")
check("ohne Kategorie -> Werkzeuge", F(""), "tools")
check("unbekannte Kategorie -> Werkzeuge", F("X-Foo;"), "tools")
check("Gross/klein egal", F("network;webbrowser"), "internet")
check("virt-manager nach Programmname -> System", F("Utility;", "virt-manager"), "system")
check("Programmname mit Pfad und env", F("", "env FOO=1 /usr/bin/virt-manager --x"), "system")
check("Flatpak: flatpak run org.gnome.Boxes -> Programmname", S.exec_name("/usr/bin/flatpak run --branch=stable org.gnome.Boxes"),
      "org.gnome.boxes")
check("Liste statt Text", F(["AudioVideo", "Video"]), "multimedia")

# --- 2. Einstellungsseiten und Liste ------------------------------------------
check("cinnamon-settings-mouse ist Einstellungsseite", S.is_settings_page("cinnamon-settings-mouse.desktop"), True)
check("cinnamon-display-panel ist Einstellungsseite", S.is_settings_page("cinnamon-display-panel.desktop"), True)
check("X-Cinnamon-Settings-Panel ist Einstellungsseite", S.is_settings_page("foo.desktop", ["X-Cinnamon-Settings-Panel"]), True)
check("cinnamon-menu-editor ist keine", S.is_settings_page("cinnamon-menu-editor.desktop"), False)
check("firefox ist keine", S.is_settings_page("firefox.desktop"), False)


class FakeInfo:
    def __init__(self, app_id, name, cats, show=True, path=None, cmd="", keys=()):
        self._id, self._name, self._cats, self._show, self._cmd, self._keys = app_id, name, cats, show, cmd, keys
        self._path = path if path is not None else "/usr/share/applications/" + app_id

    def should_show(self): return self._show
    def get_filename(self): return self._path
    def get_id(self): return self._id
    def get_keys(self): return list(self._keys)
    def get_display_name(self): return self._name
    def get_name(self): return self._name
    def get_icon(self): return None
    def get_categories(self): return self._cats
    def get_commandline(self): return self._cmd


apps = S.collect([
    FakeInfo("zz.desktop", "Zeta", "Game;"),
    FakeInfo("hidden.desktop", "Versteckt", "Utility;", show=False),
    FakeInfo("cinnamon-settings-mouse.desktop", "Maus", "Settings;"),
    FakeInfo("firefox.desktop", "Firefox", "Network;WebBrowser;"),
    FakeInfo("firefox.desktop", "Firefox doppelt", "Network;"),
    FakeInfo("nopath.desktop", "Ohne Pfad", "Utility;", path=""),
    FakeInfo("avincelaunch-desklet@avince-x.desktop", "Eigenes", "Utility;"),
])
check("Liste: nur sichtbare, ohne doppelte, ohne Pfadlose, ohne eigene",
      [(a["name"], a["fence"], a["settings_page"]) for a in apps],
      [("Firefox", "internet", False), ("Maus", "system", True), ("Zeta", "games", False)])

# --- 3. Ordnernamen -----------------------------------------------------------
check("Grafik & Fotos -> Grafik_Fotos", S.folder_name("Grafik & Fotos"), "Grafik_Fotos")
check("Büro -> Buero", S.folder_name("Büro"), "Buero")
check("Graphics & Photos -> Graphics_Photos", S.folder_name("Graphics & Photos"), "Graphics_Photos")
check("nur Sonderzeichen -> Fence", S.folder_name("&&/"), "Fence")
check("kein Schraegstrich, kein ..", S.folder_name("../a/b"), "a_b")
base = os.path.join(WORK, "base")
os.makedirs(os.path.join(base, "Internet"))
check("vorhandener Ordner -> _2", S.unique_folder(base, "Internet"), "Internet_2")
check("in taken -> _2", S.unique_folder(base, "Spiele", {"Spiele"}), "Spiele_2")
check("frei bleibt frei", S.unique_folder(base, "System"), "System")

# --- 4. Verknuepfung kopieren -------------------------------------------------
src_dir = os.path.join(WORK, "apps")
os.makedirs(src_dir)
src = os.path.join(src_dir, "demo.desktop")
with open(src, "w", encoding="utf-8") as handle:
    handle.write("[Desktop Entry]\nType=Application\nName=Demo\nExec=true\n")
os.chmod(src, 0o644)
link = os.path.join(src_dir, "verweis.desktop")
os.symlink(src, link)
target = os.path.join(WORK, "ziel")
os.makedirs(target)
check("Kopie angelegt", S.copy_link(src, target), "angelegt")
check("Kopie ausfuehrbar 755", stat.S_IMODE(os.stat(os.path.join(target, "demo.desktop")).st_mode), 0o755)
with open(os.path.join(target, "demo.desktop"), "w", encoding="utf-8") as handle:
    handle.write("EIGENES")
check("zweites Mal: vorhanden", S.copy_link(src, target), "vorhanden")
check("vorhandene Datei nicht ueberschrieben", open(os.path.join(target, "demo.desktop")).read(), "EIGENES")
check("Verweis aufgeloest: Inhalt der Quelle", (S.copy_link(link, target),
      open(os.path.join(target, "verweis.desktop")).read().startswith("[Desktop Entry]"),
      os.path.islink(os.path.join(target, "verweis.desktop"))), ("angelegt", True, False))
check("keine Zwischendateien", sorted(os.listdir(target)), ["demo.desktop", "verweis.desktop"])
check("fehlende Quelle: Fehlertext", S.copy_link(os.path.join(src_dir, "fehlt.desktop"), target).startswith("[Errno"), True)

# --- 5. create_layout ---------------------------------------------------------
default = os.path.join(WORK, "data", "avincelaunch")
order_path = os.path.join(WORK, "config", "avincelaunch", "startaufstellung-auftrag.json")
fences = [{"key": "internet", "title": "Internet", "apps": [src]},
          {"key": "graphics", "title": "Grafik & Fotos", "apps": [src, link]},
          {"key": "games", "title": "Spiele", "apps": []}]
check("Ausgangslage: Standardbasis fehlt", os.path.exists(default), False)
order, errors = S.create_layout(default, default, fences, order_path)
check("Standardbasis angelegt, keine Fehler", (os.path.isdir(default), errors), (True, []))
check("Auftrag: Ordner und Zahl der Verknuepfungen",
      [(f["key"], f["folder"], f["links"]) for f in order["fences"]],
      [("internet", "Internet", 1), ("graphics", "Grafik_Fotos", 2), ("games", "Spiele", 0)])
check("Auftrag liegt als Datei vor, gleicher Inhalt", json.load(open(order_path, encoding="utf-8")), order)
check("Ordner mit Verknuepfungen", sorted(os.listdir(os.path.join(default, "Grafik_Fotos"))),
      ["demo.desktop", "verweis.desktop"])
check("leerer Fence bekommt leeren Ordner", os.listdir(os.path.join(default, "Spiele")), [])
check("keine .tmp neben dem Auftrag", [n for n in os.listdir(os.path.dirname(order_path)) if n.endswith(".tmp")], [])
order2, errors2 = S.create_layout(default, default, fences[:1], order_path)
check("zweiter Lauf: Internet_2, nichts ueberschrieben", order2["fences"][0]["folder"], "Internet_2")
nas = os.path.join(WORK, "nas", "gruppen")
order3, errors3 = S.create_layout(nas, default, fences, order_path)
check("eigene fehlende Basis: nichts angelegt", (order3, errors3, os.path.exists(nas)),
      (None, ["base-missing:" + nas], False))
check("Auftrag vom fehlgeschlagenen Lauf nicht ersetzt",
      json.load(open(order_path, encoding="utf-8"))["fences"][0]["folder"], "Internet_2")

# --- 6. Verbindungsstellen ----------------------------------------------------
dialog = open("Desklet/startaufstellung-dialog.py", encoding="utf-8").read()
quick = open("Desklet/quickstart-dialog.py", encoding="utf-8").read()
desklet = open("Desklet/desklet.js", encoding="utf-8").read()
check("Dialog: Titel aller neun Fences uebersetzbar",
      all('"%s": _("%s")' % (k, t) in dialog for k, t in S.FENCES), True)
check("Dialog: Titel in Grossbuchstaben (Angelo 13.10.)",
      "TITLES = {key: title.upper() for key, title in TITLES.items()}" in dialog, True)
check("Ordnername aus Grossbuchstaben-Titel", (S.folder_name("GRAFIK & FOTOS"), S.folder_name("BÜRO")),
      ("GRAFIK_FOTOS", "BUERO"))
check("Dialog: Einstellungsseiten vorab abgewaehlt", 'check.set_active(not app["settings_page"])' in dialog, True)
check("Dialog: Fence ohne Programm vorab nicht anlegen (E4)", "set_active(count > 0)" in dialog, True)
check("Dialog: Rueckgabe 0/1/2", ("self.result = 0" in dialog, "self.result = 1" in dialog,
                                  "self.result = 2" in dialog), (True, True, True))
check("Schnellstart: Knopf und Code 2", ('_("Starter layout…")' in quick, "self.result = 2" in quick,
                                       "sys.exit(main())" in quick), (True, True, True))
check("Desklet: Code 2 des Schnellstarts oeffnet die Startaufstellung",
      "if (code === 2) {\n                this.openStartLayout();" in desklet, True)
check("Desklet: Fences fest und gesperrt",
      all(t in desklet for t in ('"content-fit": "fixed"', '"lock-position": true', '"source-mode": "group"')), True)
check("Desklet: Spalten passend zur Breite (360 -> 4)",
      '"columns": Math.max(2, Math.floor(cell.w / 87))' in desklet and 360 // 87 == 4, True)
check("Desklet: Groesse in Bildpunkten (logisch x Skalierung), Tower 13.10.",
      ('"max-width": Math.round(cell.w * scale)' in desklet, '"max-height": Math.round(cell.h * scale)' in desklet,
       desklet.count("this._startLayoutValues(") == 2,
       all(c in desklet for c in ("_startLayoutValues(fences[0], cell, scale)", "_startLayoutValues(fence, cell, scale)"))),
      (True, True, True, True))
check("Desklet: vor dem Anlegen gesichert",
      desklet.find("backupBeforeClone(global.settings.get_strv") > desklet.find("_runStartLayout: function"), True)
check("Desklet: Rueckweg verschiebt Ordner, loescht nicht",
      ("folder.move(" in desklet, "startaufstellung-" in desklet), (True, True))

# --- 7. Dialog aufbauen (unsichtbar), mit gestellter Programmliste ------------
fehler_im_rueckruf = []
sys.excepthook = lambda t, v, tb: fehler_im_rueckruf.append(repr(v))
try:
    import gi
    gi.require_version("Gtk", "3.0")
    from gi.repository import Gtk
    gtk_da = Gtk.init_check(sys.argv)[0]
except Exception:
    gtk_da = False
if gtk_da:
    spec = importlib.util.spec_from_file_location("startaufstellung_dialog", "Desklet/startaufstellung-dialog.py")
    D = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(D)
    fake = [{"id": "a.desktop", "name": "A", "path": src, "icon": None, "fence": "internet", "settings_page": False},
            {"id": "b.desktop", "name": "B", "path": src, "icon": None, "fence": "tools", "settings_page": False},
            {"id": "m.desktop", "name": "Maus", "path": src, "icon": None, "fence": "system", "settings_page": True}]
    D.appSort.collect = lambda: [dict(a) for a in fake]
    dlg = D.StartLayoutDialog({"places": 9, "size": [360, 210], "reuse": True}, order_path)
    check("Dialog: keine Fehler in Rueckrufen beim Aufbau", fehler_im_rueckruf, [])
    check("Dialog: angehakt nur Fences mit Programm, Einstellungsseite nicht",
          [(f["key"], len(f["apps"])) for f in dlg._selection()], [("internet", 1), ("tools", 1)])
    check("Dialog: Anlegen moeglich", dlg.create_button.get_sensitive(), True)
    combo = [c for c in dlg.app_rows["b.desktop"].get_children() if isinstance(c, Gtk.ComboBoxText)][0]
    combo.set_active_id("games")
    check("Dialog: Umsortieren schaltet den Ziel-Fence an",
          [(f["key"], len(f["apps"])) for f in dlg._selection()], [("internet", 1), ("games", 1)])
    dlg.destroy()
    dlg2 = D.StartLayoutDialog({"places": 1, "size": [300, 180], "reuse": False}, order_path)
    check("Dialog: zu wenig Platz -> Anlegen gesperrt", dlg2.create_button.get_sensitive(), False)
    dlg2.destroy()
    check("Dialog: keine Fehler in Rueckrufen", fehler_im_rueckruf, [])
else:
    print("  (keine Anzeige - Dialogaufbau uebersprungen)")

shutil.rmtree(WORK)
print("")
print(f"Geprueft: {checks}, Fehler: {failures}")
sys.exit(1 if failures else 0)
