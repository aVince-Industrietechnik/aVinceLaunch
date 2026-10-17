# Prüfliste

Nach **jeder** Änderung am Desklet oder an den Hilfsskripten vollständig
durchgehen – nicht stichprobenartig. Sie ist kurz genug.

Datum: ________  Rechner: ________  Änderung: ________________

## 1. Vor dem Einspielen

| | Prüfung | ok |
|---|---|---|
| 1.1 | Sicherung vor dem Einspielen: Desklet-Ordner, `~/.config/cinnamon/spices/avincelaunch-desklet@avince/`, `~/.config/avincelaunch/`, Gruppenordner, `enabled-desklets` (mit Prüfsummen) | ☐ |
| 1.2 | `bash tests/alle-tests.sh` meldet „Alles bestanden.“ (Syntaxprüfung + alle Offline-Tests, siehe 1a) | ☐ |
| 1.3 | Rückkopier-Befehl ist notiert und getestet | ☐ |

## 1a. Offline-Tests (Übersicht)

Alle laufen ohne Cinnamon in eigenen Wegwerfordnern; `tests/alle-tests.sh`
startet sie mit `LANGUAGE=C`, ungültiger D-Bus-Adresse und ohne
`__pycache__`. Greift die Umleitung eines Tests in seinen Wegwerfordner nicht,
bricht er mit Rückgabewert 2 ab, bevor er etwas schreibt (`tests/umleitung.py`).
Einzeln: `cjs tests/<name>.js` bzw. `python3 tests/<name>.py`.

