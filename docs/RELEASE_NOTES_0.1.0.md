# aVinceLaunch 0.1.0

**Organize · Access · Launch** – the first public version of aVinceLaunch, a
lightweight desktop organizer with fences and launcher groups for Linux Mint
Cinnamon.

aVinceLaunch is a fork of *TheLauncher 1.0.3* by MHK924 with its own UUID,
`avincelaunch-desklet@avince`, so both can be installed side by side; existing
TheLauncher groups and their order are read, never changed. Many thanks to
MHK924 for TheLauncher and for kindly allowing it to be built upon.

## Highlights

- **Starter layout** – nine titled fences in a grid that fits your screen,
  with your installed applications suggested by category in a preview.
- **Duplicate fence**, **folder portal** (a read-only view of any existing
  folder, local or on a network share) and an **item menu** (move to another
  fence, pin, remove to the trash, undo the last move).
- **Resize with the mouse**, **snapping** with guide lines, restorable
  arrangements, *Align all fences*.
- **Title row, collapsing, one search for all fences**, separate **locks** for
  position, size and content.
- **Titles that stay readable** on any wallpaper, **settings backup** for each
  fence, **quick start** and a detailed **help page**.
- **English and German**; works in the X11 session and in Cinnamon's Wayland
  session.

The full list is in [CHANGELOG.md](../CHANGELOG.md).

## Installation

**Desklet** – from Cinnamon Spices: *System Settings → Desklets → Download*,
search for *aVinceLaunch*, install, then *Manage → +* to add it to the
desktop. The quick start opens once by itself.

**Add-on package (optional)** – `aVinceLaunch-Helfer-0.1.0.tar.gz`, attached
to this release: the program watcher, Super+Shift+D "desktop free", *Move to a
fence…* in the desktop's context menu, and optionally the double-click on the
free desktop (X11 only). It installs into your own folders only, never as
root, with a backup and an uninstall script:

```bash
tar xzf aVinceLaunch-Helfer-0.1.0.tar.gz
cd aVinceLaunch-Helfer-0.1.0
./install.sh --check
./install.sh
```

Details: [scripts/README.md](../scripts/README.md).

## Requirements

- Linux Mint with Cinnamon 6.6 (tested with 6.6.9 on Linux Mint 22.3)
- Python 3 with GTK 3 bindings (present on Mint by default)
- Add-on package: `zenity` (part of Mint); for the double-click also
  `python3-xlib`

## Known limits

- The desktop double-click (add-on package) works under X11 only;
  Super+Shift+D works in both sessions.
- Fence positions are not yet kept per monitor setup – layout profiles are
  planned for the first update ([ROADMAP](ROADMAP.md)).

## Licence

GPL-3.0-only for aVinceLaunch's own work; the inherited TheLauncher code
keeps its MIT notice ([THIRD-PARTY-NOTICES.md](../THIRD-PARTY-NOTICES.md)).
TheLauncher itself started from *Quick Links - Launcher* by NotSirius-A.

aVinceLaunch is free and complete. If you would like to support its further
development: [ko-fi.com/avince](https://ko-fi.com/avince) – entirely
voluntary.
