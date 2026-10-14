// SPDX-License-Identifier: GPL-3.0-only
// Copyright (c) 2026 Angelo Vincenti, aVince Industrietechnik

// Schritt 4, V5b - Befunde der Endabnahme am Tower (avltest, Skalierung 2):
//  N24  Beschriftung unter dem Symbol: set_width zaehlt in Bildpunkten, die
//       Symbolgroesse logisch - bei Skalierung 2 war die Beschriftung halb so
//       breit wie gedacht ("Br…"). Ebenso die Mindestbreite einer Kachel.
//       Methoden aus desklet.js mit nachgebautem Fence bei Skalierung 1 und 2.
//  N20  Startaufstellungs-Dialog: feste Symbolgroesse (set_pixel_size).
// Aufruf im Repository-Wurzelverzeichnis:  cjs tests/v5b-test.js

const GLib = imports.gi.GLib;

let failures = 0;
let checks = 0;
function check(name, actual, expected) {
    checks += 1;
    const a = JSON.stringify(actual);
    const e = JSON.stringify(expected);
    if (a === e) {
        print("  ok      " + name);
    } else {
        failures += 1;
        print("  FEHLER  " + name + "\n          erwartet " + e + "\n          erhalten " + a);
    }
}

const read = path => new TextDecoder().decode(GLib.file_get_contents(path)[1]);
const source = read("Desklet/desklet.js");
function methodSource(name) {
    const start = source.indexOf("\n    " + name + ": function(");
    if (start < 0) {
        throw new Error("Methode fehlt in desklet.js: " + name);
    }
    const open = source.indexOf("{", start);
    let depth = 0;
    let i = open;
    for (; i < source.length; i++) {
        if (source[i] === "{") {
            depth += 1;
        } else if (source[i] === "}") {
            depth -= 1;
            if (depth === 0) {
                break;
            }
        }
    }
    const header = source.substring(start, open);
    return header.substring(header.indexOf("function")) + source.substring(open, i + 1);
}
function method(name, deps) {
    const names = Object.keys(deps || {});
    return new Function(...names, "return " + methodSource(name) + ";")(...names.map(n => deps[n]));
}

const BASE_TILE_WIDTH = 120;
const Pango = { WrapMode: { WORD_CHAR: 2 }, EllipsizeMode: { END: 3 }, Alignment: { LEFT: 0 } };
const Clutter = { ActorAlign: { FILL: 0, START: 1, CENTER: 2 } };

function fence(scale, extra) {
    globalThis.global = { ui_scale: scale };
    const f = Object.assign({
        icon_size: 48, text_width_padding: 10, columns: 4, col_spacing: 8, max_width: 720,
        content_fit: "fixed", layout_style: "grid",
        _getTextAlign: () => 1
    }, extra || {});
    ["_uiScale", "_isFixedContentFit", "_isListLayout", "_getDeskletPadding", "_getDeskletPaddingPx",
     "_planColumnsForWidth"].forEach(n => { f[n] = method(n); });
    f._getTileTextWidth = method("_getTileTextWidth", { BASE_TILE_WIDTH: BASE_TILE_WIDTH });
    f._getTileWidth = method("_getTileWidth", { BASE_TILE_WIDTH: BASE_TILE_WIDTH });
    f._configureItemLabel = method("_configureItemLabel", { Pango: Pango, Clutter: Clutter });
    return f;
}
function labelWidth(f) {
    let width = null;
    const label = {
        clutter_text: { set_line_wrap() {}, set_line_wrap_mode() {}, set_ellipsize() {},
                        set_line_alignment() {}, set_x_align() {}, set_y_align() {} },
        set_x_align() {}, set_y_align() {},
        set_width(w) { width = w; }
    };
    f._configureItemLabel(label);
    return width;
}

print("N24 Beschriftung und Kachelbreite:");
check("Skalierung 1: Beschriftung 58 px (wie bisher)", labelWidth(fence(1)), 58);
check("Skalierung 2: Beschriftung 116 px (Symbol waechst mit)", labelWidth(fence(2)), 116);
check("logische Textbreite unveraendert (CSS-Breite automatisch)", fence(2)._getTileTextWidth(), 58);
check("Skalierung 1: Kachel = (720-16-3*8)/4", fence(1)._getTileWidth(), 170);
check("Skalierung 2: Kachel = (720-32-3*8)/4 (Rand waechst mit, N22)", fence(2)._getTileWidth(), 166);
// N22: Raster + Rand passen genau in max-width (Tower: 735 px, Abstand 6)
const t = fence(2, { max_width: 735, col_spacing: 6 });
check("N22 Skalierung 2: Raster passt in den Innenraum (735 px)",
    4 * t._getTileWidth() + 3 * 6 <= 735 - 2 * 8 * 2, true);
check("N22 Skalierung 1: unveraendert (360 px, wie bisher 80)", fence(1, { max_width: 360, col_spacing: 6 })._getTileWidth(), 81);
const r = fence(2, { _resizeTileWidth: 166, col_spacing: 8 });
check("Ziehen: Spalten fuer 720 px bei Skalierung 2", r._planColumnsForWidth(720), 4);
check("Skalierung 1: Mindestbreite 60 bei schmalem Fence", fence(1, { max_width: 120 })._getTileWidth(), 60);
check("Skalierung 2: Mindestbreite 120 bei schmalem Fence", fence(2, { max_width: 120 })._getTileWidth(), 120);
check("Beschriftung passt in die Kachel (Skalierung 2, Startaufstellung)",
    labelWidth(fence(2)) <= fence(2)._getTileWidth(), true);
check("Liste: keine feste Breite", labelWidth(fence(2, { layout_style: "list" })), null);

print("N26 schwebender Name:");
check("Abstand zur Kante waechst mit der Skalierung", /y - naturalHeight - 7 \* this\._uiScale\(\)/.test(source), true);

print("N20 Startaufstellungs-Dialog:");
const dialog = read("Desklet/startaufstellung-dialog.py");
check("Symbol mit fester Groesse", /image = Gtk\.Image\.new_from_gicon\(app\["icon"\], Gtk\.IconSize\.LARGE_TOOLBAR\)\s+image\.set_pixel_size\(24\)/.test(dialog), true);

print("");
print("Geprueft: " + checks + ", Fehler: " + failures);
if (failures > 0) {
    imports.system.exit(1);
}
