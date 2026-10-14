# SPDX-License-Identifier: GPL-3.0-only
# Copyright (c) 2026 Angelo Vincenti, aVince Industrietechnik

"""Gemeinsame Grundlage von launcher-watch und launcher-add (AP11).

Hier steht an EINER Stelle, wo die Gruppenordner liegen und welche Gruppen
es gibt. Die Skripte fuehren keine eigene Gruppenliste mehr.

Liegt neben den Skripten in ~/.local/bin und wird von dort importiert.
GELESEN werden config.json, die <ID>.json der Fences und enabled-desklets.
Geschrieben wird nur ueber install_desktop_file (Verknuepfung in einen
Gruppenordner) und write_default_rules (rules.json) - beide legen nur NEU an,
nie ueber eine vorhandene Datei, und nie halb.
"""

from pathlib import Path
import ast
import errno
import gettext
import hashlib
import os
import json
import shutil
import subprocess
import sys
import tempfile

HOME = Path.home()

UUID = "avincelaunch-desklet@avince"

# Pruefung Phase 3 Teil 2 (T1): dieselben Benutzerordner wie Desklet (GLib),
# Dialog (orderFolderEditor._xdg_config_home/_xdg_data_home) und Cinnamon
# (Instanzdateien unter get_user_config_dir()): $XDG_CONFIG_HOME bzw.
# $XDG_DATA_HOME, sonst ~/.config und ~/.local/share. Bisher fest ~/.config -
# bei gesetztem XDG_CONFIG_HOME lasen die Skripte eine andere config.json und
# fanden die <ID>.json der Fences nicht (Rueckfall auf alle Ordner, auch
# gesperrte).
CONFIG_HOME = Path(os.environ.get("XDG_CONFIG_HOME") or HOME / ".config")
DATA_HOME = Path(os.environ.get("XDG_DATA_HOME") or HOME / ".local/share")

CONFIG_FILE = CONFIG_HOME / "avincelaunch/config.json"
LEGACY_CONFIG_FILE = CONFIG_HOME / "thelauncher/config.json"
DEFAULT_BASE = DATA_HOME / "avincelaunch"

FENCE_SETTINGS_DIR = CONFIG_HOME / "cinnamon/spices" / UUID

# --- Uebersetzung (Schritt 4, V3b / K9) --------------------------------------
# Sichtbare Texte der Helfer sind englisch im Code; die deutsche Fassung
# kommt ueber gettext (Domaene avincelaunch-helfer). Das Installationsskript
# legt die .mo nach $XDG_DATA_HOME/locale; im Repository liegt sie nach dem
# Bauen unter scripts/locale. Protokollzeilen bleiben englisch (wie T22).
TEXT_DOMAIN = "avincelaunch-helfer"


def _load_translation():
    for folder in (DATA_HOME / "locale", HOME / ".local/share/locale",
                   Path(__file__).resolve().parent / "locale"):
        if gettext.find(TEXT_DOMAIN, str(folder)):
            return gettext.translation(TEXT_DOMAIN, str(folder))
    return gettext.NullTranslations()


_translation = _load_translation()
_ = _translation.gettext
ngettext = _translation.ngettext

# --- Programmordner (Pruefung Phase 2, B14 / P51) ---------------------------
# Frueher vier fest eingetragene Ordner (eigene, System, zwei Flatpak) - in
# launcher-watch und launcher-add je eine Kopie. Jetzt wie das Startmenue aus
# der Systemeinstellung: $XDG_DATA_HOME und $XDG_DATA_DIRS, dazu Snap und zur
# Sicherheit die bisherigen vier.
LEGACY_APP_DIRS = (
    HOME / ".local/share/applications",
    Path("/usr/share/applications"),
    HOME / ".local/share/flatpak/exports/share/applications",
    Path("/var/lib/flatpak/exports/share/applications"),
)
SNAP_APP_DIR = Path("/var/lib/snapd/desktop/applications")


