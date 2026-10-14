// SPDX-License-Identifier: GPL-3.0-only
// Copyright (c) 2026 Angelo Vincenti, aVince Industrietechnik

// Prueft lib/snapEngine.js ohne Cinnamon.
// Aufruf im Repository-Wurzelverzeichnis:  cjs tests/snap-engine-test.js

imports.searchPath.unshift("Desklet/lib");
const E = imports.snapEngine;

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

// Latitude-5285: 1536 x 1024, Panel unten 38 px.
const AREA = { x: 0, y: 0, w: 1536, h: 986 };
const GRID = 25;
const MIN = 120;
const S = {};

const SYSTEM = { x: 50, y: 50, w: 360, h: 210 };
const BUERO = { x: 425, y: 50, w: 360, h: 210 };
const INTERNET = { x: 800, y: 50, w: 360, h: 210 };
const GRAFIK = { x: 50, y: 300, w: 360, h: 210 };
const MEDIEN = { x: 425, y: 300, w: 360, h: 210 };
const TOOLS = { x: 800, y: 300, w: 360, h: 210 };
const SONSTIGES = { x: 50, y: 550, w: 1110, h: 210 };
const OTHERS_OF_SYSTEM = [BUERO, INTERNET, GRAFIK, MEDIEN, TOOLS, SONSTIGES];

print("Groesse:");
{
    // Der Fall vom 01.10.: SYSTEM wieder auf 360 x 210 ziehen. Auf dem Raster
    // waere das 350 x 200 geworden.
    const r = E.snapResize({ x: 50, y: 50, w: 300, h: 200 }, 357, 207, "corner",
        OTHERS_OF_SYSTEM, AREA, S, GRID, MIN);
    check("SYSTEM rastet auf die Nachbarmasse 360 x 210", [r.w, r.h], [360, 210]);
    check("dabei Hilfslinien", r.guides.length > 0, true);
}
{
    // Kein Nachbar in Fangweite: Raster wie bisher.
    const r = E.snapResize({ x: 50, y: 50, w: 300, h: 200 }, 330, 200, "right",
        OTHERS_OF_SYSTEM, AREA, S, GRID, MIN);
    check("ohne Nachbar in Reichweite gilt das Raster", r.w, 325);
    check("ohne Treffer keine Hilfslinie", r.guides.length, 0);
}
{
    // Nach rechts in BUERO hineinziehen: stoppt mit 15 px Abstand.
    const r = E.snapResize(SYSTEM, 600, 210, "right", OTHERS_OF_SYSTEM, AREA, S, GRID, MIN);
    check("Breite stoppt vor BUERO (425 - 15 - 50)", r.w, 360);
}
{
    // Nach unten in GRAFIK hinein: stoppt mit 15 px Abstand.
    const r = E.snapResize(SYSTEM, 360, 500, "bottom", OTHERS_OF_SYSTEM, AREA, S, GRID, MIN);
    check("Hoehe stoppt vor GRAFIK (300 - 15 - 50)", r.h, 235);
}
{
    // Schon ueberlappend (Zustand vom 01.10., 350 x 375): darf sich befreien.
    const r = E.snapResize({ x: 50, y: 50, w: 350, h: 375 }, 350, 600, "bottom",
        OTHERS_OF_SYSTEM, AREA, S, GRID, MIN);
    check("verkeilter Fence ist nicht festgenagelt", r.h > 375, true);
}
{
    // SONSTIGES ganz nach rechts: Randabstand 15.
    const r = E.snapResize(SONSTIGES, 2000, 210, "right",
        [SYSTEM, BUERO, INTERNET, GRAFIK, MEDIEN, TOOLS], AREA, S, GRID, MIN);
    check("Bildschirmrand mit 15 px Abstand", 50 + r.w, 1536 - 15);
}
{
    const r = E.snapResize(SYSTEM, 20, 20, "corner", OTHERS_OF_SYSTEM, AREA, S, GRID, MIN);
    check("Mindestgroesse 120", [r.w, r.h], [120, 120]);
}

