// SPDX-License-Identifier: GPL-3.0-only
// Copyright (c) 2026 Angelo Vincenti, aVince Industrietechnik

// Asynchrone Dateizugriffe auf die Fence-Ordner (lokal wie im Netz).
//  A. lib/linkScanner.js scanDirectoryAsync: Rueckruf nie sofort (auch nicht
//     bei leerem Pfad), Abbrechen = kein Rueckruf, Eintraege nacheinander;
//     .desktop-Dateien aus dem gelesenen Inhalt (kein zweites Lesen).
//  B. lib/portalScanner.js scanPortalAsync: .desktop asynchron, Abbrechen.
//  C. desklet.js (Methoden aus dem Quelltext, Umgebung nachgebaut):
//     Dialogliste ueber _withOrderScans - Anfragen waehrend eines Durchgangs
//     ergeben genau einen Folgedurchgang, doppelte Ordner werden einmal
//     gelesen, nach der Zeitgrenze kommt {} und ein spaetes Ergebnis nicht
//     noch einmal, Abbrechen verwirft alles; Papierkorb-Rueckfrage wartet
//     hoechstens IO_WAIT_MS; ein Eintrag wird nicht zweimal zugleich
//     verschoben; Sperren/Entsperren baut mit dem letzten Stand neu auf,
//     ohne den Ordner zu lesen.
//  D. Quelltext: keine synchronen Datei- und Ordnerzugriffe mehr in
//     linkScanner.js, itemActions.js, portalScanner.js.
// Aufruf im Repository-Wurzelverzeichnis:  cjs tests/async-io-test.js

const Gio = imports.gi.Gio;
const GLib = imports.gi.GLib;

const UUID = "avincelaunch-desklet@avince";
const shim = GLib.dir_make_tmp("avl-shim-XXXXXX");
GLib.mkdir_with_parents(shim + "/desklets", 0o755);
Gio.File.new_for_path(shim + "/desklets/" + UUID).make_symbolic_link(
    GLib.get_current_dir() + "/Desklet", null);
imports.searchPath.unshift(shim);
if (typeof globalThis.global === "undefined") {
    globalThis.global = { log() {}, logError() {} };
}
// Cinnamon ergaenzt String.prototype.format ("%s", "%d") - hier nachgebildet.
if (typeof String.prototype.format !== "function") {
    String.prototype.format = function(...values) {
        let index = 0;
        return this.replace(/%[sd]/g, () => String(values[index++]));
    };
}
const L = imports.desklets[UUID].lib;
const { scanDirectoryAsync, loadDesktopEntry } = L.linkScanner;
const { scanPortalAsync, ScanGate } = L.portalScanner;

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

function runLoop(ms) {
    const loop = new GLib.MainLoop(null, false);
    GLib.timeout_add(GLib.PRIORITY_DEFAULT, ms, () => { loop.quit(); return GLib.SOURCE_REMOVE; });
    loop.run();
}

// Startet start(callback) und wartet auf den Rueckruf (hoechstens 5 s).
// sync = der Rueckruf kam noch waehrend start() lief.
function wait(start) {
    const state = { done: false, sync: false, value: null };
    const loop = new GLib.MainLoop(null, false);
    let inside = true;
    start(value => {
        state.sync = inside;
        state.done = true;
        state.value = value;
        loop.quit();
    });
    inside = false;
    if (!state.done) {
        const guard = GLib.timeout_add(GLib.PRIORITY_DEFAULT, 5000, () => { loop.quit(); return GLib.SOURCE_REMOVE; });
        loop.run();
        if (state.done) {
            GLib.source_remove(guard);
        }
    }
    return state;
}

const root = GLib.dir_make_tmp("avl-async-XXXXXX");
const D = root + "/Gruppe";
GLib.mkdir_with_parents(D + "/Unterordner", 0o755);
const desktopText = name => "[Desktop Entry]\nType=Application\nName=" + name + "\nComment=Text " + name
    + "\nIcon=folder\nExec=true\n";
