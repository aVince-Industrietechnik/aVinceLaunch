// SPDX-License-Identifier: GPL-3.0-only
// Copyright (c) 2026 Angelo Vincenti, aVince Industrietechnik

// Prueft den Portal-Schutz (Pruefung Phase 2, A6: P10, P26, P50) ohne
// Cinnamon in einem Wegwerfordner: lib/pathSource.js (Basisordner frei,
// Netzlaufwerke aus mountinfo + fstab, sichtbare Ablehnung), lib/sidecar.js
// (Schreiben im Portal / im Basisordner) und lib/portalScanner.js ScanGate
// (hoechstens ein Einlesen je Fence, BT3 Zeitgrenze).
// Aufruf im Repository-Wurzelverzeichnis:  cjs tests/portal-guard-test.js

const Gio = imports.gi.Gio;
const GLib = imports.gi.GLib;

const UUID = "avincelaunch-desklet@avince";
const shim = GLib.dir_make_tmp("avl-shim-XXXXXX");
GLib.mkdir_with_parents(shim + "/desklets", 0o755);
Gio.File.new_for_path(shim + "/desklets/" + UUID).make_symbolic_link(
    GLib.get_current_dir() + "/Desklet", null);
imports.searchPath.unshift(shim);
const P = imports.desklets[UUID].lib.pathSource;
const S = imports.desklets[UUID].lib.sidecar;
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

function clearRoots() {
    ["p1", "p2", "p3"].forEach(id => P.unregisterReadOnlyRoot(id));
}

// --- P10: Basisordner ist nie gesperrt --------------------------------------
print("P10 Basisordner:");
const reports = [];
P.setRefusedReporter(path => reports.push(path));

P._setForTests("/home/u/.local/share/thelauncher-groups", {});
P.registerReadOnlyRoot("p1", "/home/u", "owner1");
check("Portal auf ~ sperrt Gruppenordner nicht",
    P.isReadOnlyPath("/home/u/.local/share/thelauncher-groups/BUERO"), false);
check("Basisordner selbst frei", P.isReadOnlyPath("/home/u/.local/share/thelauncher-groups"), false);
check("Basisordner mit / am Ende frei", P.isReadOnlyPath("/home/u/.local/share/thelauncher-groups/"), false);
check("uebriger Inhalt von ~ bleibt gesperrt", P.isReadOnlyPath("/home/u/Downloads"), true);
check("Portalordner selbst gesperrt", P.isReadOnlyPath("/home/u"), true);
check("aehnlicher Name ist nicht im Basisordner",
    P.isReadOnlyPath("/home/u/.local/share/thelauncher-groups-alt/x"), true);
check(".. fuehrt aus dem Basisordner hinaus",
    P.isReadOnlyPath("/home/u/.local/share/thelauncher-groups/../geheim"), true);
check("ausserhalb jedes Portals frei", P.isReadOnlyPath("/srv/daten"), false);
clearRoots();

P.registerReadOnlyRoot("p1", "/", "owner1");
check("Portal auf / sperrt Gruppenordner nicht",
    P.isReadOnlyPath("/home/u/.local/share/thelauncher-groups/TOOLS"), false);
check("Portal auf / sperrt sonst alles", P.isReadOnlyPath("/etc"), true);
clearRoots();

P.registerReadOnlyRoot("p2", "/home/u/.local/share/thelauncher-groups/BUERO", "owner2");
check("Portal auf einen Gruppenordner: Gruppe schreibt weiter",
    P.isReadOnlyPath("/home/u/.local/share/thelauncher-groups/BUERO"), false);
clearRoots();

P.registerReadOnlyRoot("p1", "/home/u/Downloads", "owner1");
check("normales Portal unveraendert gesperrt", P.isReadOnlyPath("/home/u/Downloads/sub"), true);
check("ohne Portal-Bezug frei", P.isReadOnlyPath("/home/u/Bilder"), false);
P.unregisterReadOnlyRoot("p1", "fremder");
check("fremder Besitzer loescht Schutz nicht (P16)", P.isReadOnlyPath("/home/u/Downloads"), true);
clearRoots();
check("ohne Portale nichts gesperrt", P.isReadOnlyPath("/home/u/Downloads"), false);

