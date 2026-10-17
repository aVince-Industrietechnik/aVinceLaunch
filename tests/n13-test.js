// SPDX-License-Identifier: GPL-3.0-only
// Copyright (c) 2026 Angelo Vincenti, aVince Industrietechnik

// N13 (Neu-Nutzer-Pruefung am Tower, 12.10.): Regel fuer das Anlegen des
// eigenen Gruppenordners (lib/config.js ensureOwnLinkDirectory) in einem
// Wegwerfordner ohne Cinnamon, dazu die Stellen in desklet.js, die sie nutzen.
// Aufruf im Repository-Wurzelverzeichnis:  cjs tests/n13-test.js

const Gio = imports.gi.Gio;
const GLib = imports.gi.GLib;

// Vor dem ersten Zugriff auf die Benutzerordner (lib/config.js liest sie beim Laden).
const work = GLib.dir_make_tmp("avl-n13-XXXXXX");
GLib.setenv("XDG_CONFIG_HOME", work + "/config", true);
GLib.setenv("XDG_DATA_HOME", work + "/data", true);
// Greift die Umleitung nicht, sofort abbrechen - bevor etwas angelegt wird.
if (GLib.get_user_config_dir() !== work + "/config" || GLib.get_user_data_dir() !== work + "/data") {
    printerr("ABBRUCH: Umleitung in den Wegwerfordner greift nicht - nichts geschrieben.");
    imports.system.exit(2);
}

const UUID = "avincelaunch-desklet@avince";
const shim = GLib.dir_make_tmp("avl-shim-XXXXXX");
GLib.mkdir_with_parents(shim + "/desklets", 0o755);
Gio.File.new_for_path(shim + "/desklets/" + UUID).make_symbolic_link(
    GLib.get_current_dir() + "/Desklet", null);
imports.searchPath.unshift(shim);
const C = imports.desklets[UUID].lib.config;

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

const isDir = path => GLib.file_test(path, GLib.FileTest.IS_DIR);
const exists = path => GLib.file_test(path, GLib.FileTest.EXISTS);
const CONFIG_DIR = work + "/config/avincelaunch";
const DEFAULT = work + "/data/avincelaunch";

function setBase(path) {
    GLib.mkdir_with_parents(CONFIG_DIR, 0o755);
    if (path === null) {
        if (exists(CONFIG_DIR + "/config.json")) {
            GLib.unlink(CONFIG_DIR + "/config.json");
        }
        return;
    }
    GLib.file_set_contents(CONFIG_DIR + "/config.json", JSON.stringify({ version: 1, baseDirectory: path }));
}

// --- 1. Neuer Nutzer: keine config.json, Standard-Basisordner fehlt ---------
setBase(null);
check("Ausgangslage: Standard-Basisordner fehlt", exists(DEFAULT), false);
check("neuer Nutzer: default wird angelegt", C.ensureOwnLinkDirectory("default"),
    { state: "angelegt", path: DEFAULT + "/default" });
check("neuer Nutzer: Ordner ist da", isDir(DEFAULT + "/default"), true);
check("zweiter Aufruf: da, nichts Neues", C.ensureOwnLinkDirectory("default"),
    { state: "da", path: DEFAULT + "/default" });
check("leerer Unterordner gilt als default", C.ensureOwnLinkDirectory(""),
    { state: "da", path: DEFAULT + "/default" });
check("verschachtelt A/B", C.ensureOwnLinkDirectory("A/B"),
    { state: "angelegt", path: DEFAULT + "/A/B" });
check("fuehrender Schraegstrich bleibt im Basisordner", C.ensureOwnLinkDirectory("/etc"),
    { state: "angelegt", path: DEFAULT + "/etc" });

// --- 2. Nie ausserhalb des Basisordners -------------------------------------
check("'..' abgelehnt", C.ensureOwnLinkDirectory("../draussen"), { state: "ausserhalb", path: null });
check("'..' in der Mitte abgelehnt", C.ensureOwnLinkDirectory("A/../../draussen"), { state: "ausserhalb", path: null });
check("'.' abgelehnt", C.ensureOwnLinkDirectory("./x"), { state: "ausserhalb", path: null });
check("nichts neben dem Basisordner entstanden", exists(work + "/data/draussen"), false);

// --- 3. Eigener Basisordner vorhanden: nur der Gruppenordner -----------------
const OWN = work + "/eigen";
GLib.mkdir_with_parents(OWN, 0o755);
setBase(OWN);
check("eigene Basis da: Gruppenordner angelegt", C.ensureOwnLinkDirectory("GRUPPE"),
    { state: "angelegt", path: OWN + "/GRUPPE" });

