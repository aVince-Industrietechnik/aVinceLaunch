// SPDX-License-Identifier: GPL-3.0-only
// Copyright (c) 2026 Angelo Vincenti, aVince Industrietechnik

// Schritt 4, V2 - T23/T-A5: Lebenszyklus und Rettungswege ohne Cinnamon.
// Bisher waren diese Stellen nur am Code belegt (Befund T23); hier laufen
// sie mit nachgebauten Cinnamon-Teilen in einem Wegwerfordner:
//  A. desklet.js destroy/_stopBackgroundWork (P49): Zeitgeber, Ordner-
//     waechter, Portal-Einlesen enden VOR Cinnamons destroy; mehrfach
//     aufrufbar.
//  B. desklet.js _releaseSettings (P81) mit gespieltem Main.settingsManager:
//     eigene Anmeldung -> finalize, neue Instanz angemeldet -> nur eigene
//     Bindungen loesen.
//  C. desklet.js on_desklet_removed: Groessen vergessen nur beim Entfernen
//     durch den Nutzer, Einstellungen zuletzt freigeben.
//  D. lib/placement.js _syncDefinition (P13) mit gespieltem deskletManager:
//     Cinnamons Kopie (definitions) folgt der Lage, auch wenn die Liste schon
//     stimmt; leises Schreiben haengt den Listener ab und wieder an.
//  E. lib/layoutManager.js saveLayoutStore/pruneOrphanFenceLayouts/
//     forgetFenceLayout (P3, P48, AP18-5) mit umgeleitetem XDG_CONFIG_HOME;
//     eine kaputte layout.json wird nie ueberschrieben.
//  F. desklet.js _backupSettingsFile/configureDesklet (B12): Sicherung der
//     <ID>.json vor allem anderen, auch vor dem Zuruecksetzen des Ordners;
//     N11: das Einrichten-Fenster startet mit Fehlermitschrift (Befehl echt
//     ausgefuehrt mit einem gespielten xlet-settings), sonst Cinnamons Weg.
// Aufruf im Repository-Wurzelverzeichnis:  cjs tests/t23-lebenszyklus-test.js

const Gio = imports.gi.Gio;
const GLib = imports.gi.GLib;

// Vor dem ersten Zugriff auf die Benutzerordner.
const work = GLib.dir_make_tmp("avl-t23-XXXXXX");
GLib.setenv("XDG_CONFIG_HOME", work + "/config", true);
GLib.setenv("XDG_CACHE_HOME", work + "/cache", true);
function requireRedirect(dirs) {
    const wrong = dirs.filter(([name, actual, expected]) => actual !== expected)
        .map(([name, actual]) => name + "=" + actual);
    if (wrong.length > 0) {
        printerr("ABBRUCH: Umleitung in den Wegwerfordner greift nicht (" + wrong.join(", ")
            + ") - nichts geschrieben.");
        imports.system.exit(2);
    }
}
requireRedirect([
    ["XDG_CONFIG_HOME", GLib.get_user_config_dir(), work + "/config"],
    ["XDG_CACHE_HOME", GLib.get_user_cache_dir(), work + "/cache"]
]);

const UUID = "avincelaunch-desklet@avince";
const shim = GLib.dir_make_tmp("avl-shim-XXXXXX");
GLib.mkdir_with_parents(shim + "/desklets", 0o755);
Gio.File.new_for_path(shim + "/desklets/" + UUID).make_symbolic_link(
    GLib.get_current_dir() + "/Desklet", null);
// D: Cinnamons deskletManager als Modul imports.ui.deskletManager nachbauen.
GLib.mkdir_with_parents(shim + "/ui", 0o755);
GLib.file_set_contents(shim + "/ui/deskletManager.js",
    "var deskletChangeKey = 7;\n"
    + "var definitions = [];\n"
    + "var calls = 0;\n"
    + "function _onEnabledDeskletsChanged() { calls += 1; }\n");
imports.searchPath.unshift(shim);