| Test | prüft | Paket |
|---|---|---|
| `syntax-check.sh` | Python, Shell, JSON, JavaScript auf Syntax – schreibt nichts | – / A9 |
| `snap-engine-test.js` | Einrasten, Abstände, Überlappung (`lib/snapEngine.js`) | AP13b |
| `sort-pin-test.js` | Sortierarten, Anpinnen, unbekannte Sidecar-Felder | AP18-3 |
| `item-actions-test.js` | Verschieben zwischen Fences, Entfernen in den (Wegwerf-)Papierkorb | AP18-1, A9 |
| `fence-clone-test.js` | Fence duplizieren: ID-Wahl, Ordnername, Übergabe, Sicherung | AP18-5 |
| `desktop-link-test.py` | Starter bearbeiten/anlegen (`linkImport.py`), Rückfrage bei Verweis/schreibgeschützt, Name wie im Fence, ohne harte Verweise; `--live` an Kopien | A2, T-A3 |
| `safe-json-test.js` | kaputte Dateien: sichern, melden, nicht überschreiben (JS); ungültiges UTF-8; entfernte kaputte Datei → neu statt Altdatei | A3-1, T-A3 |
| `dialog-files-test.py` | dieselbe Regel im Dialog, atomares Schreiben (Python) | A3-2 |
| `watcher-state-test.py` | Wächter: `state.json` kaputt/fehlt/ohne `apps` → Grundlinie, Kopie je Inhalt einmal | A3-3, T-A1 |
| `watcher-session-test.py` | Wächter an die Sitzung gebunden, nur der Halter der Sperre aus toter Sitzung wird gestoppt, `loginctl`-Fehler = unbekannt | B1b, T-A1 |
| `launcher-add-test.py` | `launcher-add` überschreibt nicht, gesperrte Fences kein Ziel, findet den übersetzten Namen | A7, V5f |
| `shortcut-test.py` | `desktop-clean-shortcut` (Super+Umschalt+D) | AP15b |
| `dialog-list-test.py` | Dialogliste an ihren Ordner gebunden, Rückfrage vor Verwerfen | A4-1 |
| `portal-guard-test.js`, `portal-guard-test.py` | Portal-Schutz, Basisordner nie gesperrt; höchstens ein Einlesen, nach 2 min „nicht erreichbar“ und genau ein weiterer Versuch | A6, BT3 (V2) |
| `base-config-test.js`, `base-config-test.py` | Basisordner nur aus `config.json`, eine Regel überall | A4-2 |
| `dialog-merge-test.py` | Abgleich vor dem Speichern im Cinnamon-Dialog | A4-3 |
| `dialog-rest-test.py` | Dialog-Scan wie Fence-Scan, Schreibfehler abgefangen | A4-4 |
| `s8-1-test.js`, `s8-1-test.py` | Schema-Grenzen, 30 Tage Platz, Papierkorb, Einstellungssicherung (Rotation nach Zeit, Anker, entfernte Fences) | S8-1, T-A3 |
| `s8-2-test.py` | keine persönlichen Namen/Regeln, Beispielregeln | S8-2 |
| `s8-3-test.py` | Programmordner des Wächters (XDG + Snap) | S8-3 |
| `n1-position-test.js` | Strg-frei gesetzter Fence bleibt nach Neustart | N1 |
| `a8-1-test.py` | SPDX-Köpfe, Namen, Dateirechte, Über-Dialog | A8-1 |
| `a8-2-test.py` | Hilfe de/en und Schnellstart | A8-2 |
| `a8-3-test.py` | READMEs, CHANGELOG, `.pot`/`de.po` | A8-3 |
| `p3-1-test.py` | `%` beim Anlegen/Bearbeiten (N2), Über-Dialog-Pfade (N4), Lizenzsatz (N5) | P3-1 |
| `p3-1-test.js` | Dialogliste im Unterordner nicht still ersetzt (N3, `lib/orderListSync.js`) | P3-1 |
| `p3-2-test.js` | Titel-Lasche beim ersten Zeigen bündig, gesperrt aufgeklappt ohne Leiste (N9) | P3-2 |
| `a9-test.py` | Testwerkzeuge selbst: nichts geschrieben, Abbruch bei falscher Umleitung, Übersicht vollständig | A9 |
| `t-a3b-test.js` | „Diesen Fence entfernen …“ statt Cinnamons Eintrag: Rückfrage mit Fence, Ordner und Sicherung, Strg-Klick, beim Symbol ausgeblendet | T-A3b (Teil 2) |
| `n12-test.js` | Eingeklappter Fence nur so hoch wie die Leiste (feste Größe gilt nur ausgeklappt); Platz für Nachbarn bleibt, Größe ziehen gesperrt | N12 (BT6) |
| `t-a1-test.py` | Hilfsskripte legen Verknüpfungen nur neu und nie halb an (auch ohne harte Verweise), melden kaputte Dateien, `rules.json` exklusiv | T-A1 (Teil 2) |
| `n13-test.js` | Fehlender Gruppenordner: Regel zum Anlegen (Standardbasis ja, eigene fehlende Basis nein, nie außerhalb), nur beim Start und im Menü, Meldung mit Maus-Erkennung | N13 (Tower) |
| `n16-test.js` | Meldungen brechen nur bei fester Höhe um (bei „automatisch“ einzeilig, Akteur = sichtbare Fläche); Rand- und Eckzone wachsen mit der UI-Skalierung | N16 (Tower) |
| `n17-raster-test.js` | Startaufstellung: Plätze im Raster 3 × 3 für typische und kleine Bildschirme, belegte Fläche, zwei Bildschirme | N17 |
| `n17-sort-test.py` | Startaufstellung: Programme nach Kategorie, Einstellungsseiten erkannt, Ordnernamen, Verknüpfungen nie überschrieben, eigene fehlende Basis nie angelegt, Verbindung Schnellstart → Dialog → Desklet | N17 |
| `n19-test.js` | Titelzeile ab Werk an; eingeklappte Leiste mit denselben Bausteinen und Abständen wie die Titelzeile (N14); nach dem Ein-/Ausklappen gleich wieder sichtbar, wenn die Maus darüber ist | N19 |
| `t23-lebenszyklus-test.js` | Lebenszyklus mit nachgebautem Cinnamon: Hintergrundarbeit endet vor `destroy`, Einstellungen freigeben, Cinnamons Lage-Kopie nachgezogen, `layout.json` (kaputt nie überschrieben, entfernte Fences vergessen), Sicherung vor dem Einstellungsdialog, Einrichten-Fenster mit Fehlermitschrift | T23, N11 (V2) |
| `v3a-test.js`, `v3a-test.py` | „Schreibtisch frei“ ohne Eval: Markierung, die alle Fences beobachten, Flächen für den Doppelklick (`fences.json`); Umschalter mit gespieltem gsettings (eigenes „Symbole aus“ bleibt, auch ohne Fence); Doppelklick hört nur Maustasten | V3a (B6, T5, T6, P38, P71) |
| `v3b-test.py` | Helfer englisch mit deutscher Übersetzung (Vorlage frisch, `de.po` vollständig, Python und Bash zur Laufzeit); Regeln mit Liste von Ordnern; `rules.example.json` = Startaufstellung en/de | V3b (K9, K2-3) |
| `v3c-test.py` | Zusatzpaket: Archiv (Inhalt, Rechte, keine Benutzerpfade); Installation in Wegwerf-HOME mit Leerzeichen (Autostart gequotet, alte Einträge gesichert und ersetzt, Übersetzung wirkt), Update, Entfernen (freier Schreibtisch wird eingeblendet, Daten bleiben), `--restore` | V3c (P21, E5) |
| `v1-oeffentlich-test.py` | Keine internen Spuren in versionierten Dateien und Commit-Texten (private Ablage, persönliche Gruppennamen, feste Benutzerpfade); Ausnahmen mit Grund und Ende | V1, E2 |
| `v4-spices-test.py` | Spices-Hülle aus `scripts/build-spices.py`: Zip (nur `<uuid>/`, Inhalt = versionierte Desklet-Dateien, Rechte 644/755, Entpacken wie Spices.py), Pull-Request-Ordner nach den Regeln von `validate-spice` (metadata.json nur ASCII, Pflichtdateien, po/), Lizenzangaben | V4 (P19, T0) |
| `v4d-test.js` | Basisordner auf einem Netzlaufwerk: asynchrones Einlesen (Sortierarten, Reihenfolge-Datei, Verweise, mehrere Stapel), Fehler und Abbrechen; Desklet im Netz-Modus ohne synchronen Zugriff beim Einrichten und Anzeigen, eigener Ordner erst nach Antwort, Nachsehen nur bei Änderung neu, Zeitgrenze; lokal mit Ordnerwächter, Anzeige ebenfalls asynchron; Dialoge mit `python3 -B` | V4d |
| `v5b-test.js` | Befunde Tower-Endabnahme: Beschriftungs- und Mindest-Kachelbreite wachsen mit der UI-Skalierung (N24, Methoden aus `desklet.js` bei Skalierung 1 und 2), feste Symbolgröße im Startaufstellungs-Dialog (N20) | V5b |
| `v5f-test.js`, `v5f-test.py` | Befunde W6: Beschreibung im Tooltip aus `Comment=` (N28, Gio `get_description`, auch asynchron), Helfer finden und zeigen den übersetzten Programmnamen wie das Startmenü (N30, `Name[de]` und `X-Ubuntu-Gettext-Domain`, Sprache wie gettext) | V5f |
| `async-io-test.js` | Asynchrone Zugriffe auf die Fence-Ordner: Rückruf nie sofort, Abbrechen ohne Rückruf (auch mitten im Einlesen), `.desktop` aus dem gelesenen Inhalt, Portal ebenso; Dialogliste liest höchstens einen Durchgang zugleich, Wartende ergeben genau einen Folgedurchgang, Zeitgrenze und spätes Ergebnis; Papierkorb-Rückfrage wartet höchstens 3 s; kein doppeltes Verschieben; keine synchronen Zugriffe mehr in `linkScanner.js`, `itemActions.js`, `portalScanner.js` | Async-Umbau |

