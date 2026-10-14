// SPDX-License-Identifier: GPL-3.0-only
// Copyright (c) 2026 Angelo Vincenti, aVince Industrietechnik

// Prueft Paket P3-2, Befund N9 (Wayland-Testliste K11, W10/W11) ohne
// Cinnamon: Die betroffenen Methoden werden aus desklet.js herausgeloest
// und mit nachgebauten Bausteinen ausgefuehrt.
//  - Titel-Lasche: erst zeigen (St wendet dabei die Stile aller Teile an),
//    dann messen - Unterkante = Oberkante des Fence; weicht die echte Hoehe
//    ab, rueckt sie nach dem Layout nach.
//  - Aufklappen beim Ueberfahren (Angelo 09.10., Variante B): gesperrt
//    verschwindet die Leiste, der Inhalt steht in seinem Rahmen; entsperrt
//    bleibt die Leiste (Griff zum Verschieben).
// Aufruf im Repository-Wurzelverzeichnis:  cjs tests/p3-2-test.js

const GLib = imports.gi.GLib;

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

const [, bytes] = GLib.file_get_contents("Desklet/desklet.js");
const source = new TextDecoder().decode(bytes);

// "    name: function(args) { ... }," als "function(args) { ... }" herausloesen.
function methodSource(name) {
    const start = source.indexOf("\n    " + name + ": function(");
    if (start < 0) {
        return null;
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

function method(name, env) {
    const text = methodSource(name);
    if (text === null) {
        return null;
    }
    const keys = Object.keys(env || {});
    return new Function(...keys, "return (" + text + ");")(...keys.map(k => env[k]));
}

function fakeActor(visible) {
    return {
        visible: visible,
        show() { this.visible = true; },
        hide() { this.visible = false; },
        is_finalized() { return false; }
    };
}

let globalLock = false;
const isDragLocked = lock => !!lock || globalLock;

// --- Aufklappen beim Ueberfahren -------------------------------------------
print("Aufklappen beim Ueberfahren (_updateCollapsedPeek):");
const peek = method("_updateCollapsedPeek", {});
const hidesBar = method("_peekHidesBar", { isDragLocked });
check("_peekHidesBar vorhanden", hidesBar !== null, true);

function fence(lock) {
    return {
        lock_position: lock,
        expand_on_hover: true,
        _peekOpen: false,
        _collapsedBar: fakeActor(true),
        _collapsedContent: fakeActor(false),
        styled: [],
        joined: null,
        _isCollapsed() { return true; },
        _styleCollapsedBar(bar, joined) { this.styled.push(joined); },
        _setTabJoined(joined) { this.joined = joined; },
        _peekHidesBar: hidesBar || (() => false)
    };
}
const state = f => ({ leiste: f._collapsedBar.visible, inhalt: f._collapsedContent.visible,
    verbunden: f.joined, leisteEckig: f.styled[f.styled.length - 1] });

let f = fence(true);
peek.call(f, true);
check("gesperrt, auf: Leiste weg, Inhalt da, nicht verbunden", state(f),
    { leiste: false, inhalt: true, verbunden: false, leisteEckig: false });
peek.call(f, false);
check("gesperrt, zu: Leiste da, Inhalt weg", state(f),
    { leiste: true, inhalt: false, verbunden: false, leisteEckig: false });

f = fence(false);
peek.call(f, true);
check("entsperrt, auf: Leiste bleibt, verbunden (wie bisher)", state(f),
    { leiste: true, inhalt: true, verbunden: true, leisteEckig: true });
peek.call(f, false);
check("entsperrt, zu: Leiste da, Inhalt weg", state(f),
    { leiste: true, inhalt: false, verbunden: false, leisteEckig: false });

globalLock = true;
f = fence(false);
peek.call(f, true);
check("alle Desklets gesperrt (lock-desklets): Leiste weg", state(f).leiste, false);
globalLock = false;

f = fence(true);
peek.call(f, true);
const styledBefore = f.styled.length;
peek.call(f, true);
check("gleicher Zustand: nichts neu gesetzt", f.styled.length, styledBefore);

// --- Neuaufbau waehrend des Aufklappens ------------------------------------
print("Neuaufbau eingeklappt (_wrapCollapsed):");
class FakeBox {
    constructor() { this.children = []; }
    add_child(child) { this.children.push(child); }
}
const wrap = method("_wrapCollapsed", { St: { BoxLayout: FakeBox } });
function wrapFence(lock, peekOpen) {
    const base = fence(lock);
    base._peekOpen = peekOpen;
    base._buildCollapsedBar = function() {
        const bar = fakeActor(true);
        this._styleCollapsedBar(bar, !!this._peekOpen);
        return bar;
    };
    return base;
}
f = wrapFence(true, true);
let content = fakeActor(true);
let box = wrap.call(f, content);
check("gesperrt, aufgeklappt: Leiste verborgen, Inhalt sichtbar",
    [box.children[0].visible, content.visible, f.styled[f.styled.length - 1]], [false, true, false]);
f = wrapFence(false, true);
content = fakeActor(true);
box = wrap.call(f, content);
check("entsperrt, aufgeklappt: Leiste sichtbar", [box.children[0].visible, content.visible], [true, true]);
f = wrapFence(true, false);
content = fakeActor(true);
box = wrap.call(f, content);
check("eingeklappt (zu): Leiste sichtbar, Inhalt verborgen", [box.children[0].visible, content.visible], [true, false]);

// --- Titel-Lasche -----------------------------------------------------------
print("Titel-Lasche (_showTitleTab):");
const calls = [];
const STYLE_HEIGHT = 29;
const OLD_HEIGHT = 27;
function fakeTab() {
    return {
        visible: false,
        y: 0,
        height: STYLE_HEIGHT,
        dirty: false,
        is_finalized() { return false; },
        set_style() { this.dirty = true; calls.push("set_style"); },
        // ensure_style() erreicht die verborgenen Teile nicht (Geraetetest 09.10. 21:33).
        ensure_style() { calls.push("ensure_style"); },
        set_width() { calls.push("set_width"); },
        // Wie St: ohne angewendeten Stil misst die verborgene Lasche falsch.
        get_preferred_height() { calls.push("get_preferred_height"); return [0, this.dirty ? OLD_HEIGHT : STYLE_HEIGHT]; },
        set_position(x, y) { this.x = x; this.y = y; calls.push("set_position"); },
        set_y(y) { this.y = y; },
        // Zeigen mappt die Lasche samt Teilen - dabei wendet St alle Stile an.
        show() { this.visible = true; this.dirty = false; calls.push("show"); }
    };
}
const showTab = method("_showTitleTab", { Main: { uiGroup: { set_child_above_sibling() {} } } });
function tabFence() {
    return {
        transparent_background: false,
        desklet_bg_color: "rgba(128,128,128,0.3)",
        actor: { is_finalized() { return false; }, get_transformed_position() { return [50, 300]; },
                 get_transformed_size() { return [360, 210]; } },
        _titleTab: fakeTab(),
        _titleTabLabel: { set_style() {} },
        _titleTabIcon: { set_style() {} },
        _getTitleTextColors() { return { color: "#fff", shadow: "#000" }; },
        _getTitleTextAlign() { return "center"; },
        _setTabJoined(j) { this.joined = j; }
    };
}
const tf = tabFence();
showTab.call(tf);
check("erstes Zeigen: Unterkante = Oberkante des Fence (271 + 29 = 300)", tf._titleTab.y + STYLE_HEIGHT, 300);
check("erst gezeigt, dann gemessen",
    calls.indexOf("show") >= 0 && calls.indexOf("show") < calls.indexOf("get_preferred_height"), true);
check("Lage erst nach dem Messen gesetzt",
    calls.lastIndexOf("set_position") > calls.indexOf("get_preferred_height"), true);
check("verbunden, solange die Lasche steht", tf.joined, true);

print("Titel-Lasche nachruecken (_queueTitleTabAlign):");
const queued = [];
const align = method("_queueTitleTabAlign", {
    Mainloop: { idle_add(fn) { queued.push(fn); return 42; } }
});
check("_queueTitleTabAlign vorhanden", align !== null, true);
if (align) {
    const af = tabFence();
    af._titleTab.visible = true;
    af._titleTab.y = 266;
    align.call(af);
    align.call(af);
    check("nur ein Nachruecken vorgemerkt", queued.length, 1);
    check("nicht sofort (mitten im Layout)", af._titleTab.y, 266);
    queued[0]();
    check("nach dem Layout: 300 - 29 = 271", af._titleTab.y, 271);
    check("Vormerkung geloest", af._titleTabAlignId, 0);
    const hidden = tabFence();
    hidden._titleTab.visible = false;
    hidden._titleTab.y = 266;
    queued.length = 0;
    align.call(hidden);
    queued[0]();
    check("verborgene Lasche bleibt unberuehrt", hidden._titleTab.y, 266);
}

print("Quelltext:");
const build = methodSource("_buildTitleTab") || "";
check("_buildTitleTab: notify::height -> _queueTitleTabAlign",
    /connect\("notify::height",\s*this\._queueTitleTabAlign\.bind\(this\)\)/.test(build), true);
const destroy = methodSource("_destroyTitleTab") || "";
check("_destroyTitleTab: Vormerkung wird entfernt",
    /Mainloop\.source_remove\(this\._titleTabAlignId\)/.test(destroy), true);

print("\nGeprueft: " + checks + ", Fehler: " + failures);
if (failures > 0) {
    imports.system.exit(1);
}
