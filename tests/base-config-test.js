// SPDX-License-Identifier: GPL-3.0-only
// Copyright (c) 2026 Angelo Vincenti, aVince Industrietechnik

// Prueft die Basisordner-Regel und den config.json-Waechter (Pruefung Phase 2,
// A4-2: P11, P32, P33) ohne Cinnamon in einem Wegwerfordner: lib/config.js.
// Die Faelle der Regel stehen gleich in tests/base-config-test.py (Python-Seite).
// Aufruf im Repository-Wurzelverzeichnis:  cjs tests/base-config-test.js

const Gio = imports.gi.Gio;
const GLib = imports.gi.GLib;

// Vor dem ersten Zugriff auf die Benutzerordner (lib/config.js liest sie beim Laden).
const work = GLib.dir_make_tmp("avl-base-config-XXXXXX");
GLib.setenv("XDG_CONFIG_HOME", work + "/config", true);
GLib.setenv("XDG_DATA_HOME", work + "/data", true);
// A9/P70: Greift die Umleitung nicht (andere cjs-Fassung), sofort abbrechen -
// bevor etwas geschrieben oder aufgeraeumt wird.
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
    ["XDG_DATA_HOME", GLib.get_user_data_dir(), work + "/data"]
]);

const UUID = "avincelaunch-desklet@avince";
const shim = GLib.dir_make_tmp("avl-shim-XXXXXX");
GLib.mkdir_with_parents(shim + "/desklets", 0o755);
Gio.File.new_for_path(shim + "/desklets/" + UUID).make_symbolic_link(
    GLib.get_current_dir() + "/Desklet", null);
imports.searchPath.unshift(shim);
const C = imports.desklets[UUID].lib.config;
const J = imports.desklets[UUID].lib.safeJson;

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

const OWN_DIR = work + "/config/avincelaunch";
const OWN = OWN_DIR + "/config.json";
const LEGACY_DIR = work + "/config/thelauncher";
const LEGACY = LEGACY_DIR + "/config.json";
const DEFAULT = work + "/data/avincelaunch";
const HOME = GLib.get_home_dir();
GLib.mkdir_with_parents(OWN_DIR, 0o755);
GLib.mkdir_with_parents(LEGACY_DIR, 0o755);

function put(path, text) {
    if (text === null) {
        GLib.unlink(path);
    } else {
        GLib.file_set_contents(path, text);
    }
}

function read(path) {
    const [, bytes] = GLib.file_get_contents(path);
    return new TextDecoder().decode(bytes);
}

function brokenCopies(dir) {
    const list = [];
    const handle = GLib.Dir.open(dir, 0);
    let name;
    while ((name = handle.read_name()) !== null) {
        if (name.indexOf("config.json.broken-") === 0) {
            list.push(name);
        }
    }
    handle.close();
    return list;
}

function clearBroken() {
    [OWN_DIR, LEGACY_DIR].forEach(dir => brokenCopies(dir).forEach(n => GLib.unlink(dir + "/" + n)));
}

const reports = [];
J._resetForTests();
J.setReporter(path => reports.push(GLib.path_get_basename(GLib.path_get_dirname(path))));

// --- P11: eine Regel ---------------------------------------------------------
print("P11 Regel (gleiche Faelle wie base-config-test.py):");
const CASES = [
    ["beide fehlen -> Standard", null, null, DEFAULT],
    ["eigene Datei", '{"baseDirectory": "/srv/gruppen"}', null, "/srv/gruppen"],
    ["/ am Ende und .. bereinigt", '{"baseDirectory": "/srv/a/../gruppen/"}', null, "/srv/gruppen"],
    ["~ erweitert", '{"baseDirectory": "~/Gruppen"}', null, HOME + "/Gruppen"],
    ["Leerzeichen am Rand", '{"baseDirectory": "  /srv/g  "}', null, "/srv/g"],
    ["relativer Pfad -> Standard", '{"baseDirectory": "gruppen"}', '{"baseDirectory": "/alt"}', DEFAULT],
    ["ohne Wert -> Standard, nicht die alte Datei", '{"version": 1}', '{"baseDirectory": "/alt"}', DEFAULT],
    ["eigene fehlt -> alte Datei", null, '{"baseDirectory": "/alt"}', "/alt"],
    ["eigene kaputt -> alte Datei", '{"baseDirectory": "/neu"', '{"baseDirectory": "/alt"}', "/alt"],
    ["eigene ist Liste (kaputt) -> alte Datei", '["/neu"]', '{"baseDirectory": "/alt"}', "/alt"],
    ["beide kaputt -> Standard", "{", "{", DEFAULT],
    ["kein Text -> Standard", '{"baseDirectory": 5}', null, DEFAULT]
];
for (const [name, own, legacy, expected] of CASES) {
    put(OWN, own === null ? null : own);
    put(LEGACY, legacy === null ? null : legacy);
    if (own === null) {
        try { GLib.unlink(OWN); } catch (e) {}
    }
    check(name, C.getBaseDirectory(), expected);
}
clearBroken();