for (let i = 0; i < 20; i++) {
    GLib.file_set_contents(D + "/app-" + String(i).padStart(2, "0") + ".desktop", desktopText("App " + i));
}
GLib.file_set_contents(D + "/notiz.txt", "x");

// --- A. scanDirectoryAsync ------------------------------------------------------
print("A. scanDirectoryAsync:");
let r = wait(cb => scanDirectoryAsync(D, { persistOrder: false, sortMode: "name-asc" }, cb));
check("Ergebnis kommt, aber nicht sofort (asynchron)", [r.done, r.sync], [true, false]);
check("alle Eintraege, Reihenfolge nach Namen",
    [r.value.items.length, r.value.items[0].name, r.value.items[19].name, r.value.error], [22, "App 0", "App 9", null]);
const app = r.value.items.find(i => i.fileName === "app-05.desktop");
check(".desktop aus dem gelesenen Inhalt: Name, Beschreibung, Symbol, startbar",
    [app.name, app.comment, app.icon ? app.icon.to_string() : null, !!app.appInfo, app.path],
    ["App 5", "Text App 5", "folder", true, D + "/app-05.desktop"]);
r = wait(cb => scanDirectoryAsync("", {}, cb));
check("leerer Pfad: 'missing', ebenfalls nicht sofort", [r.value.error, r.sync], ["missing", false]);
r = wait(cb => scanDirectoryAsync(root + "/fehlt", {}, cb));
check("fehlender Ordner: 'missing', leere Liste, Reihenfolge-Datei leer",
    [r.value.error, r.value.items.length, r.value.manualItems.length, r.value.sidecar.order], ["missing", 0, 0, []]);
let cancelled = "kein Rueckruf";
scanDirectoryAsync(D, {}, value => { cancelled = value; }).cancel();
runLoop(300);
check("sofort abgebrochen: kein Rueckruf", cancelled, "kein Rueckruf");
// Mitten im Einlesen abbrechen: nach dem Auflisten, waehrend die .desktop-
// Dateien einzeln gelesen werden.
cancelled = "kein Rueckruf";
const midway = scanDirectoryAsync(D, {}, value => { cancelled = value; });
// Nach dem dritten erledigten Schritt der Hauptschleife abbrechen; ein
// Zeitgeber haelt die Schleife wach, damit iteration() nie endlos wartet.
let polls = 0;
const ctx = GLib.MainContext.default();
const tick = GLib.timeout_add(GLib.PRIORITY_DEFAULT, 5, () => GLib.SOURCE_CONTINUE);
while (polls < 200 && cancelled === "kein Rueckruf") {
    ctx.iteration(true);
    polls += 1;
    if (polls === 3) {
        midway.cancel();
    }
}
GLib.source_remove(tick);
runLoop(200);
check("mitten im Einlesen abgebrochen: kein Rueckruf", cancelled, "kein Rueckruf");

let desktop = wait(cb => loadDesktopEntry(D + "/app-01.desktop", "app-01.desktop", null, cb));
check("loadDesktopEntry: liest asynchron", [desktop.value.name, desktop.sync], ["App 1", false]);
desktop = wait(cb => loadDesktopEntry(D + "/gibtsnicht.desktop", "gibtsnicht.desktop", null, cb));
check("loadDesktopEntry: fehlt -> null", desktop.value, null);

// --- B. scanPortalAsync -----------------------------------------------------------
print("B. scanPortalAsync:");
r = wait(cb => scanPortalAsync(D, { sortMode: "name-asc" }, cb));
check("Portal: .desktop asynchron gelesen, alle Eintraege, nicht sofort",
    [r.value.items.length, r.value.items.filter(i => i.type === "app").length, r.value.items[0].name, r.sync],
    [22, 20, "App 0", false]);
cancelled = "kein Rueckruf";
scanPortalAsync(D, {}, value => { cancelled = value; }).cancel();
runLoop(300);
check("Portal: abgebrochen -> kein Rueckruf", cancelled, "kein Rueckruf");