def app_dirs():
    """[Path] der Programmordner, ohne doppelte, in Suchreihenfolge."""
    data_home = os.environ.get("XDG_DATA_HOME") or str(HOME / ".local/share")
    data_dirs = os.environ.get("XDG_DATA_DIRS") or "/usr/local/share:/usr/share"
    candidates = [Path(data_home) / "applications"]
    candidates += [Path(d) / "applications" for d in data_dirs.split(":") if d.strip()]
    candidates += [SNAP_APP_DIR]
    candidates += list(LEGACY_APP_DIRS)
    result = []
    seen = set()
    for path in candidates:
        key = os.path.normpath(str(path))
        if key not in seen:
            seen.add(key)
            result.append(Path(key))
    return result


# --- Programmnamen (V5f / N30) ------------------------------------------------
# Startmenue und Fences zeigen den uebersetzten Namen (Name[de]); launcher-add
# verglich nur die Zeile "Name=" (englisch) - "Rechner" wurde nicht gefunden.
# Gelesen wird nur der Abschnitt [Desktop Entry]; die Sprachen kommen wie bei
# gettext aus der ersten gesetzten Variable LANGUAGE, LC_ALL, LC_MESSAGES,
# LANG (bis "C"). Mint und Ubuntu liefern viele Uebersetzungen nicht als
# Name[de], sondern ueber X-Ubuntu-Gettext-Domain aus /usr/share/locale (so
# liest sie auch Gio im Desklet) - dann uebersetzt gettext die Zeile "Name=".
GETTEXT_DOMAIN_KEYS = ("X-Ubuntu-Gettext-Domain", "X-GNOME-Gettext-Domain")
SYSTEM_LOCALE_DIR = None  # None = gettext-Vorgabe (/usr/share/locale); Tests setzen einen Wegwerfordner


def _locale_keys():
    """Schluessel fuer Name[...] in Reihenfolge, z. B. ["de_DE", "de"]."""
    keys = []
    for var in ("LANGUAGE", "LC_ALL", "LC_MESSAGES", "LANG"):
        value = os.environ.get(var)
        if not value:
            continue
        for lang in value.split(":"):
            lang = lang.split(".")[0].split("@")[0]
            if lang in ("C", "POSIX"):
                break
            for key in (lang, lang.split("_")[0]):
                if key and key not in keys:
                    keys.append(key)
        break
    return keys


def desktop_names(path):
    """(Anzeigename, [alle Namen zum Vergleichen]) einer .desktop-Datei.
    Anzeigename = uebersetzter Name, sonst "Name="; ("", []) wenn unlesbar."""
    try:
        text = Path(path).read_text(errors="ignore")
    except Exception:
        return "", []
    plain = ""
    localized = {}
    domain = ""
    section = None
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("["):
            section = line
            continue
        if section != "[Desktop Entry]" or "=" not in line:
            continue
        key, value = (part.strip() for part in line.split("=", 1))
        if key == "Name" and not plain:
            plain = value
        elif key.startswith("Name[") and key.endswith("]") and value:
            localized.setdefault(key[5:-1], value)
        elif key in GETTEXT_DOMAIN_KEYS and value and not domain:
            domain = value
    shown = next((localized[k] for k in _locale_keys() if k in localized), "")
    if not shown and domain and plain:
        try:
            shown = gettext.translation(domain, SYSTEM_LOCALE_DIR, fallback=True).gettext(plain)
        except Exception:
            shown = ""
    shown = shown or plain
    return shown, [n for n in dict.fromkeys([shown, plain]) if n]


# Meldungen ueber kaputte Dateien (Teil 2, N7): standardmaessig nach stderr;
# launcher-watch leitet sie in sein Protokoll um (REPORT = log).
REPORT = None
_REPORTED = set()


def _report(text):
    if REPORT is not None:
        REPORT(text)
    else:
        print("aVinceLaunch: " + text, file=sys.stderr)


