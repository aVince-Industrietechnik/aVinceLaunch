# aVinceLaunch helpers (add-on package)

The desklet from Cinnamon Spices works on its own. These **optional** helpers
add things a desklet cannot do by itself:

| Helper | What it does | Start |
|---|---|---|
| **Program watcher** (`launcher-watch`) | Notices newly installed programs and web apps and asks which fence they should go into – with a suggestion | autostart, runs in the background |
| **Desktop free** (`desktop-clean-toggle`, Super+Shift+D) | Hides all fences and the desktop icons, and shows them again | keyboard shortcut (X11 and Wayland) |
| **Move to a fence…** (Nemo action, `launcher-move`) | Right-click a launcher on the desktop → into a fence | desktop context menu |
| **Double-click** (`desktop-doubleclick`, optional) | Double-click on the free desktop = desktop free | autostart, **X11 only**, listens to **mouse buttons only** |
| `launcher-add` | Sort an installed program in by hand: `launcher-add "Name" [FOLDER]` | terminal |

Texts in English and German (following the system language).

## Install

Requirements: Linux Mint / Cinnamon with the aVinceLaunch desklet, `zenity`
(part of Mint). For the double-click also `python3-xlib`.

```bash
tar xzf aVinceLaunch-Helfer-0.1.0.tar.gz
cd aVinceLaunch-Helfer-0.1.0
./install.sh --check      # only show what would happen
./install.sh
```

The script asks about the **double-click** (default: no) and the **shortcut
Super+Shift+D** (default: yes; set up only if it is free). Without questions:
`--yes`, plus `--doubleclick`, `--no-doubleclick`, `--shortcut`,
`--no-shortcut` as you like.

Everything goes into your own folders, never as root:

- `~/.local/bin/` – the helpers;
- `~/.local/share/nemo/actions/` – the Nemo action;
- `~/.local/share/locale/de/LC_MESSAGES/` – the German translation;
- `~/.config/autostart/` – watcher (and double-click, if chosen);
- `~/.local/share/avincelaunch-helfer/` – list of installed files
  (`installiert.json`), a **backup** of every file it replaced
  (`sicherung-<time>/`) and the uninstall script.

A running watcher or double-click is stopped and restarted with the new
version. Installing again (update) works the same way.

## Remove

```bash
~/.local/share/avincelaunch-helfer/uninstall.sh --check    # only show
~/.local/share/avincelaunch-helfer/uninstall.sh
~/.local/share/avincelaunch-helfer/uninstall.sh --restore  # and put back the files it had replaced
```

Only what the installation created is removed; its own shortcut is taken out.
If the desktop is "free" at that moment, fences and icons are shown first.
**Kept:** your rules (`rules.json`), the watcher state, the fences and their
folders, and the backups.

## Desktop free (Super+Shift+D, double-click)

- The state is a marker file (`~/.local/state/avincelaunch/schreibtisch-frei`).
  All fences watch it and hide or show themselves – nothing reaches into
  Cinnamon from outside. The state **stays**, also after a Cinnamon restart
  and a new login, until the next toggle.
- The desktop icons are Nemo's (`org.nemo.desktop`). Their layout is only
  remembered when the helpers hid them; if you switched the icons off
  yourself, that stays.
- The shortcut also works without a single fence.
- By hand: `desktop-clean-toggle` (toggle), `--hide`, `--show`, `--status`.
  Shortcut: `desktop-clean-shortcut --check` / `--remove`.
- **Double-click (X11 only):** under Wayland no program may watch clicks on
  the desktop; it exits there at once – use Super+Shift+D. Through XInput2 it
  subscribes to **mouse buttons only** (no keys) and starts no helper
  programs. It never toggles on a fence or a desktop icon; the desklet itself
  reports the fence areas (`$XDG_RUNTIME_DIR/avincelaunch/fences.json`).

## Program watcher

- New programs in all program folders of the menu (own, system, Flatpak,
  Snap). Whatever is there at the first start counts as seen.
- It offers the fences on the desktop (no portals, no fences with locked
  content). A launcher is only ever **created**, never overwritten, never
  half-written.
- Uninstalled programs are not removed from the fences automatically.
- The watcher belongs to your login session and stops when you log out.
  Started outside a login session (e.g. as a systemd service) it is bound to
  no session – autostart is the intended way.
- Log: `~/.local/share/thelauncher-watcher/watcher.log`.

### Suggestions (rules)

Without rules of your own the watcher asks without a preselection. Example
rules that match the desklet's starter layout (English and German folder
names):

```bash
launcher-watch --write-rules     # never overwrites an existing rules.json
```

The rules live in `~/.config/avincelaunch/rules.json`:

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

- `mode`: `suggest` (default), `ask` (no suggestion), `off` (do not ask,
  mark new programs as seen silently).
- `if`: `categories`, `name` (part of the name), `exec` (part of the
  command), `file` (part of the file name). All given must match; a value may
  be a list, then one of them is enough.
- `then`: folder name of a fence (case does not matter) or a **list** of
  them – the first existing one wins. If none exists, the rule is skipped.
- The **first** matching rule wins.
- Check without a dialog: `launcher-watch --suggest FILE.desktop`,
  `launcher-watch --check` (all programs, with hit rate).

## Move to a fence… (Nemo)

The action is in the desktop's context menu for all files – Nemo cannot limit
it to launchers there. Other files stay where they are, with a calm notice.
If the fence already has an entry of the same name, nothing is overwritten;
you are offered to remove the launcher from the desktop only (trash).

## For developers

- Build the package: `python3 scripts/build-helfer-paket.py` → `dist/`.
- Translation: `bash scripts/po/makepot.sh`, then update `scripts/po/de.po`.
- Tests: `bash tests/alle-tests.sh` (among them `v3a-test.*`, `v3b-test.py`,
  `v3c-test.py`).

## License

GPL-3.0-only, see `LICENSE`. Part of aVinceLaunch.