// --- C. desklet.js ----------------------------------------------------------------
print("C. desklet.js:");
const source = new TextDecoder().decode(GLib.file_get_contents("Desklet/desklet.js")[1]);
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

// C1 Dialogliste: ein Durchgang zugleich, Anfragen sammeln sich.
const reads = [];
const pending = [];
const orderFence = {
    actor: { is_finalized: () => false },
    folder_sort: "mixed",
    sort_mode: "manual",
    _orderJob: null,
    _scanDirectoryAsync(path, options, done) {
        reads.push(path + (options.persistOrder ? " (festschreiben)" : ""));
        pending.push(() => done({ items: [], manualItems: [], error: null, path: path }));
        return { cancel() { reads.push("abgebrochen " + path); } };
    }
};
["_withOrderScans", "_orderScanKey", "_orderScanResult", "_startOrderScans", "_onOrderScansDone",
 "_cancelOrderScans"].forEach(n => { orderFence[n] = method(n, { global: globalThis.global }); });
function makeOrderGate(timeoutMs) {
    orderFence._orderGate = new ScanGate(
        (job, done) => orderFence._startOrderScans(job, done),
        (job, result) => orderFence._onOrderScansDone(job, result),
        { timeoutMs: timeoutMs, timeoutResult: () => ({}) });
}
makeOrderGate(5000);
const answers = [];
orderFence._withOrderScans([{ path: "/g/A" }], res => answers.push(["erste", Object.keys(res).length]));
check("erste Anfrage liest sofort", reads, ["/g/A"]);
orderFence._withOrderScans([{ path: "/g/B" }, { path: "/g/A" }], res => answers.push(["zweite", Object.keys(res).length]));
orderFence._withOrderScans([{ path: "/g/B" }, { path: "" }], res => answers.push(["dritte", Object.keys(res).length]));
orderFence._withOrderScans([{ path: "/g/A", options: { persistOrder: true, ignoreSavedOrder: true } }],
    res => answers.push(["vierte", Object.keys(res).length]));
check("waehrend des Durchgangs: nichts weiter gelesen", reads, ["/g/A"]);
pending.shift()();
check("erste beantwortet, dann EIN Folgedurchgang fuer alle wartenden", answers, [["erste", 1]]);
while (pending.length) {
    pending.shift()();
}
check("Folgedurchgang: jeder Ordner einmal, leerer Pfad nicht, Festschreiben getrennt",
    reads, ["/g/A", "/g/B", "/g/A", "/g/A (festschreiben)"]);
check("alle drei wartenden Rueckrufe mit allen Ergebnissen", answers,
    [["erste", 1], ["zweite", 3], ["dritte", 3], ["vierte", 3]]);
check("Ergebnis je Ordner abrufbar (ohne Festschreiben)",
    [!!orderFence._orderScanResult({ [orderFence._orderScanKey("/g/B", {})]: { ok: 1 } }, "/g/B"),
     orderFence._orderScanResult({}, "/g/B")], [true, null]);

// C2 Zeitgrenze: {} genau einmal, spaetes Ergebnis zaehlt nicht noch einmal.
makeOrderGate(60);
reads.length = 0;
answers.length = 0;
orderFence._withOrderScans([{ path: "/nas/X" }], res => answers.push(JSON.stringify(res)));
runLoop(150);
check("haengt: nach der Zeitgrenze {} (wie nicht lesbar)", answers, ["{}"]);
pending.shift()();
check("spaetes Ergebnis: kein zweiter Rueckruf", answers.length, 1);

// C3 Abbrechen (Fence entfernt, Ordner gewechselt): kein Rueckruf.
makeOrderGate(5000);
reads.length = 0;
answers.length = 0;
orderFence._withOrderScans([{ path: "/g/C" }], () => answers.push("laufend"));
orderFence._withOrderScans([{ path: "/g/D" }], () => answers.push("wartend"));
orderFence._cancelOrderScans();
check("abgebrochen: Lesen abgebrochen, nichts gesammelt",
    [reads, orderFence._orderJob, orderFence._orderGate.busy], [["/g/C", "abgebrochen /g/C"], null, false]);
