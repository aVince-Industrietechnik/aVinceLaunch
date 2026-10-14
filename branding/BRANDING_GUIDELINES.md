# aVinceLaunch – Branding-Richtlinien

Stand: 30.09.2026 · Technische Kurzfassung, keine Marketingbroschüre.

Die freigegebenen Vorlagen bewahrt der Autor auf; sie sind nicht Teil des
Repositories. Die SVG-Quellen in `branding/svg/` sind daraus abgemessen, alle
Bilddateien daraus jederzeit reproduzierbar über `branding/build-branding.py`.

---

## 1. Markenidee

aVinceLaunch organisiert den Schreibtisch in Bereiche und startet daraus
Programme, Dateien und Ordner.

| Element | Bedeutung |
|---|---|
| Raster aus Kacheln | die Fences – geordnete Bereiche |
| Pfeil nach rechts oben | Starten, Zugriff, Bewegung |
| Farbverlauf grün → blaugrau | von aktiv und im Zugriff hin zu ruhig abgelegt |
| dunkler, abgerundeter Träger | Schreibtisch, auf dem alles liegt |

Markenbotschaft: **Organize · Access · Launch**

---

## 2. Aufbau des Icons

Alle Maße im 1024er-Raster (das SVG hat `viewBox="0 0 1024 1024"`).

```
┌──────────────────────────────── 1024 ───┐
│  152                                    │  Träger: abgerundetes Quadrat
│   ┌────────┐ ┌──┐      ╔═══════╗        │  Eckradius 221
│   │ R1C1   │ │  │      ║ Pfeil ║        │
│   │        │ │  │      ╚═══╗   ║        │  Kacheln: Eckradius 34
│   └────────┘ └──┘       ╲  ║   ║        │
│   ┌────────┐ ┌──────╮    ╲ ╚═══╝        │  R2C2 hat oben rechts eine
│   │ R2C1   │ │ R2C2 │  ┌──────┐         │  Kerbe, durch die der
│   └────────┘ └──────┘  │ R2C3 │         │  Pfeilschaft läuft
│   ┌────────┐ ┌──────┐  └──────┘         │
│   │ R3C1   │ │ R3C2 │  ┌──────┐         │
│   └────────┘ └──────┘  │ R3C3 │         │
└─────────────────────────────────────────┘
```

Feste Werte:

| Element | Wert |
|---|---|
| Eckradius Träger | 221 (21,6 % der Kantenlänge) |
| Eckradius Kacheln | 34 |
| Balkenstärke Pfeil | 91 |
| Eckradius Pfeilkopf | 26 |
| Randabstand links/oben | 152 / 176 |

---

## 3. Aufbau des Logos

| Teil | Regel |
|---|---|
| Wortmarke | `aVince` in Dunkel, `Launch` in Grün – **nie** umgekehrt, nie beide gleich |
| Abstand Icon ↔ Wortmarke | 70 Einheiten bei einer Icongröße von 300 (also rund 23 %) |
| Schutzraum | ringsum mindestens die halbe Icongröße frei lassen |
| Unterzeile | Versalien, gesperrt (22 % der Schriftgröße), nur unter der Wortmarke |

Die Wortmarke ist in den SVG-Dateien **als Pfad** hinterlegt. Es wird keine
Schrift benötigt, und die Darstellung ist auf jedem Rechner identisch.

Gesetzt wurde sie mit **Ubuntu Bold** – die Hausschrift von Linux Mint und
die nächstliegende verfügbare Entsprechung zur Vorlage. Die Vorlage selbst
ist gezeichnete Schrift, keine lizenzierte Schriftfamilie.

---

## 4. Farben

| Rolle | HEX | RGB | HSL |
|---|---|---|---|
| Primary Dark | `#141C22` | 20, 28, 34 | 206°, 26 %, 11 % |
| Primary Green | `#2BBB33` | 43, 187, 51 | 123°, 63 %, 45 % |
| Arrow Light | `#A8F348` | 168, 243, 72 | 85°, 87 %, 62 % |
| Arrow Deep | `#45EE3D` | 69, 238, 61 | 118°, 84 %, 59 % |
| Mint | `#3AC989` | 58, 201, 137 | 153°, 55 %, 51 % |
| Teal | `#2E8F80` | 46, 143, 128 | 171°, 51 %, 37 % |
| Secondary Dark | `#325563` | 50, 85, 99 | 197°, 33 %, 29 % |
| Light Neutral | `#F2F4F5` | 242, 244, 245 | 200°, 12 %, 95 % |
| White | `#FFFFFF` | 255, 255, 255 | 0°, 0 %, 100 % |
| Wordmark Dark | `#18242C` | 24, 36, 44 | 204°, 29 %, 13 % |
| Wordmark Light (auf Dunkel) | `#E8EDF0` | 232, 237, 240 | 202°, 22 %, 93 % |

Verläufe im Icon:

| Fläche | von | nach |
|---|---|---|
| Träger | `#1E272E` | `#070F15` |
| Pfeil | `#A8F348` | `#45EE3D` |
| Kachel oben links | `#9DF157` | `#45D071` |
| Kachel unten rechts | `#386B72` | `#274151` |

---

## 5. Mindestgrößen

