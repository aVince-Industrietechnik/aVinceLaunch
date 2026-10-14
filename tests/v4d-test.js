// SPDX-License-Identifier: GPL-3.0-only
// Copyright (c) 2026 Angelo Vincenti, aVince Industrietechnik

// Schritt 4, V4d - Link-Ordner auf einem Netzlaufwerk asynchron lesen.
//  A. lib/portalScanner.js scanLinkDirectoryAsync liefert fuer denselben
//     Ordner dasselbe wie linkScanner.scanDirectory (Reihenfolge-Datei,
//     Anpinnen, Ausblenden, Stile, Verweise, versteckte und defekte Eintraege,
//     alle Sortierarten), auch ueber mehrere Stapel; schreibt nichts.
//  B. Fehler (fehlt, Datei statt Ordner, nicht lesbar) wie scanDirectory;
//     abgebrochen = kein Ergebnis.
//  C. desklet.js im Netz-Modus (Methoden aus dem Quelltext, Umgebung
//     nachgebaut): beim Einrichten kein synchroner Zugriff auf den Ordner
//     (keine Pruefung, kein Anlegen, keine Dialogliste, kein Ordnerwaechter);
//     _refresh liest nur ueber das ScanGate; fehlt der eigene Ordner, wird er
//     erst nach der Antwort angelegt (einmal) und neu eingelesen; die
//     Dialogliste kommt aus dem ersten Ergebnis; Nachsehen baut nur bei
//     Aenderung neu auf; "nicht erreichbar" nach der Zeitgrenze, danach
//     Nachsehen alle 60 s; Klick auf einen Ordner liest nicht synchron.
//     Lokal bleibt der bisherige Weg.
// Aufruf im Repository-Wurzelverzeichnis:  cjs tests/v4d-test.js

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
const L = imports.desklets[UUID].lib;
const { scanLinkDirectoryAsync, ScanGate } = L.portalScanner;

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

// Asynchron einlesen und auf das Ergebnis warten (hoechstens 5 s).
function scanAsync(path, options) {
    let result = null;
    const loop = new GLib.MainLoop(null, false);
    scanLinkDirectoryAsync(path, options, r => { result = r; loop.quit(); });
    const guard = GLib.timeout_add(GLib.PRIORITY_DEFAULT, 5000, () => { loop.quit(); return GLib.SOURCE_REMOVE; });
    loop.run();
    if (result) {
        GLib.source_remove(guard);
    }
    return result;
}

function iconText(icon) {
    return icon && icon.to_string ? String(icon.to_string()) : String(icon || "");
}
function plain(result) {
    if (!result) {
        return null;
    }
    const item = i => [i.id, i.type, i.name, i.fileName, i.path, i.enabled, !!i.pinned,
        i.bgColor || "", i.iconTint || "", iconText(i.icon), i.mtime || 0, i.ctime || 0];
    return {
        error: result.error,
        items: (result.items || []).map(item),
        manual: (result.manualItems || []).map(i => i.id),
        order: (result.sidecar && result.sidecar.order) || [],
        clickMode: result.sidecar ? result.sidecar.folderClickMode : null
    };
}
function desktop(path, name, extra) {
    GLib.file_set_contents(path, "[Desktop Entry]\nType=Application\nName=" + name + "\nExec=true\n" + (extra || ""));
}

const root = GLib.dir_make_tmp("avl-v4d-XXXXXX");
const D = root + "/Gruppe";
const OUT = root + "/aussen";
GLib.mkdir_with_parents(D + "/Ordner", 0o755);
GLib.mkdir_with_parents(OUT + "/Ziel", 0o755);
desktop(D + "/b.desktop", "Bravo");
desktop(D + "/a.desktop", "Alpha");
desktop(D + "/versteckt.desktop", "Versteckt", "NoDisplay=true\n");
GLib.file_set_contents(D + "/kaputt.desktop", "[Desktop Entry]\nName=Ohne Exec\n");
GLib.file_set_contents(D + "/notiz.txt", "x");
GLib.file_set_contents(D + "/.unsichtbar", "x");
desktop(OUT + "/c.desktop", "Charlie");
Gio.File.new_for_path(D + "/verweis.desktop").make_symbolic_link(OUT + "/c.desktop", null);
Gio.File.new_for_path(D + "/Zielordner").make_symbolic_link(OUT + "/Ziel", null);
Gio.File.new_for_path(D + "/defekt").make_symbolic_link(OUT + "/gibt-es-nicht", null);
GLib.file_set_contents(D + "/.avincelaunch.json", JSON.stringify({
    version: 1,
    order: ["app:b.desktop", "folder:Ordner", "app:a.desktop", "document:notiz.txt"],
    disabled: ["app:a.desktop"],
    pinned: ["document:notiz.txt"],
    folderClickMode: "open-file-manager",
    itemStyles: { "folder:Ordner": { bgColor: "#112233" } }
}));

