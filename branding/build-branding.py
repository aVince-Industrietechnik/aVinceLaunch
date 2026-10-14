#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
# Copyright (c) 2026 Angelo Vincenti, aVince Industrietechnik

# ---------------------------------------------------------------------------
# aVinceLaunch - Branding-Produktionsset erzeugen
#
# Erzeugt aus der freigegebenen Markenbasis ein vollstaendiges, reproduzierbares
# Produktionsset: SVG-Quellen, PNG-Groessen, Logo-Varianten, GitHub-Assets.
#
# Das Skript SCHREIBT ausschliesslich in den Zielordner (Argument, sonst
# branding/build/); die SVG-Quellen werden nur gelesen.
#
# Voraussetzungen (alle auf Linux Mint vorhanden, nichts zu installieren):
#   python3, python3-gi (GdkPixbuf mit librsvg-Loader), python3-cairo
#
# Aufruf:
#   python3 build-branding.py [Zielordner]
# ---------------------------------------------------------------------------

import math
import os
import shutil
import sys

import gi
gi.require_version("GdkPixbuf", "2.0")
from gi.repository import GdkPixbuf
import cairo

# Zielordner: erstes Argument, sonst ./build neben diesem Skript.
BRANDING = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.join(BRANDING, "build")

# ---------------------------------------------------------------------------
# Farben - abgemessen aus der freigegebenen Markenbasis
# ---------------------------------------------------------------------------
C = {
    "primary_dark":    "#141C22",   # Icon-Traeger, Mittelwert
    "dark_top":        "#1E272E",   # Verlauf oben
    "dark_bottom":     "#070F15",   # Verlauf unten
    "dark_ui_plate":   "#232C34",   # etwas heller, damit das Icon auf Schwarz nicht verschwindet
    "primary_green":   "#2BBB33",   # Wortmarke "Launch"
    "arrow_light":     "#A8F348",   # Pfeil oben links
    "arrow_deep":      "#45EE3D",   # Pfeil unten rechts
    "mint":            "#3AC989",
    "teal":            "#2E8F80",
    "secondary_dark":  "#325563",   # blaugraue Kacheln
    "light_neutral":   "#F2F4F5",
    "white":           "#FFFFFF",
    "wordmark_dark":   "#18242C",
    "wordmark_light":  "#E8EDF0",
    "tagline_dark":    "#4A5860",
    "tagline_light":   "#AEBAC2",
}

# Helle Variante: neutrale Graustufen wie im Brandboard-Muster "LIGHT BACKGROUND"
TILES_LIGHT = {
    "R1C1": ("#E4EAED", "#CFD9DE"),
    "R1C2": ("#E1E8EB", "#CBD6DB"),
    "R2C1": ("#DFE6EA", "#C7D3D9"),
    "R2C2": ("#DCE4E8", "#C3D0D6"),
    "R2C3": ("#D8E1E5", "#BECCD3"),
    "R3C1": ("#DAE3E7", "#C0CED5"),
    "R3C2": ("#D7DFE4", "#BCCAD1"),
    "R3C3": ("#D3DCE1", "#B7C6CE"),
}

# Kachelverlaeufe: (oben links, unten rechts) - aus dem Original abgetastet
TILES = {
    "R1C1": ("#9DF157", "#45D071"),
    "R1C2": ("#8FF560", "#3CC86A"),
    "R2C1": ("#58E380", "#2CA588"),
    "R2C2": ("#44C179", "#368272"),
    "R2C3": ("#3A7E70", "#30525F"),
    "R3C1": ("#36D597", "#278980"),
    "R3C2": ("#358F81", "#305D67"),
    "R3C3": ("#386B72", "#274151"),
}

# Geometrie im 1024er-Raster, abgemessen am freigegebenen App-Icon
R_PLATE = 221          # Eckradius des Traegers
R_TILE = 34            # Eckradius der Kacheln
GEO = {
    "R1C1": (152, 176, 232, 240),
    "R1C2": (418, 176, 110, 240),
    "R2C1": (152, 450, 232, 198),
    "R2C2": (418, 450, 206, 198),     # mit Kerbe oben rechts
    "R2C3": (656, 498, 216, 150),
    "R3C1": (152, 680, 232, 198),
    "R3C2": (418, 680, 206, 198),
    "R3C3": (656, 680, 216, 198),
}
NOTCH = (534, 450, 90, 70)            # Kerbe an R2C2: x, y, Breite, Hoehe
ARROW = {
    "bar_t": 91,                       # Balkenstaerke
    "top":   (585, 146, 882, 237),     # oberer Balken: x0,y0,x1,y1
    "right": (791, 146, 882, 425),     # rechter Balken
    "shaft": (597, 455, 812, 240),     # Schaft: Mittellinie von unten links nach oben rechts
    "r":     26,                       # Eckradius am Pfeilkopf
}

