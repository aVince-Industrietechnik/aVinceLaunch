#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
# Copyright (c) 2026 Angelo Vincenti, aVince Industrietechnik

# Prueft die Sitzungsbindung von scripts/launcher-watch (Pruefung Phase 2,
# B1b / P15) mit Wegwerf-HOME, nachgebautem Sitzungsordner und
# Platzhalter-Prozessen. Der echte Waechter wird nie angefasst: beendet wird
# nur der Halter der Test-Sperrdatei (im Wegwerfordner) - ein Platzhalter, den
# der Test selbst gestartet hat. Teil 2: nur der Halter der Sperre (T2),
# loginctl-Fehler = unbekannt (T17).
# Aufruf im Repository-Wurzelverzeichnis:  python3 tests/watcher-session-test.py

import fcntl
import importlib.machinery
import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.dont_write_bytecode = True

WORK = tempfile.mkdtemp(prefix="avl-watcher-session-test.")
os.environ["HOME"] = WORK
# Teil 2 (T1): der Waechter legt seinen Zustand unter XDG_DATA_HOME ab.
os.environ["XDG_CONFIG_HOME"] = os.path.join(WORK, ".config")
os.environ["XDG_DATA_HOME"] = os.path.join(WORK, ".local", "share")
import umleitung  # noqa: E402 - A9/P70: Abbruch, wenn die Umleitung nicht greift
umleitung.pruefe(WORK, "HOME", "XDG_CONFIG_HOME", "XDG_DATA_HOME")
os.environ["XDG_SESSION_ID"] = "zz-avl-eigene"
sys.path.insert(0, os.path.abspath("scripts"))

loader = importlib.machinery.SourceFileLoader("launcher_watch", "scripts/launcher-watch")
spec = importlib.util.spec_from_loader("launcher_watch", loader)
W = importlib.util.module_from_spec(spec)
loader.exec_module(W)

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


sessions = Path(WORK) / "sessions"
sessions.mkdir()
W.SESSIONS_DIR = sessions
(sessions / "zz-avl-aktiv").write_text("TYPE=x11\nSTATE=active\n")
(sessions / "zz-avl-online").write_text("STATE=online\n")
(sessions / "zz-avl-closing").write_text("STATE=closing\n")

print("Sitzungszustand:")
check("Wegwerf-HOME benutzt", str(W.STATE_DIR).startswith(WORK), True)
check("active", W.session_state("zz-avl-aktiv"), "active")
check("closing", W.session_state("zz-avl-closing"), "closing")
check("unbekannte Sitzung -> gone", W.session_state("zz-avl-gibt-es-nicht"), "gone")
check("active lebt", W.session_alive("zz-avl-aktiv"), True)
check("online lebt", W.session_alive("zz-avl-online"), True)
check("closing lebt nicht", W.session_alive("zz-avl-closing"), False)
check("gone lebt nicht", W.session_alive("zz-avl-gibt-es-nicht"), False)
check("ohne Sitzungs-ID: im Zweifel lebendig", W.session_alive(""), True)

# Platzhalter, der wie der Waechter laeuft (Python + Skript "launcher-watch")
# und - wie der echte - die Sperre holt und Sitzung + PID hineinschreibt.
dummy_script = Path(WORK) / "bin" / "launcher-watch"
dummy_script.parent.mkdir()
dummy_script.write_text(
    "import fcntl, os, sys, time\n"
    "if len(sys.argv) > 1:\n"
    "    f = open(sys.argv[1], 'a'); fcntl.flock(f, fcntl.LOCK_EX)\n"
    "    f.seek(0); f.truncate()\n"
    "    f.write('%s %d\\n' % (os.environ.get('XDG_SESSION_ID', ''), os.getpid())); f.flush()\n"
    "time.sleep(30)\n")
# "Editor": derselbe Python unter dem Namen vim (argv[0] = .../vim), mit der
# Datei launcher-watch als argv[1] - wie "vim ~/.local/bin/launcher-watch".
editor = Path(WORK) / "bin" / "vim"
editor.symlink_to(sys.executable)


def start_dummy(session, lock=None, program=None):
    env = dict(os.environ, XDG_SESSION_ID=session)
    args = [str(program or sys.executable), str(dummy_script)] + ([str(lock)] if lock else [])
    proc = subprocess.Popen(args, env=env)
    time.sleep(0.5)
    return proc


def stop(*procs):
    for proc in procs:
        if proc.poll() is None:
            proc.terminate()
        proc.wait()


