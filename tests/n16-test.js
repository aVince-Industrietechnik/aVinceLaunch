// SPDX-License-Identifier: GPL-3.0-only
// Copyright (c) 2026 Angelo Vincenti, aVince Industrietechnik

// Prueft Befund N16 (Tower avltest, UI-Skalierung 2, 12.10.) ohne Cinnamon:
//  1. _wrapMessageLabel (desklet.js) bricht Meldungen nur bei fester Hoehe
//     um. Im Modus "auto" bemisst Cinnamon den Akteur ohne Umbruch - der
//     umgebrochene Text lag eine Zeile unter dem Akteur (kein Ziehen unten,
//     Rechtsklick dort = Cinnamon-Menue, Titel verschwand).
//  2. hitZone (lib/layoutManager.js) misst Rand und Ecke in logischen
//     Punkten: bei Skalierung 2 doppelt so viele Bildpunkte.
// Beide Funktionen werden aus dem Quelltext herausgeloest und mit
// nachgebauten Bausteinen ausgefuehrt.
// Aufruf im Repository-Wurzelverzeichnis:  cjs tests/n16-test.js

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

function read(path) {
    const [, bytes] = GLib.file_get_contents(path);
    return new TextDecoder().decode(bytes);
}

// Ab "start" bis zur passenden schliessenden Klammer.
function block(source, start) {
    if (start < 0) {
        return null;
    }
    const open = source.indexOf("{", start);
    let depth = 0;
    for (let i = open; i < source.length; i++) {
        if (source[i] === "{") {
            depth += 1;
        } else if (source[i] === "}") {
            depth -= 1;
            if (depth === 0) {
                return source.substring(start, i + 1);
            }
        }
    }
    return null;
}

// --- 1. Umbruch nur bei fester Hoehe ----------------------------------------
const desklet = read("Desklet/desklet.js");
const wrapText = block(desklet, desklet.indexOf("\n    _wrapMessageLabel: function("));
check("_wrapMessageLabel gefunden", wrapText !== null, true);
const wrapFn = new Function("Pango",
    "return " + wrapText.substring(wrapText.indexOf("function")) + ";")({
    WrapMode: { WORD_CHAR: "WORD_CHAR" },
    EllipsizeMode: { NONE: "NONE" }
});

function fakeLabel() {
    const calls = [];
    return {
        calls: calls,
        clutter_text: {
            set_line_wrap: v => calls.push("wrap=" + v),
            set_line_wrap_mode: v => calls.push("mode=" + v),
            set_ellipsize: v => calls.push("ellipsize=" + v)
        }
    };
}

function wrapCalls(fit, maxHeight) {
    const fence = {
        content_fit: fit,
        max_height: maxHeight,
        _isFixedContentFit: function() {
            return String(this.content_fit).toLowerCase().indexOf("fixed") === 0;
        }
    };
    const label = fakeLabel();
    const back = wrapFn.call(fence, label);
    return { same: back === label, calls: label.calls };
}

check("fest 360x210: Umbruch, kein \"...\"", wrapCalls("fixed", 210),
    { same: true, calls: ["wrap=true", "mode=WORD_CHAR", "ellipsize=NONE"] });
check("auto: unveraendert (einzeilig mit \"...\")", wrapCalls("auto", 210), { same: true, calls: [] });
check("auto ohne Hoehe: unveraendert", wrapCalls("auto", 0), { same: true, calls: [] });
check("fest, aber Hoehe 0 (natuerlich): unveraendert", wrapCalls("fixed", 0), { same: true, calls: [] });
check("beide Meldungsstellen nutzen _wrapMessageLabel",
    (desklet.match(/this\._wrapMessageLabel\(new St\.Label\(\{/g) || []).length, 2);
check("Akteur bekommt feste Hoehe unter derselben Bedingung",
    /if \(this\._isFixedContentFit\(\) && this\.max_height > 0 && !this\._isCollapsed\(\)\) \{\s+this\.actor\.set_height\(this\.max_height\);/.test(desklet),
    true);

// --- 2. Randzonen mit der UI-Skalierung --------------------------------------
const layout = read("Desklet/lib/layoutManager.js");
const edgeZone = Number((layout.match(/^var EDGE_ZONE = (\d+);/m) || [])[1]);
const cornerZone = Number((layout.match(/^var CORNER_ZONE = (\d+);/m) || [])[1]);
check("EDGE_ZONE/CORNER_ZONE logisch 8/12 (unveraendert)", [edgeZone, cornerZone], [8, 12]);
const scaleText = block(layout, layout.indexOf("function zoneScale("));
const hitText = block(layout, layout.indexOf("function hitZone("));
check("zoneScale und hitZone gefunden", scaleText !== null && hitText !== null, true);

function makeHitZone(uiScale) {
    const fakeGlobal = uiScale === undefined ? {} : { ui_scale: uiScale };
    return new Function("global", "EDGE_ZONE", "CORNER_ZONE",
        scaleText + "\n" + hitText + "\nreturn hitZone;")(fakeGlobal, edgeZone, cornerZone);
}

// Sichtbare Flaeche wie am Tower: Fence 3, 836 x 216 Bildpunkte.
function zoneAt(uiScale, x, y) {
    const actor = {
        transform_stage_point: (sx, sy) => [true, sx, sy],
        get_width: () => 836,
        get_height: () => 216
    };
    return makeHitZone(uiScale)(actor, x, y);
}

check("Skalierung 1: rechts 7 px vom Rand", zoneAt(1, 829, 100), "right");
check("Skalierung 1: rechts 9 px vom Rand = keine Zone", zoneAt(1, 827, 100), null);
check("Skalierung 1: Ecke 11 px", zoneAt(1, 825, 205), "corner");
check("Skalierung 1: unten 7 px", zoneAt(1, 400, 209), "bottom");
check("Skalierung 2: rechts 15 px vom Rand", zoneAt(2, 821, 100), "right");
check("Skalierung 2: rechts 17 px vom Rand = keine Zone", zoneAt(2, 819, 100), null);
check("Skalierung 2: Ecke 23 px", zoneAt(2, 813, 193), "corner");
check("Skalierung 2: unten 15 px", zoneAt(2, 400, 201), "bottom");
check("Skalierung 2: Mitte = keine Zone", zoneAt(2, 400, 100), null);
check("ausserhalb = keine Zone", zoneAt(2, 900, 100), null);
check("ohne global.ui_scale wie Skalierung 1", [zoneAt(undefined, 821, 100), zoneAt(undefined, 829, 100)],
    [null, "right"]);
check("unsinniger Wert (0) wie Skalierung 1", zoneAt(0, 821, 100), null);

print("");
print("Geprueft: " + checks + ", Fehler: " + failures);
if (failures > 0) {
    imports.system.exit(1);
}