const linkTarget = work + "/echt";
GLib.mkdir_with_parents(linkTarget, 0o755);
Gio.File.new_for_path(work + "/verweis").make_symbolic_link(linkTarget, null);
put(OWN, JSON.stringify({ baseDirectory: work + "/verweis" }));
put(LEGACY, null);
check("Verweis wird nicht aufgeloest", C.getBaseDirectory(), work + "/verweis");
check("Gruppenordner unter dem Basisordner", C.getResolvedPath("/BUERO/"), work + "/verweis/BUERO");
check("ohne Unterordner: default", C.getResolvedPath(""), work + "/verweis/default");

// --- P11: kaputte Datei sichern, melden, nie ueberschreiben ------------------
print("P11 kaputte config.json:");
J._resetForTests();
reports.length = 0;
J.setReporter(path => reports.push(GLib.path_get_basename(GLib.path_get_dirname(path))));
put(OWN, '{"baseDirectory": "/kaputt"');
put(LEGACY, null);
C.getBaseDirectory();
C.getBaseDirectory();
check("eine Kopie .broken-<Zeit>", brokenCopies(OWN_DIR).length, 1);
check("genau eine Meldung", reports, ["avincelaunch"]);
const sub = C.ensureLinkDirectory("BUERO");
check("ensureLinkDirectory nimmt den Standard", sub, DEFAULT + "/BUERO");
check("Gruppenordner angelegt", GLib.file_test(sub, GLib.FileTest.IS_DIR), true);
check("kaputte config.json unveraendert", read(OWN), '{"baseDirectory": "/kaputt"');
clearBroken();
put(OWN, null);
C.ensureLinkDirectory("TOOLS");
check("fehlende config.json wird nicht angelegt", GLib.file_test(OWN, GLib.FileTest.EXISTS), false);
check("saveConfig gibt es nicht mehr (nur der Dialog schreibt)", typeof C.saveConfig, "undefined");

// --- P33: Waechter -----------------------------------------------------------
print("P33 Waechter auf config.json:");
put(OWN, JSON.stringify({ version: 1, baseDirectory: "/srv/eins" }));
const seenA = [];
const seenB = [];
const ownerA = {};
const ownerB = {};
C.watchBaseDirectory(ownerA, base => seenA.push(base));
C.watchBaseDirectory(ownerB, base => seenB.push(base));

function spin(ms) {
    const loop = new GLib.MainLoop(null, false);
    GLib.timeout_add(GLib.PRIORITY_DEFAULT, ms, () => { loop.quit(); return GLib.SOURCE_REMOVE; });
    loop.run();
}

// Wie der Dialog: neue Datei schreiben und umbenennen (atomar).
function writeAtomic(text) {
    put(OWN_DIR + "/.config.json.tmp", text);
    Gio.File.new_for_path(OWN_DIR + "/.config.json.tmp").move(
        Gio.File.new_for_path(OWN), Gio.FileCopyFlags.OVERWRITE, null, null);
}

spin(200);
writeAtomic(JSON.stringify({ version: 1, baseDirectory: "/srv/zwei" }));
spin(900);
check("beide Fences erfahren den neuen Ordner", [seenA, seenB], [["/srv/zwei"], ["/srv/zwei"]]);
writeAtomic(JSON.stringify({ version: 1, baseDirectory: "/srv/zwei/" }));
spin(900);
check("gleicher Ordner (nur anders geschrieben): keine Meldung", seenA.length, 1);
put(OWN_DIR + "/andere.json", "{}");
spin(900);
check("andere Datei im Ordner: keine Meldung", seenA.length, 1);
C.unwatchBaseDirectory(ownerA);
put(OWN, JSON.stringify({ version: 1, baseDirectory: "/srv/drei" }));
spin(900);
check("abgemeldet: keine Meldung mehr", [seenA.length, seenB], [1, ["/srv/zwei", "/srv/drei"]]);
C.unwatchBaseDirectory(ownerB);
put(OWN, JSON.stringify({ version: 1, baseDirectory: "/srv/vier" }));
spin(900);
check("alle abgemeldet: Waechter aus", seenB.length, 2);

// --- Aufraeumen --------------------------------------------------------------
GLib.spawn_command_line_sync("rm -rf " + GLib.shell_quote(work) + " " + GLib.shell_quote(shim));
print("");
print("Geprueft: " + checks + ", Fehler: " + failures);
if (failures > 0) {
    imports.system.exit(1);
}
