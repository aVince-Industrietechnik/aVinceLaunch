// SPDX-License-Identifier: GPL-3.0-only
// Copyright (c) 2026 Angelo Vincenti, aVince Industrietechnik

// Prueft lib/safeJson.js und lib/sidecar.js mit kaputten Dateien
// (Pruefung Phase 2, A3-1: P3, P4, P80; Teil 2: T13, T14) ohne Cinnamon in einem
// Wegwerfordner.
// Aufruf im Repository-Wurzelverzeichnis:  cjs tests/safe-json-test.js

const Gio = imports.gi.Gio;
const GLib = imports.gi.GLib;

const UUID = "avincelaunch-desklet@avince";
const shim = GLib.dir_make_tmp("avl-shim-XXXXXX");
GLib.mkdir_with_parents(shim + "/desklets", 0o755);
Gio.File.new_for_path(shim + "/desklets/" + UUID).make_symbolic_link(
    GLib.get_current_dir() + "/Desklet", null);
imports.searchPath.unshift(shim);
const J = imports.desklets[UUID].lib.safeJson;
const S = imports.desklets[UUID].lib.sidecar;

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

function write(path, text) {
    GLib.file_set_contents(path, text);
}

function read(path) {
    const [, bytes] = GLib.file_get_contents(path);
    return new TextDecoder().decode(bytes);
}

function backups(dir, base) {
    const list = [];
    const handle = GLib.Dir.open(dir, 0);
    let name;
    while ((name = handle.read_name()) !== null) {
        if (name.indexOf(base + ".broken-") === 0) {
            list.push(name);
        }
    }
    handle.close();
    return list.sort();
}

const reports = [];
function resetReporter() {
    J._resetForTests();
    reports.length = 0;
    J.setReporter((path, backup) => reports.push([GLib.path_get_basename(path), !!backup]));
}

const root = GLib.dir_make_tmp("avl-a3-XXXXXX");

print("safeJson - Zustaende:");
resetReporter();
const layout = root + "/layout.json";
check("fehlt -> missing", J.readJson(layout).state, "missing");
check("fehlt -> Schreiben erlaubt", J.mayWrite(layout), true);
write(layout, '{"version": 1, "settings": {"gapX": 15}}');
check("gueltig -> ok", J.readJson(layout).state, "ok");
check("gueltig -> Inhalt", J.readJson(layout).data.settings.gapX, 15);
write(layout, "[1, 2]");
check("Array -> broken", J.readJson(layout).state, "broken");
write(layout, "");
check("leer -> broken", J.readJson(layout).state, "broken");

print("\nsafeJson - kaputte layout.json (P3):");
resetReporter();
const original = '{"version": 1, "originalArrangement": {"fences": {"4": {}}}, "settings": {"gapX": 15';
write(layout, original);
check("mayWrite -> false", J.mayWrite(layout), false);
check("Datei unveraendert", read(layout), original);
const first = backups(root, "layout.json");
check("genau eine Kopie", first.length, 1);
check("Kopie = Inhalt", read(root + "/" + first[0]), original);
check("Meldung einmal, mit Kopie", reports, [["layout.json", true]]);
J.mayWrite(layout);
J.secureBroken(layout);
check("zweiter Versuch: keine weitere Kopie", backups(root, "layout.json").length, 1);
check("zweiter Versuch: keine weitere Meldung", reports.length, 1);
resetReporter();
J.mayWrite(layout);
check("neue Sitzung, gleicher Inhalt: Kopie wiederverwendet", backups(root, "layout.json").length, 1);
check("neue Sitzung: wieder gemeldet", reports.length, 1);
write(layout, original + "x");
J._resetForTests();
J.mayWrite(layout);
check("anderer kaputter Inhalt: zweite Kopie", backups(root, "layout.json").length, 2);
write(layout, '{"version": 1}');
check("repariert -> Schreiben erlaubt", J.mayWrite(layout), true);

print("\nsidecar - kaputte .avincelaunch.json mit gueltiger Altdatei (P4):");
resetReporter();
const g1 = root + "/GRUPPE1";
GLib.mkdir_with_parents(g1, 0o755);
["a.desktop", "b.desktop", "c.desktop"].forEach(n =>
    write(g1 + "/" + n, "[Desktop Entry]\nName=" + n + "\nExec=true\n"));
write(g1 + "/.thelauncher.json", JSON.stringify({
    version: 1, order: ["app:c.desktop", "app:a.desktop", "app:b.desktop"],
    disabled: ["app:b.desktop"], pinned: ["app:a.desktop"]
}));
const brokenOwn = '{"version": 1, "order": ["app:b.desktop", "app:a.desk';
write(g1 + "/.avincelaunch.json", brokenOwn);
let sc = S.readSidecar(g1);
check("Reihenfolge aus der Altdatei", sc.order, ["app:c.desktop", "app:a.desktop", "app:b.desktop"]);
check("Aus-Haken aus der Altdatei", sc.disabled, ["app:b.desktop"]);
check("Nadel aus der Altdatei", sc.pinned, ["app:a.desktop"]);
check("als kaputt markiert", sc.broken, true);
const items = ["a.desktop", "b.desktop", "c.desktop"].map(n => ({ id: "app:" + n, enabled: true }));
S.persistOrderFromItems(g1, items.concat([{ id: "app:neu.desktop" }]));
check("automatisches Nachziehen schreibt nicht", read(g1 + "/.avincelaunch.json"), brokenOwn);
check("Anpinnen wird abgelehnt (null)", S.setPinned(g1, "app:c.desktop", true), null);
check("Datei weiter unveraendert", read(g1 + "/.avincelaunch.json"), brokenOwn);
check("Kopie der kaputten Datei", backups(g1, ".avincelaunch.json").length, 1);
check("Altdatei unveraendert", JSON.parse(read(g1 + "/.thelauncher.json")).order[0], "app:c.desktop");
check("einmal gemeldet", reports, [[".avincelaunch.json", true]]);
write(g1 + "/.avincelaunch.json", JSON.stringify({ version: 1, order: ["app:b.desktop"], disabled: [] }));
check("repariert: Anpinnen geht wieder", S.setPinned(g1, "app:c.desktop", true), true);
check("repariert: nicht mehr kaputt", S.readSidecar(g1).broken, undefined);

