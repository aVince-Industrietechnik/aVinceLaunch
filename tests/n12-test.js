// SPDX-License-Identifier: GPL-3.0-only
// Copyright (c) 2026 Angelo Vincenti, aVince Industrietechnik

// Prueft Befund N12 (BT6, Wayland-Lauf 10.10.) ohne Cinnamon: Ein
// eingeklappter Fence blieb im festen Modus so hoch wie ausgeklappt - eine
// unsichtbare, reaktive Flaeche unter der Leiste (Ueberfahren klappte dort
// auf, Klicks auf den Schreibtisch kamen nicht an). _syncDeskletActorSize
// wird aus desklet.js herausgeloest und mit nachgebauten Bausteinen
// ausgefuehrt:
//  - ausgeklappt, fester Modus: Akteur = max_width x max_height (wie bisher);
//  - eingeklappt: Breite wie bisher, Hoehe natuerlich (-1) = Leiste bzw.
//    Leiste + Inhalt beim Aufklappen;
//  - _getFrameRect meldet eingeklappt weiter die volle Groesse (Platz frei).
// Aufruf im Repository-Wurzelverzeichnis:  cjs tests/n12-test.js

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

const [, bytes] = GLib.file_get_contents("Desklet/desklet.js");
const source = new TextDecoder().decode(bytes);

// "    name: function(args) { ... }," als "function(args) { ... }" herausloesen.
function methodSource(name) {
    const start = source.indexOf("\n    " + name + ": function(");
    if (start < 0) {
        return null;
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

function method(name) {
    const text = methodSource(name);
    return text === null ? null : new Function("return (" + text + ");")();
}

// --- Nachbau ------------------------------------------------------------------
function fence(options) {
    const sizes = [];
    const f = {
        max_width: 360,
        max_height: 210,
        _panelBox: {},
        _lastUsedColumns: 4,
        _isLiveActor: () => true,
        _measureLivePanelWidth: () => 344,
        _getShrinkPanelWidth: () => 344,
        _isFixedContentFit: () => options.fixed !== false,
        _isCollapsed: () => !!options.collapsed,
        _updateTitleContrast: () => {},
        _applyPanelAllocation: () => {},
        _applyContainerStyle: () => {},
        actor: {
            set_width: w => sizes.push(["w", w]),
            set_height: h => sizes.push(["h", h])
        }
    };
    f._syncDeskletActorSize = method("_syncDeskletActorSize");
    return { f, sizes };
}

print("Groesse des Akteurs (_syncDeskletActorSize):");
check("Methode vorhanden", methodSource("_syncDeskletActorSize") !== null, true);
let t = fence({ fixed: true, collapsed: false });
t.f._syncDeskletActorSize();
check("ausgeklappt, fester Modus: volle Breite und Hoehe", t.sizes, [["w", 360], ["h", 210]]);
t = fence({ fixed: true, collapsed: true });
t.f._syncDeskletActorSize();
check("eingeklappt, fester Modus: volle Breite, natuerliche Hoehe (nur Leiste)", t.sizes, [["w", 360], ["h", -1]]);
t = fence({ fixed: false, collapsed: false });
t.f._syncDeskletActorSize();
check("ausgeklappt, angepasster Modus: wie bisher natuerlich", t.sizes, [["w", 344], ["h", -1]]);
t = fence({ fixed: false, collapsed: true });
t.f._syncDeskletActorSize();
check("eingeklappt, angepasster Modus: natuerlich", t.sizes, [["w", 344], ["h", -1]]);

print("Platz fuer Nachbarn bleibt (_getFrameRect):");
const frame = methodSource("_getFrameRect") || "";
check("eingeklappt meldet weiter die volle Groesse (_expandedFrameSize)",
    /this\._isCollapsed\(\) && bar[\s\S]*?const full = this\._expandedFrameSize\(\);/.test(frame), true);
check("... unabhaengig von der Hoehe des Akteurs",
    frame.indexOf("this.actor.get_height") < 0, true);

print("Groesse ziehen bleibt eingeklappt gesperrt:");
check("canResize: !this._isCollapsed()",
    /canResize: \(function\(\) \{\s*return !this\._isCollapsed\(\);/.test(methodSource("_setupPlacement") || ""), true);

print("\nGeprueft: " + checks + ", Fehler: " + failures);
imports.system.exit(failures ? 1 : 0);
