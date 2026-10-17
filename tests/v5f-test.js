// SPDX-License-Identifier: GPL-3.0-only
// Copyright (c) 2026 Angelo Vincenti, aVince Industrietechnik

// Schritt 4, V5f / N28 - Beschreibung im Tooltip eines Programms.
// lib/linkScanner.js fragte appInfo.get_comment() ab - das gibt es in Gio
// nicht (das Feld "Comment" heisst dort description); der Fehler wurde still
// abgefangen, die Beschreibung blieb immer leer (W6, 3c.7). Geprueft an
// echten .desktop-Dateien in einem Wegwerfordner: parseDesktopEntry,
// scanDirectoryAsync und das Portal-Einlesen liefern die
// Beschreibung; ohne "Comment=" bleibt sie leer; der Tooltip-Text aus
// desklet.js setzt sie unter den Namen.
// Aufruf im Repository-Wurzelverzeichnis:  cjs tests/v5f-test.js

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

const work = GLib.dir_make_tmp("avl-v5f-XXXXXX");
function write(name, text) {
    GLib.file_set_contents(work + "/" + name, text);
    return work + "/" + name;
}
const withComment = write("avl-editor.desktop",
    "[Desktop Entry]\nType=Application\nName=AVL Editor\nComment=Edit text files\nExec=true\n");
const without = write("avl-ohne.desktop",
    "[Desktop Entry]\nType=Application\nName=AVL Ohne\nExec=true\n");

// Asynchrones Einlesen abwarten (hoechstens 5 s).
function wait(start) {
    let result = null;
    const loop = new GLib.MainLoop(null, false);
    start(r => { result = r; loop.quit(); });
    GLib.timeout_add(GLib.PRIORITY_DEFAULT, 5000, () => { loop.quit(); return GLib.SOURCE_REMOVE; });
    loop.run();
    return result;
}
const bytesOf = path => GLib.file_get_contents(path)[1];

print("N28 Beschreibung aus der .desktop-Datei:");
check("parseDesktopEntry: Comment= wird Beschreibung",
    L.linkScanner.parseDesktopEntry(withComment, null, bytesOf(withComment)).comment, "Edit text files");
check("parseDesktopEntry: ohne Comment= leer",
    L.linkScanner.parseDesktopEntry(without, null, bytesOf(without)).comment, "");

const scanned = wait(cb => L.linkScanner.scanDirectoryAsync(work, { sortMode: "name-asc" }, cb)) || {};
const byName = {};
(scanned.items || []).forEach(i => { byName[i.name] = i.comment; });
check("scanDirectoryAsync: Beschreibungen", byName, { "AVL Editor": "Edit text files", "AVL Ohne": "" });

const asyncResult = wait(cb => L.portalScanner.scanPortalAsync(work, { sortMode: "name-asc" }, cb));
const asyncByName = {};
((asyncResult || {}).items || []).forEach(i => { asyncByName[i.name] = i.comment; });
check("Portal (asynchron): Beschreibungen gleich", asyncByName, byName);

const scannerSource = new TextDecoder().decode(GLib.file_get_contents("Desklet/lib/linkScanner.js")[1]);
check("kein get_comment() mehr", /get_comment\s*\(/.test(scannerSource), false);

print("Tooltip-Text (desklet.js):");
const source = new TextDecoder().decode(GLib.file_get_contents("Desklet/desklet.js")[1]);
const m = source.match(/\n    _tooltipText: function\(item\) \{\n([\s\S]*?)\n    \},\n/);
check("_tooltipText im Quelltext gefunden", !!m, true);
const tooltipText = m ? new Function("item", m[1]) : () => "";
check("Programm: Name, darunter Beschreibung",
    tooltipText({ type: "app", name: "AVL Editor", comment: "Edit text files" }), "AVL Editor\nEdit text files");
check("Programm ohne Beschreibung: nur der Name",
    tooltipText({ type: "app", name: "AVL Ohne", comment: "" }), "AVL Ohne");

// Das Einlesen legt die Reihenfolge-Datei .avincelaunch.json an.
const children = Gio.File.new_for_path(work).enumerate_children("standard::name", 0, null);
let child;
while ((child = children.next_file(null)) !== null) {
    Gio.File.new_for_path(work + "/" + child.get_name()).delete(null);
}
Gio.File.new_for_path(work).delete(null);
Gio.File.new_for_path(shim + "/desklets/" + UUID).delete(null);
Gio.File.new_for_path(shim + "/desklets").delete(null);
Gio.File.new_for_path(shim).delete(null);

print("\nGeprueft: " + checks + ", Fehler: " + failures);
imports.system.exit(failures ? 1 : 0);