print("Verschieben:");
{
    // GRAFIK fast buendig unter SYSTEM: x rastet auf 50.
    const r = E.snapMove({ x: 57, y: 296, w: 360, h: 210 },
        [SYSTEM, BUERO, INTERNET, MEDIEN, TOOLS, SONSTIGES], AREA, S, GRID);
    check("linke Kante buendig mit SYSTEM", r.rect.x, 50);
    check("mit Hilfslinien", r.guides.length > 0, true);
    check("alle Linien waagrecht oder senkrecht",
        r.guides.every(g => g.x1 === g.x2 || g.y1 === g.y2), true);
}
{
    // Tower-Fall: Spalten nicht auf dem Raster (680). Nachbar geht vor Raster.
    const towerA = { x: 50, y: 50, w: 600, h: 270 };
    const r = E.snapMove({ x: 672, y: 52, w: 600, h: 270 }, [towerA],
        { x: 0, y: 0, w: 2560, h: 1440 }, S, GRID);
    check("Abstand 30 auf dem Tower: rastet auf 665 (15 px), nicht auf 675 (Raster)",
        r.rect.x, 665);
}
{
    const r = E.snapMove({ x: 3, y: 4, w: 360, h: 210 }, [], AREA, S, GRID);
    check("nie naeher als 15 px am Rand (keine 0 - Grenzwertregel)", [r.rect.x, r.rect.y], [15, 15]);
}
{
    const r = E.snapMove({ x: 20, y: 400, w: 360, h: 210 }, [], AREA, S, GRID);
    check("am linken Rand: Hilfslinie an der Kante und Steg zum Rand",
        r.guides.some(g => g.x1 === 15 && g.x2 === 15) && r.guides.some(g => g.x1 === 0 && g.x2 === 15), true);
}
{
    const r = E.snapMove({ x: 1400, y: 900, w: 360, h: 210 }, [], AREA, S, GRID);
    check("rechts unten innerhalb der Arbeitsflaeche (Panel)", [r.rect.x, r.rect.y],
        [1536 - 15 - 360, 986 - 15 - 210]);
}

print("Gleiche Abstaende:");
{
    const g = E.knownGaps([SYSTEM, BUERO, INTERNET, GRAFIK, MEDIEN, TOOLS, SONSTIGES], E.mergeSettings({}), "y");
    check("Latitude: senkrecht bestehende 40 px werden erkannt", g.indexOf(40) !== -1, true);
    const h = E.knownGaps([SYSTEM, BUERO, INTERNET], E.mergeSettings({}), "x");
    check("Latitude: waagrecht 15 px", h, [15]);
}
{
    // SONSTIGES wieder unter GRAFIK ziehen: rastet auf 40 px wie die Reihe darueber.
    const r = E.snapMove({ x: 52, y: 556, w: 1110, h: 210 },
        [SYSTEM, BUERO, INTERNET, GRAFIK, MEDIEN, TOOLS], AREA, S, GRID);
    check("SONSTIGES rastet auf seine alte Stelle 50/550 (40 px wie oben)", [r.rect.x, r.rect.y], [50, 550]);
}
{
    // Tower: 30 px Abstand in der Reihe wird angeboten.
    const a = { x: 50, y: 50, w: 600, h: 270 };
    const b = { x: 680, y: 50, w: 600, h: 270 };
    const r = E.snapMove({ x: 1305, y: 52, w: 600, h: 270 }, [a, b],
        { x: 0, y: 0, w: 2560, h: 1440 }, S, GRID);
    check("Tower: dritter Fence rastet mit 30 px wie die anderen (1310)", r.rect.x, 1310);
}