// --- 4. Eigener Basisordner fehlt (NAS nicht eingebunden): nichts anlegen ----
const NAS = work + "/nas/aVinceLaunch";
setBase(NAS);
check("eigene Basis fehlt: basis-fehlt", C.ensureOwnLinkDirectory("GRUPPE"), { state: "basis-fehlt", path: null });
check("eigene Basis fehlt: nichts angelegt", exists(work + "/nas"), false);

// --- 5. Anlegen scheitert (Datei statt Ordner) ------------------------------
setBase(OWN);
GLib.file_set_contents(OWN + "/DATEI", "x");
check("Datei mit dem Namen: fehler", C.ensureOwnLinkDirectory("DATEI"), { state: "fehler", path: null });
check("Datei bleibt unangetastet", GLib.file_test(OWN + "/DATEI", GLib.FileTest.IS_REGULAR), true);

// --- 6. Verwendung in desklet.js --------------------------------------------
const [, bytes] = GLib.file_get_contents("Desklet/desklet.js");
const src = new TextDecoder().decode(bytes);
const start = src.indexOf('this._ensureOwnFolder("Start");');
// Schritt 4, V4d: auf einem Netzlaufwerk nicht beim Start (synchron), sondern
// erst, wenn das asynchrone Auflisten geantwortet hat.
check("Start: Ordner anlegen direkt vor _applyStoragePath(false), lokal", start > 0
    && /^this\._ensureOwnFolder\("Start"\);\s*\}\s*this\._applyStoragePath\(false\);/.test(src.substring(start))
    && /if \(!this\._isPortal\(\) && !isNetworkPath\(getResolvedPath\(this\.subdirectory\)\)\) \{\s*$/
        .test(src.substring(start - 200, start)), true);
check("drei Aufrufer (Start, Menue, Netz nach Antwort)", (src.match(/this\._ensureOwnFolder\(/g) || []).length, 3);
const netz = src.indexOf("_onLinkScanResult: function(");
const netzEnde = src.indexOf("\n    },", netz);
// Seit dem Async-Umbau lesen auch lokale Fences ueber _onLinkScanResult -
// angelegt wird dort weiter nur im Netz-Modus (lokal: beim Start).
check("Netz: anlegen nur bei 'missing' des eigenen Ordners, einmal, nur im Netz-Modus",
    /this\._linkIsNetwork && job\.path === this\._rootPath && !this\._linkOwnFolderChecked\s*&& result\.error !== "timeout"[\s\S]{0,400}if \(result\.error === "missing"\) \{\s*const ensured = this\._ensureOwnFolder\("Start"\);/
        .test(src.substring(netz, netzEnde)), true);
check("Menue: Verknuepfungsordner oeffnen legt an", src.indexOf('this._ensureOwnFolder("Menue")') > 0, true);
const menu = src.indexOf('this._ensureOwnFolder("Menue")');
check("Menue: auch ein inzwischen geloeschter Ordner wird angelegt",
    /if \(!isDir\(path\) && !this\._isPortal\(\)\) \{/.test(src.substring(menu - 400, menu)), true);
const msg = src.indexOf("_buildMessage: function(message) {");
check("_buildMessage richtet die Maus-Erkennung ein",
    src.substring(msg, src.indexOf("new St.BoxLayout", msg)).indexOf("this._ensureHoverWindowTitle();") > 0, true);
check("Meldung bricht um (kein Abschneiden)",
    src.substring(msg, msg + 900).indexOf("this._wrapMessageLabel(new St.Label({") > 0
    && /set_line_wrap\(true\)[\s\S]{0,200}EllipsizeMode\.NONE/.test(src), true);
check("auch 'Noch keine Eintraege' mit Pfad bricht um",
    /const empty = this\._wrapMessageLabel\(new St\.Label\(\{\s+text: allItems\.length > 0/.test(src), true);
check("alter Meldungstext entfernt", src.indexOf("Link subdirectory → Browse") === -1, true);
check("Portale legen nichts an", /_ensureOwnFolder: function\(anlass\) \{\s+if \(this\._isPortal\(\)\) \{\s+return null;/.test(src), true);

// --- Aufraeumen --------------------------------------------------------------
GLib.spawn_command_line_sync("rm -rf " + GLib.shell_quote(work) + " " + GLib.shell_quote(shim));
print("");
print("Geprueft: " + checks + ", Fehler: " + failures);
if (failures > 0) {
    imports.system.exit(1);
}
