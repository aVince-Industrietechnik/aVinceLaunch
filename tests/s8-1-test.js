// SPDX-License-Identifier: GPL-3.0-only
// Copyright (c) 2026 Angelo Vincenti, aVince Industrietechnik

// Prueft Schritt 8, Paket S8-1 (Pruefung Phase 2) ohne Cinnamon in einem
// Wegwerfordner:
//   B4  Schema-Grenzen eine Stufe weiter als die Bereiche in desklet.js
//       (RANGED_SETTINGS) - kein erlaubter Wert liegt auf einer Grenze;
//   B10 lib/sidecar.js keepMissingEntries / Einlesen / saveItemState
//       (Faelle wie tests/s8-1-test.py);
//   B12 lib/settingsBackup.js (Kopie nur bei Aenderung, letzte 5).
//   Teil 2 BT1: Rotation nach Zeit, Anker-Kopie, Sicherungen entfernter Fences.
// Aufruf im Repository-Wurzelverzeichnis:  cjs tests/s8-1-test.js

const Gio = imports.gi.Gio;
const GLib = imports.gi.GLib;

const UUID = "avincelaunch-desklet@avince";
const shim = GLib.dir_make_tmp("avl-shim-XXXXXX");
GLib.mkdir_with_parents(shim + "/desklets", 0o755);
Gio.File.new_for_path(shim + "/desklets/" + UUID).make_symbolic_link(
    GLib.get_current_dir() + "/Desklet", null);
imports.searchPath.unshift(shim);
const S = imports.desklets[UUID].lib.sidecar;
const B = imports.desklets[UUID].lib.settingsBackup;

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

const work = GLib.dir_make_tmp("avl-s8-1-XXXXXX");

// --- B4 ---------------------------------------------------------------------
print("B4 Grenzen:");
const schema = JSON.parse(read("Desklet/settings-schema.json"));
const source = read("Desklet/desklet.js");
const block = source.substring(source.indexOf("const RANGED_SETTINGS = ["),
    source.indexOf("];", source.indexOf("const RANGED_SETTINGS = [")));
const ranges = [];
block.replace(/\["([a-z_]+)", ([0-9.]+), ([0-9.]+)\]/g, (m, prop, low, high) => {
    ranges.push([prop.replace(/_/g, "-"), Number(low), Number(high)]);
});
check("9 Einstellungen begrenzt", ranges.length, 9);
ranges.forEach(([key, low, high]) => {
    const def = schema[key];
    check(key + ": Schema " + def.min + ".." + def.max + " umschliesst " + low + ".." + high,
        def.min < low && def.max > high && def.default >= low && def.default <= high, true);
});

// --- B10 --------------------------------------------------------------------
print("B10 fehlende Eintraege behalten ihren Platz:");
const DAY = 24 * 60 * 60;
const NOW = 1800000000;
S._setNowForTests(NOW);
// Gleiche Faelle wie tests/s8-1-test.py
const CASES = [
    ["nichts fehlt", ["a", "b", "c"], ["a", "b", "c"], {}, ["a", "b", "c"], {}],
    ["b fehlt: bleibt an Platz 2", ["a", "b", "c"], ["a", "c"], {}, ["a", "b", "c"], { b: NOW }],
    ["erster fehlt: bleibt vorn", ["a", "b", "c"], ["b", "c"], {}, ["a", "b", "c"], { a: NOW }],
    ["zwei hintereinander fehlen", ["a", "b", "c", "d"], ["a", "d"], {}, ["a", "b", "c", "d"], { b: NOW, c: NOW }],
    ["Zeitstempel bleibt der erste", ["a", "b"], ["a"], { b: NOW - 5 * DAY }, ["a", "b"], { b: NOW - 5 * DAY }],
    ["nach 30 Tagen gestrichen", ["a", "b"], ["a"], { b: NOW - 31 * DAY }, ["a"], {}],
    ["genau 30 Tage: noch da", ["a", "b"], ["a"], { b: NOW - 30 * DAY }, ["a", "b"], { b: NOW - 30 * DAY }],
    ["wieder da: Zeitstempel weg", ["a", "b"], ["a", "b"], { b: NOW - DAY }, ["a", "b"], {}],
    ["neue Reihenfolge umsortiert, fehlender folgt Vorgaenger", ["a", "b", "c"], ["c", "a"], {}, ["c", "a", "b"], { b: NOW }],
    ["kaputter Zeitstempel = jetzt", ["a", "b"], ["a"], { b: "x" }, ["a", "b"], { b: NOW }]
];
CASES.forEach(([name, oldOrder, newOrder, since, order, expSince]) => {
    const r = S.keepMissingEntries(oldOrder, newOrder, since);
    check(name, [r.order, r.missingSince], [order, expSince]);
});