## 2. Grundfunktion

| | Prüfung | Sollwert | ok |
|---|---|---|---|
| 2.1 | Alle Fences sichtbar | wie vor dem Einspielen (`enabled-desklets` gleich) | ☐ |
| 2.2 | Richtige Gruppe bzw. richtiges Portal je Fence | wie vorher | ☐ |
| 2.3 | Positionen unverändert | wie vorher | ☐ |
| 2.4 | Größen unverändert | wie vorher (Akteur = sichtbare Fläche) | ☐ |
| 2.5 | Spalten | wie vorher | ☐ |
| 2.6 | Reihenfolge der Kacheln unverändert | wie vorher | ☐ |
| 2.7 | Farben und Schrift unverändert | keine sichtbare Änderung | ☐ |
| 2.8 | Programm startet per Einfachklick | startet | ☐ |

## 3. Sonderfunktionen

| | Prüfung | ok |
|---|---|---|
| 3.1 | Hover zeigt den Gruppentitel über der Fläche | ☐ |
| 3.2 | Titel ist auf dem aktuellen Hintergrund lesbar (Luminanz) | ☐ |
| 3.3 | Mausrad scrollt innerhalb einer vollen Gruppe | ☐ |
| 3.4 | Alle Gruppen bleiben gesperrt (`lock-position`) | ☐ |
| 3.5 | Nach Entsperren einer Testinstanz (Rechtsklick → Sperren ▸ Position) lässt sie sich an der Titelzeile ziehen – danach wieder sperren | ☐ |
| 3.6 | Ordnernavigation: Testunterordner öffnet sich im Fence, Zurück funktioniert | ☐ |
| 3.7 | Einstellungsdialog öffnet sich und zeigt die Einträge | ☐ |