print("Ausrichten:");
const LATITUDE = [
    Object.assign({ id: "4" }, SYSTEM), Object.assign({ id: "5" }, BUERO),
    Object.assign({ id: "7" }, INTERNET), Object.assign({ id: "6" }, GRAFIK),
    Object.assign({ id: "8" }, MEDIEN), Object.assign({ id: "9" }, TOOLS),
    Object.assign({ id: "10" }, SONSTIGES)
];
const GAPS = { gapX: 15, gapY: 40 };
{
    const r = E.alignFences(LATITUDE, AREA, GAPS);
    check("Latitude heute: schon ausgerichtet, nichts bewegt sich",
        LATITUDE.every(f => r[f.id].x === f.x && r[f.id].y === f.y), true);
}
{
    // Leicht verrutscht (Test 02.10. frueh): zurueck auf 50/425/800 und 50/300/550.
    const messy = [
        { id: "4", x: 57, y: 72, w: 360, h: 210 }, { id: "5", x: 425, y: 50, w: 360, h: 210 },
        { id: "7", x: 887, y: 64, w: 360, h: 210 }, { id: "6", x: 50, y: 300, w: 360, h: 210 },
        { id: "8", x: 425, y: 300, w: 360, h: 210 }, { id: "9", x: 800, y: 300, w: 360, h: 210 },
        { id: "10", x: 72, y: 534, w: 1110, h: 210 }
    ];
    const r = E.alignFences(messy, AREA, GAPS);
    check("verrutscht: Spalten 50 / 425 / 800", [r["4"].x, r["5"].x, r["7"].x], [50, 425, 800]);
    check("verrutscht: Reihen 50 / 300 / 550", [r["4"].y, r["6"].y, r["10"].y], [50, 300, 550]);
    check("verrutscht: SONSTIGES links buendig", r["10"].x, 50);
}
{
    // Weit verschoben (Test 02.10. 08:19): SYSTEM ganz rechts, INTERNET zwischen
    // zwei Reihen. Ausrichten darf die Anordnung nicht umbauen.
    const far = [
        { id: "4", x: 1161, y: 187, w: 360, h: 210 }, { id: "5", x: 425, y: 50, w: 360, h: 210 },
        { id: "7", x: 630, y: 392, w: 360, h: 210 }, { id: "6", x: 50, y: 300, w: 360, h: 210 },
        { id: "8", x: 425, y: 300, w: 360, h: 210 }, { id: "9", x: 800, y: 300, w: 360, h: 210 },
        { id: "10", x: 105, y: 633, w: 1110, h: 210 }
    ];
    const r = E.alignFences(far, AREA, GAPS);
    check("weit verschoben: BUERO bleibt bei 425/50 (frueher nach links gesprungen)",
        [r["5"].x, r["5"].y], [425, 50]);
    check("weit verschoben: Reihe 2 bleibt bei 50 / 425 / 800",
        [r["6"].x, r["8"].x, r["9"].x], [50, 425, 800]);
    // INTERNET lag schon frei ueber MEDIEN/TOOLS (mit Strg abgelegt) und hat
    // in Reichweite keinen freien Platz: er bleibt. Neu darf nichts ueberlappen.
    const overlaps = [];
    far.forEach(a => far.forEach(b => {
        if (a.id < b.id && r[a.id].x < r[b.id].x + b.w && r[b.id].x < r[a.id].x + a.w
            && r[a.id].y < r[b.id].y + b.h && r[b.id].y < r[a.id].y + a.h) {
            overlaps.push(a.id + "/" + b.id);
        }
    }));
    check("weit verschoben: nur die schon vorher bestehende Ueberlappung bleibt",
        overlaps.every(o => o.split("/").indexOf("7") !== -1), true);
    check("weit verschoben: SYSTEM bleibt, wo es hingezogen wurde", [r["4"].x, r["4"].y], [1161, 187]);
}
{
    // Fall 02.10. 08:51: BUERO nach oben rechts verschoben (468/22), INTERNET
    // leicht daneben. Frueher folgten alle BUERO (Reihe 1 auf y = 15).
    const moved = [
        { id: "4", x: 50, y: 50, w: 360, h: 210 }, { id: "5", x: 468, y: 22, w: 360, h: 210 },
        { id: "7", x: 830, y: 58, w: 360, h: 210 }, { id: "6", x: 50, y: 300, w: 360, h: 210 },
        { id: "8", x: 425, y: 300, w: 360, h: 210 }, { id: "9", x: 800, y: 300, w: 360, h: 210 },
        { id: "10", x: 50, y: 550, w: 1110, h: 210 }
    ];
    const r = E.alignFences(moved, AREA, GAPS);
    check("Mehrheit: Reihe 1 bleibt bei 50, BUERO kommt zurueck",
        [r["4"].y, r["5"].y, r["7"].y], [50, 50, 50]);
    check("Mehrheit: Spalten 50 / 425 / 800", [r["4"].x, r["5"].x, r["7"].x], [50, 425, 800]);
    check("Mehrheit: die anderen Reihen bleiben", [r["6"].y, r["8"].y, r["10"].y], [300, 300, 550]);
}
{
    // Fall 02.10. 08:57: TOOLS (925/325) und SONSTIGES (175/550) verschoben.
    const moved = [
        { id: "4", x: 50, y: 50, w: 360, h: 210 }, { id: "5", x: 425, y: 50, w: 360, h: 210 },
        { id: "7", x: 800, y: 50, w: 360, h: 210 }, { id: "6", x: 50, y: 300, w: 360, h: 210 },
        { id: "8", x: 425, y: 300, w: 360, h: 210 }, { id: "9", x: 925, y: 325, w: 360, h: 210 },
        { id: "10", x: 175, y: 550, w: 1110, h: 210 }
    ];
    const r = E.alignFences(moved, AREA, GAPS);
    check("TOOLS zurueck auf 800/300", [r["9"].x, r["9"].y], [800, 300]);
    check("SONSTIGES zurueck auf 50/550", [r["10"].x, r["10"].y], [50, 550]);
}
{
    const r = E.alignFences([{ id: "1", x: 3, y: 2, w: 300, h: 200 }], AREA, S);
    check("einzelner Fence nah am Rand: Randabstand", [r["1"].x, r["1"].y], [15, 15]);
}
{
    const g = E.measureGaps(LATITUDE, S);
    check("aus der sauberen Latitude-Anordnung gelernt: 15 / 40", [g.gapX, g.gapY], [15, 40]);
}