P._setForTests("", {});
P.registerReadOnlyRoot("p1", "/home/u", "owner1");
check("Basisordner unbekannt: Schutz wie bisher",
    P.isReadOnlyPath("/home/u/.local/share/thelauncher-groups/BUERO"), true);
clearRoots();

// --- P10: Sidecar schreiben + sichtbare Meldung ----------------------------
print("P10 Sidecar und Meldung:");
const work = GLib.dir_make_tmp("avl-portal-guard-XXXXXX");
const base = work + "/groups";
const group = base + "/BUERO";
const outside = work + "/fremd";
GLib.mkdir_with_parents(group, 0o755);
GLib.mkdir_with_parents(outside, 0o755);
P._setForTests(base, {});
P.registerReadOnlyRoot("p1", work, "owner1");
reports.length = 0;
check("Gruppe im Portal-Bereich: Sidecar geschrieben",
    S.writeSidecar(group, { version: 1, order: ["a"], disabled: [] }), true);
check("Sidecar-Datei da", GLib.file_test(group + "/.avincelaunch.json", GLib.FileTest.EXISTS), true);
check("fremder Ordner im Portal: abgelehnt",
    S.writeSidecar(outside, { version: 1, order: [], disabled: [] }), false);
check("keine Datei im fremden Ordner",
    GLib.file_test(outside + "/.avincelaunch.json", GLib.FileTest.EXISTS), false);
S.writeSidecar(outside, { version: 1, order: [], disabled: [] });
check("Meldung genau einmal je Ordner", reports, [outside]);
clearRoots();

// --- P26: Netzlaufwerk aus mountinfo und fstab -----------------------------
print("P26 Netzlaufwerk:");
const mountinfo = [
    "22 1 8:2 / / rw,relatime shared:1 - ext4 /dev/sda2 rw",
    "61 22 0:51 / /mnt/nas-share rw,relatime shared:30 - autofs systemd-1 rw",
    "90 22 0:60 / /run/user/1000/gvfs rw - fuse.gvfsd-fuse gvfsd-fuse rw",
    "91 22 0:61 / /media/Mit\\040Leer rw - nfs4 srv:/x rw"
].join("\n");
const fstab = [
    "# /etc/fstab",
    "UUID=abc / ext4 errors=remount-ro 0 1",
    "//nas/Backup /mnt/nas-backup cifs credentials=x,noauto 0 0",
    "srv:/export /mnt/nfs-share/ nfs defaults 0 0",
    "sshfs#me@host:/ /mnt/ssh fuse defaults 0 0",
    "#//192.168.0.5/alt /mnt/alt cifs x 0 0",
    "/dev/sdb1 /mnt/usb ext4 noauto 0 0"
].join("\n");
P._setForTests(base, { "/proc/self/mountinfo": mountinfo, "/etc/fstab": fstab });
check("autofs aus mountinfo", P.isNetworkPath("/mnt/nas-share/projekte"), true);
check("cifs nur in fstab (nicht eingehaengt)", P.isNetworkPath("/mnt/nas-backup/x"), true);
check("fstab-Einhaengepunkt selbst", P.isNetworkPath("/mnt/nas-backup"), true);
check("nfs in fstab mit / am Ende", P.isNetworkPath("/mnt/nfs-share/a"), true);
check("sshfs# in fstab", P.isNetworkPath("/mnt/ssh/b"), true);
check("auskommentierte Zeile zaehlt nicht", P.isNetworkPath("/mnt/alt"), false);
check("lokales ext4 in fstab (/) zaehlt nicht", P.isNetworkPath("/home/u"), false);
check("USB ext4 zaehlt nicht", P.isNetworkPath("/mnt/usb"), false);
check("aehnlicher Name zaehlt nicht", P.isNetworkPath("/mnt/nas-backupX"), false);
check("Leerzeichen (\\040) in mountinfo", P.isNetworkPath("/media/Mit Leer/z"), true);
check("gvfs", P.isNetworkPath("/run/user/1000/gvfs/smb-share:x"), true);
check("leerer Pfad", P.isNetworkPath(""), false);