## 3a. Größe ändern (AP13a)

| | Prüfung | ok |
|---|---|---|
| 3a.1 | Gesperrter Fence: kein Größen- oder Verschiebezeiger, Größe nicht änderbar, kein Hinweis im Menü | ☐ |
| 3a.2 | Entsperren über das Menü: Hinweis „Größe: Rand oder Ecke ziehen“ erscheint sofort | ☐ |
| 3a.3 | Zeiger an rechtem Rand, unterem Rand, Ecke; Verschiebekreuz über der Titelzeile | ☐ |
| 3a.4 | Breite, Höhe und beides ziehen; Rahmen zeigt Größe und Spalten | ☐ |
| 3a.5 | Wenige Pixel Breite ändern: Spaltenzahl bleibt | ☐ |
| 3a.6 | `Esc` während des Ziehens: Abbruch, Maus sofort frei | ☐ |
| 3a.7 | „Vorherige Größe wiederherstellen“ holt die vorige Größe, zweiter Klick tauscht zurück | ☐ |
| 3a.8 | Nach Cinnamon-Neustart ist die neue Größe noch da | ☐ |
| 3a.9 | Kein Wert genau auf `min`/`max` in den Instanzdateien | ☐ |
| 3a.10 | Zurückscrollen: 2,5 s nach Verlassen sanft nach oben, hält bei Rückkehr der Maus | ☐ |

## 3b. Einrasten und Ränder (AP13b)