const logs = [];
// Nachbildung von global.settings (enabled-desklets, Raster aus).
const fakeSettings = {
    strv: [],
    writes: 0,
    events: [],
    get_strv(key) { return this.strv.slice(); },
    set_strv(key, list) { this.writes += 1; this.events.push("set"); this.strv = list.slice(); },
    get_boolean() { return false; },
    get_int() { return 0; },
    connect(signal, handler) { this.events.push("connect " + signal); this.handler = handler; return 8; },
    disconnect(id) { this.events.push("disconnect " + id); }
};
globalThis.global = {
    settings: fakeSettings,
    log(message) { logs.push(String(message)); },
    logError(e, message) { logs.push("FEHLER " + (message || e)); }
};

const SafeJson = imports.desklets[UUID].lib.safeJson;
const SettingsBackup = imports.desklets[UUID].lib.settingsBackup;
const { ScanGate } = imports.desklets[UUID].lib.portalScanner;

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

// Methode aus desklet.js mit den angegebenen Modul-Namen (deps) ausfuehren.
function method(name, deps) {
    const names = Object.keys(deps || {});
    return new Function(...names, "return " + methodSource(name) + ";")(...names.map(n => deps[n]));
}

// lib/layoutManager.js jedes Mal frisch laden (Modulzustand _orphansPruned),
// ohne St/Meta/Clutter/Main (nur ausserhalb der Ablage gebraucht).
const layoutSource = read("Desklet/lib/layoutManager.js")
    .replace(/^const (Clutter|St|GLib|Meta|Main) = imports\.[a-z]+\.[A-Za-z]+;$/mg, "");
function loadLayoutManager() {
    const fakeGi = new Proxy({}, { get: () => new Proxy({}, { get: () => 0 }) });
    return new Function("Clutter", "St", "GLib", "Meta", "Main", "imports", "global",
        layoutSource + "\nreturn { getLayoutStorePath, loadLayoutStore, saveLayoutStore, "
        + "forgetFenceLayout, pruneOrphanFenceLayouts, setPreviousSize, getPreviousSize };")(
        fakeGi, fakeGi, GLib, fakeGi, {}, imports, globalThis.global);
}

const Mainloop = { source_remove: id => GLib.source_remove(id) };

// --- A. destroy / _stopBackgroundWork (P49) ------------------------------------
print("A. destroy / _stopBackgroundWork (P49):");
const order = [];
const fired = [];
function timer(name) {
    return GLib.timeout_add(GLib.PRIORITY_DEFAULT, 30, () => { fired.push(name); return GLib.SOURCE_REMOVE; });
}
const stopDeps = { Mainloop: Mainloop, GLib: GLib, unwatchBaseDirectory: f => order.push("unwatch " + f._id) };
const fence = {
    _id: "4",
    _cancelScrollReset: method("_cancelScrollReset", stopDeps),
    _cancelPortalScan: method("_cancelPortalScan", stopDeps),
    _stopPortalPoll: method("_stopPortalPoll", stopDeps),
    _cancelLinkScan: method("_cancelLinkScan", stopDeps),
    _stopLinkPoll: method("_stopLinkPoll", stopDeps),
    _stopFileMonitor: method("_stopFileMonitor", stopDeps),
    _cancelScheduledRefresh: method("_cancelScheduledRefresh", stopDeps),
    _cancelPanelSizeSync: method("_cancelPanelSizeSync", stopDeps),
    _stopBackgroundWork: method("_stopBackgroundWork", stopDeps),
    _stopFenceRect() { order.push("flaechen " + this._id); },
    destroy: method("destroy", {
        Desklet: { Desklet: { prototype: { destroy(deleteConfig) {
            order.push("cinnamon destroy " + deleteConfig + ", Zeitgeber offen: "
                + ["_scrollResetId", "_refreshIdleId", "_sizeSyncId", "_portalPollId", "_linkPollId", "_dialogListSyncId",
                   "_storageChangeTimeoutId", "_presetSettleId", "_applyingPositionId",
                   "_configurePanelTimerId", "_titleSyncId"].filter(k => this[k]).length);
        } } } }
    })
};
["_scrollResetId", "_refreshIdleId", "_sizeSyncId", "_portalPollId", "_linkPollId", "_dialogListSyncId",
 "_storageChangeTimeoutId", "_presetSettleId", "_applyingPositionId", "_configurePanelTimerId",
 "_titleSyncId"].forEach(key => { fence[key] = timer(key); });