pending.splice(0).forEach(fn => fn());
runLoop(50);
check("abgebrochen: kein Rueckruf", answers, []);

// C4 Papierkorb-Rueckfrage: wartet hoechstens IO_WAIT_MS auf das Zaehlen.
const dialogs = [];
const removeFence = {
    actor: { is_finalized: () => false },
    _busyItems: {},
    _ioCancellable: new Gio.Cancellable()
};
let countCallback = null;
const removeDeps = {
    _: s => s,
    GLib: GLib,
    Mainloop: {
        timeout_add: (ms, fn) => GLib.timeout_add(GLib.PRIORITY_DEFAULT, ms, fn),
        source_remove: id => GLib.source_remove(id)
    },
    IO_WAIT_MS: 80,
    countEntries: (path, cancellable, cb) => { countCallback = cb; },
    ModalDialog: { ConfirmDialog: function(text) { this.open = () => dialogs.push(text.split("\n")[0]); } }
};
["_confirmRemoveItem", "_lockItem", "_unlockItem", "_isGone"].forEach(n => { removeFence[n] = method(n, removeDeps); });
const folder = { type: "folder", name: "Werkzeuge", fileName: "Werkzeuge" };
removeFence._confirmRemoveItem(folder, "/g");
removeFence._confirmRemoveItem(folder, "/g");
check("Zaehlen laeuft: noch keine Rueckfrage, zweiter Klick startet nichts", dialogs, []);
countCallback(7);
check("gezaehlt: Rueckfrage mit Anzahl", dialogs,
    ["Move the folder “Werkzeuge” with 7 entries to the trash and remove it from this fence?"]);
dialogs.length = 0;
removeFence._confirmRemoveItem(folder, "/g");
runLoop(150);
check("Ordner antwortet nicht: nach IO_WAIT_MS Rueckfrage mit 0 (wie bei Lesefehler)", dialogs,
    ["Move the folder “Werkzeuge” with 0 entries to the trash and remove it from this fence?"]);
countCallback(3);
check("spaete Zahl: keine zweite Rueckfrage", dialogs.length, 1);
// Ordnerwechsel: das Cancellable wird abgebrochen und ersetzt.
dialogs.length = 0;
removeFence._confirmRemoveItem(folder, "/g");
const old = removeFence._ioCancellable;
old.cancel();
removeFence._ioCancellable = new Gio.Cancellable();
runLoop(150);
check("Ordner gewechselt: keine Rueckfrage fuer den alten Eintrag", dialogs, []);
removeFence._ioCancellable.cancel();
dialogs.length = 0;
removeFence._confirmRemoveItem(folder, "/g");
countCallback(2);
check("Fence entfernt: keine Rueckfrage mehr", dialogs, []);

// C5 Verschieben: derselbe Eintrag nicht zweimal zugleich.
const moves = [];
const moveFence = {
    actor: { is_finalized: () => false },
    _busyItems: {},
    _ioCancellable: new Gio.Cancellable(),
    _getFenceTitle: () => "QUELLE",
    _itemsChanged(paths) { moves.push("geaendert " + paths.join(",")); },
    _notifyMoved(record, name) { moves.push("gemeldet " + name); }
};
let moveCallback = null;
const moveDeps = {
    _: s => s,
    global: globalThis.global,
    Main: { notify: text => moves.push("meldung " + text) },
    ModalDialog: removeDeps.ModalDialog,
    moveEntry: (src, dst, name, id, cb) => { moves.push("verschiebe " + name); moveCallback = cb; }
};
["_moveItemTo", "_lockItem", "_unlockItem", "_isGone"].forEach(n => { moveFence[n] = method(n, moveDeps); });
const entry = { name: "Firefox", fileName: "firefox.desktop", id: "app:firefox.desktop" };
moveFence._moveItemTo(entry, "/g/A", { path: "/g/B", title: "ZIEL" });
moveFence._moveItemTo(entry, "/g/A", { path: "/g/B", title: "ZIEL" });
check("Doppelklick: nur einmal verschoben", moves, ["verschiebe firefox.desktop"]);
moveCallback({ ok: true, record: {} });
check("Ergebnis: Fences aktualisiert, Meldung", moves.slice(1), ["geaendert /g/A,/g/B", "gemeldet Firefox"]);
moveFence._moveItemTo(entry, "/g/A", { path: "/g/B", title: "ZIEL" });
check("danach wieder frei", moves[moves.length - 1], "verschiebe firefox.desktop");

