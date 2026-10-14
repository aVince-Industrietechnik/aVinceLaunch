// SPDX-License-Identifier: GPL-3.0-only
// Copyright (c) 2026 Angelo Vincenti, aVince Industrietechnik

// N17 - Startaufstellung: Plaetze im Raster (lib/startLayout.js computeCells)
// fuer typische Bildschirme, belegte Flaechen, zu kleine Bildschirme und
// zwei Bildschirme. Alles in logischen Punkten.
// Aufruf im Repository-Wurzelverzeichnis:  cjs tests/n17-raster-test.js

const Gio = imports.gi.Gio;
const GLib = imports.gi.GLib;

const UUID = "avincelaunch-desklet@avince";
const shim = GLib.dir_make_tmp("avl-shim-XXXXXX");
GLib.mkdir_with_parents(shim + "/desklets", 0o755);
Gio.File.new_for_path(shim + "/desklets/" + UUID).make_symbolic_link(
    GLib.get_current_dir() + "/Desklet", null);
imports.searchPath.unshift(shim);
const L = imports.desklets[UUID].lib.startLayout;

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

const size = r => r.cells.length ? [r.cells[0].w, r.cells[0].h] : null;
const pos = r => r.cells.map(c => [c.x, c.y]);
const overlaps = (a, b) => a.x < b.x + b.w && b.x < a.x + a.w && a.y < b.y + b.h && b.y < a.y + a.h;
const anyOverlap = cells => cells.some((a, i) => cells.some((b, j) => i < j && overlaps(a, b)));
const inside = (cells, areas) => cells.every(c => {
    const a = areas[c.area];
    return c.x >= a.x && c.y >= a.y && c.x + c.w <= a.x + a.w && c.y + c.h <= a.y + a.h;
});

// --- 1. Latitude: 1536 x 1024, Leiste unten 40 -----------------------------
let areas = [{ x: 0, y: 0, w: 1536, h: 984 }];
let r = L.computeCells(areas, [], 9);
check("Latitude: 9 Plaetze, keiner fehlt", [r.cells.length, r.missing], [9, 0]);
check("Latitude: Grundmass 360 x 210", size(r), [360, 210]);
check("Latitude: Lagen im 25er-Raster, Schritt 375 / 250 (N26: senkrecht 30 Abstand)", pos(r),
    [[50, 50], [425, 50], [800, 50], [50, 300], [425, 300], [800, 300], [50, 550], [425, 550], [800, 550]]);
check("Latitude: keine Ueberlappung, alles auf der Flaeche", [anyOverlap(r.cells), inside(r.cells, areas)], [false, true]);

// --- 2. Kleinere Bildschirme --------------------------------------------------
r = L.computeCells([{ x: 0, y: 0, w: 1366, h: 728 }], [], 9);
check("1366 x 728: 9 Plaetze, Hoehe kleiner", [r.cells.length, size(r)], [9, [360, 175]]);  // N26: senkrecht mehr Abstand
r = L.computeCells([{ x: 0, y: 0, w: 1280, h: 680 }], [], 9);
check("1280 x 680: 9 Plaetze", [r.cells.length, size(r)], [9, [360, 170]]);  // N26
r = L.computeCells([{ x: 0, y: 0, w: 1024, h: 560 }], [], 9);
check("1024 x 560: nur 2 Zeilen (6), Rest fehlt", [r.cells.length, r.missing], [6, 3]);
check("1024 x 560: Mindestmass eingehalten", r.cells.every(c => c.w >= 240 && c.h >= 140), true);
r = L.computeCells([{ x: 0, y: 0, w: 700, h: 400 }], [], 9);
check("700 x 400: kein Platz", [r.cells.length, r.missing], [0, 9]);

// --- 3. Belegte Flaeche: erster Fence oben links ------------------------------
areas = [{ x: 0, y: 0, w: 1920, h: 1040 }];
r = L.computeCells(areas, [{ x: 50, y: 50, w: 360, h: 210 }], 9);
check("1920 x 1040 mit Fence oben links: 9 Plaetze", r.cells.length, 9);
check("... ohne Ueberlappung mit dem Fence", r.cells.some(c => overlaps(c, { x: 50, y: 50, w: 360, h: 210 })), false);
check("... Block rechts daneben", r.cells[0].x >= 50 + 360 + 15, true);

// --- 4. Zwei Bildschirme (Tower avltest, Skalierung 2 -> 1920 x 1080 logisch) -
areas = [{ x: 0, y: 0, w: 1920, h: 1040 }, { x: 1920, y: 0, w: 1920, h: 1080 }];
r = L.computeCells(areas, [], 9);
check("Tower: alle 9 auf dem Hauptbildschirm", r.cells.every(c => c.area === 0), true);
const busy = [{ x: 0, y: 0, w: 1920, h: 1040 }];
r = L.computeCells(areas, busy, 9);
check("Hauptbildschirm voll: alle auf dem zweiten", [r.cells.length, r.cells.every(c => c.area === 1)], [9, true]);
r = L.computeCells([{ x: 0, y: 0, w: 1024, h: 560 }, { x: 1024, y: 0, w: 1920, h: 1080 }], [], 9);
check("kleiner Haupt- + grosser Zweitbildschirm: 6 + 3", [r.cells.filter(c => c.area === 0).length,
    r.cells.filter(c => c.area === 1).length, r.missing], [6, 3, 0]);
check("... nichts ueberlappt", anyOverlap(r.cells), false);

// --- 4b. Voller Schreibtisch (Latitude 13.10.: 9 Fences + avincepulse) -------
const latFences = [[50, 50], [425, 50], [800, 50], [50, 300], [425, 300], [800, 300], [50, 550], [425, 550], [800, 550]]
    .map(p => ({ x: p[0], y: p[1], w: 360, h: 210 })).concat([{ x: 1300, y: 475, w: 197, h: 273 }]);
r = L.computeCells([{ x: 0, y: 0, w: 1536, h: 986 }], latFences, 9);
// N26: unter Angelos Fences (40 Abstand) bleibt mit 30 Mindestabstand keine
// Zeile >= 140 mehr frei - nichts wird gesetzt, alle 9 fehlen (Meldung).
check("voller Latitude-Schreibtisch: kein Platz mehr (N26), 9 fehlen",
    [r.cells.length, r.missing, size(r), pos(r)], [0, 9, null, []]);
check("... nichts ueberlappt die vorhandenen", r.cells.some(c => latFences.some(f => overlaps(c, f))), false);

// --- 5. Weniger Fences ---------------------------------------------------------
r = L.computeCells([{ x: 0, y: 0, w: 1536, h: 984 }], [], 4);
check("4 Fences: 3 + 1, Grundmass", [r.cells.length, size(r), pos(r)],
    [4, [360, 210], [[50, 50], [425, 50], [800, 50], [50, 300]]]);
r = L.computeCells([{ x: 0, y: 0, w: 1536, h: 984 }], [], 0);
check("0 Fences: nichts", [r.cells.length, r.missing], [0, 0]);
r = L.computeCells([{ x: 0, y: 0, w: 1536, h: 984 }], [], 12);
check("mehr als 9 wird auf 9 begrenzt", r.cells.length, 9);

GLib.spawn_command_line_sync("rm -rf " + GLib.shell_quote(shim));
print("");
print("Geprueft: " + checks + ", Fehler: " + failures);
if (failures > 0) {
    imports.system.exit(1);
}