fence._refreshPending = true;
fence._scrollView = null;
fence._fileMonitor = { stop() { order.push("monitor stop"); } };
let scanCancelled = 0;
const gateResults = [];
fence._portalGate = new ScanGate(() => ({ cancel() { scanCancelled += 1; } }),
    (job, result) => gateResults.push(result),
    { timeoutMs: 20, timeoutResult: () => "zeit" });
fence._portalGate.request({ name: "laufend" });
fence._portalGate.request({ name: "wartend" });
// V4d: Link-Ordner auf einem Netzlaufwerk - eigenes Einlesen.
let linkScanCancelled = 0;
fence._linkGate = new ScanGate(() => ({ cancel() { linkScanCancelled += 1; } }),
    (job, result) => gateResults.push(result),
    { timeoutMs: 20, timeoutResult: () => "zeit" });
fence._linkGate.request({ name: "netz laufend" });
fence._linkGate.request({ name: "netz wartend" });

fence.destroy(true);
check("Reihenfolge: Hintergrundarbeit vor Cinnamons destroy, kein Zeitgeber mehr offen",
    order, ["unwatch 4", "flaechen 4", "monitor stop", "cinnamon destroy true, Zeitgeber offen: 0"]);
check("Portal-Einlesen abgebrochen, nichts wartet", [scanCancelled, fence._portalGate.busy, fence._portalGate.stalled],
    [1, false, 0]);
check("V4d: Netz-Einlesen abgebrochen, nichts wartet",
    [linkScanCancelled, fence._linkGate.busy, fence._linkGate.stalled], [1, false, 0]);
check("Ordnerueberwachung weg, Aktualisierung nicht mehr vorgemerkt",
    [fence._fileMonitor, fence._refreshPending], [null, false]);
runLoop(120);
check("kein Zeitgeber feuert danach (auch nicht die Zeitgrenze des Einlesens)", [fired, gateResults], [[], []]);
order.length = 0;
fence._stopBackgroundWork();
fence._stopBackgroundWork();
check("mehrfach aufrufbar (on_desklet_removed nach destroy)", order,
    ["unwatch 4", "flaechen 4", "unwatch 4", "flaechen 4"]);

// --- B. _releaseSettings (P81) --------------------------------------------------
print("B. _releaseSettings (P81):");
function settingsObject(log) {
    return {
        bindings: { "fence-title": [1], "max-width": [2] },
        finalize() { log.push("finalize"); },
        unbindAll(key) { log.push("unbindAll " + key); },
        disconnectAll() { log.push("disconnectAll"); }
    };
}
function release(registeredFor, makeThrow) {
    const log = [];
    const own = settingsObject(log);
    if (makeThrow) {
        own.unbindAll = () => { throw new Error("weg"); };
    }
    const uuids = {};
    if (registeredFor !== "fehlt") {
        uuids[UUID] = { "4": registeredFor === "eigene" ? own : (registeredFor === "neue" ? settingsObject([]) : null) };
    }
    const desklet = {
        settings: own,
        _getInstanceId: () => "4",
        _releaseSettings: method("_releaseSettings", {
            Main: { settingsManager: { uuids: uuids } }, UUID: UUID, global: globalThis.global
        })
    };
    desklet._releaseSettings();
    return log;
}
check("eigene Anmeldung -> finalize", release("eigene"), ["finalize"]);
check("keine Anmeldung (UUID fehlt) -> finalize", release("fehlt"), ["finalize"]);
check("Anmeldung null -> finalize", release("null"), ["finalize"]);
check("neue Instanz angemeldet -> nur eigene Bindungen loesen, kein finalize",
    release("neue"), ["unbindAll fence-title", "unbindAll max-width", "disconnectAll"]);
logs.length = 0;
check("Fehler beim Loesen wird gemeldet, nicht geworfen", [release("neue", true), logs],
    [[], ["FEHLER aVinceLaunch: Bindungen nicht geloest"]]);