{
    // Fremdes Desklet (aVincePulse) als Hindernis: Ausrichten schiebt keinen
    // Fence darauf.
    const pulse = { x: 1175, y: 280, w: 250, h: 300 };
    const fences = [
        Object.assign({ id: "4" }, SYSTEM), Object.assign({ id: "5" }, BUERO),
        { id: "9", x: 1168, y: 312, w: 360, h: 210 }
    ];
    const r = E.alignFences(fences, AREA, GAPS, [pulse]);
    const hit = r["9"].x < pulse.x + pulse.w && pulse.x < r["9"].x + 360
        && r["9"].y < pulse.y + pulse.h && pulse.y < r["9"].y + 210;
    check("Ausrichten schiebt nichts auf ein fremdes Desklet", hit
        ? (r["9"].x === 1168 && r["9"].y === 312) : true, true);
}

print("Ueberlappung:");
{
    // GRAFIK auf SYSTEM fallen lassen, knapp: rueckt neben SYSTEM.
    const start = { x: 50, y: 300, w: 360, h: 210 };
    const dropped = { x: 50, y: 200, w: 360, h: 210 };
    const r = E.resolveOverlap(dropped, [SYSTEM], AREA, S, start);
    check("knapp ueberlappend: rueckt unter SYSTEM", [r.outcome, r.rect.y], ["moved", 275]);
}
{
    // Mitten auf BUERO: kein freier Platz in Reichweite -> zurueck.
    const start = { x: 50, y: 300, w: 360, h: 210 };
    const r = E.resolveOverlap({ x: 425, y: 60, w: 360, h: 210 }, OTHERS_OF_SYSTEM, AREA, S, start);
    check("mitten drauf: zurueck an den Ausgangspunkt", [r.outcome, r.rect.x, r.rect.y],
        ["reverted", 50, 300]);
}
{
    const r = E.resolveOverlap({ x: 1200, y: 50, w: 300, h: 210 }, OTHERS_OF_SYSTEM, AREA, S, SYSTEM);
    check("frei: unveraendert", r.outcome, "free");
}
{
    // Fremdes Desklet in der Liste: Ablegen darauf wird verhindert.
    const pulse = { x: 1175, y: 475, w: 250, h: 300 };
    const r = E.resolveOverlap({ x: 1160, y: 500, w: 360, h: 210 }, [pulse], AREA, S,
        { x: 800, y: 300, w: 360, h: 210 });
    check("Ablegen auf aVincePulse: daneben oder zurueck", r.outcome !== "free", true);
}
{
    const r = E.resolveOverlap({ x: 425, y: 60, w: 360, h: 210 }, OTHERS_OF_SYSTEM, AREA,
        { preventOverlap: false }, SYSTEM);
    check("Schutz abschaltbar", r.outcome, "free");
}