print("\nNur der Halter der Sperre (Teil 2, T2):")
W.LOCK_FILE.write_text("")
check("leere Sperrdatei: kein Halter", W.stale_lock_holder(), None)
W.LOCK_FILE.write_text("zz-avl-closing keine-zahl\n")
check("Unsinn in der Sperrdatei: kein Halter", W.stale_lock_holder(), None)
holder = start_dummy("zz-avl-closing", W.LOCK_FILE)
other = start_dummy("zz-avl-closing")                       # Waechter-Name, ohne Sperre
vim = start_dummy("zz-avl-closing", program=editor)         # Editor mit der Datei
check("Halter aus der Sperrdatei", W.lock_holder(), (holder.pid, "zz-avl-closing"))
found = W.stale_lock_holder()
check("Halter einer toten Sitzung erkannt", found[:2] if found else None, (holder.pid, "zz-avl-closing"))
check("beendet nur den Halter", W.stop_stale_watcher(), [holder.pid])
check("Halter weg", holder.wait(timeout=5) is not None, True)
check("anderer Prozess mit Waechter-Namen laeuft weiter", other.poll(), None)
check("Editor mit launcher-watch laeuft weiter", vim.poll(), None)
check("im Protokoll vermerkt", "Old watcher" in W.LOG_FILE.read_text(), True)
stop(other, vim)

print("\nKein Waechter als Halter:")
vim = start_dummy("zz-avl-closing", W.LOCK_FILE, program=editor)
check("Editor haelt die Sperre: kein Kandidat", W.stale_lock_holder(), None)
check("... und wird nicht beendet", (W.stop_stale_watcher(), vim.poll()), ([], None))
stop(vim)
live = start_dummy("zz-avl-aktiv", W.LOCK_FILE)
check("Halter einer lebenden Sitzung: kein Kandidat", W.stale_lock_holder(), None)
check("... und wird nicht beendet", (W.stop_stale_watcher(), live.poll()), ([], None))
stop(live)

print("\nPID neu vergeben (Startzeit anders):")
holder = start_dummy("zz-avl-closing", W.LOCK_FILE)
real_start = W._start_time
times = iter([111, 222])
W._start_time = lambda pid: next(times, 222)
check("Startzeit geaendert: nichts beendet", W.stop_stale_watcher(), [])
W._start_time = real_start
check("Prozess laeuft weiter", holder.poll(), None)
stop(holder)

print("\nloginctl-Fehler (Teil 2, T17):")
real_run = W.subprocess.run
W.subprocess.run = lambda *a, **k: subprocess.CompletedProcess(
    a[0], 1, "", "Failed to connect to bus: No such file or directory\n")
check("Busfehler -> unbekannt", W.session_state("zz-avl-fehlt"), None)
check("... gilt als lebendig", W.session_alive("zz-avl-fehlt"), True)
W.subprocess.run = lambda *a, **k: subprocess.CompletedProcess(
    a[0], 1, "", "Failed to get path for session 'zz-avl-fehlt': No session 'zz-avl-fehlt' known\n")
check("No session -> gone", W.session_state("zz-avl-fehlt"), "gone")
W.subprocess.run = real_run

print("\nSperre:")
original_stop = W.stop_stale_watcher
W.stop_stale_watcher = lambda: []   # hier kein Beenden
first = W.acquire_lock()
check("Sperre geholt", first is not None, True)
check("Sitzung und PID in der Sperrdatei",
      W.LOCK_FILE.read_text(), f"zz-avl-eigene {os.getpid()}\n")
second = W.acquire_lock()
check("zweiter Versuch (lebender Halter) -> None", second, None)
check("Sperrdatei dabei nicht geleert",
      W.LOCK_FILE.read_text(), f"zz-avl-eigene {os.getpid()}\n")
first.close()
W.stop_stale_watcher = original_stop

print("\nSperre einer toten Sitzung uebernehmen:")
holder = start_dummy("zz-avl-closing", W.LOCK_FILE)
taken = W.acquire_lock()
check("Sperre uebernommen", taken is not None, True)
check("alter Halter beendet", holder.wait(timeout=5) is not None, True)
check("neue Angaben in der Sperrdatei",
      W.LOCK_FILE.read_text(), f"zz-avl-eigene {os.getpid()}\n")
taken.close()

holder = start_dummy("zz-avl-aktiv", W.LOCK_FILE)
check("Halter einer lebenden Sitzung: keine Uebernahme", W.acquire_lock(), None)
check("lebender Halter laeuft weiter", holder.poll(), None)
stop(holder)

shutil.rmtree(WORK)
print(f"\nGeprueft: {checks}, Fehler: {failures}")
sys.exit(1 if failures else 0)
