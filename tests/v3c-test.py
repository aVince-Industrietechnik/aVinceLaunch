#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
# Copyright (c) 2026 Angelo Vincenti, aVince Industrietechnik

# Schritt 4, V3c (P21, E5) ohne Cinnamon, in einem Wegwerf-HOME (mit
# Leerzeichen im Pfad), ohne Anzeige und ohne echtes gsettings/dconf:
#  A. Paket: Inhalt, Rechte 755/644, ohne Besitzer, .mo dabei, keine festen
#     Benutzerpfade.
#  B. Installation: Dateien, Rechte, Autostart mit dem echten (gequoteten)
#     Pfad, alte Autostart-Eintraege gesichert und ersetzt, Liste und
#     Sicherung, Uebersetzung wirkt aus dem installierten Ort, --check aendert
#     nichts.
#  C. Update ohne Doppelklick entfernt dessen Autostart (gesichert).
#  D. Entfernen: nur Installiertes weg, Daten bleiben, ein "freier"
#     Schreibtisch wird vorher eingeblendet; --restore holt die ersetzten
#     Dateien zurueck.
# Aufruf im Repository-Wurzelverzeichnis:  python3 tests/v3c-test.py

import json
import shlex
import os
import stat
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True

WORK = tempfile.mkdtemp(prefix="avl-v3c-test.")
HOME = os.path.join(WORK, "home mit leer")
os.makedirs(HOME)
os.environ["HOME"] = HOME
for name in ("XDG_CONFIG_HOME", "XDG_DATA_HOME", "XDG_STATE_HOME"):
    os.environ.pop(name, None)
import umleitung  # noqa: E402 - A9/P70
umleitung.pruefe(WORK, "HOME")

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


H = Path(HOME)
BIN = H / ".local/bin"
OWN = H / ".local/share/avincelaunch-helfer"
AUTOSTART = H / ".config/autostart"

# Gespieltes gsettings (fuer desktop-clean-toggle beim Entfernen).
FAKE = Path(WORK) / "fakebin"
FAKE.mkdir()
GS_LOG = Path(WORK) / "gsettings.log"
(FAKE / "gsettings").write_text("#!/bin/sh\necho \"$*\" >> %s\n"
                                "case \"$1\" in list-keys) echo desktop-layout ;; get) echo \"'false::false'\" ;; esac\n"
                                % GS_LOG)
(FAKE / "gsettings").chmod(0o755)
ENV = {"PATH": "%s:/usr/bin:/bin" % FAKE, "HOME": HOME, "LANGUAGE": "C", "LANG": "C.UTF-8",
       "GSETTINGS_BACKEND": "memory", "DBUS_SESSION_BUS_ADDRESS": "unix:path=/nonexistent/avl-v3c",
       "PYTHONDONTWRITEBYTECODE": "1"}


def run(argv, cwd=None, env=None):
    out = subprocess.run(argv, cwd=cwd, env=env or ENV, capture_output=True, text=True)
    return out.returncode, out.stdout + out.stderr


