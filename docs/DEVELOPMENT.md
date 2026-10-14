# Entwicklung

Stand: 2026-10-13.

## Arbeitskopie und Live-Installation

Entwickelt wird in einer Git-Arbeitskopie; ausprobiert in der eigenen
Cinnamon-Sitzung:

```
~/.local/share/cinnamon/desklets/avincelaunch-desklet@avince/   Code (Inhalt von Desklet/)
~/.config/cinnamon/spices/avincelaunch-desklet@avince/          Einstellungen je Fence
~/.config/avincelaunch/                                         config.json, layout.json, Sicherungen
~/.local/share/avincelaunch/                                    Gruppenordner (Standard)
```

Diese Pfade nicht von Hand bearbeiten. Geändert wird in der Arbeitskopie,
eingespielt wird bewusst – vorher eine Sicherung der genannten Ordner.

## Ablauf einer Änderung

1. **Zweig anlegen.** `main` bleibt der stabile Stand.
2. **Ändern** – klein und nachvollziehbar, eine Sache pro Commit.
3. **Offline prüfen** (kein laufendes Cinnamon nötig):
   ```
   bash tests/alle-tests.sh
   ```
   Syntaxprüfung und alle `tests/*-test.js`/`*-test.py`. Die Tests arbeiten in
   Wegwerfordnern, setzen `LANGUAGE=C` und sperren D-Bus.
4. **Einspielen** (Dateien aus `Desklet/` in den Live-Ordner kopieren), dann
   Cinnamon neu starten: <kbd>Alt</kbd>+<kbd>F2</kbd>, `r`, <kbd>Enter</kbd>.

   > **Kein `ReloadXlet`.** Bei mehreren Instanzen lädt Cinnamon nur eine neu
   > und entfernt die übrigen vom Schreibtisch.

   > **Einstellungen nie von außen in die `<ID>.json` schreiben**, solange
   > Cinnamon läuft – stattdessen den Einrichten-Dialog oder
   > `settings.setValue()` im Desklet.
5. **Übersetzung erneuern**, wenn sich Texte geändert haben: `.pot` mit
   `cinnamon-xlet-makepot` in einer Kopie des Ordners erzeugen (der Ordnername
   muss die UUID sein); zum Ausprobieren im Live-Ordner
   `cinnamon-xlet-makepot -i .` (installiert die `.mo`).
6. **Protokoll ansehen:**
   ```
   grep -i "avincelaunch\|JS ERROR" ~/.xsession-errors | tail -20
   ```
7. **Abnahmeliste:** `tests/PRUEFLISTE.md` – möglichst auch mit UI-Skalierung 2
   und mit zwei Bildschirmen, denn Größen und Lagen zählen in Bildpunkten.

## Werkzeuge

Vorausgesetzt: `python3` (mit GTK 3), `cjs`, `git`, `gdbus`, `gsettings`,
`zenity`; für die Übersetzung `gettext` und `cinnamon-xlet-makepot`; für die
Tests `polib` (Python). Node.js oder npm werden nicht gebraucht.

Eine echte Testumgebung für Cinnamon-Desklets gibt es nicht. Geprüft wird mit
Offline-Tests (Funktionen werden aus dem Quelltext gelöst und mit
nachgebauten Bausteinen ausgeführt), Neuladen und Prüfliste.

## Konventionen

- Commit-Nachrichten englisch, Entwicklerdoku deutsch, Oberfläche englisch mit
  deutscher Übersetzung.
- Ein Thema pro Commit, Nachricht in der Befehlsform.
- Keine Urheber- oder Lizenzhinweise aus TheLauncher entfernen; neue Dateien
  mit SPDX-Kopf (`GPL-3.0-only`, geerbte Teile zusätzlich `MIT`).
- Neue Einstellungsschlüssel **hinzufügen**, niemals vorhandene umdeuten – ein
  umbenannter Schlüssel löscht den Wert beim Anwender.
- Keine Dauerabfragen mit kurzem Takt, wo Dateisystem-Ereignisse genügen.
- Neue Funktionen als eigenes Modul unter `Desklet/lib/`.

## Veröffentlichung bei Cinnamon Spices

Die Einreichung braucht diese Ordnerform:

```
avincelaunch-desklet@avince/
├── files/avincelaunch-desklet@avince/   ← der Inhalt von Desklet/
├── info.json
├── README.md
└── screenshot.png
```

Vorgehen: Fork von `linuxmint/cinnamon-spices-desklets`, Zweig anlegen,
Inhalt hineinkopieren, `./validate-spice avincelaunch-desklet@avince`, Pull
Request. Die Hilfsskripte gehören nicht dazu; sie erscheinen als eigene Datei
im GitHub-Release.