// C6 Sperren baut mit dem letzten Stand neu auf, ohne den Ordner zu lesen
// (Schreibtischtest: waehrend der Ordner hing, kam beim Entsperren keine
// Titelzeile zum Ziehen).
const surface = [];
const lockFence = {
    actor: { is_finalized: () => false },
    _lastScanResult: null,
    _surfaceRebuildId: 0,
    _scheduleRefresh() { surface.push("liest den Ordner"); },
    _resetSurfaceState() { surface.push("Flaeche geleert"); },
    _buildUI(result) { surface.push("aufgebaut " + result.items.length); }
};
["_rebuildSurfaceSoon", "_rebuildFromLastScan"].forEach(n => {
    lockFence[n] = method(n, { GLib: GLib, Mainloop: { idle_add: fn => GLib.idle_add(GLib.PRIORITY_DEFAULT, fn) } });
});
lockFence._rebuildSurfaceSoon();
check("Sperren ohne gelesenen Stand: wie bisher einlesen", surface, ["liest den Ordner"]);
surface.length = 0;
lockFence._lastScanResult = { items: [1, 2, 3], error: null };
lockFence._rebuildSurfaceSoon();
lockFence._rebuildSurfaceSoon();
runLoop(50);
check("Sperren mit gelesenem Stand: einmal neu aufgebaut, nichts gelesen", surface,
    ["Flaeche geleert", "aufgebaut 3"]);
["_lockMenuItem", "_lockSizeItem"].forEach(name => {
    const at = source.indexOf("this." + name + " = ");
    const handler = source.substring(source.lastIndexOf(".connect(\"toggled\"", at), at);
    check(name + ": Umschalten baut aus dem letzten Stand neu auf",
        [handler.indexOf("this._rebuildSurfaceSoon();") > 0, handler.indexOf("this._scheduleRefresh();")], [true, -1]);
});
check("Ordnerwechsel vergisst den letzten Stand",
    /this\._linkOrderListPending = false;\s*\/\/[^\n]*\n\s*this\._lastScanResult = null;/.test(methodSource("_applyStoragePath")), true);

// --- D. Quelltext -------------------------------------------------------------------
print("D. Quelltext:");
const SYNC_PATTERNS = ["file_test", "file_get_contents", "query_exists", "enumerate_children(",
    "query_info(", "next_file(", ".read(null", "new_from_filename", "file_read_link"];
["linkScanner.js", "itemActions.js", "portalScanner.js"].forEach(name => {
    const text = new TextDecoder().decode(GLib.file_get_contents("Desklet/lib/" + name)[1]);
    check(name + ": keine synchronen Datei- und Ordnerzugriffe",
        SYNC_PATTERNS.filter(pattern => text.indexOf(pattern) !== -1), []);
});
check("desklet.js: kein synchrones Einlesen der Fence-Ordner mehr",
    [/[^.]scanDirectory\(/.test(source), /this\._scanDirectory\(/.test(source), source.indexOf("scanLinkDirectoryAsync")],
    [false, false, -1]);

GLib.spawn_command_line_sync("rm -rf " + GLib.shell_quote(root) + " " + GLib.shell_quote(shim));
print("");
print("Geprueft: " + checks + ", Fehler: " + failures);
if (failures > 0) {
    imports.system.exit(1);
}
