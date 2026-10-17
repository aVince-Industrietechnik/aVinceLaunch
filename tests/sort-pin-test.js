// SPDX-License-Identifier: GPL-3.0-only
// Copyright (c) 2026 Angelo Vincenti, aVince Industrietechnik

// Prueft AP18-3 (Sortierarten, Anpinnen, Sidecar-Felder) ohne Cinnamon.
// Aufruf im Repository-Wurzelverzeichnis:  cjs tests/sort-pin-test.js

const Gio = imports.gi.Gio;
const GLib = imports.gi.GLib;

const UUID = "avincelaunch-desklet@avince";
const shim = GLib.dir_make_tmp("avl-shim-XXXXXX");
GLib.mkdir_with_parents(shim + "/desklets", 0o755);
Gio.File.new_for_path(shim + "/desklets/" + UUID).make_symbolic_link(
    GLib.get_current_dir() + "/Desklet", null);
imports.searchPath.unshift(shim);
const L = imports.desklets[UUID].lib;

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
function desktop(path, name) {
    GLib.file_set_contents(path, "[Desktop Entry]\nType=Application\nName=" + name + "\nExec=true\n");
}
function touch(path, secondsAgo) {
    GLib.spawn_command_line_sync("touch -m -d @" + (Math.floor(Date.now() / 1000) - secondsAgo) + " " + GLib.shell_quote(path));
}
const names = r => r.items.map(i => i.name);

const root = GLib.dir_make_tmp("avl-ap183-XXXXXX");
const D = root + "/G";
const T = root + "/H";
GLib.mkdir_with_parents(D + "/Ordner", 0o755);
GLib.mkdir_with_parents(T, 0o755);
desktop(D + "/b.desktop", "Bravo");
desktop(D + "/a.desktop", "Alpha");
desktop(D + "/c.desktop", "Charlie");
GLib.file_set_contents(D + "/notiz.txt", "x");
touch(D + "/a.desktop", 300);
touch(D + "/b.desktop", 100);
touch(D + "/c.desktop", 200);
touch(D + "/notiz.txt", 400);
touch(D + "/Ordner", 500);
// c wird zuletzt "hinzugefuegt" (ctime jetzt), a/b davor.
GLib.usleep(1100000);
GLib.spawn_command_line_sync("chmod 644 " + GLib.shell_quote(D + "/c.desktop"));

GLib.file_set_contents(D + "/.avincelaunch.json", JSON.stringify({
    version: 1,
    order: ["app:b.desktop", "app:a.desktop", "app:c.desktop", "folder:Ordner", "document:notiz.txt"],
    disabled: [],
    zukunft: { feld: 1 }
}));

// Asynchron einlesen und auf das Ergebnis warten.
const scan = mode => {
    let result = null;
    const loop = new GLib.MainLoop(null, false);
    L.linkScanner.scanDirectoryAsync(D, { persistOrder: false, sortMode: mode, folderSort: "mixed" }, r => {
        result = r;
        loop.quit();
    });
    loop.run();
    return result;
};

print("Sortierarten:");
check("manual = gespeicherte Reihenfolge", names(scan("manual")), ["Bravo", "Alpha", "Charlie", "Ordner", "notiz"]);
check("Name A-Z", names(scan("name-asc")), ["Alpha", "Bravo", "Charlie", "notiz", "Ordner"]);
check("Name Z-A", names(scan("name-desc")), ["Ordner", "notiz", "Charlie", "Bravo", "Alpha"]);
check("Typ", names(scan("type")), ["Ordner", "Alpha", "Bravo", "Charlie", "notiz"]);
check("Aenderungsdatum", names(scan("modified")), ["Bravo", "Charlie", "Alpha", "notiz", "Ordner"]);
check("zuletzt hinzugefuegt: Charlie vorn", names(scan("added"))[0], "Charlie");
check("Dialog bekommt immer die gespeicherte Reihenfolge",
    scan("name-desc").manualItems.map(i => i.name), ["Bravo", "Alpha", "Charlie", "Ordner", "notiz"]);

