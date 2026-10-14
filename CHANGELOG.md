# Changelog

All notable changes to aVinceLaunch. Newest first.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versions follow [Semantic Versioning](https://semver.org/).

## [0.1.0] – 2026-10-14

First public version. aVinceLaunch is a fork of *TheLauncher 1.0.3* by MHK924
(see [THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md)) with a new UUID,
`avincelaunch-desklet@avince`, so both can be installed side by side.

### Added

- **Starter layout** – offered in the quick start and in the fence menu:
  nine titled fences (INTERNET, COMMUNICATION, OFFICE, GRAPHICS & PHOTOS,
  MULTIMEDIA, GAMES, DEVELOPMENT, TOOLS, SYSTEM; translated) in a 3 × 3 grid
  that fits the screen and the UI scale. Installed applications are suggested
  by category in a preview where they can be unticked or moved to another
  fence; Cinnamon's settings pages are not suggested. *Remove starter
  layout…* undoes it and only moves the folders into a backup.
- **Duplicate fence** – same look, a folder of its own, placed next to the
  original.
- **Folder portal** – a fence can show any existing folder, local or on a
  network share, as a pure view; nothing is created, changed or deleted there.
- **Item menu** – move an item to another fence, pin it to the front, remove
  it to the trash; the last move can be undone.
- **Resize with the mouse** at the right edge, the bottom edge and the corner;
  the edges grow with the UI scale.
- **Snapping and arrangement** – fences snap to their neighbours with guide
  lines and equal gaps; recent arrangements and the original one can be
  restored; *Align all fences*.
- **Title row, collapsing, search** – a title row with menu button (☰) and
  collapse arrow, on by default for new fences; a collapsed fence keeps a bar
  as wide as the fence; one search filters all fences.
- **Separate locks** for position, size and content.
- **Quick start** and a detailed **help page** (English and German).
- **Settings backup** – recent states of each fence's settings are kept;
  *Remove this fence…* asks first, names the fence and keeps a copy.
- **German translation** of the desklet, its dialogs and the help.

### Changed (compared with TheLauncher 1.0.3)

- Own name, icon, help and about dialog; settings and data live under
  `~/.config/avincelaunch` and `~/.local/share/avincelaunch`.
- A new fence creates its own link folder if it is missing – but never on a
  base folder that is not available (for example a network share that is not
  mounted).
- A base folder on a network drive is read in the background with a time
  limit, like a folder portal – a NAS that hangs no longer stops the desktop.
- Application tooltips show the description (`Comment=`) below the full
  name – it was always empty in TheLauncher 1.0.3.
- Messages wrap in fixed-size fences instead of being cut off.
- Damaged settings or layout files are kept and backed up instead of being
  replaced silently.
- Works in Cinnamon's Wayland session (tested with Cinnamon 6.6); the desktop
  double-click helper is X11 only.

### Helper scripts

Optional helpers – a watcher that offers newly installed applications for a
fence, Super+Shift+D to show and hide the desktop, a Nemo action and the
desktop double-click – are published as a separate download with the release
(`aVinceLaunch-Helfer-0.1.0.tar.gz`), not through Cinnamon Spices. It installs
into the user's own folders with a backup and an uninstall script, speaks
English and German, hides the fences through a marker file the desklet watches
(no `org.Cinnamon.Eval`), and the double-click listens to mouse buttons only.
`launcher-add` also finds applications by the translated name shown in the
menu.