// --- A. gleiches Ergebnis -----------------------------------------------------
print("A. asynchron = synchron:");
const readText = path => new TextDecoder().decode(GLib.file_get_contents(path)[1]);
const sidecarBefore = readText(D + "/.avincelaunch.json");
let allSame = true;
const modes = ["manual", "name-asc", "name-desc", "type", "modified", "added"];
const folderSorts = ["mixed", "folders-first", "folders-last"];
for (const sortMode of modes) {
    for (const folderSort of folderSorts) {
        const options = { persistOrder: false, sortMode: sortMode, folderSort: folderSort };
        const a = plain(scanAsync(D, options));
        const s = plain(L.linkScanner.scanDirectory(D, options));
        if (JSON.stringify(a) !== JSON.stringify(s)) {
            allSame = false;
            check("gleich: " + sortMode + "/" + folderSort, a, s);
        }
    }
}
check("alle 18 Sortierarten gleich", allSame, true);
const manual = plain(scanAsync(D, { persistOrder: false }));
// Angepinnt vorn, dann gespeicherte Reihenfolge, Rest nach Namen (Charlie,
// Versteckt, Zielordner); ohne .unsichtbar, defekten Verweis, .desktop ohne Exec.
check("Inhalt wie erwartet (Angepinnte vorn, Verweise, ohne Versteckte/Defekte)",
    manual.items.map(i => i[0]),
    ["document:notiz.txt", "app:b.desktop", "folder:Ordner", "app:a.desktop", "app:verweis.desktop",
     "app:versteckt.desktop", "folder:Zielordner"]);
check("ausgeblendet, angepinnt, Stil, Klickart aus der Reihenfolge-Datei",
    [manual.items.find(i => i[0] === "app:a.desktop")[5], manual.items[0][6],
     manual.items.find(i => i[0] === "folder:Ordner")[7], manual.clickMode],
    [false, true, "#112233", "open-file-manager"]);
check("asynchron schreibt nichts", readText(D + "/.avincelaunch.json"), sidecarBefore);

const E = root + "/leer-ohne-datei";
GLib.mkdir_with_parents(E, 0o755);
desktop(E + "/x.desktop", "X");
scanAsync(E, { persistOrder: false });
check("ohne Reihenfolge-Datei: keine angelegt", GLib.file_test(E + "/.avincelaunch.json", GLib.FileTest.EXISTS), false);

const M = root + "/viele";
GLib.mkdir_with_parents(M, 0o755);
for (let i = 0; i < 150; i++) {
    GLib.file_set_contents(M + "/datei-" + String(i).padStart(3, "0") + ".txt", "x");
}
const many = plain(scanAsync(M, { persistOrder: false, sortMode: "name-asc" }));
check("150 Eintraege (3 Stapel) vollstaendig und gleich",
    [many.items.length, JSON.stringify(many) === JSON.stringify(plain(L.linkScanner.scanDirectory(M,
        { persistOrder: false, sortMode: "name-asc" })))], [150, true]);

// --- B. Fehler und Abbrechen --------------------------------------------------
print("B. Fehler und Abbrechen:");
check("fehlt -> missing (wie synchron)",
    [scanAsync(root + "/gibt-es-nicht", {}).error, L.linkScanner.scanDirectory(root + "/gibt-es-nicht", { persistOrder: false }).error],
    ["missing", "missing"]);
check("Datei statt Ordner -> missing (wie synchron)",
    [scanAsync(D + "/notiz.txt", {}).error, L.linkScanner.scanDirectory(D + "/notiz.txt", { persistOrder: false }).error],
    ["missing", "missing"]);