WORDMARK_FONT = "Ubuntu"
TAGLINE_FONT = "Ubuntu"


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------
def rr(x, y, w, h, r):
    """Pfaddaten fuer ein abgerundetes Rechteck."""
    return (f"M{x + r},{y} H{x + w - r} A{r},{r} 0 0 1 {x + w},{y + r} "
            f"V{y + h - r} A{r},{r} 0 0 1 {x + w - r},{y + h} "
            f"H{x + r} A{r},{r} 0 0 1 {x},{y + h - r} "
            f"V{y + r} A{r},{r} 0 0 1 {x + r},{y} Z")


def notched_tile(x, y, w, h, r, nx, ny, nw, nh):
    """Kachel mit rechteckiger Kerbe an der oberen rechten Ecke, innen gerundet."""
    x1, y1 = x + w, y + h
    return (f"M{x + r},{y} H{nx - r} A{r},{r} 0 0 0 {nx},{y + r} "
            f"V{ny + nh - r} A{r},{r} 0 0 0 {nx + r},{ny + nh} "
            f"H{x1 - r} A{r},{r} 0 0 1 {x1},{ny + nh + r} "
            f"V{y1 - r} A{r},{r} 0 0 1 {x1 - r},{y1} "
            f"H{x + r} A{r},{r} 0 0 1 {x},{y1 - r} "
            f"V{y + r} A{r},{r} 0 0 1 {x + r},{y} Z")


def arrow_paths():
    """Pfeil als zwei Pfade: L-foermiger Kopf und diagonaler Schaft."""
    tx0, ty0, tx1, ty1 = ARROW["top"]
    rx0, ry0, rx1, ry1 = ARROW["right"]
    r = ARROW["r"]
    head = (f"M{tx0 + r},{ty0} H{tx1 - r} A{r},{r} 0 0 1 {tx1},{ty0 + r} "
            f"V{ry1 - r} A{r},{r} 0 0 1 {tx1 - r},{ry1} "
            f"H{rx0 + r} A{r},{r} 0 0 1 {rx0},{ry1 - r} "
            f"V{ty1 + r} A{r},{r} 0 0 0 {rx0 - r},{ty1} "
            f"H{tx0 + r} A{r},{r} 0 0 1 {tx0},{ty1 - r} "
            f"V{ty0 + r} A{r},{r} 0 0 1 {tx0 + r},{ty0} Z")
    sx0, sy0, sx1, sy1 = ARROW["shaft"]
    shaft = f"M{sx0},{sy0} L{sx1},{sy1}"
    return head, shaft


def text_path(text, font, size, weight=cairo.FONT_WEIGHT_BOLD):
    """Text ueber cairo in SVG-Pfaddaten wandeln - macht das Logo schriftunabhaengig."""
    # Unbegrenzte Aufzeichnungsflaeche: eine kleine Bildflaeche wuerde lange
    # Textpfade abschneiden (in der Pruefung nachgewiesen).
    surface = cairo.RecordingSurface(cairo.CONTENT_COLOR_ALPHA, None)
    ctx = cairo.Context(surface)
    ctx.select_font_face(font, cairo.FONT_SLANT_NORMAL, weight)
    ctx.set_font_size(size)
    ctx.move_to(0, 0)
    ctx.text_path(text)
    d = []
    for kind, pts in ctx.copy_path():
        if kind == cairo.PATH_MOVE_TO:
            d.append("M%.2f,%.2f" % pts)
        elif kind == cairo.PATH_LINE_TO:
            d.append("L%.2f,%.2f" % pts)
        elif kind == cairo.PATH_CURVE_TO:
            d.append("C%.2f,%.2f %.2f,%.2f %.2f,%.2f" % pts)
        elif kind == cairo.PATH_CLOSE_PATH:
            d.append("Z")
    ext = ctx.text_extents(text)
    return " ".join(d), ext.width, ext.x_advance


