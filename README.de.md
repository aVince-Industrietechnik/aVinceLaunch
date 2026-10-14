<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/logo-ondark.png">
    <img src="docs/logo.png" alt="aVinceLaunch" width="440">
  </picture>
</p>

# aVinceLaunch

<p align="center"><b>Ordnen · Finden · Starten</b></p>

**Schlanker Schreibtisch-Organisierer mit Fences und Starter-Gruppen für Linux Mint Cinnamon.**

*[This page in English](README.md)*

aVinceLaunch macht aus gewöhnlichen Verzeichnissen aufgeräumte Gruppen auf dem
Schreibtisch – Programme, Dokumente und Ordner, jede Gruppe eine Fläche, die
dort liegt, wo Du sie hinlegst. Das Programm macht eine Sache und hält sich aus
allem anderen heraus.

> **Stand: Version 0.1.0, veröffentlicht am 14. Oktober 2026** – siehe
> [Release](https://github.com/aVince-Industrietechnik/aVinceLaunch/releases/tag/v0.1.0).
> Das Desklet wird seit September 2026 unter Linux Mint 22.3 mit Cinnamon 6.6.9
> täglich benutzt, derzeit mit neun Fences. Es ist ein Fork von *TheLauncher
> 1.0.3* von MHK924, siehe [THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md). Es
> hat eine eigene UUID und lässt sich neben TheLauncher installieren;
> vorhandene TheLauncher-Gruppen und ihre Reihenfolge werden gelesen, nie
> verändert.

## Was es kann

- **Gruppen (Fences)** – mehrere unabhängige Instanzen auf dem Schreibtisch,
  jede zeigt ein Verzeichnis. Ein weiterer Fence ist einen Klick entfernt:
  *Fence duplizieren*.
- **Startaufstellung** – auf Wunsch neun Fences mit Titel in einem Raster, das
  zum Bildschirm passt, die installierten Programme nach Kategorie
  vorgeschlagen; was wohin kommt, entscheidest Du in einer Vorschau.
- **Programme, Dokumente, Ordner** – alles, was in diesem Verzeichnis liegt,
  erscheint als Kachel, in eigener Reihenfolge oder nach Name, Typ oder Datum
  sortiert; Lieblinge lassen sich vorn anpinnen.
- **Ordnernavigation innerhalb einer Gruppe** – Unterordner an Ort und Stelle
  öffnen, über eine Pfadzeile zurückgehen, ohne den Schreibtisch zu verlassen.
- **Ordner-Portal** – ein Fence kann jeden vorhandenen Ordner zeigen, lokal
  oder auf einer Netzwerkfreigabe, als reine Ansicht: dort wird nichts
  angelegt, geändert oder gelöscht.
- **Symbol-Menü** – einen Eintrag in einen anderen Fence verschieben,
  anpinnen oder in den Papierkorb entfernen; das letzte Verschieben lässt
  sich zurücknehmen.
- **Einrasten und Anordnung** – Fences rasten mit Hilfslinien und gleichen
  Abständen an ihren Nachbarn ein, mit Strg frei platziert. Frühere
  Anordnungen und die ursprüngliche lassen sich zurückholen, alle Fences auf
  einmal ausrichten.
- **Titelzeile, Einklappen, Suche** – eine wählbare Titelzeile, ein Fence lässt
  sich auf seinen Titel einklappen, eine Suche filtert alle Fences.
- **Sperren** – Position, Größe und Inhalt lassen sich einzeln sperren, damit
  nichts verrutscht.
- **Automatische Größe** – Spalten und Breite richten sich nach dem Inhalt,
  wahlweise feste Fenstergröße mit Mausradscrollen.
- **Lesbare Gruppentitel** – der Titel ist der Name des Fence oder seines
  Verzeichnisses, seine Farbe richtet sich nach der Helligkeit des
  Hintergrundbildes dahinter (gewichtete RGB-Luminanz).
- **Neue Programme werden bemerkt** – ein kleiner Wächter bietet neu
  installierte Programme und WebApps zur Einsortierung an (Zusatzpaket).
- **Schreibtisch ein- und ausblenden** – Super+Umschalt+D oder, wenn
  eingeschaltet, ein Doppelklick auf den freien Schreibtisch (X11) blendet
  Gruppen und Desktopsymbole gemeinsam aus, der nächste holt sie zurück
  (Zusatzpaket).
- **Einstellungssicherung** – die letzten fünf Stände der Einstellungen jedes
  Fence werden von selbst aufbewahrt.

## Noch offen

| | |
|---|---|
| Layoutprofile je Monitorlage | Lage der Fences je Bildschirmanordnung und Auflösung – geplant für das erste Update |
| Tabs | mehrere Quellen teilen sich eine Fläche – später, vielleicht |

Einzelheiten in [docs/ROADMAP.md](docs/ROADMAP.md).

## Bewusst nicht enthalten

Kein Wetter, keine Uhr, kein Kalender, kein Pomodoro, kein KI-Assistent, kein
Wallpaper-Katalog, keine Live-Wallpaper, kein Screenshot-Werkzeug, kein
System-Theming, kein Startmenü-Ersatz, kein Cloud-Konto, keine Werbung, keine
Telemetrie.

Andere Cinnamon-Applets können das besser. aVinceLaunch bleibt klein, schnell
und wartbar.

## Voraussetzungen

- Linux Mint mit Cinnamon 6.6 (geprüft 6.6.9; andere Fassungen lässt Cinnamon nicht zu); X11-Sitzung oder Wayland-Sitzung
  (geprüft mit Cinnamon 6.6 „on Wayland (Experimental)“)
- Python 3 mit GTK-3-Anbindung (auf Mint vorhanden)

## Zusatzpaket (optional)

Das Desklet aus Cinnamon Spices läuft für sich allein. Die
**aVinceLaunch-Helfer** sind ein eigener Download
(`aVinceLaunch-Helfer-0.1.0.tar.gz` auf der Release-Seite bei GitHub) mit
Installations- und Deinstallationsskript – nur in die eigenen Ordner, nie als
root, mit Sicherung von allem, was sie ersetzen:

- der Programm-Wächter (neues Programm → in welchen Fence?),
- Super+Umschalt+D „Schreibtisch frei“ (X11 und Wayland),
- „In einen Fence verschieben …“ im Kontextmenü des Schreibtischs (Nemo),
- wahlweise der Doppelklick auf den freien Schreibtisch (nur X11, hört nur
  Maustasten; braucht `python3-xlib`).

Sie brauchen `zenity` (bei Mint dabei). Einzelheiten:
[scripts/README.de.md](scripts/README.de.md).

## Aufbau des Repositories

```
Desklet/     das Cinnamon-Desklet selbst (JavaScript, Python-Einstellungsseiten, Hilfe, Übersetzung)
scripts/     das optionale Zusatzpaket: Helfer, Installation, Übersetzung, Paketbau;
             build-spices.py baut Ordner und Zip für Cinnamon Spices
spices/      info.json und README.md für die Seite bei Cinnamon Spices
docs/        Architektur, Entwicklung, Roadmap, Herkunftsnachweis
branding/    Logo- und Icon-Quellen, Farbpalette, Asset-Generator
tests/       Offline-Tests (ohne laufendes Cinnamon), Syntaxprüfung, Prüfliste
```

Wie man am Code arbeitet: [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md).

## Unterstützung

aVinceLaunch ist kostenlos und vollständig. Es gibt keine Bezahlversion,
kein Abonnement und keine Funktion, die hinter einer Zahlung
zurückgehalten wird – alles hier Beschriebene steckt in der Fassung,
die Du herunterladen kannst.

Wenn es Dir nützt und Du die Weiterentwicklung unterstützen möchtest,
freut mich das. Es ist vollkommen freiwillig und ändert nichts am
Programm. aVinceLaunch baut auf TheLauncher von MHK924 auf; eine
Unterstützung gilt der Weiterentwicklung von aVinceLaunch.

**[aVinceLaunch auf Ko-fi unterstützen](https://ko-fi.com/avince)**

Im Programm selbst ist davon keine Rede: keine Einblendungen, keine
Erinnerungen.

## Lizenz

`GPL-3.0-only` für die eigene Arbeit von aVinceLaunch. Der übernommene
TheLauncher-Code wurde unter MIT bezogen; dieser Vermerk bleibt in
[THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md) erhalten und liegt zusammen mit
dem GPL-Text auch im Desklet-Ordner. TheLauncher selbst baut auf
*Quick Links - Launcher* von NotSirius-A auf; auch diese Nennung bleibt erhalten.

Herzlichen Dank an MHK924 für TheLauncher und die freundliche Erlaubnis,
darauf aufzubauen.

Markenquellen und ihre Erzeugung: [`branding/`](branding/).

Urheber: Angelo Vincenti – aVince Industrietechnik.
Schwesterprojekt: [aVincePulse](https://github.com/aVince-Industrietechnik/aVincePulse).
