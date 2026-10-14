# Roadmap

As of 2026-10-13, before the first release (0.1.0).

## Principle

aVinceLaunch stays small, fast and maintainable. Every new feature has to
answer one question: **does it help to organise the desktop?** If not, it
does not belong here.

New features go into their own module under `Desklet/lib/`; `desklet.js` is
not meant to grow further.

## Planned after 0.1.0

| Topic | What | Status |
|---|---|---|
| **Layout profiles per monitor setup** | Fence positions are kept per monitor arrangement and resolution (signature of the setup). A known setup is restored after a change; an unknown one moves nothing except fences that would be out of reach. Menu: *Save current arrangement as profile*. | first update after 0.1.0 |
| **Network base folder: dialog actions in the background** | Since 0.1.0 the fences read a base folder on a network drive in the background, with a time limit. Actions the user starts – the Configure dialog, the item menu – still read the folder directly and wait if the share hangs at that moment; they will move to the background as well. | later |
| **Tabs** | One fence with a tab bar switching between several sources (groups or portals) – not by merging desklet instances, which works against Cinnamon's model. | later, possibly |
| **Wayland** | Repeat the Wayland test with Linux Mint 23 / Cinnamon 6.8. Today: works in the session "Cinnamon on Wayland" like under X11, except the desktop double-click (X11 only); Super+Shift+D works in both. | with Mint 23 |

## Deliberately not planned

Weather, clock, calendar, pomodoro, AI assistant, wallpaper catalogue, live
wallpapers, screenshot tool, system theming, start menu replacement, cursor
management, password vault, cloud services, an own update platform,
animations, telemetry, advertising.

Technically excluded as well: thumbnails, recursive scanning, writing into
other people's folders, moving user files automatically.