const U = root + "/gesperrt";
GLib.mkdir_with_parents(U, 0o755);
GLib.spawn_command_line_sync("chmod 000 " + GLib.shell_quote(U));
const canRead = GLib.access(U, 4) === 0;  // root liest trotzdem
if (!canRead) {
    check("nicht lesbar -> unreadable", scanAsync(U, {}).error, "unreadable");
} else {
    print("  hinweis nicht-lesbar-Fall uebersprungen (laeuft als root)");
}
GLib.spawn_command_line_sync("chmod 755 " + GLib.shell_quote(U));
let cancelledResult = "keins";
const cancellable = scanLinkDirectoryAsync(D, {}, r => { cancelledResult = r; });
cancellable.cancel();
runLoop(300);
check("abgebrochen: kein Ergebnis", cancelledResult, "keins");

// --- C. desklet.js im Netz-Modus ----------------------------------------------
print("C. desklet.js im Netz-Modus:");
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

const NET_ROOT = "/mnt/nas/gruppen/BUERO";
const LOCAL_ROOT = "/home/nutzer/gruppen/BUERO";
let netPaths = [NET_ROOT];
const calls = [];
const scans = [];
const deps = {
    _: s => s,
    GLib: GLib,
    global: { log() {}, logError(e, m) { calls.push("logError " + m); } },
    isNetworkPath: p => netPaths.some(n => p === n || p.indexOf(n + "/") === 0),
    getResolvedPath: () => netPaths.length ? NET_ROOT : LOCAL_ROOT,
    unregisterReadOnlyRoot: () => {},
    ensureLinkDirectory: () => { calls.push("ensureLinkDirectory"); return LOCAL_ROOT; },
    scanLinkDirectoryAsync: (path, options, done) => {
        scans.push({ path: path, options: options, done: done });
        return { cancel() {} };
    }
};
function makeFence() {
    const f = {
        subdirectory: "BUERO",
        folder_sort: "mixed",
        sort_mode: "manual",
        order_folder_path: "",
        actor: { is_finalized: () => false },
        settings: { setValue(k, v) { calls.push("setValue " + k + "=" + v); }, getValue: () => "" },
        _navStack: [],
        _isPortal: () => false,
        _getInstanceId: () => "7",
        _getSourceState: () => "group||",
        _cancelPortalScan() {},
        _stopPortalPoll() {},
        _isDirectoryPath(p) { calls.push("SYNC _isDirectoryPath " + p); return true; },
        _syncOrderListFromDirectory() { calls.push("SYNC _syncOrderListFromDirectory"); },
        _setOrderBrowsePath(p) { calls.push("SYNC _setOrderBrowsePath " + p); },
        _restartFileMonitor() { calls.push("_restartFileMonitor"); },
        _stopFileMonitor() { calls.push("_stopFileMonitor"); },
        _clearOrderListForMissingPath() {},
        _scheduleRefresh() { calls.push("_scheduleRefresh"); },
        _scanDirectory() { calls.push("SYNC _scanDirectory"); return { sidecar: { folderClickMode: "x" } }; },
        _resetSurfaceState() { calls.push("_resetSurfaceState"); },
        _buildMessage(m) { calls.push("_buildMessage " + m.split("\n")[0]); },
        _buildUI(r) { calls.push("_buildUI " + (r.error || (r.items || []).map(i => i.id).join(","))); this._lastScanResult = r; },
        _ensureOwnFolder(anlass) { calls.push("_ensureOwnFolder " + anlass); return { state: this._ensureState }; },
        _applyOrderListScan(p, r) { calls.push("_applyOrderListScan " + p + " " + (r.manualItems || []).length); },
        _updateOrderNavState() { calls.push("_updateOrderNavState"); },
        _isFenceVisible: () => true,
        _ensureState: "angelegt"
    };
    ["_applyStoragePath", "_applyNetworkLinkPath", "_refresh", "_refreshNetworkLink", "_startLinkScan",
     "_onLinkScanResult", "_linkResultSignature", "_cancelLinkScan", "_stopLinkPoll", "_armLinkPoll",
     "_getCurrentPath", "_getCurrentSidecar"].forEach(n => { f[n] = method(n, deps); });
    f._linkGate = new ScanGate((job, done) => f._startLinkScan(job, done),
        (job, result, superseded) => f._onLinkScanResult(job, result, superseded),
        { timeoutMs: 150, timeoutResult: () => ({ items: [], manualItems: [], error: "timeout" }) });
    return f;
}
const syncCalls = () => calls.filter(c => c.indexOf("SYNC ") === 0 || c === "ensureLinkDirectory" || c === "_restartFileMonitor");
const item = (id, extra) => Object.assign({ id: id, type: "app", fileName: id, name: id, enabled: true }, extra || {});
const ok = (ids, extra) => ({ items: ids.map(id => item(id, extra)), manualItems: ids.map(id => item(id)),
    sidecar: { folderClickMode: "open-file-manager", order: [] }, error: null });