| | Prüfung | ok |
|---|---|---|
| 3b.0 | `snap-engine-test.js` in `alle-tests.sh` bestanden (1.2) | ☐ |
| 3b.1 | Verschieben: grüne Linien bei bündiger Kante, gleichem Abstand, Bildschirmrand | ☐ |
| 3b.2 | Fence bleibt schon beim Ziehen 15 px innerhalb der Arbeitsfläche | ☐ |
| 3b.3 | Ablegen auf einem anderen Fence: daneben oder zurück | ☐ |
| 3b.4 | Größe: Rand stoppt vor dem Nachbarn; 360 × 210 erreichbar | ☐ |
| 3b.5 | `Strg`: frei, „FREI (Strg)“, keine Linien, kein Rasterplatzhalter; nach Cinnamon-Neustart steht der Fence genau dort (N1) | ☐ |
| 3b.6 | Nach dem Ablegen: Menü sofort bedienbar, Zeiger normal, kein Neuaufbau im Protokoll | ☐ |
| 3b.7 | Breiter Fence: Menü, Verschieben, Rand auch rechts der letzten Kachel | ☐ |
| 3b.8 | Menü öffnet neben dem Klick, vollständig sichtbar | ☐ |
| 3b.9 | Menü offen → Klick auf Titelzeile/Rand: Menü zu, Ziehen beginnt sofort | ☐ |
| 3b.10 | „Ursprüngliche Größe wiederherstellen“ bei jedem Fence verfügbar | ☐ |
| 3b.11 | **Nach jedem Cinnamon-Update:** interne Stellen noch vorhanden (`deskletManager.deskletChangeKey`, `definitions`, `_draggable._dragOffsetX/_overrideX`, `deskletContainer._dragPlaceholder`) | ☐ |

## 3c. Verlauf und Ausrichten (AP13c)

| | Prüfung | ok |
|---|---|---|
| 3c.1 | Nach Verschieben/Größeändern: Eintrag mit Uhrzeit und passendem Symbol | ☐ |
| 3c.2 | Mehrere Züge innerhalb 60 s: ein Eintrag, Symbole ergänzt | ☐ |
| 3c.3 | Eintrag zurückholen: **gespeicherte** Werte prüfen (`enabled-desklets`, `<ID>.json`), nicht nur die Anzeige | ☐ |
| 3c.4 | „Ursprüngliche Anordnung“ vorhanden und wirksam | ☐ |
| 3c.5 | Ausrichten: leicht verrutscht → zurück; Ausreißer gegen Mehrheit → korrigiert; weit verschoben → bleibt | ☐ |
| 3c.6 | Ohne `Strg` kein Ziehen über Fence oder fremdes Desklet; mit `Strg` frei | ☐ |
| 3c.7 | Tooltip: voller Name, darunter Beschreibung | ☐ |

## 4. Hilfsskripte

| | Prüfung | ok |
|---|---|---|
| 4.1 | `launcher-watch` läuft (`pgrep -af launcher-watch`) | ☐ |
| 4.2 | Protokoll wächst **nicht** im Sekundentakt | ☐ |
| 4.3 | `launcher-add "Name"` sortiert in die gewählte Gruppe ein | ☐ |
| 4.4 | Doppelklick auf freie Fläche blendet Gruppen und Desktopsymbole aus | ☐ |
| 4.5 | Erneuter Doppelklick bringt beides zurück, Positionen unverändert | ☐ |
| 4.6 | `mint-master-backup` läuft durch und enthält die aVinceLaunch-Daten (Gruppenordner, `~/.config/avincelaunch`) | ☐ |

## 4a. Hilfsskripte ohne feste IDs (AP15a)

| | Prüfung | ok |
|---|---|---|
| 4a.1 | Neue Fassung läuft: `pgrep -af desktop-doubleclick` zeigt genau einen Prozess, gestartet nach dem Einspielen | ☐ |
| 4a.2 | Doppelklick auf freie Fläche blendet **alle** Fences und die Desktopsymbole aus; erneuter Doppelklick bringt alles zurück, Positionen unverändert | ☐ |
| 4a.3 | Sperrflächen: Doppelklick **auf** einen Fence (auch zwischen den Kacheln) blendet **nichts** aus | ☐ |
| 4a.4 | Sperrflächen: Doppelklick knapp **neben** einen Fence (mehr als 5 px Abstand) blendet aus | ☐ |
| 4a.5 | Neuer Test-Fence (Desklets → aVinceLaunch → „+“): ID notieren (`gsettings get org.cinnamon enabled-desklets`), sie ist **keine** der vorhandenen IDs | ☐ |
| 4a.6 | Test-Fence wird beim Doppelklick mit ausgeblendet und wieder eingeblendet | ☐ |
| 4a.7 | Doppelklick auf den Test-Fence blendet nichts aus (Sperrfläche wirkt auch für die neue ID). Hinweis: Sperrflächen nutzen `max-width`/`max-height`; ein Fence mit Anpassung „automatisch“ (0 × 0) hat praktisch keine Sperrfläche – das war vor AP15a genauso | ☐ |
| 4a.8 | Test-Fence nur per Rechtsklick auf eine freie Stelle → „Diesen Fence entfernen …“ entfernen, **nie** mit „–“ in der Desklet-Verwaltung (entfernt alle Fences) | ☐ |

