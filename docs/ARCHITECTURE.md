# Architektur

Stand: 2026-10-13 (Version 0.1.0). Beschreibt den Code, wie er ist – nicht,
wie er einmal werden soll. Geplantes steht in [ROADMAP.md](ROADMAP.md).

## Zwei Laufzeiten

Der Code läuft in **zwei getrennten Prozessen**, die nur das Dateisystem und
D-Bus gemeinsam haben:

| | Läuft in | Sprache | Aufgabe |
|---|---|---|---|
| `Desklet/desklet.js`, `Desklet/lib/*.js` | Cinnamon selbst (CJS) | JavaScript | Anzeige auf dem Schreibtisch, Menüs, Ziehen, Größe |
| `Desklet/*.py` | eigene Prozesse (`cinnamon-settings`, Dialoge) | Python + GTK 3 | Einrichten-Dialog, Schnellstart, Startaufstellung, Über |

Die Python-Seite ruft das Desklet über D-Bus zurück
(`org.Cinnamon.activateCallback`). Das Desklet startet Python-Dialoge als
eigene Prozesse (`_spawnDialog`, `_spawnDialogAsync` mit Rückgabewert).

## Dateien und Zuständigkeiten

| Datei | Aufgabe |
|---|---|
| `desklet.js` | Steuerung: Aufbau der Oberfläche, Titelzeile und Einklappen, Menüs, Suche, Startaufstellung, Einstellungs-Rückrufe |
| `lib/config.js` | Gemeinsamer Basisordner (`~/.config/avincelaunch/config.json`), eigener Gruppenordner anlegen (nur im Standard-Basisordner) |
| `lib/pathSource.js` | Quelle eines Fence: Gruppenordner oder Ordner-Portal |
| `lib/linkScanner.js`, `lib/portalScanner.js` | Ordner einlesen (Portal im Hintergrund) |
| `lib/sidecar.js` | `.avincelaunch.json` je Ordner: Reihenfolge, abgeschaltete und angepinnte Einträge, Ordnerfarben |
| `lib/placement.js` | Position in `org.cinnamon enabled-desklets`, Raster, Sperren – die einzige Schreibstelle für Positionen |
| `lib/layoutManager.js` | Größe ziehen (Randzonen), Fence-Verzeichnis, Hilfslinien, Ablage `layout.json` (Verlauf, Größen, Schnellstart, Startaufstellung) |
| `lib/snapEngine.js` | Einrasten, Ränder, Überlappungsschutz, freier Platz |
| `lib/startLayout.js` | Raster der Startaufstellung (3 × 3, rein rechnend) |
| `lib/fenceClone.js` | Fence duplizieren: freie ID, Übergabedatei, Sicherung |
| `lib/itemActions.js`, `lib/orderListSync.js` | Symbole verschieben/entfernen; Liste im Dialog abgleichen |
| `lib/settingsBackup.js`, `lib/safeJson.js` | Einstellungssicherung; unlesbare JSON-Dateien sichern statt ersetzen |
| `lib/launcher.js`, `lib/fileMonitor.js` | Starten/Öffnen; Dateiüberwachung mit Entprellung |
| `lib/themePresets.js`, `lib/settingsDefaults.js` | Farbvorlagen, Standardwerte |
| `appSort.py`, `startaufstellung-dialog.py` | Startaufstellung: Programme nach Kategorie, Vorschau, Ordner und Verknüpfungen anlegen |
| `quickstart-dialog.py`, `about-dialog.py` | Schnellstart, Über |
| `settingsPageBuilder.py`, `OrderListWidget.py`, `*Chooser.py`, `portalGuard.py`, `settingsMerge.py`, `linkImport.py` u. a. | Einrichten-Dialog |
| `settings-schema.json` | Alle Einstellungsschlüssel |
| `metadata.json` | UUID, Name, Version, `max-instances` |

## Wo die Daten liegen

```
~/.local/share/cinnamon/desklets/avincelaunch-desklet@avince/  Programmcode
~/.config/cinnamon/spices/avincelaunch-desklet@avince/<ID>.json Einstellungen je Fence
~/.config/avincelaunch/config.json                             gemeinsamer Basisordner
~/.config/avincelaunch/layout.json                             Verlauf, Größen, Startaufstellung
~/.config/avincelaunch/backups/                                Einstellungssicherungen u. a.
~/.local/share/avincelaunch/<GRUPPE>/                          Inhalt der Gruppen (Standard-Basisordner)
        └── .avincelaunch.json                                 Reihenfolge und Zustand
org.cinnamon enabled-desklets                                  "UUID:ID:X:Y"
```

`config.json` und `.thelauncher.json` aus TheLauncher werden gelesen, wenn es
die neuen Dateien noch nicht gibt.

**Bildpunkte:** Positionen in `enabled-desklets` sowie `max-width`/`max-height`
zählen in Bildpunkten des Bildschirms (logisch × UI-Skalierung). Rechnungen in
logischen Punkten (Raster der Startaufstellung, Randzonen) werden umgerechnet.

## Ablauf beim Anzeigen

```
Einstellung oder Dateiänderung
        │
        ▼
_scheduleRefresh()          entprellt über Mainloop.idle_add
        │
        ▼
_refresh() ── Quelle (Gruppe/Portal) ──► einlesen ── Sidecar (Reihenfolge)
        │
        ▼
_buildUI() / _buildMessage() ── Titelzeile (_fillTitleControls) ── Kachelraster
        │
        ▼
_setDeskletContent() ── ScrollView bei fester Größe; eingeklappt: Leiste (_wrapCollapsed)
        │
        ▼
_schedulePanelSizeSync()    Akteur = sichtbare Fläche (feste Größe: max-width/max-height)
```

## Besonderheiten, die man kennen muss

- **Nie `ReloadXlet`:** Bei mehreren Instanzen lädt Cinnamon nur eine neu und
  entfernt die übrigen vom Schreibtisch. Änderungen an `lib/*.js` wirken erst
  nach einem Neustart von Cinnamon.
- **Nie von außen in `<ID>.json` schreiben**, solange Cinnamon läuft. Neue
  Fences (Duplikat, Startaufstellung) bekommen ihre Werte über eine
  Übergabedatei, die die neue Instanz selbst liest.
- **`settings.bindProperty`** schreibt in Cinnamon 6.6 bei jeder Zuweisung an
  eine gebundene Eigenschaft sofort die Einstellung (die Richtung wird
  ignoriert).
- **Titel:** Titelzeile (☰, Name, Suche, Pfeil) und die Leiste eines
  eingeklappten Fence bauen dieselben Bausteine mit denselben Abständen.
- **Randzonen** zum Größe-Ziehen werden an der sichtbaren Fläche gemessen und
  wachsen mit der UI-Skalierung.

## Bekannte technische Schulden

| Thema | Fundstelle | Wirkung |
|---|---|---|
| Private Cinnamon-Funktionen | `_draggable._onButtonPress`, `global.desklet_container` | Können bei einem Cinnamon-Update brechen |
| Größe von `desklet.js` | rund 6000 Zeilen | Neue Funktionen kommen als Modul unter `lib/` |
| Nur X11 | Hilfsskript Doppelklick | Unter Wayland ersetzt durch Super+Umschalt+D |