check("ohne settings nichts zu tun", (() => {
    const d = { settings: null, _releaseSettings: method("_releaseSettings", { Main: {}, UUID: UUID, global: globalThis.global }) };
    d._releaseSettings();
    return "ok";
})(), "ok");

// --- C. on_desklet_removed ------------------------------------------------------
print("C. on_desklet_removed:");
function removed(deleteConfig) {
    const steps = [];
    const desklet = {
        _getInstanceId: () => "4",
        _stopBackgroundWork: () => steps.push("stop"),
        _destroySearch: () => steps.push("search"),
        _stopHoverWatch: () => steps.push("hover"),
        _destroyTitleTab: () => steps.push("tab"),
        _destroyItemTooltips: () => steps.push("tooltips"),
        _teardownPlacement: () => steps.push("placement"),
        _releaseSettings: () => steps.push("release"),
        _menuAnchor: { destroy: () => steps.push("anchor") },
        _freeHint: null,
        _focusWindowId: 0,
        on_desklet_removed: method("on_desklet_removed", {
            forgetFenceLayout: id => steps.push("forget " + id),
            unregisterReadOnlyRoot: id => steps.push("unregister " + id),
            global: globalThis.global
        })
    };
    desklet.on_desklet_removed(deleteConfig);
    return steps;
}
const byUser = removed(true);
check("vom Nutzer entfernt: Groessen zuerst vergessen", byUser[0], "forget 4");
check("Einstellungen zuletzt freigeben", byUser[byUser.length - 1], "release");
check("Hintergrundarbeit vor dem Abbau der Bausteine", byUser.indexOf("stop") < byUser.indexOf("search"), true);
check("beim Neustart (nicht entfernt): Groessen bleiben", removed(false).indexOf("forget 4"), -1);

// --- D. placement _syncDefinition (P13) -----------------------------------------
print("D. placement _syncDefinition (P13):");
const Manager = imports.ui.deskletManager;
const P = imports.desklets[UUID].lib.placement;
function definitions() {
    return Manager.definitions.map(d => d.desklet_id + "@" + d.x + "," + d.y);
}
Manager.definitions = [
    { uuid: UUID, desklet_id: "4", x: "50", y: "50" },
    { uuid: UUID, desklet_id: "40", x: "800", y: "550" },
    { uuid: "anderes@x", desklet_id: "4", x: "1", y: "1" }
];
fakeSettings.strv = [UUID + ":4:300:200", UUID + ":40:800:550", "anderes@x:4:1:1"];
fakeSettings.writes = 0;
fakeSettings.events = [];
check("Liste stimmt schon (Cinnamon schrieb beim Ablegen): Rueckgabe",
    P.writeGSettingsPosition(UUID, "4", 300, 200, false), { x: 300, y: 200 });
check("... kein Schreiben der Liste", fakeSettings.writes, 0);
check("... aber Cinnamons Kopie nachgezogen, nur fuer Fence 4 dieses Desklets",
    definitions(), ["4@300,200", "40@800,550", "4@1,1"]);
fakeSettings.events = [];
P.writeGSettingsPosition(UUID, "4", 410, 220, false);
check("neue Lage: Liste leise geschrieben (Listener ab, schreiben, wieder an)",
    fakeSettings.events, ["disconnect 7", "set", "connect changed::enabled-desklets"]);
check("... Liste neu", fakeSettings.strv, [UUID + ":4:410:220", UUID + ":40:800:550", "anderes@x:4:1:1"]);
check("... Kopie nachgezogen", definitions(), ["4@410,220", "40@800,550", "4@1,1"]);
check("... neuer Listener ist Cinnamons eigener", fakeSettings.handler === Manager._onEnabledDeskletsChanged, true);
check("... Cinnamon hat nichts neu aufgebaut", Manager.calls, 0);
fakeSettings.writes = 0;
check("unbekannter Fence: nichts geschrieben",
    [P.writeGSettingsPosition(UUID, "99", 5, 5, false), fakeSettings.writes], [{ x: 5, y: 5 }, 0]);