// --- P50: hoechstens ein Einlesen ------------------------------------------
print("P50 ScanGate:");
const started = [];
const results = [];
const cancelled = [];
const gate = new ScanGate((job, done) => {
    started.push(job.name);
    const handle = { done: done, cancel: () => cancelled.push(job.name) };
    gate._lastDone = done;
    gate._handles = gate._handles || {};
    gate._handles[job.name] = handle;
    return handle;
}, (job, result, superseded) => results.push([job.name, result, superseded]));

check("erste Anfrage startet", gate.request({ name: "A" }), true);
check("laeuft", gate.busy, true);
check("Abfrage waehrend Einlesen entfaellt", gate.request({ name: "B", fromPoll: true }), false);
check("Anfrage waehrend Einlesen wartet", gate.request({ name: "C" }), false);
check("weitere Anfrage ersetzt die wartende", gate.request({ name: "D" }), false);
check("nur ein Durchgang gestartet", started, ["A"]);
gate._handles.A.done("ra");
check("A veraltet gemeldet, D gestartet", [results, started], [[["A", "ra", true]], ["A", "D"]]);
gate._handles.D.done("rd");
check("D gueltig gemeldet", results[1], ["D", "rd", false]);
check("danach frei", gate.busy, false);
gate._handles.A.done("spaet");
check("spaete Meldung eines alten Durchgangs ignoriert", results.length, 2);

gate.request({ name: "E" });
gate.request({ name: "F" });
gate.cancel();
check("cancel bricht laufenden ab", cancelled, ["E"]);
check("cancel verwirft wartende", gate.busy, false);
gate._handles.E.done("re");
check("Ergebnis nach cancel ignoriert", results.length, 2);
check("nach cancel kein Folgedurchgang", started, ["A", "D", "E"]);

const syncGate = new ScanGate((job, done) => { done("sofort"); return null; },
    (job, result, superseded) => results.push([job.name, result, superseded]));
syncGate.request({ name: "S" });
check("sofortige Meldung (Fehlerweg) geht durch", results[2], ["S", "sofort", false]);
check("sofortige Meldung: danach frei", syncGate.busy, false);

const chainResults = [];
let chainGate = null;
chainGate = new ScanGate((job, done) => {
    GLib.idle_add(GLib.PRIORITY_DEFAULT, () => { done(job.name); return GLib.SOURCE_REMOVE; });
    return null;
}, (job, result, superseded) => {
    chainResults.push([result, superseded]);
    if (result === "G1" && !superseded) {
        // Ergebnis loest selbst eine neue Anfrage aus (z. B. anderer Ordner).
        chainGate.request({ name: "G2" });
    }
});
chainGate.request({ name: "G1" });
const loop = new GLib.MainLoop(null, false);
GLib.timeout_add(GLib.PRIORITY_DEFAULT, 200, () => { loop.quit(); return GLib.SOURCE_REMOVE; });
loop.run();
check("Anfrage aus dem Ergebnis heraus startet neu", chainResults, [["G1", false], ["G2", false]]);

// --- BT3 (T16): Zeitgrenze, genau ein weiterer Versuch -----------------------
print("BT3 Zeitgrenze:");
function runLoop(ms) {
    const l = new GLib.MainLoop(null, false);
    GLib.timeout_add(GLib.PRIORITY_DEFAULT, ms, () => { l.quit(); return GLib.SOURCE_REMOVE; });
    l.run();
}
const tStarted = [];
const tResults = [];
const tHandles = {};
const tGate = new ScanGate((job, done) => {
    tStarted.push(job.name);
    tHandles[job.name] = { done: done, cancelled: false };
    return { cancel: () => { tHandles[job.name].cancelled = true; } };
}, (job, result, superseded) => tResults.push([job.name, result, superseded]),
{ timeoutMs: 50, timeoutResult: job => "zeit:" + job.name });