const dir = work + "/TOOLS";
GLib.mkdir_with_parents(dir, 0o755);
GLib.file_set_contents(dir + "/.avincelaunch.json", JSON.stringify({
    version: 1, order: ["app:a.desktop", "app:b.desktop", "app:c.desktop"],
    disabled: ["app:b.desktop"], itemStyles: {}, zukunft: { feld: 1 }
}));
S.persistOrderFromItems(dir, [{ id: "app:a.desktop" }, { id: "app:c.desktop" }]);
let data = JSON.parse(read(dir + "/.avincelaunch.json"));
check("Einlesen: b behaelt Platz und Haken", [data.order, data.disabled, data.missingSince],
    [["app:a.desktop", "app:b.desktop", "app:c.desktop"], ["app:b.desktop"], { "app:b.desktop": NOW }]);
check("unbekanntes Feld bleibt", data.zukunft, { feld: 1 });
const before = read(dir + "/.avincelaunch.json");
S.persistOrderFromItems(dir, [{ id: "app:a.desktop" }, { id: "app:c.desktop" }]);
check("zweites Einlesen schreibt nichts Neues", read(dir + "/.avincelaunch.json"), before);
S.persistOrderFromItems(dir, [{ id: "app:a.desktop" }, { id: "app:b.desktop" }, { id: "app:c.desktop" }]);
data = JSON.parse(read(dir + "/.avincelaunch.json"));
check("b wieder da: an Platz 2, kein Zeitstempel", [data.order, data.missingSince === undefined],
    [["app:a.desktop", "app:b.desktop", "app:c.desktop"], true]);

GLib.file_set_contents(dir + "/.avincelaunch.json", JSON.stringify({
    version: 1, order: ["folder:X", "app:a.desktop"], disabled: ["folder:X"],
    itemStyles: { "folder:X": { icon: "folder-red" } }
}));
S.saveItemState(dir, ["app:a.desktop"], [], {});
data = JSON.parse(read(dir + "/.avincelaunch.json"));
check("Uebernehmen: fehlender Ordner behaelt Platz, Haken, Farbe",
    [data.order, data.disabled, data.itemStyles], [["folder:X", "app:a.desktop"], ["folder:X"], { "folder:X": { icon: "folder-red" } }]);
S._setNowForTests(NOW + 31 * DAY);
S.saveItemState(dir, ["app:a.desktop"], [], {});
data = JSON.parse(read(dir + "/.avincelaunch.json"));
check("nach 31 Tagen: Ordner gestrichen (Platz, Haken, Farbe)",
    [data.order, data.disabled, data.itemStyles === undefined, data.missingSince === undefined],
    [["app:a.desktop"], [], true, true]);
S._setNowForTests();

// --- B12 --------------------------------------------------------------------
print("B12 Sicherung der Einstellungen:");
const src = work + "/7.json";
const bdir = B.backupDirFor(work + "/config", 7);
check("Zielordner", bdir, work + "/config/avincelaunch/backups/einstellungen-7");
check("fehlende Datei: nichts", B.backupSettingsFile(src, bdir), null);
GLib.file_set_contents(src, "{\"a\": 1}");
const first = B.backupSettingsFile(src, bdir);
check("erste Kopie angelegt", first !== null && read(first) === "{\"a\": 1}", true);
check("unveraendert: keine weitere Kopie", B.backupSettingsFile(src, bdir), null);
for (let i = 2; i <= 8; i++) {
    GLib.file_set_contents(src, "{\"a\": " + i + "}");
    B.backupSettingsFile(src, bdir);
}
const left = [];
const handle = GLib.Dir.open(bdir, 0);
let name;
while ((name = handle.read_name()) !== null) {
    left.push(name);
}
handle.close();
left.sort();
check("nur die letzten 5", left.length, 5);
check("die neueste ist der aktuelle Stand", read(bdir + "/" + left[left.length - 1]), "{\"a\": 8}");
check("die aelteste ist Stand 4", read(bdir + "/" + left[0]), "{\"a\": 4}");

// --- Teil 2, BT1 --------------------------------------------------------------
print("Teil 2 BT1 Rotation nach Zeit und Anker-Kopie:");
const nowSec = Math.floor(GLib.get_real_time() / 1000000);

function setAge(path, secondsAgo) {
    const file = Gio.File.new_for_path(path);
    file.set_attribute_uint64("time::modified", nowSec - secondsAgo, Gio.FileQueryInfoFlags.NOFOLLOW_SYMLINKS, null);
    file.set_attribute_uint32("time::modified-usec", 0, Gio.FileQueryInfoFlags.NOFOLLOW_SYMLINKS, null);
}

