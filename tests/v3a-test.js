// SPDX-License-Identifier: GPL-3.0-only
// Copyright (c) 2026 Angelo Vincenti, aVince Industrietechnik

// Schritt 4, V3a (B6/E4, P65, T6, P38) ohne Cinnamon, in Wegwerfordnern:
//  A. lib/desktopState.js: Markierung "schreibtisch-frei" (Zustand,
//     Beobachtung fuer alle Fences, nur echte Aenderungen), Flaechen nach
//     fences.json (gesammelt, atomar, Fence weg = Eintrag weg).
//  B. desklet.js _applyDesktopFree/_publishFenceRect/_stopFenceRect mit
//     nachgebautem Akteur: ausblenden, einblenden, Flaeche = Akteur in
//     Bildschirmpixeln, nach dem Abbau nichts mehr.
// Aufruf im Repository-Wurzelverzeichnis:  cjs tests/v3a-test.js

const Gio = imports.gi.Gio;
const GLib = imports.gi.GLib;

const UUID = "avincelaunch-desklet@avince";
const work = GLib.dir_make_tmp("avl-v3a-XXXXXX");
const STATE = work + "/state/avincelaunch";
const RUNTIME = work + "/run/avincelaunch";
const shim = GLib.dir_make_tmp("avl-shim-XXXXXX");
GLib.mkdir_with_parents(shim + "/desklets", 0o755);
Gio.File.new_for_path(shim + "/desklets/" + UUID).make_symbolic_link(
    GLib.get_current_dir() + "/Desklet", null);
imports.searchPath.unshift(shim);

const logs = [];
globalThis.global = { log(m) { logs.push(String(m)); }, logError(e, m) { logs.push("FEHLER " + (m || e)); } };

const D = imports.desklets[UUID].lib.desktopState;
D._setDirsForTests(STATE, RUNTIME);

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

function runLoop(ms) {
    const loop = new GLib.MainLoop(null, false);
    GLib.timeout_add(GLib.PRIORITY_DEFAULT, ms, () => { loop.quit(); return GLib.SOURCE_REMOVE; });
    loop.run();
}

// --- A. lib/desktopState.js --------------------------------------------------
print("A. Markierung und Flaechen:");
const MARKER = STATE + "/schreibtisch-frei";
check("Pfad der Markierung", D.markerPath(), MARKER);
check("Pfad der Flaechen", D.rectsPath(), RUNTIME + "/fences.json");
check("ohne Datei: nicht frei", D.isDesktopFree(), false);

const heard = [];
const ownerA = {};
const ownerB = {};
check("watch liefert den aktuellen Zustand", D.watchDesktopFree(ownerA, free => heard.push("A " + free)), false);
D.watchDesktopFree(ownerB, free => heard.push("B " + free));
check("Ordner fuer die Markierung angelegt", GLib.file_test(STATE, GLib.FileTest.IS_DIR), true);
GLib.file_set_contents(MARKER, "");
runLoop(400);
check("Markierung angelegt: alle Fences hoeren 'frei'", heard, ["A true", "B true"]);
GLib.file_set_contents(STATE + "/anderes", "x");
runLoop(300);
check("andere Datei im Ordner: keine Meldung", heard.length, 2);
GLib.file_set_contents(MARKER, "neu");
runLoop(300);
check("Markierung nur neu geschrieben: keine Meldung (keine echte Aenderung)", heard.length, 2);
D.unwatchDesktopFree(ownerB);
Gio.File.new_for_path(MARKER).delete(null);
runLoop(400);
check("Markierung weg: nur noch angemeldete hoeren 'nicht frei'", heard, ["A true", "B true", "A false"]);
// Wie das Skript: ueber Zwischendatei + Umbenennen.
GLib.file_set_contents(STATE + "/.tmp", "");
Gio.File.new_for_path(STATE + "/.tmp").move(Gio.File.new_for_path(MARKER), Gio.FileCopyFlags.OVERWRITE, null, null);
runLoop(400);
check("auch durch Umbenennen angelegt", heard[heard.length - 1], "A true");
D.unwatchDesktopFree(ownerA);
Gio.File.new_for_path(MARKER).delete(null);
runLoop(300);
check("nach dem letzten unwatch: keine Meldung mehr", heard.length, 4);

D.publishFenceRect("4", { x: 50.4, y: 49.6, w: 360, h: 210, visible: true });
D.publishFenceRect("40", { x: 800, y: 550, w: 360, h: 27, visible: false });
check("gesammelt: noch nicht geschrieben", GLib.file_test(RUNTIME + "/fences.json", GLib.FileTest.EXISTS), false);
runLoop(500);
check("nach dem Sammeln geschrieben, gerundet, sortiert",
    JSON.parse(read(RUNTIME + "/fences.json")),
    { version: 1, fences: { "4": { x: 50, y: 50, w: 360, h: 210, visible: true },
        "40": { x: 800, y: 550, w: 360, h: 27, visible: false } } });
check("keine Zwischendatei liegen geblieben", GLib.file_test(RUNTIME + "/fences.json.tmp", GLib.FileTest.EXISTS), false);
const stamp = Gio.File.new_for_path(RUNTIME + "/fences.json").query_info("time::modified-usec,time::modified",
    Gio.FileQueryInfoFlags.NONE, null).get_modification_date_time().to_unix_usec();
