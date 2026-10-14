// SPDX-License-Identifier: GPL-3.0-only
// Copyright (c) 2026 Angelo Vincenti, aVince Industrietechnik

// N19 (Angelo 13.10.) ohne Cinnamon:
//  A. "Titel anzeigen" ab Werk an (Schema, Startwert, Startaufstellung).
//  B. N14: Titelzeile (ausgeklappt) und Leiste (eingeklappt) bauen ☰, Name,
//     (Suche) und Pfeil mit derselben Funktion; die Leiste hat dieselben
//     Abstaende wie die Titelzeile samt Rand des Fence (stylesheet.css).
//  C. N14: nach dem Ein-/Ausklappen sieht der Fence selbst nach, ob die Maus
//     ueber ihm ist, und zeigt dann die Titelzeile gleich.
// Funktionen werden aus desklet.js herausgeloest und mit nachgebauten
// Bausteinen ausgefuehrt.
// Aufruf im Repository-Wurzelverzeichnis:  cjs tests/n19-test.js

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

const source = read("Desklet/desklet.js");

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

// --- A. Titel ab Werk an -------------------------------------------------------
const schema = JSON.parse(read("Desklet/settings-schema.json"));
check("Schema: show-title ab Werk an", schema["show-title"].default, true);
check("Startwert im Desklet an", /\n        this\.show_title = true;/.test(source), true);
check("Startaufstellung setzt show-title", source.indexOf('"show-title": true,') > source.indexOf("_startLayoutValues: function"), true);

// --- B. gleicher Aufbau --------------------------------------------------------
const rowSrc = methodSource("_buildTitleRow");
const barSrc = methodSource("_buildCollapsedBar");
check("Titelzeile baut ueber _fillTitleControls(row, false)", rowSrc.indexOf("this._fillTitleControls(row, false)") > 0, true);
check("Leiste baut ueber _fillTitleControls(bar, true)", barSrc.indexOf("this._fillTitleControls(bar, true)") > 0, true);
check("keine eigenen Namen/Knoepfe mehr in Zeile und Leiste",
    [rowSrc, barSrc].map(t => /new St\.Label|_buildTitleMenuButton\(|_buildCollapseButton\(|_buildSearchButton\(/.test(t)),
    [false, false]);

// _fillTitleControls mit nachgebauten Bausteinen ausfuehren.
const fillFn = new Function("return " + methodSource("_fillTitleControls") + ";")();
function fill(collapsed, search) {
    const children = [];
    const fence = {
        show_search_button: search,
        _buildTitleMenuButton: () => ({ button: { kind: "menu" }, icon: {} }),
        _buildTitleLabel: () => ({ kind: "label" }),
        _buildSearchButton: () => ({ kind: "search", opacity: 255, reactive: true }),
        _buildCollapseButton: c => ({ kind: c ? "ausklappen" : "einklappen" })
    };
    fillFn.call(fence, { add_child: c => children.push(c) }, collapsed);
    return children.map(c => c.kind + (c.kind === "search" ? "/" + c.opacity + "/" + c.reactive : ""));
}
check("ausgeklappt mit Suche: ☰, Name, Suche, Pfeil", fill(false, true),
    ["menu", "label", "search/255/true", "einklappen"]);
check("eingeklappt mit Suche: Suche als unsichtbarer Platzhalter", fill(true, true),
    ["menu", "label", "search/0/false", "ausklappen"]);
check("ohne Suche: in beiden Zustaenden gleich viele Bausteine", [fill(false, false).length, fill(true, false).length], [3, 3]);

// Abstaende der Leiste = Rand des Fence + Titelzeile (stylesheet.css).
const css = read("Desklet/stylesheet.css");
const px = (block, prop) => {
    const m = css.match(new RegExp("\\." + block + "\\s*\\{[^}]*?" + prop + ":\\s*([^;]+);"));
    return m ? m[1].trim().split(/\s+/).map(v => parseInt(v, 10)) : null;
};
const fencePad = px("thelauncher-desklet", "padding")[0];
const rowPad = px("thelauncher-title-row", "padding");
const rowMargin = px("thelauncher-title-row", "margin-bottom")[0];
const expected = [fencePad + rowPad[0], fencePad + rowPad[1], rowPad[2] + rowMargin, fencePad + rowPad[3]]
    .map(v => v + "px").join(" ");
const constant = (source.match(/const TITLE_BAR_PADDING = "([^"]+)";/) || [])[1];
check("Leiste: Abstaende = Fence-Rand + Titelzeile (" + expected + ")", constant, expected);
check("Leiste nutzt TITLE_BAR_PADDING (auch beim Aufklappen)",
    methodSource("_styleCollapsedBar").indexOf('"padding: " + TITLE_BAR_PADDING') > 0, true);

// --- D. Breite der Leiste bei Groesse "automatisch" (Tower 13.10.) ---------------
check("vor dem Einklappen wird die ausgeklappte Groesse gemessen",
    /if \(state\) \{\s+this\._getFrameRect\(\);\s+\}\s+this\.settings\.setValue\("collapsed", state\)/.test(methodSource("_setCollapsed")), true);
const widthFn = new Function("return " + methodSource("_collapsedBarWidth") + ";")();
const barWidth = (full, cached) => widthFn.call({ _expandedFrameSize: () => full, _cachedPanelWidth: cached });
check("Leiste: gemessene Breite des ausgeklappten Fence", barWidth({ w: 836, h: 188 }, 500), 836);
check("Leiste: ohne Messung die Inhaltsbreite", barWidth(null, 836), 836);
check("Leiste: gar nichts bekannt -> natuerliche Breite (0)", barWidth(null, 0), 0);
check("Leiste nutzt _collapsedBarWidth", methodSource("_buildCollapsedBar").indexOf("this._collapsedBarWidth()") > 0, true);

// --- C. nach dem Umschalten nachsehen ------------------------------------------
const setSrc = methodSource("_setCollapsed");
check("_setCollapsed plant die Nachschau", /_titleSyncId = Mainloop\.timeout_add\(50[\s\S]*_syncTitleRowWithPointer\(\)/.test(setSrc), true);
check("Nachschau wird beim Abbau gestoppt", /"_titleSyncId"\]\.forEach/.test(methodSource("_stopBackgroundWork")), true);
const syncFn = new Function("return " + methodSource("_syncTitleRowWithPointer") + ";")();
function sync(over) {
    const calls = [];
    syncFn.call({
        actor: { is_finalized: () => false },
        _isPointerOverFence: () => over,
        _setTitleRowVisible: v => calls.push("zeile=" + v),
        _showHoverWindowTitle: () => calls.push("schwebend"),
        _syncHoverAfterMenu: () => calls.push("verlassen")
    });
    return calls;
}
check("Maus ueber dem Fence: Titelzeile sofort sichtbar", sync(true), ["zeile=true", "schwebend"]);
check("Maus weg: wie nach dem Menue (ausblenden)", sync(false), ["verlassen"]);

print("");
print("Geprueft: " + checks + ", Fehler: " + failures);
if (failures > 0) {
    imports.system.exit(1);
}