// C1 Einrichten im Netz
let f = makeFence();
calls.length = 0;
check("Netz: _applyStoragePath liefert true", f._applyStoragePath(false), true);
check("Netz: kein synchroner Zugriff beim Einrichten", syncCalls(), []);
check("Netz: Wurzel, Navigation, Ordner fuer den Dialog gesetzt, Refresh geplant",
    [f._linkIsNetwork, f._rootPath, f._navStack.length, f.order_folder_path,
     calls.indexOf("setValue order-folder-path=" + NET_ROOT) >= 0, calls.indexOf("_scheduleRefresh") >= 0],
    [true, NET_ROOT, 1, NET_ROOT, true, true]);

// C2 _refresh -> nur ueber das ScanGate, erster Hinweis "Loading…"
calls.length = 0;
f._refresh();
check("Netz: _refresh startet genau ein asynchrones Einlesen, nichts synchron",
    [scans.length, scans[0].path, scans[0].options.persistOrder, syncCalls()], [1, NET_ROOT, false, []]);
check("Netz: erster Hinweis 'Loading…'", calls.indexOf("_buildMessage Loading…") >= 0, true);
f._refresh();
check("Netz: zweites _refresh waehrend des Einlesens startet nichts", scans.length, 1);

// C3 eigener Ordner fehlt -> erst nach der Antwort anlegen, dann neu einlesen
const last = () => scans[scans.length - 1];
calls.length = 0;
scans[0].done({ items: [], manualItems: [], sidecar: {}, error: "missing" });
check("veraltetes Ergebnis (Folgedurchgang vorgemerkt) wird verworfen, Folgedurchgang laeuft",
    [calls.filter(c => c.indexOf("_ensureOwnFolder") === 0 || c.indexOf("_buildUI") === 0), scans.length], [[], 2]);
last().done({ items: [], manualItems: [], sidecar: {}, error: "missing" });
check("Netz: 'missing' -> eigener Ordner wird jetzt angelegt, neu eingelesen",
    [calls.filter(c => c.indexOf("_ensureOwnFolder") === 0), scans.length], [["_ensureOwnFolder Start"], 3]);
calls.length = 0;
last().done(ok(["app:a", "app:b"]));
check("Netz: Ergebnis -> Dialogliste aus dem Ergebnis, Anzeige aufgebaut",
    calls.filter(c => c.indexOf("_applyOrderListScan") === 0 || c.indexOf("_buildUI") === 0 || c === "_updateOrderNavState"),
    ["_applyOrderListScan " + NET_ROOT + " 2", "_updateOrderNavState", "_buildUI app:a,app:b"]);
check("Netz: Nachsehen in 30 s geplant", f._linkPollId > 0, true);
check("Netz: weiterhin nichts synchron", syncCalls(), []);

// C4 Nachsehen: unveraendert -> kein Neuaufbau; geaendert -> Neuaufbau
calls.length = 0;
f._refreshNetworkLink(true);
last().done(ok(["app:a", "app:b"]));
check("Nachsehen unveraendert: kein Neuaufbau, keine zweite Dialogliste",
    calls.filter(c => c.indexOf("_buildUI") === 0 || c.indexOf("_applyOrderListScan") === 0), []);
calls.length = 0;
f._refreshNetworkLink(true);
last().done(ok(["app:a", "app:b"], { pinned: true }));
check("Nachsehen mit geaenderter Nadel: Neuaufbau", calls.filter(c => c.indexOf("_buildUI") === 0), ["_buildUI app:a,app:b"]);
calls.length = 0;
f._refreshNetworkLink(false);
last().done(ok(["app:a", "app:b"], { pinned: true }));
check("ausdrueckliches _refresh baut immer neu auf", calls.filter(c => c.indexOf("_buildUI") === 0).length, 1);
calls.length = 0;
f._refreshNetworkLink(false);
last().done({ items: [], manualItems: [], error: "missing" });
check("fehlt spaeter wieder: nicht noch einmal angelegt, Meldung",
    [calls.filter(c => c.indexOf("_ensureOwnFolder") === 0), calls.filter(c => c.indexOf("_buildUI") === 0)],
    [[], ["_buildUI missing"]]);

