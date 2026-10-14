#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
# Copyright (c) 2026 Angelo Vincenti, aVince Industrietechnik

# Schritt 4, V3a ohne Cinnamon, in einem Wegwerfordner:
#  A. scripts/desktop-clean-toggle (B6, T5) mit gespieltem gsettings:
#     Markierung statt Eval, Nemo-Symbole aus/an, eigenes "Symbole aus" des
#     Nutzers wird nie ueberschrieben, Uebernahme des alten Zustands,
#     --hide/--show/--status.
#  B. scripts/desktop-doubleclick (P38, P71, T6): Flaechen aus fences.json,
#     Entscheidung frei/gesperrt, Doppelklick-Erkennung, nur Maustasten
#     abonniert, keine Hilfsprozesse je Klick.
# Aufruf im Repository-Wurzelverzeichnis:  python3 tests/v3a-test.py

import importlib.machinery
import importlib.util
import json
import os
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True

WORK = tempfile.mkdtemp(prefix="avl-v3a-test.")
os.environ["HOME"] = os.path.join(WORK, "home")
os.environ["XDG_STATE_HOME"] = os.path.join(WORK, "state")
os.environ["XDG_RUNTIME_DIR"] = os.path.join(WORK, "run")
import umleitung  # noqa: E402 - A9/P70
umleitung.pruefe(WORK, "HOME", "XDG_STATE_HOME", "XDG_RUNTIME_DIR")

checks = 0
failures = 0


def check(name, actual, expected):
    global checks, failures
    checks += 1
    if actual == expected:
        print("  ok      " + name)
    else:
        failures += 1
        print(f"  FEHLER  {name}\n          erwartet {expected!r}\n          erhalten {actual!r}")


# --- A. desktop-clean-toggle ---------------------------------------------------
print("A. desktop-clean-toggle:")
BIN = os.path.join(WORK, "bin")
os.makedirs(BIN)
GS = os.path.join(WORK, "gsettings.json")
# Gespieltes gsettings: nur org.nemo.desktop, Werte in einer Datei.
with open(os.path.join(BIN, "gsettings"), "w") as f:
    f.write("""#!/usr/bin/env python3
import json, sys
path = %r
data = json.load(open(path))
cmd, schema = sys.argv[1], sys.argv[2]
if schema != "org.nemo.desktop":
    sys.exit(1)
if cmd == "list-keys":
    print("\\n".join(data["keys"]))
elif cmd == "get":
    print(data["values"][sys.argv[3]])
elif cmd == "set":
    if data.get("fail_set"):
        sys.exit(1)
    value = sys.argv[4]
    # Wie gsettings: Zeichenketten kommen mit Anfuehrungszeichen zurueck.
    if value not in ("true", "false") and not value.startswith("'"):
        value = "'" + value + "'"
    data["values"][sys.argv[3]] = value
    data["log"].append(sys.argv[3] + "=" + sys.argv[4])
    json.dump(data, open(path, "w"))
""" % GS)
os.chmod(os.path.join(BIN, "gsettings"), 0o755)
ENV = dict(os.environ, PATH=BIN + ":/usr/bin:/bin")
STATE = os.path.join(WORK, "state", "avincelaunch")
MARKER = os.path.join(STATE, "schreibtisch-frei")
LAYOUT = os.path.join(STATE, "nemo-layout")


def nemo(layout="'true::false'", keys=("desktop-layout",), show="true", fail_set=False):
    json.dump({"keys": list(keys), "values": {"desktop-layout": layout, "show-desktop-icons": show},
               "log": [], "fail_set": fail_set}, open(GS, "w"))


def gs():
    return json.load(open(GS))


def toggle(*args):
    out = subprocess.run(["bash", "scripts/desktop-clean-toggle", *args], env=ENV,
                         capture_output=True, text=True)
    return out.returncode, out.stdout.strip()


nemo()
check("Status ohne Markierung", toggle("--status"), (0, "shown"))
rc, out = toggle()
check("Umschalten 1: blendet aus", (rc, os.path.exists(MARKER), gs()["values"]["desktop-layout"]),
      (0, True, "'false::false'"))
check("... Anordnung gemerkt", open(LAYOUT).read().strip(), "'true::false'")
check("Status frei", toggle("--status"), (0, "free"))
rc, out = toggle()
check("Umschalten 2: blendet ein, Anordnung zurueck und vergessen",
      (rc, os.path.exists(MARKER), gs()["values"]["desktop-layout"], os.path.exists(LAYOUT)),
      (0, False, "'true::false'", False))