def _read_json(path):
    """Inhalt einer JSON-Datei oder None. Fehlt sie, still None. Ist sie
    unlesbar oder kaputt, ebenfalls None - aber mit einer Meldung, einmal je
    Inhalt (Pruefung Phase 3 Teil 2, N7: bisher still wie fehlend). Hier wird
    nichts gesichert oder geaendert; die Kopie .broken-<Zeit> legen Desklet
    und Dialog an, wenn sie die Datei lesen."""
    try:
        raw = Path(path).read_bytes()
    except FileNotFoundError:
        return None
    except OSError as error:
        key = (str(path), str(error))
        if key not in _REPORTED:
            _REPORTED.add(key)
            _report(f"{path} is not readable ({error}) - skipped.")
        return None
    try:
        return json.loads(raw.decode("utf-8"))
    except Exception as error:
        key = (str(path), hashlib.sha256(raw).hexdigest())
        if key not in _REPORTED:
            _REPORTED.add(key)
            _report(f"{path} is damaged ({error}) - skipped, nothing overwritten.")
        return None


# --- Neue Datei sicher anlegen (Pruefung Phase 3 Teil 2, T3 / N7) ---------
# Nie ueberschreiben (auch keinen toten Verweis gleichen Namens), nie eine
# halbe Datei: Inhalt erst in eine versteckte Zwischendatei im Zielordner,
# dann exklusiv unter dem Zielnamen anlegen (harter Verweis). Dateisysteme
# ohne harte Verweise (vfat, manche Netzfreigaben): exklusiv neu anlegen und
# schreiben; scheitert das Schreiben, wird die neue Datei wieder entfernt.
_NO_HARDLINK = {errno.EPERM, errno.EOPNOTSUPP, errno.ENOTSUP, errno.EXDEV,
                errno.EMLINK, errno.ENOSYS, errno.EACCES}


def _write_exclusive(target, data, mode):
    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, mode)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
    except BaseException:
        try:
            os.unlink(target)
        except OSError:
            pass
        raise


def create_new_file(target, data, mode=0o644, stat_from=None):
    """Legt target mit data an. True = angelegt, False = es gab schon etwas
    mit diesem Namen (nichts geaendert). Andere Fehler als OSError."""
    target = Path(target)
    if os.path.lexists(target):
        return False
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix="." + target.name + ".", suffix=".tmp",
                               dir=str(target.parent))
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        if stat_from is not None:
            try:
                shutil.copystat(stat_from, tmp)
            except OSError:
                pass
        os.chmod(tmp, mode)
        try:
            os.link(tmp, target)
        except FileExistsError:
            return False
        except OSError as error:
            if error.errno not in _NO_HARDLINK:
                raise
            try:
                _write_exclusive(target, data, mode)
            except FileExistsError:
                return False
        return True
    finally:
        try:
            os.unlink(tmp)
        except OSError:
            pass


def install_desktop_file(source, target_dir):
    """Kopiert eine Verknuepfung (Verweise aufgeloest) als NEUE Datei nach
    target_dir/<Name>, ausfuehrbar. Liefert (Ziel, None), (None, "exists")
    oder (None, Fehlertext)."""
    source = Path(source)
    target = Path(target_dir) / source.name
    try:
        real = source.resolve()
        if not create_new_file(target, real.read_bytes(), 0o755, stat_from=real):
            return None, "exists"
        return target, None
    except OSError as error:
        return None, str(error)


def base_directory():
    # Dieselbe Regel wie Desklet/lib/config.js (Pruefung Phase 2, P11): zuerst
    # die eigene Datei, sonst die aus TheLauncher-Zeiten (fehlt oder kaputt =
    # naechste); die erste lesbare entscheidet - "~" erweitert, nur absolute
    # Pfade, Verweise nicht aufgeloest -, sonst der Standardpfad.
    for path in (CONFIG_FILE, LEGACY_CONFIG_FILE):
        data = _read_json(path)
        if not isinstance(data, dict):
            continue
        value = data.get("baseDirectory")
        text = value.strip() if isinstance(value, str) else ""
        if text == "~" or text.startswith("~/"):
            text = str(HOME) + text[1:]
        if text.startswith("/"):
            return Path(os.path.normpath(text))
        return DEFAULT_BASE
    return DEFAULT_BASE