D.publishFenceRect("4", { x: 50, y: 50, w: 360, h: 210, visible: true });
runLoop(500);
const stamp2 = Gio.File.new_for_path(RUNTIME + "/fences.json").query_info("time::modified-usec,time::modified",
    Gio.FileQueryInfoFlags.NONE, null).get_modification_date_time().to_unix_usec();
check("gleiche Flaeche: nicht neu geschrieben", stamp2, stamp);
D.publishFenceRect("40", null);
D._flushForTests();
check("Fence weg: Eintrag weg", Object.keys(JSON.parse(read(RUNTIME + "/fences.json")).fences), ["4"]);

// --- B. desklet.js ------------------------------------------------------------
print("B. Desklet:");
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

const published = [];
const watchers = [];
const deps = {
    publishFenceRect: (id, rect) => published.push([id, rect]),
    unwatchDesktopFree: owner => watchers.push("unwatch")
};
function fakeActor() {
    const handlers = {};
    let next = 1;
    return {
        visible: true,
        finalized: false,
        x: 425, y: 300, w: 720, h: 420,
        handlers: handlers,
        is_finalized() { return this.finalized; },
        get_stage() { return {}; },
        hide() { this.visible = false; this.emit("notify::visible"); },
        show() { this.visible = true; this.emit("notify::visible"); },
        get_transformed_position() { return [this.x, this.y]; },
        get_transformed_size() { return [this.w, this.h]; },
        connect(signal, fn) { const id = next++; handlers[id] = [signal, fn]; return id; },
        disconnect(id) { delete handlers[id]; },
        emit(signal) { Object.values(handlers).filter(h => h[0] === signal).forEach(h => h[1]()); }
    };
}
const fence = {
    actor: fakeActor(),
    _rectSignals: [],
    _getInstanceId: () => "9",
    _applyDesktopFree: method("_applyDesktopFree", deps),
    _watchFenceRect: method("_watchFenceRect", deps),
    _publishFenceRect: method("_publishFenceRect", deps),
    _stopFenceRect: method("_stopFenceRect", deps)
};
fence._watchFenceRect();
check("beim Einrichten Flaeche gemeldet (Akteur, Bildschirmpixel)", published[0],
    ["9", { x: 425, y: 300, w: 720, h: 420, visible: true }]);
check("auf Lage/Groesse und Sichtbarkeit gehoert",
    Object.values(fence.actor.handlers).map(h => h[0]).sort(), ["notify::allocation", "notify::visible"]);
fence._watchFenceRect();
check("zweimal einrichten: nicht doppelt verbunden", Object.keys(fence.actor.handlers).length, 2);
published.length = 0;
fence._applyDesktopFree(true);
check("frei: Akteur aus, Flaeche als unsichtbar gemeldet",
    [fence.actor.visible, fence._desktopFree, published[published.length - 1][1].visible], [false, true, false]);
fence.actor.x = 430;
fence.actor.emit("notify::allocation");
check("verschoben: neue Lage gemeldet", published[published.length - 1][1].x, 430);
fence._applyDesktopFree(false);
check("nicht frei: Akteur wieder an, sichtbar gemeldet",
    [fence.actor.visible, published[published.length - 1][1].visible], [true, true]);
published.length = 0;
fence._stopFenceRect();
check("Abbau: abgemeldet, Signale getrennt, Eintrag entfernt",
    [watchers, Object.keys(fence.actor.handlers).length, published], [["unwatch"], 0, [["9", null]]]);
fence._applyDesktopFree(true);
fence._publishFenceRect();
check("nach dem Abbau: Akteur bleibt, nichts mehr gemeldet",
    [fence.actor.visible, published.length], [true, 1]);
const gone = { actor: null, _rectSignals: [], _getInstanceId: () => "1",
    _applyDesktopFree: method("_applyDesktopFree", deps), _publishFenceRect: method("_publishFenceRect", deps) };
gone._applyDesktopFree(true);
check("ohne Akteur kein Absturz, Zustand gemerkt", gone._desktopFree, true);
check("Einbindung: Start meldet sich an, Hinzufuegen wendet an, Abbau stoppt",
    [/this\._desktopFree = watchDesktopFree\(this, free => this\._applyDesktopFree\(free\)\);/.test(source),
     /this\._watchFenceRect\(\);\s*this\._applyDesktopFree\(this\._desktopFree\);/.test(methodSource("on_desklet_added_to_desktop")),
     methodSource("_stopBackgroundWork").indexOf("this._stopFenceRect();") > 0],
    [true, true, true]);
check("kein org.Cinnamon.Eval mehr in den Helfern",
    ["scripts/desktop-clean-toggle", "scripts/desktop-doubleclick"].filter(p => /gdbus|--method org\.Cinnamon\.Eval|"Eval"/.test(read(p))), []);

// --- Aufraeumen --------------------------------------------------------------
GLib.spawn_command_line_sync("rm -rf " + GLib.shell_quote(work) + " " + GLib.shell_quote(shim));

print("");
print("Geprueft: " + checks + ", Fehler: " + failures);
if (failures > 0) {
    imports.system.exit(1);
}