# T5: Symbole hat der Nutzer selbst ausgeschaltet.
nemo(layout="'false::false'")
open(LAYOUT, "w").write("'true::true'\n")
toggle()
check("T5: Symbole schon aus -> keine (alte) Anordnung gemerkt, nichts gesetzt",
      (os.path.exists(MARKER), os.path.exists(LAYOUT), gs()["log"]), (True, False, []))
toggle()
check("T5: Einblenden laesst das eigene 'Symbole aus' stehen",
      (os.path.exists(MARKER), gs()["values"]["desktop-layout"], gs()["log"]),
      (False, "'false::false'", []))

# T5: ohne einen einzigen Fence entscheidet die Markierung (kein Eval mehr).
nemo()
toggle("--hide")
toggle("--hide")
check("--hide zweimal: bleibt frei, Anordnung nicht ueberschrieben",
      (os.path.exists(MARKER), open(LAYOUT).read().strip()), (True, "'true::false'"))
toggle("--show")
toggle("--show")
check("--show zweimal: bleibt sichtbar", (os.path.exists(MARKER), gs()["values"]["desktop-layout"]),
      (False, "'true::false'"))

nemo(fail_set=True)
toggle()
check("gsettings scheitert: Fences trotzdem aus, keine Anordnung gemerkt",
      (os.path.exists(MARKER), os.path.exists(LAYOUT)), (True, False))
nemo()
toggle()

nemo(keys=("show-desktop-icons",))
toggle()
check("aeltere Nemo-Fassung (show-desktop-icons)", gs()["values"]["show-desktop-icons"], "false")
toggle()
check("... zurueck", (gs()["values"]["show-desktop-icons"], os.path.exists(os.path.join(STATE, "nemo-show-icons"))),
      ("true", False))

# Uebernahme des Zustands von vor V3.
OLD = os.path.join(WORK, "state", "desktop-clean-toggle")
os.makedirs(OLD)
open(os.path.join(OLD, "nemo-layout"), "w").write("'true::false'\n")
open(os.path.join(OLD, "nemo-show-icons"), "w").write("true\n")
nemo()
check("alter Zustand nicht ausgeblendet: Reste verworfen, Status sichtbar",
      (toggle("--status"), os.path.exists(OLD), os.path.exists(LAYOUT)), ((0, "shown"), False, False))
os.makedirs(OLD)
open(os.path.join(OLD, "hidden"), "w").write("c2")
open(os.path.join(OLD, "nemo-layout"), "w").write("'true::true'\n")
nemo(layout="'false::false'")
check("alter Zustand ausgeblendet: Markierung + Anordnung uebernommen",
      (toggle("--status"), open(LAYOUT).read().strip(), os.path.exists(OLD)), ((0, "free"), "'true::true'", False))
toggle()
check("... Einblenden stellt die alte Anordnung her", gs()["values"]["desktop-layout"], "'true::true'")
check("unbekannte Option", toggle("--egal")[0], 2)
with open("scripts/desktop-clean-toggle", encoding="utf-8") as f:
    src = f.read()
check("kein Eval/gdbus mehr", ["gdbus" in src, "--method org.Cinnamon.Eval" in src], [False, False])

# --- B. desktop-doubleclick ------------------------------------------------------
print("B. desktop-doubleclick:")
loader = importlib.machinery.SourceFileLoader("desktop_doubleclick", "scripts/desktop-doubleclick")
spec = importlib.util.spec_from_loader("desktop_doubleclick", loader)
DC = importlib.util.module_from_spec(spec)
loader.exec_module(DC)
check("Markierung = dieselbe wie beim Umschalter", str(DC.MARKER), MARKER)
check("Flaechen aus dem Laufzeitordner", str(DC.FENCES_FILE), os.path.join(WORK, "run", "avincelaunch", "fences.json"))
check("Umschalter liegt neben dem Skript", DC.TOGGLE.name, "desktop-clean-toggle")

FENCES = os.path.join(WORK, "fences.json")
check("ohne fences.json: keine Sperrflaechen", DC.fence_rectangles(FENCES), [])
open(FENCES, "w").write("{kaputt")
check("kaputte fences.json: keine Sperrflaechen, kein Absturz", DC.fence_rectangles(FENCES), [])
json.dump({"version": 1, "fences": {
    "4": {"x": 50, "y": 50, "w": 360, "h": 210, "visible": True},
    "8": {"x": 425, "y": 300, "w": 360, "h": 27, "visible": True},
    "9": {"x": 800, "y": 300, "w": 360, "h": 210, "visible": False},
    "x": {"x": "a"}, "y": None}}, open(FENCES, "w"))