def default_title(subdirectory):
    """Titel eines Fence ohne eigenen Namen - wie _getHoverWindowTitle in
    Desklet/desklet.js (Pruefung Phase 2, B7: keine eingebaute Namenstabelle
    mehr): Ordnername, "_" als Leerzeichen."""
    folder = str(subdirectory or "").strip()
    return folder.replace("_", " ") if folder else "aVinceLaunch"


def _enabled_fences():
    """Liefert [(ID, x, y)] der laufenden aVinceLaunch-Fences."""
    try:
        result = subprocess.run(
            ["gsettings", "get", "org.cinnamon", "enabled-desklets"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        entries = ast.literal_eval(result.stdout.strip().removeprefix("@as "))
    except Exception:
        return []

    fences = []
    for entry in entries:
        parts = str(entry).split(":")
        if len(parts) < 2 or parts[0] != UUID:
            continue
        try:
            x = int(parts[2]) if len(parts) > 2 else 0
            y = int(parts[3]) if len(parts) > 3 else 0
        except ValueError:
            x = y = 0
        fences.append((parts[1], x, y))
    return fences


def _value(settings, key):
    item = settings.get(key)
    if isinstance(item, dict):
        return item.get("value")
    return None


def groups_from_fences(include_locked=True):
    """Gruppen aus den Fences auf dem Schreibtisch, Reihe fuer Reihe.

    Portale zaehlen nicht: dort liegen fremde Dateien, keine Verknuepfungen.
    include_locked=False laesst Fences mit gesperrtem Inhalt weg (AP18-4).
    """
    groups = []
    seen = set()

    for fence_id, x, y in sorted(_enabled_fences(), key=lambda f: (f[2], f[1])):
        settings = _read_json(FENCE_SETTINGS_DIR / f"{fence_id}.json")
        if not isinstance(settings, dict):
            continue
        if _value(settings, "source-mode") == "portal":
            continue
        if not include_locked and _value(settings, "lock-content"):
            continue

        subdirectory = str(_value(settings, "subdirectory") or "").strip("/")
        if not subdirectory or subdirectory in seen:
            continue
        seen.add(subdirectory)

        title = str(_value(settings, "fence-title") or "").strip()
        groups.append((subdirectory, title or default_title(subdirectory)))

    return groups


def groups_from_folders():
    """Rueckfall: jeder sichtbare Ordner im Basisordner ist eine Gruppe."""
    base = base_directory()
    try:
        folders = sorted(
            p.name for p in base.iterdir()
            if p.is_dir() and not p.name.startswith(".")
        )
    except Exception:
        return []
    return [(name, default_title(name)) for name in folders]


def _unique_labels(groups):
    # Der Dialog liefert nur den Anzeigenamen zurueck. Tragen zwei Fences
    # denselben Namen, wird der Ordner angehaengt, sonst waere die Wahl
    # nicht eindeutig.
    count = {}
    for key, label in groups:
        count[label] = count.get(label, 0) + 1
    return [
        (key, f"{label} ({key})" if count[label] > 1 else label)
        for key, label in groups
    ]


def get_groups(include_locked=True):
    """[(Ordner, Anzeigename)] in Schreibtisch-Reihenfolge."""
    fences = groups_from_fences(include_locked)
    if not fences and not include_locked and groups_from_fences():
        # Alle Fences gesperrt: nicht auf die Ordner ausweichen.
        return []
    return _unique_labels(fences or groups_from_folders())


def find_group(name, groups=None):
    """Ordnername zu einer Eingabe wie 'grafik' (Gross/klein egal)."""
    wanted = str(name or "").strip("/").casefold()
    for key, label in groups if groups is not None else get_groups():
        if key.casefold() == wanted:
            return key
    return None


def already_in_launcher(filename):
    """Liegt eine gleichnamige Verknuepfung schon in irgendeiner Gruppe?

    Durchsucht alle Ordner im Basisordner, auch stillgelegte ohne Fence (z. B.
    einen alten Sammelordner). Was dort liegt, gilt als einsortiert.
    """
    base = base_directory()
    try:
        folders = [p for p in base.iterdir() if p.is_dir()]
    except Exception:
        folders = []
    # Gruppen in Unterordnern (Ordnername mit "/") liegen tiefer.
    folders += [base / key for key, label in get_groups() if "/" in key]
    # Teil 2 (T3): lexists - auch ein toter Verweis gleichen Namens gilt als
    # belegt (exists() folgte ihm und nannte den Namen frei).
    return any(os.path.lexists(folder / filename) for folder in folders)


# ---------------------------------------------------------------------------
# Regelwerk (AP11-2)
#
# Der Waechter schlaegt fuer ein neues Programm einen Fence vor; der
# Anwender bestaetigt. Die Regeln stehen in rules.json neben config.json
# ($XDG_CONFIG_HOME/avincelaunch, meist ~/.config/avincelaunch).
# Fehlt die Datei, gibt es keine Regeln (B7). Angelegt wird sie nur
# auf ausdruecklichen Wunsch (launcher-watch --write-rules).
# ---------------------------------------------------------------------------

RULES_FILE = CONFIG_HOME / "avincelaunch/rules.json"

# off     = keine Dialoge, neue Programme werden still als gesehen vermerkt
# ask     = fragen ohne Vorschlag (wie vor AP11)
# suggest = fragen, passender Fence vorausgewaehlt (Standard)
MODES = ("off", "ask", "suggest")
DEFAULT_MODE = "suggest"

# Kriterien je Regel (alle angegebenen muessen zutreffen):
#   categories  ein Eintrag aus Categories= (genau, Gross/klein egal)
#   name        Teil des Programmnamens
#   exec        Teil des Programmaufrufs (Exec=)
#   file        Teil des Dateinamens der .desktop-Datei
# Jeder Wert darf eine Liste sein; dann genuegt einer davon.
# Die erste zutreffende Regel gewinnt. Darum Ausnahmen und besondere
# Kategorien vor den allgemeinen.
# Pruefung Phase 2, B7 (P42): keine eingebauten Regeln mehr - sie zeigten
# auf persoenliche Ordnernamen. Ohne eigene rules.json gibt es keinen
# Vorschlag (der Dialog fragt ohne Vorauswahl). Ein Beispiel zum Anpassen
# liegt in rules.example.json neben diesem Modul (launcher-watch
# --write-rules legt es als rules.json an).
DEFAULT_RULES = []
EXAMPLE_FILE = Path(__file__).resolve().parent / "rules.example.json"


CRITERIA = ("categories", "name", "exec", "file")

def _reason(key, hit):
    """Grund fuer den Vorschlag, wie ihn der Dialog zeigt (uebersetzt)."""
    texts = {
        "categories": _("category %s"),
        "name": _("name contains “%s”"),
        "exec": _("command contains “%s”"),
        "file": _("file name contains “%s”"),
    }
    return texts[key] % hit


def _as_list(value):
    if isinstance(value, (list, tuple)):
        return [str(v) for v in value if str(v).strip()]
    if value is None or not str(value).strip():
        return []
    return [str(value)]


def rule_targets(rule):
    """Ziele einer Regel: "then" ist ein Ordnername oder (V3b, K2-3) eine
    Liste davon - der erste vorhandene Fence gilt. So passt eine Regel zur
    Startaufstellung in jeder Sprache ("Office", "Buero" ...)."""
    then = rule.get("then") if isinstance(rule, dict) else None
    if isinstance(then, str):
        return [then] if then.strip() else []
    if isinstance(then, list) and all(isinstance(t, str) for t in then):
        return [t for t in then if t.strip()]
    return []


def _find_target(rule, groups):
    for target in rule_targets(rule):
        found = find_group(target, groups)
        if found is not None:
            return found
    return None


def _valid_rule(rule):
    if not isinstance(rule, dict) or not rule_targets(rule):
        return False
    cond = rule.get("if")
    if not isinstance(cond, dict) or not cond:
        return False
    return all(key in CRITERIA and _as_list(val) for key, val in cond.items())


def load_rules():
    """(Betriebsart, Regeln, Hinweise). Wirft nie eine Ausnahme.

    Hinweise sind Texte fuer das Protokoll, z. B. bei kaputter Datei.
    """
    notes = []

    if not RULES_FILE.exists():
        return DEFAULT_MODE, list(DEFAULT_RULES), notes

    data = _read_json(RULES_FILE)
    if not isinstance(data, dict):
        notes.append(f"{RULES_FILE} is not readable - no rules, no suggestion")
        return DEFAULT_MODE, list(DEFAULT_RULES), notes

    mode = str(data.get("mode", DEFAULT_MODE)).strip().lower()
    if mode not in MODES:
        notes.append(f"Unknown mode \"{mode}\" - using \"{DEFAULT_MODE}\"")
        mode = DEFAULT_MODE

    raw = data.get("rules")
    if raw is None:
        return mode, list(DEFAULT_RULES), notes
    if not isinstance(raw, list):
        notes.append("\"rules\" is not a list - no rules, no suggestion")
        return mode, list(DEFAULT_RULES), notes

    rules = []
    for number, rule in enumerate(raw, 1):
        if _valid_rule(rule):
            rules.append(rule)
        else:
            notes.append(f"Rule {number} is incomplete and is skipped")
    return mode, rules, notes


def _match(rule, info):
    """Grund-Text, wenn die Regel zutrifft, sonst None."""
    categories = {
        c.strip().casefold()
        for c in str(info.get("Categories", "")).split(";") if c.strip()
    }
    fields = {
        "name": str(info.get("Name", "")).casefold(),
        "exec": str(info.get("Exec", "")).casefold(),
        "file": str(info.get("_file", "")).casefold(),
    }

    reasons = []
    for key, value in rule["if"].items():
        wanted = _as_list(value)
        if key == "categories":
            hit = next((w for w in wanted if w.casefold() in categories), None)
        else:
            hit = next((w for w in wanted if w.casefold() in fields[key]), None)
        if hit is None:
            return None
        reasons.append(_reason(key, hit))
    return ", ".join(reasons)


def suggest(info, filename, rules=None, groups=None):
    """(Ordner, Grund) fuer ein Programm oder (None, None).

    info: Felder der .desktop-Datei (Name, Exec, Categories).
    Regeln, deren Fence es nicht gibt, werden uebersprungen.
    """
    if rules is None:
        rules = load_rules()[1]
    if groups is None:
        groups = get_groups()

    info = dict(info or {})
    info["_file"] = filename or ""

    for rule in rules:
        target = _find_target(rule, groups)
        if target is None:
            continue
        reason = _match(rule, info)
        if reason:
            return target, reason
    return None, None


def missing_targets(rules=None, groups=None):
    """Ziele von Regeln, zu denen es keinen Fence gibt (fuer das Protokoll)."""
    if rules is None:
        rules = load_rules()[1]
    if groups is None:
        groups = get_groups()
    return sorted({
        " / ".join(rule_targets(rule)) for rule in rules
        if _find_target(rule, groups) is None
    })


def example_rules():
    """Regeln aus rules.example.json ([] wenn sie fehlt oder unlesbar ist)."""
    data = _read_json(EXAMPLE_FILE)
    rules = data.get("rules") if isinstance(data, dict) else None
    return [rule for rule in rules if _valid_rule(rule)] if isinstance(rules, list) else []


def write_default_rules():
    """Legt rules.json mit den Beispielregeln an (Ordnernamen anpassen!) -
    nie ueber eine vorhandene, nie halb (Teil 2, N7: exklusiv und atomar)."""
    payload = {"version": 1, "mode": DEFAULT_MODE, "rules": example_rules()}
    text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    return create_new_file(RULES_FILE, text.encode("utf-8"), 0o644)