| Verwendung | Mindestgröße |
|---|---|
| App-Icon farbig | 16 px |
| Icon monochrom im Panel | 16 px |
| Logo waagerecht ohne Unterzeile | 120 px Breite |
| Logo waagerecht mit Unterzeile | 240 px Breite |
| Logo gestapelt | 96 px Breite |

Unter 240 px Breite die Unterzeile weglassen – sie wird sonst unleserlich.

---

## 6. Hell, Dunkel, Monochrom

| Variante | Wofür | Datei |
|---|---|---|
| **Color** | Standard, dunkler Träger | `ICONS/COLOR/` |
| **Light** | helle Oberflächen; Kacheln neutral grau, Pfeil grün | `ICONS/LIGHT/` |
| **Dark** | sehr dunkle Oberflächen; Träger etwas aufgehellt, damit der Umriss sichtbar bleibt | `ICONS/DARK/` |
| **Monochrome Light** | helle Form auf dunklem Grund, z. B. Panel im dunklen Thema | `ICONS/MONOCHROME/` |
| **Monochrome Dark** | dunkle Form auf hellem Grund | `ICONS/MONOCHROME/` |
| **Small** | 16–32 px: gleiche Geometrie, flächige Farben, keine Kerbe | `ICONS/SMALL/` |

Zur kleinen Fassung: Eine stärkere Vereinfachung (2×2-Raster) wurde geprüft
und **verworfen** – sie war nicht besser lesbar und verlor den
Markencharakter. Vereinfacht sind nur Verläufe, Kerbe und Eckradien.

---

## 7. Dateinamen

```
aVinceLaunch_Icon_Color_<Größe>.png
aVinceLaunch_Icon_Light_<Größe>.png
aVinceLaunch_Icon_Dark_<Größe>.png
aVinceLaunch_Icon_Monochrome_Light_<Größe>.png
aVinceLaunch_Icon_Monochrome_Dark_<Größe>.png
aVinceLaunch_Icon_Small_<Variante>_<Größe>.png

aVinceLaunch_Logo_Horizontal[_Tagline][_OnDark]_<Breite>.png
aVinceLaunch_Logo_Stacked[_Tagline][_OnDark]_<Breite>.png

aVinceLaunch_Icon[_Variante].svg
aVinceLaunch_Logo_<Anordnung>[_Tagline][_OnDark].svg
aVinceLaunch_Wordmark[_OnDark].svg
```

---

## 8. Einsatz in Cinnamon

| Zweck | Datei | Größe |
|---|---|---|
| Desklet-Symbol in der Verwaltung | `CINNAMON/icon.png` | 128 px |
| Panel/symbolisch, helles Thema | `CINNAMON/panel/avincelaunch-symbolic-dark-*.png` | 16–48 px |
| Panel/symbolisch, dunkles Thema | `CINNAMON/panel/avincelaunch-symbolic-light-*.png` | 16–48 px |
| Anwendungsstarter, Dateimanager | `CINNAMON/hicolor/avincelaunch-*.png`, `avincelaunch.svg` | 48–256 px + SVG |

Cinnamon skaliert PNG-Symbole nicht besonders gut. Deshalb für jede benötigte
Größe die passende Datei verwenden statt eine große herunterzurechnen.

**Noch nicht eingebaut:** Kein produktives Desklet-Verzeichnis, keine UUID und
keine Cinnamon-Konfiguration wurden für das Branding verändert.

---

## 9. Einsatz in GitHub

| Zweck | Datei |
|---|---|
| README, helles Thema | `GITHUB/aVinceLaunch_README_Logo_880.png` |
| README, dunkles Thema | `GITHUB/aVinceLaunch_README_Logo_OnDark_880.png` |
| Social Preview (Repository-Einstellungen) | `GITHUB/aVinceLaunch_Social_Preview_1280x640.png` |
| Repository-Symbol | `GITHUB/aVinceLaunch_Repo_Icon_512.png`, `_128.png` |
| Wortmarke frei stehend | `GITHUB/aVinceLaunch_Wordmark_600.png` |

Für ein README, das in beiden GitHub-Themen funktioniert:

```html
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/logo-ondark.png">
  <img src="docs/logo.png" alt="aVinceLaunch" width="440">
</picture>
```

---

## 10. Richtig und falsch

**Richtig**

- Icon immer im Seitenverhältnis 1:1
- Logo nur als Ganzes verschieben, nie Teile einzeln
- auf unruhigem Hintergrund die Fassung mit Träger verwenden
- monochrome Fassung nutzen, wo das System nur eine Farbe erlaubt

**Falsch**

- `aVince` grün und `Launch` dunkel einfärben
- Icon verzerren, drehen oder beschneiden
- eigene Schatten oder Leuchteffekte hinzufügen
- Wortmarke in einer anderen Schrift neu setzen
- farbiges Icon auf gleichfarbig grünem Grund platzieren
- Unterzeile unter 240 px Logobreite verwenden

---

## 11. Erzeugung

```bash
python3 branding/build-branding.py [ZIELORDNER]
```

Das Skript schreibt **ausschließlich** in den Zielordner (Vorgabe:
`branding/build/`) und erzeugt ihn jedes Mal neu. Benötigt werden nur
Bordmittel von Linux Mint: `python3`, `python3-gi` (GdkPixbuf mit
librsvg-Loader) und `python3-cairo`. Es wird nichts installiert.
