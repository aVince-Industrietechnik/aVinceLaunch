// SPDX-License-Identifier: GPL-3.0-only
// Copyright (c) 2026 Angelo Vincenti, aVince Industrietechnik

// Prueft Paket N1 (Pruefung Phase 2) ohne Cinnamon: Ein frei gesetzter
// Fence (Strg oder 15 px Abstand zum Nachbarn) bleibt nach einem Neustart
// genau dort.
//   - lib/placement.js mit nachgebildetem global.settings (enabled-desklets,
//     desklet-snap an, Raster 25): Ablegen ohne Raster aendert nichts,
//     Gegenprobe mit Raster zeigt den alten Fehler (174/486 -> 175/475);
//   - zwei nachgestellte Starts (Cinnamon setzt die Lage aus der Liste, das
//     Desklet legt sie ab): Liste bleibt gleich, kein Schreiben;
//   - desklet.js: _syncPositionFromActor schreibt ohne Raster, das Eintippen
//     von X/Y (_applyPositionFromSettings) weiter mit.
// Aufruf im Repository-Wurzelverzeichnis:  cjs tests/n1-position-test.js

const Gio = imports.gi.Gio;
const GLib = imports.gi.GLib;

const UUID = "avincelaunch-desklet@avince";
const shim = GLib.dir_make_tmp("avl-shim-XXXXXX");
GLib.mkdir_with_parents(shim + "/desklets", 0o755);
Gio.File.new_for_path(shim + "/desklets/" + UUID).make_symbolic_link(
    GLib.get_current_dir() + "/Desklet", null);
imports.searchPath.unshift(shim);

// Nachbildung von Cinnamons global.settings (nur was placement.js braucht).
const fake = {
    strv: [],
    snap: true,
    interval: 25,
    writes: 0,
    get_strv(key) { return this.strv.slice(); },
    set_strv(key, list) { this.writes += 1; this.strv = list.slice(); },
    get_boolean(key) { return key === "desklet-snap" ? this.snap : false; },
    get_int(key) { return key === "desklet-snap-interval" ? this.interval : 0; },
    connect() { return 1; },
    disconnect() {}
};
globalThis.global = { settings: fake, log() {} };

const P = imports.desklets[UUID].lib.placement;

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

const LIST = [
    UUID + ":4:50:50",
    UUID + ":40:800:550",
    UUID + ":41:425:550",
    "avincepulse-desklet@avince:36:1300:475"
];

function reset(list) {
    fake.strv = list.slice();
    fake.snap = true;
    fake.interval = 25;
    fake.writes = 0;
}

// --- Rechnen ------------------------------------------------------------------
print("Raster:");
check("ohne Raster bleibt 174/486", P.snapCoordinates(174, 486, false), { x: 174, y: 486 });
check("Gegenprobe mit Raster 174/486 -> 175/475", P.snapCoordinates(174, 486, true), { x: 175, y: 475 });
fake.snap = false;
check("Cinnamon-Raster aus: auch mit Schalter 174/486", P.snapCoordinates(174, 486, true), { x: 174, y: 486 });
fake.snap = true;

// --- Ablegen nach freiem Ziehen ---------------------------------------------------
print("Ablegen:");
reset(LIST);
let r = P.writeGSettingsPosition(UUID, 40, 812, 563, false);
check("Rueckgabe 812/563", r, { x: 812, y: 563 });
check("Liste: nur Fence 40 geaendert", fake.strv, [
    UUID + ":4:50:50",
    UUID + ":40:812:563",
    UUID + ":41:425:550",
    "avincepulse-desklet@avince:36:1300:475"
]);
check("ein Schreibvorgang", fake.writes, 1);
check("lesen ergibt 812/563", P.readGSettingsPosition(UUID, 40), { x: 812, y: 563 });

// --- Start: Cinnamon setzt die Lage aus der Liste, Desklet legt sie ab ----------
// (deskletManager.js _loadDesklet: actor.set_position(definition.x, .y), dann
// on_desklet_added_to_desktop -> _syncPositionFromActor)
function simulateStart(id, useGrid) {
    const actor = P.readGSettingsPosition(UUID, id);
    P.writeGSettingsPosition(UUID, id, actor.x, actor.y, useGrid);
    return actor;
}

print("Start (neu, ohne Raster):");
reset(LIST);
P.writeGSettingsPosition(UUID, 40, 174, 486, false);
fake.writes = 0;
const start1 = simulateStart(40, false);
check("1. Start: Fence steht bei 174/486", start1, { x: 174, y: 486 });
const start2 = simulateStart(40, false);
check("2. Start: Fence steht bei 174/486", start2, { x: 174, y: 486 });
check("Liste unveraendert 174/486", P.readGSettingsPosition(UUID, 40), { x: 174, y: 486 });
check("kein Schreibvorgang beim Start", fake.writes, 0);
check("Nachbarn 4 und 41 unveraendert", [P.readGSettingsPosition(UUID, 4), P.readGSettingsPosition(UUID, 41)],
    [{ x: 50, y: 50 }, { x: 425, y: 550 }]);

print("Start (Gegenprobe alter Weg, mit Raster):");
reset(LIST);
P.writeGSettingsPosition(UUID, 40, 174, 486, false);
fake.writes = 0;
const old1 = simulateStart(40, true);
check("1. Start: Fence steht noch bei 174/486", old1, { x: 174, y: 486 });
check("aber Liste eingerastet 175/475", P.readGSettingsPosition(UUID, 40), { x: 175, y: 475 });
const old2 = simulateStart(40, true);
check("2. Start: Fence gerueckt auf 175/475", old2, { x: 175, y: 475 });

print("Raster-Lagen (3x3) bleiben:");
reset(LIST);
for (const id of [4, 40, 41]) {
    simulateStart(id, false);
}
check("Liste byte-gleich", fake.strv, LIST);
check("kein Schreibvorgang", fake.writes, 0);

// --- desklet.js: wer rastet ein, wer nicht ----------------------------------------
print("desklet.js:");
const [, bytes] = GLib.file_get_contents("Desklet/desklet.js");
const source = new TextDecoder().decode(bytes);

function body(name) {
    const start = source.indexOf("\n    " + name + ": function(");
    if (start < 0) {
        return "";
    }
    const end = source.indexOf("\n    },", start);
    return source.substring(start, end);
}

const sync = body("_syncPositionFromActor");
check("_syncPositionFromActor gefunden", sync.length > 0, true);
check("_syncPositionFromActor schreibt ohne Raster",
    /writeGSettingsPosition\(\s*UUID,\s*this\._getInstanceId\(\),\s*x,\s*y,\s*false\s*\)/.test(sync), true);
check("_syncPositionFromActor ohne snap_to_grid", sync.indexOf("snap_to_grid") < 0, true);
check("_applyPositionFromSettings rastet weiter ein",
    body("_applyPositionFromSettings").indexOf("this.snap_to_grid") >= 0, true);
check("Start ruft _syncPositionFromActor",
    body("on_desklet_added_to_desktop").indexOf("this._syncPositionFromActor()") >= 0, true);
check("Knopf \"Aktuelle Position\" ruft _syncPositionFromActor",
    body("on_capture_position_callback").indexOf("this._syncPositionFromActor()") >= 0, true);

GLib.unlink(shim + "/desklets/" + UUID);
GLib.rmdir(shim + "/desklets");
GLib.rmdir(shim);

print("");
print("Geprueft: " + checks + ", Fehler: " + failures);
if (failures > 0) {
    imports.system.exit(1);
}
