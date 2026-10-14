// SPDX-License-Identifier: GPL-3.0-only
// Copyright (c) 2026 Angelo Vincenti, aVince Industrietechnik

// Prueft lib/itemActions.js (AP18-1) ohne Cinnamon in einem Wegwerfordner.
// Aufruf im Repository-Wurzelverzeichnis:  cjs tests/item-actions-test.js

const Gio = imports.gi.Gio;
const GLib = imports.gi.GLib;

// A9/P70: Der Papierkorb liegt unter XDG_DATA_HOME - auf einen Wegwerfordner
// umbiegen, sonst landet die Testdatei im echten Papierkorb (bis 09.10.2026
// wurde sie danach ueber "gio trash --list" herausgeholt; das braucht D-Bus
// und fand bei Tests ohne D-Bus nichts - fuenf Reste im echten Papierkorb).
// Der Wegwerfordner liegt in /tmp wie die Testordner: GLib nimmt diesen
// Papierkorb nur auf demselben Dateisystem.
const work = GLib.dir_make_tmp("avl-ap18-data-XXXXXX");
GLib.setenv("XDG_DATA_HOME", work, true);
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
requireRedirect([["XDG_DATA_HOME", GLib.get_user_data_dir(), work]]);

// Im Desklet heisst die Bibliothek imports.desklets[UUID].lib - nachgebildet
// mit einem Verweis in einem Wegwerfordner.
const UUID = "avincelaunch-desklet@avince";
const shim = GLib.dir_make_tmp("avl-shim-XXXXXX");
GLib.mkdir_with_parents(shim + "/desklets", 0o755);
Gio.File.new_for_path(shim + "/desklets/" + UUID).make_symbolic_link(
    GLib.get_current_dir() + "/Desklet", null);
imports.searchPath.unshift(shim);
const A = imports.desklets[UUID].lib.itemActions;
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

function exists(path) {
    return GLib.file_test(path, GLib.FileTest.EXISTS);
}

const root = GLib.dir_make_tmp("avl-ap18-XXXXXX");
const A_DIR = root + "/INTERNET";
const B_DIR = root + "/BUERO";
GLib.mkdir_with_parents(A_DIR, 0o755);
GLib.mkdir_with_parents(B_DIR, 0o755);
GLib.mkdir_with_parents(A_DIR + "/Werkzeuge", 0o755);
["firefox.desktop", "thunderbird.desktop", "chrome.desktop"].forEach(n =>
    write(A_DIR + "/" + n, "[Desktop Entry]\nName=" + n + "\nExec=true\n"));
write(A_DIR + "/Werkzeuge/a.desktop", "x");
write(A_DIR + "/Werkzeuge/b.desktop", "x");
write(B_DIR + "/calc.desktop", "[Desktop Entry]\nName=calc\nExec=true\n");
write(B_DIR + "/chrome.desktop", "andere Datei");
S.writeSidecar(A_DIR, {
    order: ["app:thunderbird.desktop", "app:firefox.desktop", "app:chrome.desktop", "folder:Werkzeuge"],
    disabled: ["app:firefox.desktop"],
    itemStyles: { "folder:Werkzeuge": { icon: "folder-red" } }
});
S.writeSidecar(B_DIR, { order: ["app:calc.desktop"], disabled: [] });

print("Verschieben:");
let r = A.moveEntry(A_DIR, B_DIR, "firefox.desktop", "app:firefox.desktop");
check("gelingt", r.ok, true);
check("Datei im Ziel", exists(B_DIR + "/firefox.desktop"), true);
check("Datei nicht mehr in der Quelle", exists(A_DIR + "/firefox.desktop"), false);
check("Quelle: Reihenfolge ohne Luecke", S.readSidecar(A_DIR).order,
    ["app:thunderbird.desktop", "app:chrome.desktop", "folder:Werkzeuge"]);
check("Quelle: abgeschaltet ausgetragen", S.readSidecar(A_DIR).disabled, []);
check("Ziel: am Ende", S.readSidecar(B_DIR).order, ["app:calc.desktop", "app:firefox.desktop"]);
check("Ziel: Zustand abgeschaltet mitgenommen", S.readSidecar(B_DIR).disabled, ["app:firefox.desktop"]);

print("Rueckgaengig:");
const undo = A.undoMove(r.record);
check("gelingt", undo.ok, true);
check("Datei wieder in der Quelle", exists(A_DIR + "/firefox.desktop"), true);
check("Quelle: alter Platz", S.readSidecar(A_DIR).order,
    ["app:thunderbird.desktop", "app:firefox.desktop", "app:chrome.desktop", "folder:Werkzeuge"]);
check("Quelle: wieder abgeschaltet", S.readSidecar(A_DIR).disabled, ["app:firefox.desktop"]);
check("Ziel: wieder wie vorher", S.readSidecar(B_DIR).order, ["app:calc.desktop"]);
check("Ziel: abgeschaltet leer", S.readSidecar(B_DIR).disabled, []);

print("Gleicher Name im Ziel:");
r = A.moveEntry(A_DIR, B_DIR, "chrome.desktop", "app:chrome.desktop");
check("abgelehnt", r.reason, "exists");
const [, inhalt] = GLib.file_get_contents(B_DIR + "/chrome.desktop");
check("Ziel unveraendert", new TextDecoder().decode(inhalt), "andere Datei");
check("Quelle unveraendert", exists(A_DIR + "/chrome.desktop"), true);

print("Ordner mit Stil:");
check("Eintraege gezaehlt", A.countEntries(A_DIR + "/Werkzeuge"), 2);
r = A.moveEntry(A_DIR, B_DIR, "Werkzeuge", "folder:Werkzeuge");
check("gelingt", r.ok, true);
check("Inhalt mitgewandert", exists(B_DIR + "/Werkzeuge/b.desktop"), true);
check("Stil im Ziel", S.readSidecar(B_DIR).itemStyles["folder:Werkzeuge"], { icon: "folder-red" });
check("Stil in der Quelle weg", S.readSidecar(A_DIR).itemStyles["folder:Werkzeuge"], undefined);

print("Sonderfaelle:");
check("gleicher Ordner", A.moveEntry(A_DIR, A_DIR + "/", "firefox.desktop", "x").reason, "same");
check("fehlt", A.moveEntry(A_DIR, B_DIR, "gibtsnicht.desktop", "x").reason, "missing");

print("Entfernen (Papierkorb):");
r = A.trashEntry(A_DIR, "thunderbird.desktop", "app:thunderbird.desktop");
check("gelingt", r.ok, true);
check("Datei weg", exists(A_DIR + "/thunderbird.desktop"), false);
check("aus der Reihenfolge", S.readSidecar(A_DIR).order, ["app:firefox.desktop", "app:chrome.desktop"]);

check("im Wegwerf-Papierkorb", exists(work + "/Trash/files/thunderbird.desktop"), true);

// Aufraeumen: Testordner und Wegwerf-Papierkorb loeschen.
GLib.spawn_command_line_sync("rm -rf " + GLib.shell_quote(root) + " " + GLib.shell_quote(shim)
    + " " + GLib.shell_quote(work));

print("\nGeprueft: " + checks + ", Fehler: " + failures);
if (failures > 0) {
    imports.system.exit(1);
}