function names(dir) {
    const list = [];
    try {
        const h = GLib.Dir.open(dir, 0);
        let n;
        while ((n = h.read_name()) !== null) {
            list.push(n);
        }
        h.close();
    } catch (e) {
        return null;
    }
    return list.sort();
}

const src9 = work + "/9.json";
const bdir9 = B.backupDirFor(work + "/config9", 9);
GLib.file_set_contents(src9, "{\"gut\": 1}");
const good = B.backupSettingsFile(src9, bdir9);
setAge(good, 3 * 24 * 60 * 60);
for (let i = 1; i <= 6; i++) {
    GLib.file_set_contents(src9, "{\"vorgabe\": " + i + "}");
    const copy = B.backupSettingsFile(src9, bdir9);
    setAge(copy, (7 - i) * 60);
}
check("gute Kopie (aelter als ein Tag) bleibt als Anker", GLib.file_test(good, GLib.FileTest.EXISTS), true);
check("dazu die 5 neuesten (6 Dateien)", names(bdir9).length, 6);
check("die neueste ist der aktuelle Stand", (() => {
    const list = names(bdir9).filter(n => n !== GLib.path_get_basename(good));
    return list.some(n => read(bdir9 + "/" + n) === "{\"vorgabe\": 6}");
})(), true);
check("Stand 1 ist verdraengt", names(bdir9).some(n => read(bdir9 + "/" + n) === "{\"vorgabe\": 1}"), false);

// Uhr zurueckgesprungen: die vorhandenen Kopien liegen "in der Zukunft".
names(bdir9).forEach(n => setAge(bdir9 + "/" + n, -3600));
GLib.file_set_contents(src9, "{\"nach-uhrsprung\": 1}");
const afterJump = B.backupSettingsFile(src9, bdir9);
check("neue Kopie bleibt, auch nach einem Uhrsprung", GLib.file_test(afterJump, GLib.FileTest.EXISTS), true);
check("weiter hoechstens 5 + Anker", names(bdir9).length <= 6, true);

print("Teil 2 BT1 Sicherungen entfernter Fences:");
const cfg = work + "/config-entfernt";
const root4 = B.backupDirFor(cfg, 4);
const root117 = B.backupDirFor(cfg, 117);
const root118 = B.backupDirFor(cfg, 118);
[root4, root117, root118].forEach(d => {
    GLib.mkdir_with_parents(d, 0o755);
    GLib.file_set_contents(d + "/2026-10-01_10-00-00-000000.json", "{}");
});
GLib.file_set_contents(root118 + "/notiz.txt", "fremd");
const t0 = 1800000000;
B._setNowForTests(t0);
check("leere Fence-Liste: nichts tun (Schutz)", B.pruneRemovedFenceBackups(cfg, []), []);
check("... keine Markierung", GLib.file_test(root117 + "/.entfernt", GLib.FileTest.EXISTS), false);
check("erstes Bemerken: nur markiert", B.pruneRemovedFenceBackups(cfg, ["4"]), []);
check("Markierung 117 mit Zeit", read(root117 + "/.entfernt").trim(), String(t0));
check("lebender Fence 4 ohne Markierung", GLib.file_test(root4 + "/.entfernt", GLib.FileTest.EXISTS), false);
B._setNowForTests(t0 + 29 * 24 * 60 * 60);
check("nach 29 Tagen: noch alles da", [B.pruneRemovedFenceBackups(cfg, ["4"]), names(root117).length], [[], 2]);
B._setNowForTests(t0 + 30 * 24 * 60 * 60);
check("nach 30 Tagen: 117 geloescht", B.pruneRemovedFenceBackups(cfg, ["4"]), ["117"]);
check("117-Ordner weg", names(root117), null);
check("118 mit fremder Datei bleibt ganz", names(root118), ["2026-10-01_10-00-00-000000.json", ".entfernt", "notiz.txt"].sort());
check("4 unberuehrt", names(root4), ["2026-10-01_10-00-00-000000.json"]);
check("Fence 118 kommt zurueck: Markierung weg", [B.pruneRemovedFenceBackups(cfg, ["4", "118"]),
    GLib.file_test(root118 + "/.entfernt", GLib.FileTest.EXISTS)], [[], false]);
B._setNowForTests();

GLib.spawn_command_line_sync("rm -rf " + GLib.shell_quote(work) + " " + GLib.shell_quote(shim));
print("");
print("Geprueft: " + checks + ", Fehler: " + failures);
if (failures > 0) {
    imports.system.exit(1);
}