print("\nsidecar - nur kaputte Altdatei:");
resetReporter();
const g2 = root + "/GRUPPE2";
GLib.mkdir_with_parents(g2, 0o755);
write(g2 + "/a.desktop", "[Desktop Entry]\nName=a\nExec=true\n");
write(g2 + "/.thelauncher.json", "{kaputt");
sc = S.ensureSidecarForDirectory(g2, [{ id: "app:a.desktop", enabled: true }]);
check("keine neue .avincelaunch.json", GLib.file_test(g2 + "/.avincelaunch.json", GLib.FileTest.EXISTS), false);
check("Altdatei unveraendert", read(g2 + "/.thelauncher.json"), "{kaputt");
check("Kopie der Altdatei", backups(g2, ".thelauncher.json").length, 1);

print("\nsidecar - Normalfall unveraendert:");
resetReporter();
const g3 = root + "/GRUPPE3";
GLib.mkdir_with_parents(g3, 0o755);
write(g3 + "/a.desktop", "[Desktop Entry]\nName=a\nExec=true\n");
S.ensureSidecarForDirectory(g3, [{ id: "app:a.desktop", enabled: true }]);
check("fehlende Datei wird angelegt", JSON.parse(read(g3 + "/.avincelaunch.json")).order, ["app:a.desktop"]);
S.writeSidecar(g3, { order: ["app:a.desktop"], disabled: [], extra: { zukunft: 1 } });
check("unbekannte Felder bleiben", JSON.parse(read(g3 + "/.avincelaunch.json")).zukunft, 1);
check("keine Meldung", reports.length, 0);

print("\nTeil 2 (T14) - ungueltiges UTF-8:");
resetReporter();
const badUtf8 = root + "/utf8.json";
GLib.file_set_contents(badUtf8, new Uint8Array([0x7b, 0x22, 0x61, 0x22, 0x3a, 0x22, 0xff, 0x22, 0x7d]));
check("{\"a\":\"\\xff\"} gilt als kaputt (wie im Dialog)", J.readJson(badUtf8).state, J.STATE_BROKEN);
write(root + "/utf8-ok.json", '{"a": "Ä"}');
check("gueltiges UTF-8 bleibt ok", J.readJson(root + "/utf8-ok.json").data.a, "Ä");

print("\nTeil 2 (T13) - kaputte Datei entfernt, Altdatei gilt nicht mehr:");
resetReporter();
const g4 = root + "/GRUPPE4";
GLib.mkdir_with_parents(g4, 0o755);
write(g4 + "/a.desktop", "[Desktop Entry]\nName=a\nExec=true\n");
write(g4 + "/.thelauncher.json", JSON.stringify({ version: 1, order: ["app:alt.desktop"], disabled: ["app:a.desktop"] }));
write(g4 + "/.avincelaunch.json", "{kaputt");
check("kaputt: Altdatei wird gelesen (nur Anzeige)", S.readSidecar(g4).order, ["app:alt.desktop"]);
check("Kopie angelegt", backups(g4, ".avincelaunch.json").length, 1);
check("hasBrokenCopy", J.hasBrokenCopy(g4 + "/.avincelaunch.json"), true);
Gio.File.new_for_path(g4 + "/.avincelaunch.json").delete(null);
sc = S.readSidecar(g4);
check("entfernt: NICHT die Altdatei, neu beginnen", [sc.order, sc.disabled, sc.broken], [[], [], undefined]);
check("Schreiben erlaubt", S.sidecarSourceBroken(g4), false);
S.ensureSidecarForDirectory(g4, [{ id: "app:a.desktop", enabled: true }]);
check("neue .avincelaunch.json aus dem Ordner", JSON.parse(read(g4 + "/.avincelaunch.json")).order, ["app:a.desktop"]);
check("Altdatei unveraendert", JSON.parse(read(g4 + "/.thelauncher.json")).order, ["app:alt.desktop"]);
const g5 = root + "/GRUPPE5";
GLib.mkdir_with_parents(g5, 0o755);
write(g5 + "/.thelauncher.json", JSON.stringify({ version: 1, order: ["app:x.desktop"] }));
check("ohne Kopie: Altdatei wie bisher (Umstieg von TheLauncher)", S.readSidecar(g5).order, ["app:x.desktop"]);

// Aufraeumen
function removeTree(path) {
    const file = Gio.File.new_for_path(path);
    const info = file.query_info("standard::type", Gio.FileQueryInfoFlags.NOFOLLOW_SYMLINKS, null);
    if (info.get_file_type() === Gio.FileType.DIRECTORY) {
        const en = file.enumerate_children("standard::name", Gio.FileQueryInfoFlags.NOFOLLOW_SYMLINKS, null);
        let child;
        while ((child = en.next_file(null)) !== null) {
            removeTree(path + "/" + child.get_name());
        }
        en.close(null);
    }
    file.delete(null);
}
removeTree(root);
removeTree(shim);

print("\nGeprueft: " + checks + ", Fehler: " + failures);
imports.system.exit(failures ? 1 : 0);