def svg(width, height, body, extra_defs=""):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}">\n'
            f'<defs>{extra_defs}</defs>\n{body}\n</svg>\n')


def grad(id_, c0, c1, x1=0, y1=0, x2=1, y2=1):
    return (f'<linearGradient id="{id_}" x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}">'
            f'<stop offset="0" stop-color="{c0}"/><stop offset="1" stop-color="{c1}"/>'
            f'</linearGradient>')


# ---------------------------------------------------------------------------
# Icon-Varianten
# ---------------------------------------------------------------------------
def icon_parts(variant, p=""):
    """Liefert (defs, body) getrennt, damit das Icon in Logos eingebettet werden kann.
    p ist ein Praefix fuer die Verlaufs-IDs, damit sie sich nie ueberschneiden."""
    defs, body = _icon_build(variant, p)
    return "".join(defs), "\n".join(body)


def icon_svg(variant):
    """variant: color | light | dark | mono_light | mono_dark"""
    defs, body = _icon_build(variant, "")
    return svg(1024, 1024, "\n".join(body), "".join(defs))


def _icon_build(variant, p=""):
    defs = []
    body = []

    if variant == "color":
        defs.append(grad(p + "plate", C["dark_top"], C["dark_bottom"]))
        plate, plate_on = "url(#%splate)" % p, True
    elif variant == "dark":
        defs.append(grad(p + "plate", "#2A343C", "#141C22"))
        plate, plate_on = "url(#%splate)" % p, True
    elif variant == "light":
        defs.append(grad(p + "plate", "#FFFFFF", "#E7EBED"))
        plate, plate_on = "url(#%splate)" % p, True
    elif variant == "mono_light":
        plate, plate_on = None, False
    elif variant == "mono_dark":
        plate, plate_on = None, False
    else:
        raise ValueError(variant)

    if plate_on:
        body.append(f'<path d="{rr(0, 0, 1024, 1024, R_PLATE)}" fill="{plate}"/>')

    mono = variant.startswith("mono")
    fg = C["white"] if variant == "mono_light" else C["wordmark_dark"]

    for key, (x, y, w, h) in GEO.items():
        if key == "R2C2":
            d = notched_tile(x, y, w, h, R_TILE, *NOTCH)
        else:
            d = rr(x, y, w, h, R_TILE)
        if mono:
            fill = fg
        else:
            c0, c1 = (TILES_LIGHT if variant == "light" else TILES)[key]
            defs.append(grad(f"{p}t{key}", c0, c1))
            fill = f"url(#{p}t{key})"
        body.append(f'<path d="{d}" fill="{fill}"/>')

    head, shaft = arrow_paths()
    if mono:
        afill, astroke = fg, fg
    else:
        defs.append(grad(p + "arrow", C["arrow_light"], C["arrow_deep"]))
        afill = astroke = "url(#%sarrow)" % p
    body.append(f'<path d="{shaft}" fill="none" stroke="{astroke}" '
                f'stroke-width="{ARROW["bar_t"]}" stroke-linecap="round"/>')
    body.append(f'<path d="{head}" fill="{afill}"/>')

    return defs, body


def icon_small_svg(variant):
    """Fassung fuer 16 bis 32 Pixel.

    Die Pruefung hat gezeigt: eine staerkere Vereinfachung (2x2-Raster) verliert
    den Markencharakter und ist NICHT besser lesbar. Deshalb bleibt die
    Geometrie erhalten; vereinfacht werden nur die Feinheiten, die bei wenigen
    Pixeln ohnehin zu Matsch werden:
      - keine Verlaeufe, sondern flaechige Farben
      - keine Kerbe an R2C2
      - etwas kleinere Eckradien
      - minimal kraeftigerer Pfeil
    """
    body = []
    mono = variant.startswith("mono")
    flach = {k: mischen(a, b) for k, (a, b) in
             ((TILES_LIGHT if variant == "light" else TILES).items())}

    if variant == "color":
        plate = "#161E24"
    elif variant == "dark":
        plate = "#232C34"
    elif variant == "light":
        plate = "#F4F7F8"
    else:
        plate = None
    if plate:
        body.append(f'<path d="{rr(0, 0, 1024, 1024, R_PLATE)}" fill="{plate}"/>')

    fg = C["white"] if variant == "mono_light" else C["wordmark_dark"]
    for key, (x, y, w, h) in GEO.items():
        fill = fg if mono else flach[key]
        body.append(f'<path d="{rr(x, y, w, h, 26)}" fill="{fill}"/>')

    head, shaft = arrow_paths()
    afill = fg if mono else "#57E844"
    body.append(f'<path d="{shaft}" fill="none" stroke="{afill}" '
                f'stroke-width="{ARROW["bar_t"] + 6}" stroke-linecap="round"/>')
    body.append(f'<path d="{head}" fill="{afill}"/>')
    return svg(1024, 1024, "\n".join(body))