## 5. Protokoll

| | Prüfung | Sollwert | ok |
|---|---|---|---|
| 5.1 | `grep -c "JS ERROR" ~/.xsession-errors` | 0 | ☐ |
| 5.2 | Keine neuen Warnungen mit Bezug zum Desklet | – | ☐ |
| 5.3 | Keine dauerhafte CPU-Last durch Desklet oder Watcher (`top`, einige Minuten) | – | ☐ |

## 5a. Wayland-Sitzung (K11)

Nach Änderungen an Ziehen, Größe, Menü, Suche, Tooltip, Titel-Lasche,
Einklappen, Kürzel, Wächter oder Dialog in „Cinnamon on Wayland“ wiederholen.
Erstlauf 09.10.2026 mit einem geführten Selbsttest: alles bestanden außer
W10/W11 (Lasche beim ersten Zeigen nicht bündig, behoben).

| | Prüfung | ok |
|---|---|---|
| 5a.1 | Randzeiger rechts/unten/Ecke (Pfeil mit Balken), Titel → Kreuz; Größe ziehen: Esc bricht ab, 30 s still bricht ab, außen loslassen übernimmt, Maus danach frei | ☐ |
| 5a.2 | Verschieben ohne Strg mit Hilfslinien, mit Strg „FREI (Strg)“; Fence 4 ziehen lässt 40/41 an ihrer Stelle | ☐ |
| 5a.3 | Kontextmenü am Zeiger, Rechtsklick daneben öffnet sofort neu, Linksklick auf Titel zieht sofort | ☐ |
| 5a.4 | Suche: Tippen kommt im Feld an, Enter startet, Esc schließt; Tooltip verschwindet beim Programmstart | ☐ |
| 5a.5 | Verschieben zwischen Fences mit „Rückgängig“ (Meldung und Menü); Titel-Lasche und Aufklappen beim Überfahren bündig, ohne Flackern | ☐ |
| 5a.6 | Super+Umschalt+D aus/ein; Nemo-Aktion am Schreibtischsymbol; Wächter-Dialog erscheint; „Starter bearbeiten“ vorn und modal | ☐ |

## 6. Zweiter Rechner, UI-Skalierung 2, zwei Bildschirme

| | Prüfung | ok |
|---|---|---|
| 6.1 | Neuer Benutzer: Desklet hinzufügen, Schnellstart, Startaufstellung | ☐ |
| 6.2 | Abschnitte 2 bis 5 dort ebenfalls geprüft (Größen und Lagen zählen in Bildpunkten) | ☐ |
| 6.3 | Zwei-Monitor-Anordnung: keine Gruppe verschoben oder außerhalb des Bildes | ☐ |

## 7. Abschluss

| | Prüfung | ok |
|---|---|---|
| 7.1 | Ergebnis als Prüfprotokoll abgelegt | ☐ |
| 7.2 | Dokumentation und `CHANGELOG.md` aktualisiert | ☐ |
| 7.3 | Commit und Push erfolgt | ☐ |
| 7.4 | Sicherung des neuen Stands vorhanden | ☐ |
