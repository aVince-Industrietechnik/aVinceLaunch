# aVinceLaunch-Helfer (Zusatzpaket)

Das Desklet aus Cinnamon Spices läuft für sich allein. Diese **optionalen**
Helfer ergänzen es um Dinge, die ein Desklet nicht selbst kann:

| Helfer | Was er tut | Start |
|---|---|---|
| **Programm-Wächter** (`launcher-watch`) | Erkennt neu installierte Programme und WebApps und fragt, in welchen Fence sie sollen – mit Vorschlag | Autostart, läuft im Hintergrund |
| **Schreibtisch frei** (`desktop-clean-toggle`, Super+Umschalt+D) | Blendet alle Fences und die Schreibtischsymbole aus und wieder ein | Tastenkürzel (X11 und Wayland) |
| **In einen Fence verschieben …** (Nemo-Aktion, `launcher-move`) | Rechtsklick auf ein Programmsymbol auf dem Schreibtisch → in einen Fence | Kontextmenü des Schreibtischs |
| **Doppelklick** (`desktop-doubleclick`, optional) | Doppelklick auf den freien Schreibtisch = Schreibtisch frei | Autostart, **nur X11**, hört **nur Maustasten** |
| `launcher-add` | Ein vorhandenes Programm von Hand einsortieren: `launcher-add "Name" [ORDNER]` | Terminal |

Texte englisch und deutsch (je nach Systemsprache).

## Installieren

Voraussetzungen: Linux Mint / Cinnamon mit dem Desklet aVinceLaunch, `zenity`
(bei Mint vorhanden). Für den Doppelklick zusätzlich `python3-xlib`.

```bash
tar xzf aVinceLaunch-Helfer-0.1.0.tar.gz
cd aVinceLaunch-Helfer-0.1.0
./install.sh --check      # nur anzeigen, was passieren würde
./install.sh
```

Das Skript fragt nach dem **Doppelklick** (Standard: nein) und nach dem
**Tastenkürzel Super+Umschalt+D** (Standard: ja; wird nur eingerichtet, wenn
es frei ist). Ohne Rückfragen: `--yes`, dazu wahlweise `--doubleclick`,
`--no-doubleclick`, `--shortcut`, `--no-shortcut`.

Installiert wird nur in die eigenen Ordner, nie als root:

- `~/.local/bin/` – die Helfer;
- `~/.local/share/nemo/actions/` – die Nemo-Aktion;
- `~/.local/share/locale/de/LC_MESSAGES/` – die deutsche Übersetzung;
- `~/.config/autostart/` – Wächter (und Doppelklick, wenn gewählt);
- `~/.local/share/avincelaunch-helfer/` – Liste der installierten Dateien
  (`installiert.json`), **Sicherung** aller ersetzten Dateien
  (`sicherung-<Zeit>/`) und das Deinstallationsskript.

Ein laufender Wächter oder Doppelklick wird beendet und mit der neuen Fassung
neu gestartet. Eine erneute Installation (Update) geht genauso.

## Entfernen

```bash
~/.local/share/avincelaunch-helfer/uninstall.sh --check   # nur anzeigen
~/.local/share/avincelaunch-helfer/uninstall.sh
~/.local/share/avincelaunch-helfer/uninstall.sh --restore # und die vorher ersetzten Dateien zurück
```

Entfernt wird nur, was die Installation angelegt hat; das eigene Tastenkürzel
wird herausgenommen. Ist der Schreibtisch gerade „frei“, werden Fences und
Symbole vorher wieder eingeblendet. **Bleiben** deine Regeln
(`rules.json`), der Zustand des Wächters, die Fences und ihre Ordner sowie die
Sicherungen.

## Schreibtisch frei (Super+Umschalt+D, Doppelklick)

- Der Zustand steht in einer Markierung
  (`~/.local/state/avincelaunch/schreibtisch-frei`). Alle Fences beobachten
  sie und blenden sich selbst aus und ein – kein Eingriff in Cinnamon von
  außen. Der Zustand **bleibt**, auch nach einem Neustart von Cinnamon und
  nach neuer Anmeldung, bis zum nächsten Umschalten.