print("Anpinnen:");
check("anpinnen", L.sidecar.setPinned(D, "app:c.desktop", true), true);
check("angepinnt vorn (manual)", names(scan("manual")), ["Charlie", "Bravo", "Alpha", "Ordner", "notiz"]);
check("angepinnt vorn (Z-A)", names(scan("name-desc"))[0], "Charlie");
check("Dialog-Reihenfolge ohne Nadel", scan("manual").manualItems.map(i => i.name)[0], "Bravo");
check("Feld pinned geschrieben", L.sidecar.readSidecar(D).pinned, ["app:c.desktop"]);
check("fremdes Feld erhalten (JS)", L.sidecar.readSidecar(D).extra, { zukunft: { feld: 1 } });

print("Reihenfolge speichern laesst pinned und fremde Felder stehen:");
L.sidecar.saveItemState(D, ["app:a.desktop", "app:b.desktop", "app:c.desktop", "folder:Ordner", "document:notiz.txt"], [], {});
let raw = JSON.parse(new TextDecoder().decode(GLib.file_get_contents(D + "/.avincelaunch.json")[1]));
check("pinned nach saveItemState", raw.pinned, ["app:c.desktop"]);
check("zukunft nach saveItemState", raw.zukunft, { feld: 1 });

print("Verschieben nimmt die Nadel mit:");
// Verschieben meldet asynchron - auf das Ergebnis warten.
const wait = start => {
    let result = null;
    const loop = new GLib.MainLoop(null, false);
    start(value => {
        result = value;
        loop.quit();
    });
    loop.run();
    return result;
};
const r = wait(cb => L.itemActions.moveEntry(D, T, "c.desktop", "app:c.desktop", cb));
GLib.file_set_contents(T + "/.avincelaunch.json", JSON.stringify({ version: 1, order: [], disabled: [] }));
wait(cb => L.itemActions.undoMove(r.record, cb));
check("nach Hin und Zurueck wieder angepinnt", L.sidecar.readSidecar(D).pinned, ["app:c.desktop"]);
wait(cb => L.itemActions.moveEntry(D, T, "c.desktop", "app:c.desktop", cb));
check("im Ziel angepinnt", L.sidecar.readSidecar(T).pinned, ["app:c.desktop"]);
check("in der Quelle nicht mehr", L.sidecar.readSidecar(D).pinned, []);

print("Loesen:");
check("loesen", L.sidecar.setPinned(T, "app:c.desktop", false), false);
check("leer", L.sidecar.readSidecar(T).pinned, []);

print("Python-Dialog verliert keine Felder:");
const py = "import sys, importlib.util as u\n"
    + "s=u.spec_from_file_location('e','Desklet/orderFolderEditor.py'); m=u.module_from_spec(s); s.loader.exec_module(m)\n"
    + "d=m.read_sidecar(sys.argv[1]); d['order']=list(reversed(d['order'])); m.write_sidecar(sys.argv[1], d)\n";
GLib.file_set_contents(root + "/py.py", py);
L.sidecar.setPinned(D, "app:a.desktop", true);
const [, , , status] = GLib.spawn_command_line_sync("python3 " + GLib.shell_quote(root + "/py.py") + " " + GLib.shell_quote(D));
raw = JSON.parse(new TextDecoder().decode(GLib.file_get_contents(D + "/.avincelaunch.json")[1]));
check("Python lief", status, 0);
check("pinned nach Python-Schreiben", raw.pinned, ["app:a.desktop"]);
check("zukunft nach Python-Schreiben", raw.zukunft, { feld: 1 });

GLib.spawn_command_line_sync("rm -rf " + GLib.shell_quote(root) + " " + GLib.shell_quote(shim));
print("\nGeprueft: " + checks + ", Fehler: " + failures);
if (failures > 0) {
    imports.system.exit(1);
}