// --- E. layoutManager: Ablage layout.json (P3, P48, AP18-5) ----------------------
print("E. layoutManager layout.json:");
const STORE = work + "/config/avincelaunch/layout.json";
let L = loadLayoutManager();
check("Pfad im umgeleiteten Konfigurationsordner", L.getLayoutStorePath(), STORE);
check("leer ohne Datei", L.loadLayoutStore(), { version: 1 });
check("saveLayoutStore legt Ordner und Datei an",
    [L.saveLayoutStore({ history: ["h1"], fremd: { a: 1 } }), GLib.file_test(STORE, GLib.FileTest.EXISTS)], [true, true]);
check("version ergaenzt, Inhalt erhalten", JSON.parse(read(STORE)), { history: ["h1"], fremd: { a: 1 }, version: 1 });
L.setPreviousSize("4", { w: 360, h: 210 });
L.setPreviousSize("42", { w: 100, h: 100 });
const stored = JSON.parse(read(STORE));
stored.originalSize = { "4": { w: 300, h: 200 }, "42": { w: 1, h: 1 }, "77": { w: 2, h: 2 } };
GLib.file_set_contents(STORE, JSON.stringify(stored));
check("unbekannte Felder bleiben beim Schreiben", [stored.fremd, stored.history], [{ a: 1 }, ["h1"]]);

fakeSettings.strv = [UUID + ":4:0:0", UUID + ":7:0:0", "anderes@x:42:0:0"];
logs.length = 0;
check("pruneOrphanFenceLayouts: Fences ausserhalb enabled-desklets vergessen (auch gleiche ID eines anderen Desklets)",
    L.pruneOrphanFenceLayouts(UUID), ["42", "77"]);
const pruned = JSON.parse(read(STORE));
check("... Groessen der lebenden bleiben, Verlauf bleibt",
    [Object.keys(pruned.previousSize), Object.keys(pruned.originalSize), pruned.history], [["4"], ["4"], ["h1"]]);
check("... eine Zeile im Protokoll", logs, ["aVinceLaunch: Groessen entfernter Fences vergessen: 42, 77"]);
pruned.previousSize["55"] = { w: 1, h: 1 };
GLib.file_set_contents(STORE, JSON.stringify(pruned));
check("nur einmal je Start", L.pruneOrphanFenceLayouts(UUID), []);
L = loadLayoutManager();
fakeSettings.strv = [];
check("leere Liste (nicht lesbar/Start): nichts vergessen", L.pruneOrphanFenceLayouts(UUID), []);
check("... 55 noch da", "55" in JSON.parse(read(STORE)).previousSize, true);

check("forgetFenceLayout: beide Abschnitte", L.forgetFenceLayout("4"), true);
const forgot = JSON.parse(read(STORE));
check("... 4 weg, 55 bleibt", [Object.keys(forgot.previousSize), Object.keys(forgot.originalSize)], [["55"], []]);
check("forgetFenceLayout ohne Eintrag schreibt nicht", L.forgetFenceLayout("4"), false);

// P3: kaputte layout.json bleibt liegen, wird gesichert, nie ueberschrieben.
const BROKEN = '{"previousSize": {"4": ';
GLib.file_set_contents(STORE, BROKEN);
logs.length = 0;
L = loadLayoutManager();
check("kaputt: Laden liefert leer", L.loadLayoutStore(), { version: 1 });
check("kaputt: saveLayoutStore schreibt nicht", L.setPreviousSize("4", { w: 9, h: 9 }), false);
check("kaputt: Datei unveraendert", read(STORE), BROKEN);
const dirList = [];
const dirHandle = GLib.Dir.open(work + "/config/avincelaunch", 0);
let entry;
while ((entry = dirHandle.read_name()) !== null) {
    dirList.push(entry);
}
dirHandle.close();
const brokenCopies = dirList.filter(n => n.indexOf("layout.json.broken-") === 0);
check("kaputt: genau eine Kopie layout.json.broken-<Zeit> mit dem Inhalt",
    [brokenCopies.length, brokenCopies.length ? read(work + "/config/avincelaunch/" + brokenCopies[0]) : null],
    [1, BROKEN]);
