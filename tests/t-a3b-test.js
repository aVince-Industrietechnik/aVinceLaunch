// SPDX-License-Identifier: GPL-3.0-only
// Copyright (c) 2026 Angelo Vincenti, aVince Industrietechnik

// Prueft Paket T-A3b der Pruefung Phase 3 Teil 2, Befund N10 (Fence statt
// Symbol entfernt, 10.10.) ohne Cinnamon: Die Methoden werden aus desklet.js
// herausgeloest und mit nachgebauten Menue-Bausteinen ausgefuehrt.
//  - Cinnamons "Dieses Desklet entfernen" wird durch "Diesen Fence entfernen ..."
//    ersetzt; die Rueckfrage nennt den Fence, den Ordner und die Sicherung;
//    vor dem Entfernen wird gesichert; Strg-Klick entfernt ohne Rueckfrage.
//  - Beim Rechtsklick auf ein Symbol ist der Eintrag ausgeblendet.
// Aufruf im Repository-Wurzelverzeichnis:  cjs tests/t-a3b-test.js

const GLib = imports.gi.GLib;
// Wie in Cinnamon: "%s".format(...) (GJS imports.format).
String.prototype.format = imports.format.format;

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

// --- Nachbauten ---------------------------------------------------------------
const CONTROL = 4;
let eventState = 0;
const dialogs = [];

function MenuItem(label) {
    this.label = { text: label, set_text(t) { this.text = t; } };
    this.actor = { visible: true };
    this.handlers = [];
    this.destroyed = false;
}
MenuItem.prototype.connect = function(signal, handler) {
    this.handlers.push(handler);
};
MenuItem.prototype.destroy = function() {
    this.destroyed = true;
};
MenuItem.prototype.activate = function() {
    this.handlers.forEach(h => h(this.actor, { fake: true }));
};

const env = {
    _: s => s,
    PopupMenu: { PopupMenuItem: MenuItem },
    ModalDialog: {
        ConfirmDialog: function(text, callback) {
            this.text = text;
            this.callback = callback;
            this.open = () => dialogs.push(this);
        }
    },
    Clutter: { ModifierType: { CONTROL_MASK: CONTROL } },
    Cinnamon: { get_event_state: () => eventState },
    GLib: { get_user_config_dir: () => "/home/x/.config" },
    MeLib: { settingsBackup: { backupDirFor: (dir, id) => dir + "/avincelaunch/backups/einstellungen-" + id } }
};

function fence(options) {
    const log = [];
    const menuItems = [];
    const cinnamonItem = new MenuItem("Remove this desklet");
    const f = {
        fence_title: options.title || "",
        _rootPath: options.root || null,
        context_menu_item_remove: cinnamonItem,
        _menu: { addMenuItem: item => menuItems.push(item) },
        _getInstanceId: () => "9",
        _getFenceTitle: () => options.title,
        _isPortal: () => !!options.portal,
        _getPortalPath: () => options.portal || null,
        _getCurrentPath: () => options.root || null,
        _backupSettingsFile: () => log.push("Sicherung"),
        _onRemoveDesklet: () => log.push("entfernt")
    };
    ["_replaceRemoveDeskletItem", "_confirmRemoveFence", "_removeFenceNow"].forEach(name => {
        f[name] = method(name, env);
    });
    return { f, log, menuItems, cinnamonItem };
}

// --- Eintrag ersetzt ----------------------------------------------------------
print("Eigener Eintrag statt Cinnamons \"Dieses Desklet entfernen\":");
check("Methoden vorhanden", ["_replaceRemoveDeskletItem", "_confirmRemoveFence", "_removeFenceNow"]
    .map(n => methodSource(n) !== null), [true, true, true]);
let t = fence({ title: "TOOLS", root: "/home/x/.local/share/thelauncher-groups/TOOLS" });
t.f._replaceRemoveDeskletItem();
check("Cinnamons Eintrag entfernt", t.cinnamonItem.destroyed, true);
check("eigener Eintrag im Menue", t.menuItems.map(i => i.label.text), ["Remove this fence…"]);
check("... ist jetzt context_menu_item_remove", t.f.context_menu_item_remove === t.menuItems[0], true);
check("in finalizeContextMenu aufgerufen",
    /finalizeContextMenu\.call\(this\);\n\s*this\._replaceRemoveDeskletItem\(\);/.test(source), true);

print("Rueckfrage:");
eventState = 0;
dialogs.length = 0;
t.menuItems[0].activate();
check("ohne Strg: Rueckfrage, noch nichts entfernt", [dialogs.length, t.log], [1, []]);
const text = dialogs[0].text;
check("nennt den Fence", text.indexOf("“TOOLS”") >= 0, true);
check("nennt den Ordner mit den Symbolen", text.indexOf("/home/x/.local/share/thelauncher-groups/TOOLS") >= 0, true);
check("nennt die Sicherung", text.indexOf("/home/x/.config/avincelaunch/backups/einstellungen-9") >= 0, true);
dialogs[0].callback();
check("Bestaetigen: erst sichern, dann entfernen", t.log, ["Sicherung", "entfernt"]);

t = fence({ title: "DOWNLOADS", portal: "/home/x/Downloads" });
t.f._replaceRemoveDeskletItem();
dialogs.length = 0;
t.menuItems[0].activate();
check("Portal: Ordner bleibt unberuehrt", dialogs[0].text.indexOf("/home/x/Downloads is not touched") >= 0, true);

print("Strg-Klick wie bei Cinnamon:");
t = fence({ title: "TOOLS", root: "/g/TOOLS" });
t.f._replaceRemoveDeskletItem();
eventState = CONTROL;
dialogs.length = 0;
t.menuItems[0].activate();
check("ohne Rueckfrage, mit Sicherung", [dialogs.length, t.log], [0, ["Sicherung", "entfernt"]]);
eventState = 0;

print("Beim Rechtsklick auf ein Symbol ausgeblendet:");
const prepare = methodSource("_prepareItemSection") || "";
check("_prepareItemSection blendet den Eintrag bei einem Symbol aus",
    /this\.context_menu_item_remove\.actor\.visible = !item;/.test(prepare), true);
check("... vor dem Berechnen der Menuegroesse",
    prepare.indexOf("context_menu_item_remove.actor.visible") < prepare.indexOf("this._resetMenuSize()"), true);

print("\nGeprueft: " + checks + ", Fehler: " + failures);
imports.system.exit(failures ? 1 : 0);
