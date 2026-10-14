// SPDX-License-Identifier: GPL-3.0-only
// Copyright (c) 2026 Angelo Vincenti, aVince Industrietechnik

// Prueft lib/fenceClone.js (AP18-5) ohne Cinnamon in einem Wegwerfordner.
// Aufruf im Repository-Wurzelverzeichnis:  cjs tests/fence-clone-test.js

const Gio = imports.gi.Gio;
const GLib = imports.gi.GLib;

// Uebergabedatei und Sicherungen landen unter XDG_CONFIG_HOME - vor dem
// ersten Zugriff auf einen Wegwerfordner umbiegen.
const tmp = GLib.dir_make_tmp("avl-clone-XXXXXX");
GLib.setenv("XDG_CONFIG_HOME", tmp, true);
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
requireRedirect([["XDG_CONFIG_HOME", GLib.get_user_config_dir(), tmp]]);

imports.searchPath.unshift("Desklet/lib");
const C = imports.fenceClone;

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

check("Wegwerfordner aktiv", GLib.get_user_config_dir(), tmp);

print("ID-Wahl (Praefixfehler):");
const LATITUDE = ["4", "5", "7", "6", "8", "9", "10", "40", "41"];
check("45 beginnt mit 4 -> 110", C.pickInstanceId(45, LATITUDE), 110);
check("111 ist frei", C.pickInstanceId(111, LATITUDE.concat(["110"])), 111);
check("3 waere Anfang von 36 nicht relevant (nur eigene UUID)", C.pickInstanceId(3, LATITUDE), 3);
check("1 ist Anfang von 10 -> 2", C.pickInstanceId(1, LATITUDE), 2);
check("leere Liste", C.pickInstanceId(45, []), 45);
check("Unsinn als next -> ab 1", C.pickInstanceId("x", []), 1);

print("\nIDs aus enabled-desklets:");
check("nur eigene UUID", C.instanceIdsOf([
    "avincelaunch-desklet@avince:4:50:50",
    "avincepulse-desklet@avince:36:1300:475",
    "kaputt",
    "avincelaunch-desklet@avince:40:800:550"
], "avincelaunch-desklet@avince"), ["4", "40"]);

print("\nOrdnername:");
const have = ["SYSTEM", "SYSTEM_2", "BUERO"];
const exists = name => have.indexOf(name) >= 0;
check("SYSTEM -> SYSTEM_3 (SYSTEM_2 vergeben)", C.nextGroupName("SYSTEM", exists), "SYSTEM_3");
check("BUERO -> BUERO_2", C.nextGroupName("BUERO", exists), "BUERO_2");
check("SYSTEM_2 -> SYSTEM_3", C.nextGroupName("SYSTEM_2", exists), "SYSTEM_3");
check("leer -> FENCE_2", C.nextGroupName("", exists), "FENCE_2");

print("\nWerte:");
{
    const store = { "icon-size": 64, "fence-title": "SYSTEM", "position-x": 50,
        "lock-position": true, "desklet-bg-color": "rgba(1,2,3,0.4)", "max-width": 360 };
    const values = C.buildCloneValues(key => store[key],
        { "fence-title": "SYSTEM (Kopie)", "lock-position": false });
    check("Aussehen und Masse kommen mit", [values["icon-size"], values["desklet-bg-color"], values["max-width"]],
        [64, "rgba(1,2,3,0.4)", 360]);
    check("Position nicht", "position-x" in values, false);
    check("Titel und Sperre ueberschrieben", [values["fence-title"], values["lock-position"]],
        ["SYSTEM (Kopie)", false]);
    check("fehlende Schluessel ausgelassen", "portal-path" in values, false);
    check("keine Arbeitswerte des Dialogs", C.CLONE_COPY_KEYS.some(k => k.indexOf("order-") === 0
        || k === "link-order-list-data" || k === "base-directory"), false);
}

print("\nUebergabedatei:");
{
    check("vorher keine", C.handoverExists(110), false);
    const path = C.writeHandover(110, { from: "4", values: { "icon-size": 64 } });
    check("liegt unter avincelaunch/", path, tmp + "/avincelaunch/clone-110.json");
    check("vorhanden", C.handoverExists(110), true);
    const data = C.takeHandover(110);
    check("gelesen", [data.from, data.values["icon-size"]], ["4", 64]);
    check("danach weg", C.handoverExists(110), false);
    check("zweites Lesen -> null", C.takeHandover(110), null);
    GLib.file_set_contents(C.handoverPath(111), "{kaputt");
    check("kaputte Datei -> null", C.takeHandover(111), null);
    check("kaputte Datei geloescht", C.handoverExists(111), false);
}

print("\nSicherung:");
{
    GLib.file_set_contents(tmp + "/avincelaunch/layout.json", "{\"version\": 1}\n");
    const dir = C.backupBeforeClone(["a:1:2:3", "b:4:5:6"]);
    const [, list] = GLib.file_get_contents(dir + "/enabled-desklets.txt");
    check("enabled-desklets gesichert", new TextDecoder().decode(list), "a:1:2:3\nb:4:5:6\n");
    check("layout.json gesichert", GLib.file_test(dir + "/layout.json", GLib.FileTest.EXISTS), true);
    // Aufraeumen: nur die letzten BACKUP_KEEP bleiben.
    for (let i = 0; i < 12; i++) {
        GLib.mkdir_with_parents(tmp + "/avincelaunch/backups/clone-2000-01-01_00-00-" + String(i).padStart(2, "0"), 0o755);
    }
    C.backupBeforeClone([]);
    const names = [];
    const en = Gio.File.new_for_path(tmp + "/avincelaunch/backups").enumerate_children(
        "standard::name", Gio.FileQueryInfoFlags.NONE, null);
    let info;
    while ((info = en.next_file(null)) !== null) {
        names.push(info.get_name());
    }
    check("hoechstens " + C.BACKUP_KEEP + " Sicherungen", names.length, C.BACKUP_KEEP);
    check("die neueste bleibt", names.indexOf(GLib.path_get_basename(dir)) >= 0, true);
}

// Wegwerfordner entfernen.
GLib.spawn_command_line_sync("rm -rf " + GLib.shell_quote(tmp));

print("\nGeprueft: " + checks + ", Fehler: " + failures);
if (failures > 0) {
    imports.system.exit(1);
}