print("\nPlatz fuer ein Duplikat (AP18-5):");
{
    // Gelernte Abstaende des Latitude: 15 waagrecht, 40 senkrecht.
    const GAPS = { gapX: 15, gapY: 40 };
    const PULSE = { x: 1300, y: 475, w: 197, h: 273 };
    const ROW1 = [SYSTEM, BUERO, INTERNET];
    const R2 = y => [50, 425, 800].map(x => ({ x: x, y: y, w: 360, h: 210 }));
    const GRID3 = R2(50).concat(R2(300), R2(550));

    check("allein: rechts daneben", E.findFreeSpot(SYSTEM, [], AREA, GAPS),
        { x: 425, y: 50, w: 360, h: 210 });
    check("rechts belegt: darunter mit 40", E.findFreeSpot(SYSTEM, [BUERO], AREA, GAPS),
        { x: 50, y: 300, w: 360, h: 210 });
    check("Reihe voll: unter dem Original", E.findFreeSpot(INTERNET, [SYSTEM, BUERO], AREA, GAPS),
        { x: 800, y: 300, w: 360, h: 210 });
    check("3x3 mit aVincePulse auf 1536 px: kein Platz", E.findFreeSpot(GRID3[2],
        GRID3.filter((r, i) => i !== 2).concat([PULSE]), AREA, GAPS), null);
    const small = { x: 800, y: 50, w: 300, h: 210 };
    check("schmaler Fence: rechts neben sich selbst", E.findFreeSpot(small,
        GRID3.filter((r, i) => i !== 2).concat([PULSE]), AREA, GAPS),
        { x: 1115, y: 50, w: 300, h: 210 });
    check("rechts und unten belegt: naechster Platz schraeg darunter", E.findFreeSpot(SYSTEM,
        [BUERO, GRAFIK], AREA, GAPS), { x: 425, y: 300, w: 360, h: 210 });
    const spot = E.findFreeSpot(SYSTEM, ROW1.slice(1), AREA, GAPS);
    check("haelt Abstand zu allen", ROW1.concat([spot]).every((a, i, all) =>
        all.every((b, j) => i === j || !E.intersects(
            { x: a.x - 14, y: a.y - 14, w: a.w + 28, h: a.h + 28 }, b))), true);
    check("ohne Arbeitsflaeche trotzdem ein Platz", E.findFreeSpot(SYSTEM, [], null, {}) !== null, true);
}

print("\nGeprueft: " + checks + ", Fehler: " + failures);
if (failures > 0) {
    imports.system.exit(1);
}