// C5 Klick auf einen Ordner liest nicht synchron
calls.length = 0;
f._lastScanResult = ok(["folder:x"]);
check("Klick: Klickart aus dem letzten Ergebnis, ohne synchrones Lesen",
    [f._getCurrentSidecar().folderClickMode, syncCalls()], ["open-file-manager", []]);

// C6 Zeitgrenze: haengt -> "nicht erreichbar", Nachsehen 60 s
f._stopLinkPoll();
calls.length = 0;
f._refreshNetworkLink(false);
const hung = scans.length;
runLoop(400);
check("haengt: nach der Zeitgrenze 'timeout' angezeigt", calls.filter(c => c.indexOf("_buildUI") === 0), ["_buildUI timeout"]);
check("haengt: genau ein Durchgang lief", scans.length, hung);
check("haengt: Nachsehen geplant (60 s)", f._linkPollId > 0, true);
f._stopLinkPoll();
f._cancelLinkScan();

// C7 Lokal: bisheriger Weg
netPaths = [];
f = makeFence();
calls.length = 0;
f._applyStoragePath(false);
check("lokal: wie bisher (Pruefung, Ordner fuer den Dialog, Waechter, Dialogliste)",
    [f._linkIsNetwork, calls.indexOf("SYNC _isDirectoryPath " + LOCAL_ROOT) >= 0,
     calls.indexOf("SYNC _setOrderBrowsePath " + LOCAL_ROOT) >= 0, calls.indexOf("_restartFileMonitor") >= 0,
     calls.indexOf("SYNC _syncOrderListFromDirectory") >= 0],
    [false, true, true, true, true]);
check("lokal: kein asynchrones Einlesen", (() => { const n = scans.length; f._getCurrentSidecar(); return scans.length - n; })(), 0);

// C8 Quelltext: Start, Ordnerwaechter, Fehleranzeige, Python -B
check("Start: eigener Ordner nur lokal synchron angelegt",
    /if \(!this\._isPortal\(\) && !isNetworkPath\(getResolvedPath\(this\.subdirectory\)\)\) \{\s*this\._ensureOwnFolder\("Start"\);/.test(source), true);
check("kein Ordnerwaechter im Netz", /if \(!this\._isPortal\(\) && this\._linkIsNetwork\) \{[^}]*return;/.test(methodSource("_restartFileMonitor")), true);
check("Fehleranzeige: Netz meldet 'unreadable'/'timeout' wie das Portal",
    /\(this\._isPortal\(\) \|\| this\._linkIsNetwork\)\s*&& \(scanResult\.error === "unreadable" \|\| scanResult\.error === "timeout"\)/.test(source), true);
check("Abbau bricht auch das Netz-Einlesen ab",
    /this\._cancelLinkScan\(\);\s*this\._stopLinkPoll\(\);/.test(methodSource("_stopBackgroundWork")), true);
check("eigene Dialoge mit python3 -B", (source.match(/\["python3", "-B", /g) || []).length, 2);
check("kein python3 ohne -B", /\["python3", (?!"-B")/.test(source), false);

// Ueber-Dialog (Angelo 14.10.): Leerzeile zwischen den Punkten; Slogan auch
// mit ":" (englische Beschreibung ist fuer Spices ASCII).
const about = new TextDecoder().decode(GLib.file_get_contents("Desklet/about-dialog.py")[1]);
check("Ueber-Dialog: Punkte mit Leerzeile", about.indexOf('parts.append("\\n\\n".join(items))') > 0, true);
check("Ueber-Dialog: Slogan auch mit ':'", about.indexOf('for sep in (" – ", " - ", ": "):') > 0, true);

GLib.spawn_command_line_sync("rm -rf " + GLib.shell_quote(root) + " " + GLib.shell_quote(shim));
print("");
print("Geprueft: " + checks + ", Fehler: " + failures);
if (failures > 0) {
    imports.system.exit(1);
}