check("kaputt: gemeldet (einmal)", logs.filter(l => l.indexOf("layout.json ist nicht lesbar") >= 0).length, 1);
check("kaputt: pruneOrphanFenceLayouts schreibt nicht",
    (() => { fakeSettings.strv = [UUID + ":1:0:0"]; L.pruneOrphanFenceLayouts(UUID); return read(STORE); })(), BROKEN);

// --- F. _backupSettingsFile / configureDesklet (B12) -----------------------------
print("F. _backupSettingsFile / configureDesklet (B12):");
const SPICES = work + "/config/cinnamon/spices/" + UUID;
GLib.mkdir_with_parents(SPICES, 0o755);
GLib.file_set_contents(SPICES + "/4.json", '{"fence-title": {"value": "BUERO"}}\n');
const BACKUPS = SettingsBackup.backupDirFor(work + "/config", "4");
check("Sicherungsordner unter dem umgeleiteten Konfigurationsordner",
    BACKUPS, work + "/config/avincelaunch/backups/einstellungen-4");

function backupCopies() {
    if (!GLib.file_test(BACKUPS, GLib.FileTest.IS_DIR)) {
        return [];
    }
    const names = [];
    const h = GLib.Dir.open(BACKUPS, 0);
    let n;
    while ((n = h.read_name()) !== null) {
        if (n.endsWith(".json")) {
            names.push(n);
        }
    }
    h.close();
    return names.sort();
}

const steps = [];
const timers = [];
const dialogFence = {
    _rootPath: "/basis/BUERO",
    _getInstanceId: () => "4",
    _keepDialogListInSubfolder: () => { steps.push("keep?"); return false; },
    _syncDialogListIfClean: () => steps.push("sync"),
    _reloadOrderSettingsFromPanel: () => steps.push("reload"),
    _configurePanelTimerId: 0
};
// Cinnamons bindProperty schreibt bei jeder Zuweisung sofort (settings.js:375).
Object.defineProperty(dialogFence, "order_folder_path", {
    set(v) { steps.push("schreibt order-folder-path=" + v); }, get() { return ""; }
});
Object.defineProperty(dialogFence, "order_in_subfolder", {
    set(v) { steps.push("schreibt order-in-subfolder=" + v); }, get() { return false; }
});
const realBackup = method("_backupSettingsFile", {
    MeLib: { settingsBackup: SettingsBackup }, GLib: GLib, UUID: UUID
});
dialogFence._backupSettingsFile = function() {
    steps.push("sichern");
    return realBackup.call(this);
};
const spawned = [];
let spawnFails = false;
const cinnamonDesklet = { Desklet: { prototype: { configureDesklet(tab) { steps.push("dialog cinnamon " + tab); } } } };
dialogFence._spawnSettingsWindow = method("_spawnSettingsWindow", {
    Desklet: cinnamonDesklet,
    GLib: GLib,
    UUID: UUID,
    global: globalThis.global,
    Util: { trySpawn(argv) {
        if (spawnFails) {
            throw new Error("kein sh");
        }
        spawned.push(argv);
        steps.push("dialog " + argv[argv.length - 2]);
        return 1;
    } }
});
dialogFence.configureDesklet = method("configureDesklet", {
    Desklet: cinnamonDesklet,
    Mainloop: {
        source_remove: () => {},
        timeout_add: (ms, fn) => { timers.push([ms, fn]); return 5; }
    },
    GLib: GLib
});
dialogFence.configureDesklet();
check("Reihenfolge: zuerst sichern, dann Ordner zuruecksetzen, dann Dialog",
    steps, ["sichern", "keep?", "schreibt order-folder-path=/basis/BUERO", "schreibt order-in-subfolder=false",
        "sync", "reload", "dialog 0"]);
const copies = backupCopies();
check("genau eine Kopie, Inhalt = <ID>.json",
    [copies.length, copies.length ? read(BACKUPS + "/" + copies[0]) : null],
    [1, '{"fence-title": {"value": "BUERO"}}\n']);
check("Dialog-Merker gesetzt, Zeitgeber 500 ms", [dialogFence._configurePanelOpen, timers.length, timers[0][0]],
    [true, 1, 500]);