def mischen(a, b):
    """Mittelwert zweier Hexfarben - fuer die flaechigen Kleinfassungen."""
    ar, ag, ab = int(a[1:3], 16), int(a[3:5], 16), int(a[5:7], 16)
    br, bg_, bb = int(b[1:3], 16), int(b[3:5], 16), int(b[5:7], 16)
    return "#%02X%02X%02X" % ((ar + br) // 2, (ag + bg_) // 2, (ab + bb) // 2)


# ---------------------------------------------------------------------------
# Logos
# ---------------------------------------------------------------------------
def text_path_spaced(text, font, size, spacing, weight=cairo.FONT_WEIGHT_NORMAL):
    """Wie text_path, aber mit Sperrung (Zeichenabstand) wie in der Unterzeile."""
    teile = []
    x = 0.0
    for ch in text:
        d, _, adv = text_path(ch, font, size, weight)
        if d.strip():
            teile.append(f'<g transform="translate({x:.2f},0)"><path d="{d}"/></g>')
        x += adv + spacing
    return "".join(teile), max(0.0, x - spacing)


def logo_svg(layout, tagline, on_dark):
    """layout: horizontal | stacked"""
    size = 300.0
    d_av, w_av, adv_av = text_path("aVince", WORDMARK_FONT, size)
    d_la, w_la, adv_la = text_path("Launch", WORDMARK_FONT, size)
    tag_size = 62.0
    tag_group, tag_w = text_path_spaced("ORGANIZE  \u2022  ACCESS  \u2022  LAUNCH",
                                        TAGLINE_FONT, tag_size, tag_size * 0.22)

    col_av = C["wordmark_light"] if on_dark else C["wordmark_dark"]
    col_la = "#4CD455" if on_dark else C["primary_green"]
    col_tag = C["tagline_light"] if on_dark else C["tagline_dark"]

    icon_defs, icon_inner = icon_parts("color", "ic_")
    word_w = adv_av + adv_la
    pad = 60

    if layout == "horizontal":
        icon_size = 300
        gap = 70
        inhalt_w = icon_size + gap + max(word_w, tag_w if tagline else 0)
        total_w = inhalt_w + 2 * pad
        total_h = icon_size + 2 * pad
        icon_x, icon_y = pad, pad
        tx = pad + icon_size + gap
        if tagline:
            # Wortmarke etwas hoeher, Unterzeile darunter
            base_y = pad + icon_size * 0.50 + size * 0.30
            tag_y = base_y + tag_size * 1.15
        else:
            base_y = pad + icon_size * 0.5 + size * 0.36
            tag_y = None
        tag_x = tx + 4
    else:
        icon_size = 420
        block_w = max(icon_size, word_w, tag_w if tagline else 0)
        total_w = block_w + 2 * pad
        icon_x = (total_w - icon_size) / 2
        icon_y = pad
        base_y = pad + icon_size + 80 + size * 0.72
        total_h = base_y + pad * 0.6
        tag_y = None
        if tagline:
            tag_y = base_y + tag_size * 1.5
            total_h = tag_y + pad * 0.8
        tx = (total_w - word_w) / 2
        tag_x = (total_w - tag_w) / 2

    body = [f'<g transform="translate({icon_x},{icon_y}) scale({icon_size / 1024.0})">{icon_inner}</g>',
            f'<g transform="translate({tx},{base_y})">'
            f'<path d="{d_av}" fill="{col_av}"/>'
            f'<g transform="translate({adv_av},0)"><path d="{d_la}" fill="{col_la}"/></g>'
            f'</g>']
    if tagline:
        body.append(f'<g transform="translate({tag_x},{tag_y})" fill="{col_tag}">{tag_group}</g>')

    return svg(round(total_w), round(total_h), "\n".join(body), icon_defs)


def wordmark_svg(on_dark):
    size = 300.0
    d_av, _, adv_av = text_path("aVince", WORDMARK_FONT, size)
    d_la, _, adv_la = text_path("Launch", WORDMARK_FONT, size)
    col_av = C["wordmark_light"] if on_dark else C["wordmark_dark"]
    col_la = C["primary_green"] if not on_dark else "#4CD455"
    pad = 30
    w = adv_av + adv_la + 2 * pad
    h = size * 1.0 + 2 * pad
    body = (f'<g transform="translate({pad},{pad + size * 0.75})">'
            f'<path d="{d_av}" fill="{col_av}"/>'
            f'<g transform="translate({adv_av},0)"><path d="{d_la}" fill="{col_la}"/></g></g>')
    return svg(round(w), round(h), body)


def social_svg():
    """GitHub-Vorschaubild 1280x640, mittig gesetzt."""
    icon_defs, icon = icon_parts("color", "ic_")
    size = 300.0
    d_av, _, adv_av = text_path("aVince", WORDMARK_FONT, size)
    d_la, _, adv_la = text_path("Launch", WORDMARK_FONT, size)

    ziel_wortbreite = 540.0
    k = ziel_wortbreite / (adv_av + adv_la)          # Massstab der Wortmarke
    icon_size = 190
    abstand = 46
    block_w = icon_size + abstand + ziel_wortbreite
    x0 = (1280 - block_w) / 2.0
    y_icon = 195

    tag_size = 30.0
    tag_group, tag_w = text_path_spaced("ORGANIZE  \u2022  ACCESS  \u2022  LAUNCH",
                                        TAGLINE_FONT, tag_size, tag_size * 0.30)
    d_sub, _, sub_w = text_path("Lightweight desktop organizer for Linux Mint Cinnamon",
                                TAGLINE_FONT, 32, cairo.FONT_WEIGHT_NORMAL)

    grundlinie = y_icon + icon_size * 0.5 + size * k * 0.35
    body = [
        '<rect width="1280" height="640" fill="url(#bg)"/>',
        f'<g transform="translate({x0:.1f},{y_icon}) scale({icon_size / 1024.0:.5f})">{icon}</g>',
        f'<g transform="translate({x0 + icon_size + abstand:.1f},{grundlinie:.1f}) scale({k:.5f})">'
        f'<path d="{d_av}" fill="{C["wordmark_light"]}"/>'
        f'<g transform="translate({adv_av},0)"><path d="{d_la}" fill="#4CD455"/></g></g>',
        f'<g transform="translate({(1280 - tag_w) / 2:.1f},{y_icon + icon_size + 105:.1f})" '
        f'fill="#8CA0AC">{tag_group}</g>',
        f'<g transform="translate({(1280 - sub_w) / 2:.1f},{y_icon + icon_size + 175:.1f})">'
        f'<path d="{d_sub}" fill="#5E7180"/></g>',
    ]
    defs = grad("bg", "#1B242B", "#0A1217") + icon_defs
    return svg(1280, 640, "\n".join(body), defs)


# ---------------------------------------------------------------------------
# Ausgabe
# ---------------------------------------------------------------------------
def write_svg(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)
    return path


def render_png(svg_path, png_path, width, height=None):
    os.makedirs(os.path.dirname(png_path), exist_ok=True)
    if height is None:
        height = width
    pb = GdkPixbuf.Pixbuf.new_from_file_at_size(svg_path, width, height)
    pb.savev(png_path, "png", [], [])
    return png_path


def main():
    if os.path.isdir(OUT):
        print("Hinweis: %s existiert bereits und wird neu erzeugt." % OUT)
        shutil.rmtree(OUT)

    erzeugt = []
    svg_dir = os.path.join(OUT, "SVG")

    # --- Icon-SVGs
    icon_variants = {
        "aVinceLaunch_Icon.svg": icon_svg("color"),
        "aVinceLaunch_Icon_Light.svg": icon_svg("light"),
        "aVinceLaunch_Icon_Dark.svg": icon_svg("dark"),
        "aVinceLaunch_Icon_Monochrome_Light.svg": icon_svg("mono_light"),
        "aVinceLaunch_Icon_Monochrome_Dark.svg": icon_svg("mono_dark"),
        "aVinceLaunch_Icon_Small.svg": icon_small_svg("color"),
        "aVinceLaunch_Icon_Small_Monochrome_Light.svg": icon_small_svg("mono_light"),
        "aVinceLaunch_Icon_Small_Monochrome_Dark.svg": icon_small_svg("mono_dark"),
    }
    for name, content in icon_variants.items():
        erzeugt.append(write_svg(os.path.join(svg_dir, name), content))

    # --- Logo-SVGs
    logos = {
        "aVinceLaunch_Logo_Horizontal.svg": logo_svg("horizontal", False, False),
        "aVinceLaunch_Logo_Horizontal_Tagline.svg": logo_svg("horizontal", True, False),
        "aVinceLaunch_Logo_Horizontal_OnDark.svg": logo_svg("horizontal", False, True),
        "aVinceLaunch_Logo_Horizontal_Tagline_OnDark.svg": logo_svg("horizontal", True, True),
        "aVinceLaunch_Logo_Stacked.svg": logo_svg("stacked", False, False),
        "aVinceLaunch_Logo_Stacked_Tagline.svg": logo_svg("stacked", True, False),
        "aVinceLaunch_Logo_Stacked_OnDark.svg": logo_svg("stacked", False, True),
        "aVinceLaunch_Logo_Stacked_Tagline_OnDark.svg": logo_svg("stacked", True, True),
        "aVinceLaunch_Wordmark.svg": wordmark_svg(False),
        "aVinceLaunch_Wordmark_OnDark.svg": wordmark_svg(True),
    }
    for name, content in logos.items():
        erzeugt.append(write_svg(os.path.join(svg_dir, name), content))

    # --- PNG-Icons
    sizes = [16, 24, 32, 48, 64, 128, 256, 512, 1024]
    klein = {16, 24, 32}
    icon_sets = [
        ("COLOR", "color", "aVinceLaunch_Icon_Color_%d.png"),
        ("LIGHT", "light", "aVinceLaunch_Icon_Light_%d.png"),
        ("DARK", "dark", "aVinceLaunch_Icon_Dark_%d.png"),
    ]
    for ordner, variant, muster in icon_sets:
        gross = write_svg(os.path.join(OUT, "_tmp", f"{variant}.svg"), icon_svg(variant))
        small = write_svg(os.path.join(OUT, "_tmp", f"{variant}_small.svg"), icon_small_svg(variant))
        for s in sizes:
            quelle = small if s in klein else gross
            erzeugt.append(render_png(quelle, os.path.join(OUT, "ICONS", ordner, muster % s), s))

    for ordner, variant, muster in (("MONOCHROME", "mono_light", "aVinceLaunch_Icon_Monochrome_Light_%d.png"),
                                    ("MONOCHROME", "mono_dark", "aVinceLaunch_Icon_Monochrome_Dark_%d.png")):
        gross = write_svg(os.path.join(OUT, "_tmp", f"{variant}.svg"), icon_svg(variant))
        small = write_svg(os.path.join(OUT, "_tmp", f"{variant}_small.svg"), icon_small_svg(variant))
        for s in sizes:
            quelle = small if s in klein else gross
            erzeugt.append(render_png(quelle, os.path.join(OUT, "ICONS", ordner, muster % s), s))

    for variant, muster in (("color", "aVinceLaunch_Icon_Small_Color_%d.png"),
                            ("mono_light", "aVinceLaunch_Icon_Small_Monochrome_Light_%d.png"),
                            ("mono_dark", "aVinceLaunch_Icon_Small_Monochrome_Dark_%d.png")):
        quelle = os.path.join(OUT, "_tmp", f"{variant}_small.svg")
        for s in (16, 24, 32, 48):
            erzeugt.append(render_png(quelle, os.path.join(OUT, "ICONS", "SMALL", muster % s), s))

    # --- Logo-PNGs
    def logo_png(svg_name, ordner, png_name, breiten):
        quelle = os.path.join(svg_dir, svg_name)
        pb = GdkPixbuf.Pixbuf.new_from_file(quelle)
        seite = pb.get_height() / pb.get_width()
        for b in breiten:
            ziel = os.path.join(OUT, "LOGOS", ordner, png_name % b)
            os.makedirs(os.path.dirname(ziel), exist_ok=True)
            p = GdkPixbuf.Pixbuf.new_from_file_at_size(quelle, b, round(b * seite))
            p.savev(ziel, "png", [], [])
            erzeugt.append(ziel)

    logo_png("aVinceLaunch_Logo_Horizontal.svg", "HORIZONTAL", "aVinceLaunch_Logo_Horizontal_%d.png", [400, 800, 1600])
    logo_png("aVinceLaunch_Logo_Horizontal_Tagline.svg", "HORIZONTAL", "aVinceLaunch_Logo_Horizontal_Tagline_%d.png", [400, 800, 1600])
    logo_png("aVinceLaunch_Logo_Horizontal_OnDark.svg", "HORIZONTAL", "aVinceLaunch_Logo_Horizontal_OnDark_%d.png", [800, 1600])
    logo_png("aVinceLaunch_Logo_Stacked.svg", "STACKED", "aVinceLaunch_Logo_Stacked_%d.png", [400, 800, 1200])
    logo_png("aVinceLaunch_Logo_Stacked_Tagline.svg", "STACKED", "aVinceLaunch_Logo_Stacked_Tagline_%d.png", [400, 800, 1200])
    logo_png("aVinceLaunch_Logo_Stacked_OnDark.svg", "STACKED", "aVinceLaunch_Logo_Stacked_OnDark_%d.png", [800])

    # --- GitHub
    gh = os.path.join(OUT, "GITHUB")
    erzeugt.append(write_svg(os.path.join(gh, "aVinceLaunch_Social_Preview.svg"), social_svg()))
    erzeugt.append(render_png(os.path.join(gh, "aVinceLaunch_Social_Preview.svg"),
                              os.path.join(gh, "aVinceLaunch_Social_Preview_1280x640.png"), 1280, 640))
    for quelle, ziel, breite in (
            ("aVinceLaunch_Logo_Horizontal.svg", "aVinceLaunch_README_Logo_880.png", 880),
            ("aVinceLaunch_Logo_Horizontal_OnDark.svg", "aVinceLaunch_README_Logo_OnDark_880.png", 880),
            ("aVinceLaunch_Wordmark.svg", "aVinceLaunch_Wordmark_600.png", 600),
            ("aVinceLaunch_Icon.svg", "aVinceLaunch_Repo_Icon_512.png", 512),
            ("aVinceLaunch_Icon.svg", "aVinceLaunch_Repo_Icon_128.png", 128)):
        src = os.path.join(svg_dir, quelle)
        pb = GdkPixbuf.Pixbuf.new_from_file(src)
        seite = pb.get_height() / pb.get_width()
        erzeugt.append(render_png(src, os.path.join(gh, ziel), breite, round(breite * seite)))

    # --- Cinnamon-Ablage: genau die Groessen, die Cinnamon tatsaechlich nutzt
    cin = os.path.join(OUT, "CINNAMON")
    erzeugt.append(render_png(os.path.join(svg_dir, "aVinceLaunch_Icon.svg"),
                              os.path.join(cin, "icon.png"), 128))
    for s_ in (16, 22, 24, 32, 48):
        erzeugt.append(render_png(os.path.join(svg_dir, "aVinceLaunch_Icon_Small_Monochrome_Light.svg"),
                                  os.path.join(cin, "panel", f"avincelaunch-symbolic-light-{s_}.png"), s_))
        erzeugt.append(render_png(os.path.join(svg_dir, "aVinceLaunch_Icon_Small_Monochrome_Dark.svg"),
                                  os.path.join(cin, "panel", f"avincelaunch-symbolic-dark-{s_}.png"), s_))
    for s_ in (48, 64, 128, 256):
        erzeugt.append(render_png(os.path.join(svg_dir, "aVinceLaunch_Icon.svg"),
                                  os.path.join(cin, "hicolor", f"avincelaunch-{s_}.png"), s_))
    shutil.copy2(os.path.join(svg_dir, "aVinceLaunch_Icon.svg"),
                 os.path.join(cin, "hicolor", "avincelaunch.svg"))
    erzeugt.append(os.path.join(cin, "hicolor", "avincelaunch.svg"))

    shutil.rmtree(os.path.join(OUT, "_tmp"), ignore_errors=True)
    erzeugt = [p for p in erzeugt if "_tmp" not in p]
    print("Erzeugte Dateien: %d" % len(erzeugt))
    return erzeugt


if __name__ == "__main__":
    main()