rects = DC.fence_rectangles(FENCES)
check("nur sichtbare Fences, mit 5 px Rand; Unsinn uebergangen",
      rects, [(45, 45, 415, 265), (420, 295, 790, 332)])
check("P38: eingeklappter Fence nur so hoch wie seine Leiste (unter der Leiste frei)",
      [DC.inside(500, 320, rects[1]), DC.inside(500, 400, rects[1])], [True, False])

icons = [(900, 600, 1060, 705)]
check("sichtbar: freie Flaeche auf dem Schreibtisch -> umschalten",
      DC.decide(1300, 900, True, False, False, rects, icons), True)
check("sichtbar: auf einem Fence -> nie", DC.decide(100, 100, True, False, False, rects, icons), False)
check("sichtbar: auf einem Symbol -> nie", DC.decide(950, 650, True, False, False, rects, icons), False)
check("sichtbar: in einem Fenster -> nie", DC.decide(1300, 900, False, False, False, rects, icons), False)
check("frei: Schreibtisch -> zurueckholen (Fence-Flaechen egal)",
      DC.decide(100, 100, True, False, True, rects, icons), True)
check("frei: gar kein Fenster -> zurueckholen", DC.decide(100, 100, False, True, True, [], []), True)
check("frei: in einem Fenster -> nie", DC.decide(100, 100, False, False, True, [], []), False)

t = DC.ClickTracker()
check("erster Klick: kein Doppelklick", t.press(10.0, 100, 100), False)
check("doppelt gemeldetes Ereignis (< 70 ms) zaehlt nicht", t.press(10.03, 100, 100), False)
check("zweiter Klick in 0,45 s, nah: Doppelklick", t.press(10.3, 105, 98), True)
check("danach beginnt es neu", t.press(10.5, 105, 98), False)
check("zu spaet: kein Doppelklick", t.press(11.0, 105, 98), False)
check("zu weit weg: kein Doppelklick", t.press(11.2, 130, 98), False)

with open("scripts/desktop-doubleclick", encoding="utf-8") as f:
    src = f.read()
check("P71: abonniert nur RawButtonPress (keine Tasten)",
      [src.count("Mask"), "RawButtonPressMask" in src, "KeyPress" in src], [1, True, False])
check("P71: keine Hilfsprozesse je Klick (xinput/xdotool/xprop/xrandr)",
      [w for w in ("xinput test-xi2", "xdotool", "\"xprop\"", "xrandr") if w in src], [])
try:
    from Xlib.ext import ge, xinput
    from types import SimpleNamespace as E
    press = E(type=ge.GenericEventCode, extension=131, evtype=xinput.RawButtonPress)
    check("Ereignisfilter mit den echten python3-xlib-Konstanten (Absturz 13.10. 18:00)",
          [DC.is_raw_button_press(press, 131),
           DC.is_raw_button_press(E(type=ge.GenericEventCode, extension=131, evtype=xinput.RawKeyPress), 131),
           DC.is_raw_button_press(E(type=ge.GenericEventCode, extension=99, evtype=xinput.RawButtonPress), 131),
           DC.is_raw_button_press(E(type=2), 131)],
          [True, False, False, False])
    import struct

    class FakeDisplay:
        ge_event_data = {(131, xinput.RawButtonPress): DC.raw_button_struct()}

    raw = struct.pack("=BBHIHHII", ge.GenericEventCode, 131, 7, 2, xinput.RawButtonPress, 2, 123456, 1) + bytes(14)
    event = ge.GenericEvent(binarydata=raw, display=FakeDisplay())
    check("Rohereignis aus Bytes: Taste, Geraet, Zeit (python3-xlib zerlegt es selbst nicht)",
          [DC.is_raw_button_press(event, 131), event.data.detail, event.data.deviceid, event.data.time],
          [True, 1, 2, 123456])
except ImportError:
    print("  (python3-xlib fehlt - Ereignisfilter uebersprungen)")
out = subprocess.run([sys.executable, "scripts/desktop-doubleclick"], capture_output=True, text=True,
                     env=dict(os.environ, XDG_SESSION_TYPE="wayland"))
check("Wayland: endet sofort mit Hinweis", (out.returncode, "X11 only" in out.stderr), (0, True))

subprocess.run(["rm", "-rf", WORK])
print("")
print("Geprueft: %d, Fehler: %d" % (checks, failures))
sys.exit(1 if failures else 0)
