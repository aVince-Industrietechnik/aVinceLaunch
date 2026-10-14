# Branding

Source files for the aVinceLaunch identity. Everything here is the **source**;
the rendered PNG sets are build output and are not kept in the repository.

```
branding/
├── svg/                     18 SVG sources (icon, logos, wordmark)
├── BRANDING_GUIDELINES.md   geometry, colours, sizes, do / don't
├── COLORS.json              the palette, machine readable
└── build-branding.py        regenerates the whole production set
```

## Rebuild the full asset set

```bash
python3 branding/build-branding.py [target-directory]
```

Without an argument it writes to `branding/build/`. It creates 113 files:
icons in 16–1024 px for five colourways, logo PNGs, GitHub assets and a
Cinnamon icon set.

Requirements are Linux Mint stock packages only — `python3`, `python3-gi`
(GdkPixbuf with the librsvg loader) and `python3-cairo`. Nothing is installed,
nothing outside the target directory is written.

## What is in the repository

| File | Purpose |
|---|---|
| `docs/logo.png`, `docs/logo-ondark.png` | README header, light and dark theme |
| `docs/icon-512.png`, `docs/icon-128.png` | repository and general use |
| `docs/social-preview-1280x640.png` | GitHub social preview (repository settings) |
| `Desklet/icon.png` | the icon Cinnamon shows in its desklet list |

## Origin

The identity was approved on 2026-09-30. The approved reference images are
kept by the author and are not part of this repository. Geometry and colours in the SVG sources were measured from those
references, not redrawn by eye.

The wordmark is stored as outlines, so no font is required to render the logos.
It was set in Ubuntu Bold, the Linux Mint system typeface and the closest
available match to the reference lettering; the reference itself is drawn
lettering, not a licensed typeface. Ubuntu Bold is published under the
Ubuntu Font Licence 1.0. The logos contain only outlined lettering, which is
artwork made with the font, not font software; no font file is part of this
repository or of the desklet package.