tGate.request({ name: "H1" });
runLoop(120);
check("nach der Zeitgrenze: 'haengt' gemeldet", tResults, [["H1", "zeit:H1", false]]);
check("haengender Durchgang wird nicht abgebrochen (Faden kann zurueckkehren)",
    tHandles.H1.cancelled, false);
check("ein haengender, Gate frei", [tGate.busy, tGate.stalled], [false, 1]);
check("genau ein weiterer Versuch (auch als Abfrage)", tGate.request({ name: "H2", fromPoll: true }), true);
runLoop(120);
check("auch der zweite haengt", tResults[1], ["H2", "zeit:H2", false]);
check("zwei haengende", tGate.stalled, 2);
check("Abfrage startet keinen dritten", tGate.request({ name: "H3", fromPoll: true }), false);
check("Anfrage startet keinen dritten, wartet", tGate.request({ name: "H4" }), false);
check("nur zwei Durchgaenge gestartet", tStarted, ["H1", "H2"]);
tHandles.H1.done("spaet1");
check("spaete Rueckkehr mit wartender Anfrage: veraltet, wartende startet",
    [tResults[2], tStarted], [["H1", "spaet1", true], ["H1", "H2", "H4"]]);
check("ein haengender bleibt", tGate.stalled, 1);
tHandles.H2.done("spaet2");
check("spaete Rueckkehr waehrend neuerer laeuft: ignoriert", tResults.length, 3);
check("kein haengender mehr", tGate.stalled, 0);
tHandles.H4.done("r4");
check("neuerer Durchgang gilt", tResults[3], ["H4", "r4", false]);
runLoop(120);
check("erledigter Durchgang meldet keine Zeitueberschreitung", tResults.length, 4);

tGate.request({ name: "H5" });
runLoop(120);
tHandles.H5.done("spaet5");
check("spaete Rueckkehr ohne neueren Durchgang: Ergebnis gilt (Freigabe wieder da)",
    [tResults[5], tGate.stalled, tGate.busy], [["H5", "spaet5", false], 0, false]);

tGate.request({ name: "H6" });
runLoop(120);
tGate.request({ name: "H7" });
runLoop(120);
check("vor cancel: zwei haengende", tGate.stalled, 2);
tGate.cancel();
check("cancel vergisst haengende und bricht sie ab",
    [tGate.stalled, tHandles.H6.cancelled, tHandles.H7.cancelled], [0, true, true]);
const vorWechsel = tResults.length;
check("neuer Ordner nach cancel startet sofort", tGate.request({ name: "H8" }), true);
tHandles.H6.done("alt6");
check("Ergebnis eines vergessenen haengenden ignoriert", tResults.length, vorWechsel);
tHandles.H8.done("r8");
check("neuer Ordner gemeldet", tResults[tResults.length - 1], ["H8", "r8", false]);
tGate.request({ name: "H9" });
tGate.cancel();
runLoop(120);
check("cancel stoppt die Zeitgrenze", tResults[tResults.length - 1], ["H8", "r8", false]);

const noTimeout = new ScanGate(() => null, () => tResults.push("x"));
noTimeout.request({ name: "N" });
runLoop(120);
check("ohne timeoutResult keine Zeitgrenze", [noTimeout.busy, noTimeout.stalled], [true, 0]);

// --- Aufraeumen --------------------------------------------------------------
P._setForTests(undefined, null);
GLib.spawn_command_line_sync("rm -rf " + GLib.shell_quote(work) + " " + GLib.shell_quote(shim));

print("");
print("Geprueft: " + checks + ", Fehler: " + failures);
if (failures > 0) {
    imports.system.exit(1);
}