- Die Schreibtischsymbole schaltet Nemo (`org.nemo.desktop`). Ihre
  Anordnung wird nur gemerkt, wenn die Helfer sie ausgeblendet haben; hast du
  die Symbole selbst ausgeschaltet, bleibt das so.
- Das Kürzel wirkt auch ohne einen einzigen Fence.
- Von Hand: `desktop-clean-toggle` (umschalten), `--hide`, `--show`,
  `--status`. Kürzel: `desktop-clean-shortcut --check` / `--remove`.
- **Doppelklick (nur X11):** Unter Wayland darf kein Programm Klicks auf dem
  Schreibtisch mitlesen; dort beendet er sich sofort – dann gilt
  Super+Umschalt+D. Er abonniert über XInput2 **nur Maustasten** (keine
  Tasten) und startet keine Hilfsprogramme. Auf einem Fence oder einem
  Schreibtischsymbol schaltet er nie um; die Flächen der Fences meldet das
  Desklet selbst (`$XDG_RUNTIME_DIR/avincelaunch/fences.json`).

## Programm-Wächter

- Neue Programme in allen Programmordnern des Startmenüs (eigene, System,
  Flatpak, Snap). Was beim ersten Start schon da ist, gilt als gesehen.
- Angeboten werden die Fences auf dem Schreibtisch (ohne Portale und ohne
  Fences mit gesperrtem Inhalt). Eine Verknüpfung wird nur **neu** angelegt,
  nie überschrieben, nie halb.
- Deinstallierte Programme werden nicht automatisch aus den Fences entfernt.
- Der Wächter gehört zu deiner Anmeldesitzung und endet beim Abmelden. Ohne
  Anmeldesitzung gestartet (z. B. als systemd-Dienst) ist er an keine
  Sitzung gebunden – vorgesehen ist der Autostart.
- Protokoll: `~/.local/share/thelauncher-watcher/watcher.log`.

### Vorschlag (Regeln)

Ohne eigene Regeln fragt der Wächter ohne Vorauswahl. Beispielregeln passend
zur Startaufstellung des Desklets (englische und deutsche Ordnernamen) legt an:

```bash
launcher-watch --write-rules     # überschreibt nie eine vorhandene rules.json
```

Die Regeln stehen in `~/.config/avincelaunch/rules.json`:

```json
{
  "version": 1,
  "mode": "suggest",
  "rules": [
    { "if": { "name": "Syncthing" },      "then": "Tools" },
    { "if": { "categories": "Graphics" }, "then": ["Graphics_Photos", "Grafik_Fotos"] }
  ]
}
```

- `mode`: `suggest` (Vorschlag, Standard), `ask` (ohne Vorschlag), `off`
  (nicht fragen, neue Programme still als gesehen vermerken).
- `if`: `categories`, `name` (Teil des Namens), `exec` (Teil des
  Programmaufrufs), `file` (Teil des Dateinamens). Alle angegebenen müssen
  zutreffen; ein Wert darf eine Liste sein, dann genügt einer.
- `then`: Ordnername eines Fence (Groß/klein egal) oder eine **Liste** davon –
  der erste vorhandene gilt. Gibt es keinen, wird die Regel übersprungen.
- Die **erste** zutreffende Regel gewinnt.
- Prüfen ohne Dialog: `launcher-watch --suggest DATEI.desktop`,
  `launcher-watch --check` (alle Programme, mit Trefferquote).

## In einen Fence verschieben … (Nemo)

Die Aktion steht im Kontextmenü des Schreibtischs bei allen Dateien – Nemo
kann sie dort nicht auf Programmsymbole beschränken. Andere Dateien bleiben
mit einem ruhigen Hinweis liegen. Gibt es im Fence schon einen Eintrag
gleichen Namens, wird nichts überschrieben; angeboten wird, das Symbol nur
vom Schreibtisch zu entfernen (Papierkorb).

## Lizenz

GPL-3.0-only, siehe `LICENSE`. Teil von aVinceLaunch.