# --- A. Paket -------------------------------------------------------------------
print("A. Paket:")
rc, out = run([sys.executable, "scripts/build-helfer-paket.py", os.path.join(WORK, "dist")],
              env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
archive = out.strip().splitlines()[-1]
check("gebaut", (rc, os.path.basename(archive)), (0, "aVinceLaunch-Helfer-0.1.0.tar.gz"))
with tarfile.open(archive) as tar:
    members = {m.name.split("/", 1)[1] if "/" in m.name else "": m for m in tar.getmembers()}
    texts = {n: tar.extractfile(m).read() for n, m in members.items() if m.isfile()}
expected = {"install.sh", "uninstall.sh", "avincelaunch-helfer", "README.md", "README.de.md", "LICENSE",
            "nemo/avincelaunch-move-to-fence.nemo_action", "autostart/avincelaunch-watcher.desktop.in",
            "autostart/avincelaunch-doubleclick.desktop.in", "locale/de/LC_MESSAGES/avincelaunch-helfer.mo",
            "bin/launcher-watch", "bin/launcher-add", "bin/launcher-move", "bin/desktop-clean-toggle",
            "bin/desktop-clean-shortcut", "bin/desktop-doubleclick", "bin/avincelaunch_rules.py",
            "bin/rules.example.json"}
check("Inhalt vollstaendig, nichts dazu", sorted(texts), sorted(expected))
executable = {"install.sh", "uninstall.sh", "avincelaunch-helfer"} | {n for n in expected if n.startswith("bin/")
                                                                     and not n.endswith((".py", ".json"))}
check("Rechte 755/644, Ordner 755, ohne Besitzer",
      sorted(n for n, m in members.items()
             if m.mode != (0o755 if (m.isdir() or n in executable) else 0o644) or m.uid or m.gid or m.uname),
      [])
check("keine festen Benutzerpfade im Paket", [n for n, b in texts.items() if b"/home/" in b], [])

# --- B. Installation -----------------------------------------------------------
print("B. Installation:")
subprocess.run(["tar", "xzf", archive, "-C", WORK], check=True)
PKG = os.path.join(WORK, "aVinceLaunch-Helfer-0.1.0")
# Stand vor der Installation: alte Helfer wie bei Angelo (Autostart mit festem Pfad).
AUTOSTART.mkdir(parents=True)
OLD_WATCHER = AUTOSTART / "thelauncher-watcher.desktop"
OLD_WATCHER.write_text("[Desktop Entry]\nExec=/somewhere/.local/bin/launcher-watch\n")
FOREIGN = AUTOSTART / "desktop-doubleclick.desktop"
FOREIGN.write_text("[Desktop Entry]\nExec=/usr/bin/fremdes-programm\n")
BIN.mkdir(parents=True)
(BIN / "launcher-add").write_text("alte Fassung\n")
(H / ".config/avincelaunch").mkdir(parents=True)
(H / ".config/avincelaunch/rules.json").write_text('{"version": 1, "rules": []}\n')

rc, out = run(["./install.sh", "--check", "--yes", "--no-shortcut", "--doubleclick"], cwd=PKG)
check("--check: Rueckgabe 0, nichts geaendert",
      (rc, (BIN / "launcher-add").read_text(), OLD_WATCHER.exists(), OWN.exists()),
      (0, "alte Fassung\n", True, False))
rc, out = run(["./install.sh", "--yes", "--no-shortcut", "--doubleclick"], cwd=PKG)
check("installiert (Rueckgabe 0)", (rc, "Installed." in out), (0, True))
names = ["launcher-watch", "launcher-add", "launcher-move", "desktop-clean-toggle", "desktop-clean-shortcut",
         "desktop-doubleclick"]
check("Helfer in ~/.local/bin, ausfuehrbar",
      [stat.S_IMODE((BIN / n).stat().st_mode) for n in names], [0o755] * len(names))
check("Modul und Beispiel 644", [stat.S_IMODE((BIN / n).stat().st_mode) for n in
                                 ("avincelaunch_rules.py", "rules.example.json")], [0o644, 0o644])
check("Nemo-Aktion und Uebersetzung", [(H / ".local/share/nemo/actions/avincelaunch-move-to-fence.nemo_action").exists(),
                                       (H / ".local/share/locale/de/LC_MESSAGES/avincelaunch-helfer.mo").exists()],
      [True, True])
# N23 (Tower 14.10.): ~/.local/bin steht fuer einen neuen Nutzer erst nach der
# naechsten Anmeldung im PATH - die Nemo-Aktion nennt deshalb den vollen Pfad.
action = (H / ".local/share/nemo/actions/avincelaunch-move-to-fence.nemo_action").read_text().splitlines()
check("Nemo-Aktion: Exec mit vollem Pfad, gequotet",
      'Exec="%s" %%F' % (BIN / "launcher-move") in action, True)
check("Nemo-Aktion: Exec zerlegt (Leerzeichen im Pfad)",
      shlex.split(next(z for z in action if z.startswith("Exec="))[5:]), [str(BIN / "launcher-move"), "%F"])
check("Nemo-Aktion: Dependencies mit vollem Pfad",
      "Dependencies=%s;zenity;" % (BIN / "launcher-move") in action, True)
check("Nemo-Aktion: Rest wie im Paket (Name, Bedingung)",
      ["Conditions=desktop;" in action, "Name[de]=In einen Fence verschieben …" in action], [True, True])
watcher = (AUTOSTART / "avincelaunch-watcher.desktop").read_text()
check("Autostart mit dem echten Pfad, gequotet",
      'Exec="%s"' % (BIN / "launcher-watch") in watcher.splitlines(), True)
probe = ("import gi; gi.require_version('GLib','2.0'); from gi.repository import GLib; import sys; "
         "k=GLib.KeyFile(); k.load_from_file(sys.argv[1], GLib.KeyFileFlags.NONE); "
         "print(GLib.shell_parse_argv(k.get_string('Desktop Entry','Exec'))[1][0])")
rc, out = run([sys.executable, "-c", probe, str(AUTOSTART / "avincelaunch-watcher.desktop")])
check("Exec zerlegt (wie beim Start) = Pfad mit Leerzeichen", out.strip(), str(BIN / "launcher-watch"))
check("Doppelklick-Autostart (gewaehlt)", (AUTOSTART / "avincelaunch-doubleclick.desktop").exists(), True)
check("alter Wachter-Autostart ersetzt, fremder Eintrag gleichen Namens bleibt",
      (OLD_WATCHER.exists(), FOREIGN.read_text()), (False, "[Desktop Entry]\nExec=/usr/bin/fremdes-programm\n"))
manifest = json.loads((OWN / "installiert.json").read_text())
check("Liste der installierten Dateien", len(manifest["files"]), 12)
check("Sicherung: alte Fassung und alter Autostart",
      sorted(manifest["backed_up"]), sorted([str(BIN / "launcher-add"), str(OLD_WATCHER)]))
backup_dir = Path(manifest["backup"])
check("... Inhalt gesichert", (backup_dir / "files" / str(BIN / "launcher-add").lstrip("/")).read_text(),
      "alte Fassung\n")
check("Deinstallationsskript liegt bereit", os.access(OWN / "uninstall.sh", os.X_OK), True)
rc, out = run([str(BIN / "launcher-add")], env=dict(ENV, LANGUAGE="de", LANG="de_DE.UTF-8", LC_ALL="de_DE.UTF-8"))
check("Uebersetzung wirkt aus dem installierten Ort", out.splitlines()[0],
      'Verwendung: launcher-add "Programmname" [GRUPPE]')
check("eigene Regeln unberuehrt", (H / ".config/avincelaunch/rules.json").read_text(),
      '{"version": 1, "rules": []}\n')

# --- C. Update ohne Doppelklick --------------------------------------------------
print("C. Update:")
rc, out = run(["./install.sh", "--yes", "--no-shortcut", "--no-doubleclick"], cwd=PKG)
check("Update ohne Doppelklick: dessen Autostart weg",
      (rc, (AUTOSTART / "avincelaunch-doubleclick.desktop").exists()), (0, False))
manifest2 = json.loads((OWN / "installiert.json").read_text())
check("... vorher gesichert", str(AUTOSTART / "avincelaunch-doubleclick.desktop") in manifest2["backed_up"], True)
check("... Liste ohne ihn", len(manifest2["files"]), 11)

# --- D. Entfernen -------------------------------------------------------------------
print("D. Entfernen:")
STATE = H / ".local/state/avincelaunch"
STATE.mkdir(parents=True)
(STATE / "schreibtisch-frei").write_text("")
(STATE / "nemo-layout").write_text("'true::false'\n")
rc, out = run([str(OWN / "uninstall.sh"), "--check"])
check("--check aendert nichts", (rc, (BIN / "launcher-watch").exists()), (0, True))
rc, out = run([str(OWN / "uninstall.sh")])
check("entfernt (Rueckgabe 0)", (rc, "Removed." in out), (0, True))
check("Schreibtisch vorher eingeblendet (Markierung weg, Anordnung zurueck)",
      ((STATE / "schreibtisch-frei").exists(), "set org.nemo.desktop desktop-layout 'true::false'" in GS_LOG.read_text()),
      (False, True))
check("alle installierten Dateien weg", [p for p in manifest2["files"] if Path(p).exists()], [])
check("Liste und Werkzeug weg, Sicherungen bleiben",
      [(OWN / "installiert.json").exists(), (OWN / "uninstall.sh").exists(), backup_dir.exists()],
      [False, False, True])
check("Daten bleiben (Regeln, fremder Autostart)",
      [(H / ".config/avincelaunch/rules.json").exists(), FOREIGN.exists()], [True, True])
rc, out = run([sys.executable, os.path.join(PKG, "avincelaunch-helfer"), "uninstall"])
check("zweites Entfernen: nichts installiert", rc, 1)

BIN.mkdir(parents=True, exist_ok=True)
(BIN / "launcher-watch").write_text("aeltere Fassung\n")
run(["./install.sh", "--yes", "--no-shortcut", "--no-doubleclick"], cwd=PKG)
manifest3 = json.loads((OWN / "installiert.json").read_text())
check("3. Installation sichert die aeltere Fassung", manifest3["backed_up"], [str(BIN / "launcher-watch")])
rc, out = run([str(OWN / "uninstall.sh"), "--restore"])
check("--restore: Paketdateien weg, aeltere Fassung zurueck",
      (rc, (BIN / "launcher-add").exists(), (BIN / "launcher-watch").read_text()),
      (0, False, "aeltere Fassung\n"))

subprocess.run(["rm", "-rf", WORK])
print("")
print("Geprueft: %d, Fehler: %d" % (checks, failures))
sys.exit(1 if failures else 0)
