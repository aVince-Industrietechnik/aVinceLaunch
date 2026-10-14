<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/logo-ondark.png">
    <img src="docs/logo.png" alt="aVinceLaunch" width="440">
  </picture>
</p>

# aVinceLaunch

<p align="center"><b>Organize · Access · Launch</b></p>

**Lightweight desktop organizer with fences and launcher groups for Linux Mint Cinnamon.**

*[Diese Seite auf Deutsch](README.de.md)*

aVinceLaunch turns ordinary directories into tidy groups on your desktop —
applications, documents and folders, each group a panel you place where you
want it. It is built for one job and stays out of everything else.

> **Status: version 0.1.0, not yet published.** The desklet has been in daily
> use on Linux Mint 22.3 with Cinnamon 6.6.9 since September 2026, currently
> with nine fences. It is a fork of *TheLauncher 1.0.3* by MHK924 — see
> [THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md). It has its own UUID and can
> be installed next to TheLauncher; existing TheLauncher groups and their order
> are read, never changed.

## What it does

- **Groups (fences)** — several independent instances on the desktop, each
  showing one directory. A further fence is one click away: *Duplicate fence*.
- **Starter layout** — on request, nine titled fences in a grid that fits your
  screen, with your installed applications suggested by category; you decide
  in a preview what goes where.
- **Applications, documents, folders** — anything that lives in that
  directory shows up as a tile, in your own order or sorted by name, type or
  date; favourites can be pinned to the front.
- **Navigation inside a fence** — open a subfolder in place, walk back with a
  breadcrumb, without ever leaving the desktop.
- **Folder portal** — a fence can show any existing folder, local or on a
  network share, as a pure view: nothing is created, changed or deleted there.
- **Item menu** — move an item to another fence, pin it, or remove it to the
  trash; the last move can be undone.
- **Snapping and arrangement** — fences snap to their neighbours with guide
  lines and equal gaps, Ctrl places them freely. Recent arrangements and the
  original one can be restored, and all fences realigned at once.
- **Title row, collapsing, search** — an optional title row, a fence can be
  collapsed to its title, and one search filters all fences.
- **Locks** — position, size and content can each be locked, so nothing
  shifts by accident.
- **Automatic sizing** — columns and panel width follow the content, or a
  fixed window with mouse-wheel scrolling.
- **Group titles that stay readable** — the title is the fence's name or its
  directory name, and its colour follows the brightness of the wallpaper
  behind it (weighted RGB luminance).
- **New applications are noticed** — a small watcher offers newly installed
  programs and web apps for assignment to a group (add-on package).
- **Show and hide the desktop** — Super+Shift+D or, if switched on, a
  double-click on the free desktop (X11) hides the fences and the desktop
  icons together, the next brings them back (add-on package).
- **Settings backup** — the last five states of each fence's settings are
  kept automatically.

## Still open

| | |
|---|---|
| Layout profiles per monitor setup | fence positions kept per monitor arrangement and resolution — planned for the first update |
| Tabs | several sources sharing one area — later, possibly |

See [docs/ROADMAP.md](docs/ROADMAP.md).

## Deliberately not part of this

No weather, no clock, no calendar, no pomodoro, no AI assistant, no wallpaper
catalogue, no live wallpapers, no screenshot tool, no system theming, no start
menu replacement, no cloud account, no advertising, no telemetry.

Other Cinnamon applets do those things better. aVinceLaunch stays small, fast
and maintainable.

## Requirements

- Linux Mint with Cinnamon 6.6 (tested 6.6.9; Cinnamon does not load it on other versions); X11 session, or the Wayland session
  (tested with Cinnamon 6.6 "on Wayland (Experimental)")
- Python 3 with GTK 3 bindings (present on Mint by default)

## Add-on package (optional)

The desklet from Cinnamon Spices works on its own. The **aVinceLaunch
helpers** are a separate download (`aVinceLaunch-Helfer-0.1.0.tar.gz` on the
GitHub release page) with an install and an uninstall script — only your own
folders, never root, with a backup of everything they replace:

- the program watcher (new programs → which fence?),
- Super+Shift+D "desktop free" (X11 and Wayland),
- "Move to a fence…" in the desktop's context menu (Nemo),
- optionally the double-click on the free desktop (X11 only, listens to mouse
  buttons only; needs `python3-xlib`).

They need `zenity` (part of Mint). Details: [scripts/README.md](scripts/README.md).

## Repository layout

```
Desklet/     the Cinnamon desklet itself (JavaScript, Python settings pages, help, translation)
scripts/     the optional add-on package: helpers, installer, translation, package build;
             build-spices.py builds the Cinnamon Spices folder and zip
spices/      info.json and README.md for the Cinnamon Spices page
docs/        architecture, development, roadmap, upstream record
branding/    logo and icon sources, palette, asset generator
tests/       offline tests (no running Cinnamon needed), syntax check, checklist
```

How to work on the code: [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md).

## Support

aVinceLaunch is free and complete. There is no paid version, no
subscription, and nothing held back behind a payment — every feature
described here is in the version you can download.

If it is useful to you and you would like to support its further
development, you are welcome to do so. It is entirely voluntary and
changes nothing about the program. aVinceLaunch builds on TheLauncher by
MHK924; support goes to the further development of aVinceLaunch.

**[Support aVinceLaunch on Ko-fi](https://ko-fi.com/avince)**

The program itself does not mention it: no pop-ups, no reminders.

## License

`GPL-3.0-only` for aVinceLaunch's own work. The inherited TheLauncher code was
received under MIT; that notice is preserved in
[THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md) and ships inside the desklet
folder together with the GPL text. TheLauncher itself started from
*Quick Links - Launcher* by NotSirius-A; that acknowledgment is kept as well.

Many thanks to MHK924 for TheLauncher and for kindly allowing it to be built
upon.

Brand assets and how to rebuild them: [`branding/`](branding/).

Author: Angelo Vincenti — aVince Industrietechnik.
Sister project: [aVincePulse](https://github.com/aVince-Industrietechnik/aVincePulse).
