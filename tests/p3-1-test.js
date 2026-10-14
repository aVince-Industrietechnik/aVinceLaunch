// SPDX-License-Identifier: GPL-3.0-only
// Copyright (c) 2026 Angelo Vincenti, aVince Industrietechnik

// Prueft Paket P3-1, Befund N3 (Pruefung Phase 3) ohne Cinnamon:
// lib/orderListSync.js - die Dialogliste wird beim Oeffnen von "Einrichten"
// nicht mehr still ersetzt, wenn sie zu einem Unterordner gehoert und dort
// offene Aenderungen hat; dazu Quelltextpruefung von desklet.js.
// Aufruf im Repository-Wurzelverzeichnis:  cjs tests/p3-1-test.js

const GLib = imports.gi.GLib;

imports.searchPath.unshift("Desklet/lib");
const O = imports.orderListSync;

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

const id = entry => entry.id;
const list = (ids, off) => ids.map(i => ({ id: i, enabled: !(off || []).includes(i) }));

print("classifyOrderList:");
check("gleich -> same", O.classifyOrderList(list(["a", "b"]), list(["a", "b"]), id), "same");
check("Eintrag dazu -> clean", O.classifyOrderList(list(["a", "b", "c"]), list(["a", "b"]), id), "clean");
check("Eintrag weg -> clean", O.classifyOrderList(list(["a"]), list(["a", "b"]), id), "clean");
check("umsortiert -> dirty", O.classifyOrderList(list(["a", "b"]), list(["b", "a"]), id), "dirty");
check("Haken weg -> dirty", O.classifyOrderList(list(["a", "b"]), list(["a", "b"], ["b"]), id), "dirty");
check("kein gemeinsamer Eintrag -> clean (darum N3)",
    O.classifyOrderList(list(["r1", "r2"]), list(["s2", "s1"]), id), "clean");

print("planDialogListSync (N3):");
// Startordner /g mit r1, r2; Unterordner /g/sub mit s1, s2 - gespeichert ist
// die Unterordner-Liste in umsortierter Reihenfolge (nicht uebernommen).
const folders = { "/g": list(["r1", "r2"]), "/g/sub": list(["s1", "s2"]) };
const stored = list(["s2", "s1"]);
const classify = path => (path in folders ? O.classifyOrderList(folders[path], stored, id) : null);
check("Unterordner mit offener Aenderung -> stale (Liste bleibt)",
    O.planDialogListSync("/g/sub", "/g", classify), "stale");
check("Gegenprobe ohne Ordnerwissen (alter Weg) -> sync",
    O.planDialogListSync("", "/g", classify), "sync");
const cleanStored = list(["s1", "s2"]);
const classifyClean = path => (path in folders ? O.classifyOrderList(folders[path], cleanStored, id) : null);
check("Unterordner ohne Aenderung -> sync (wie bisher)", O.planDialogListSync("/g/sub", "/g", classifyClean), "sync");
check("Unterordner nicht lesbar -> keep", O.planDialogListSync("/g/weg", "/g", classify), "keep");
check("gleicher Ordner, gleich -> same",
    O.planDialogListSync("/g", "/g", p => O.classifyOrderList(folders[p], list(["r1", "r2"]), id)), "same");
check("gleicher Ordner, umsortiert -> stale",
    O.planDialogListSync("/g", "/g", p => O.classifyOrderList(folders[p], list(["r2", "r1"]), id)), "stale");
check("gleicher Ordner, neuer Eintrag -> sync",
    O.planDialogListSync("/g", "/g", p => O.classifyOrderList(list(["r1", "r2", "r3"]), list(["r1", "r2"]), id)), "sync");

print("desklet.js:");
const [, bytes] = GLib.file_get_contents("Desklet/desklet.js");
const source = new TextDecoder().decode(bytes);
const start = source.indexOf("\n    _syncDialogListIfClean: function(");
const body = start < 0 ? "" : source.substring(start, source.indexOf("\n    },", start));
check("_syncDialogListIfClean nutzt planDialogListSync mit gespeichertem Ordner",
    /planDialogListSync\(\s*this\._storedOrderListPath\(\),\s*orderPath,\s*this\._dialogListClassifier\(\)\)/.test(body), true);
check("kein eigener Vergleich mehr in desklet.js", body.indexOf("commonFresh") < 0, true);
const cfgStart = source.indexOf("\n    configureDesklet: function(");
const cfg = source.substring(cfgStart, source.indexOf("\n    },", cfgStart));
// Am Geraet gefunden (09.10.): Die Zuweisung an order_folder_path schreibt die
// Einstellung sofort (bindProperty beachtet die Richtung nicht) - die
// Entscheidung muss davor fallen.
const keepAt = cfg.indexOf("this._keepDialogListInSubfolder()");
const resetAt = cfg.indexOf("this.order_folder_path = this._rootPath");
check("configureDesklet: Unterordner-Entscheidung VOR dem Zuruecksetzen",
    keepAt >= 0 && resetAt > keepAt
    && /if \(this\._rootPath && !this\._keepDialogListInSubfolder\(\)\) \{\s*this\.order_folder_path = this\._rootPath;/.test(cfg), true);
const keepStart = source.indexOf("\n    _keepDialogListInSubfolder: function(");
const keepBody = keepStart < 0 ? "" : source.substring(keepStart, source.indexOf("\n    },", keepStart));
check("_keepDialogListInSubfolder: nur bei \"stale\" im eigenen Ordner",
    /planDialogListSync\(\s*listPath,\s*this\._rootPath,\s*this\._dialogListClassifier\(\)\)\s*===\s*"stale"/.test(keepBody), true);
check("configureDesklet: erst Abgleich, dann gespeicherten Ordner laden",
    cfg.indexOf("this._syncDialogListIfClean()") >= 0
    && cfg.indexOf("this._syncDialogListIfClean()") < cfg.indexOf("this._reloadOrderSettingsFromPanel()"), true);

print("\nGeprueft: " + checks + ", Fehler: " + failures);
if (failures > 0) {
    imports.system.exit(1);
}