timers[0][1].call(dialogFence);
check("nach 500 ms Merker weg", [dialogFence._configurePanelOpen, dialogFence._configurePanelTimerId], [false, 0]);
steps.length = 0;
dialogFence.configureDesklet(2);
check("unveraendert: keine weitere Kopie; Seite wird weitergereicht",
    [backupCopies().length, steps[steps.length - 1]], [1, "dialog 2"]);
GLib.file_set_contents(SPICES + "/4.json", '{"fence-title": {"value": "BUERO 2"}}\n');
dialogFence.configureDesklet();
check("geaendert: neue Kopie", backupCopies().length, 2);
GLib.file_set_contents(SPICES + "/4.json", "");
dialogFence.configureDesklet();
check("leere <ID>.json (Cinnamon schreibt gerade neu) wird nicht gesichert", backupCopies().length, 2);

// N11: Startbefehl wie Cinnamon, Fehlerausgabe in den Cache.
const LOG = work + "/cache/avincelaunch/einrichten-4.log";
check("Startbefehl: sh mit Cinnamons Aufruf, Werte als eigene Argumente",
    spawned[0].slice(0, 2).concat(spawned[0].slice(3)),
    ["sh", "-c", "sh", UUID, "4", "0", LOG]);
check("Befehl startet xlet-settings wie Cinnamon (desklet UUID -i ID -t SEITE)",
    /exec xlet-settings desklet "\$1" -i "\$2" -t "\$3"$/.test(spawned[0][2]), true);
check("Seite wird weitergereicht", spawned[1][spawned[1].length - 2], "2");
check("Cache-Ordner angelegt", GLib.file_test(work + "/cache/avincelaunch", GLib.FileTest.IS_DIR), true);
// Den Befehl wirklich ausfuehren - mit einem gespielten xlet-settings.
const fakeBin = work + "/bin";
GLib.mkdir_with_parents(fakeBin, 0o755);
GLib.file_set_contents(fakeBin + "/xlet-settings",
    "#!/bin/sh\necho \"args: $*\"\necho \"Traceback: Fehler fuer N11\" >&2\n");
GLib.chmod(fakeBin + "/xlet-settings", 0o755);
GLib.file_set_contents(LOG, "alter Inhalt\n");
const argv = spawned[1].slice();
const [, , , status] = GLib.spawn_sync(null, argv,
    ["PATH=" + fakeBin + ":/usr/bin:/bin"], GLib.SpawnFlags.SEARCH_PATH, null);
const logLines = read(LOG).trim().split("\n");
check("Befehl laeuft (Rueckgabe 0)", status, 0);
check("Mitschrift: Startzeit, Aufruf, Fehlerausgabe; alter Inhalt ersetzt",
    [/^\d{4}-\d\d-\d\d \d\d:\d\d:\d\d start$/.test(logLines[0]), logLines.slice(1)],
    [true, ["args: desklet " + UUID + " -i 4 -t 2", "Traceback: Fehler fuer N11"]]);
const odd = argv.slice();
odd[odd.length - 1] = work + "/cache/avincelaunch/mit Leer'zeichen \"$(x).log";
GLib.spawn_sync(null, odd, ["PATH=" + fakeBin + ":/usr/bin:/bin"], GLib.SpawnFlags.SEARCH_PATH, null);
check("Sonderzeichen im Pfad werden nicht ausgewertet",
    GLib.file_test(odd[odd.length - 1], GLib.FileTest.EXISTS), true);
steps.length = 0;
logs.length = 0;
spawnFails = true;
dialogFence.configureDesklet(1);
check("Start mit Mitschrift scheitert: Cinnamons eigener Weg mit derselben Seite, gemeldet",
    [steps[steps.length - 1], logs], ["dialog cinnamon 1", ["FEHLER aVinceLaunch: settings window with log failed"]]);

// --- Aufraeumen --------------------------------------------------------------
SafeJson._resetForTests();
GLib.spawn_command_line_sync("rm -rf " + GLib.shell_quote(work) + " " + GLib.shell_quote(shim));

print("");
print("Geprueft: " + checks + ", Fehler: " + failures);
if (failures > 0) {
    imports.system.exit(1);
}
