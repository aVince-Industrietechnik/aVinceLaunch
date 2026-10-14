# SPDX-License-Identifier: GPL-3.0-only
# Copyright (c) 2026 Angelo Vincenti, aVince Industrietechnik

"""Gemeinsame Sicherung der Offline-Tests (Pruefung Phase 2, A9/P70).

Ein Test, der seine Benutzerordner (XDG_CONFIG_HOME, XDG_DATA_HOME, HOME)
auf einen Wegwerfordner umbiegt, ruft direkt danach

    umleitung.pruefe(WORK, "XDG_CONFIG_HOME", "XDG_DATA_HOME")

auf. Liegt einer der Ordner - laut Umgebung oder laut GLib, das die Werte
beim ersten Abruf festhaelt - nicht im Wegwerfordner, bricht der Test mit
Rueckgabewert 2 ab, bevor er etwas schreibt. So kann er nie die echten
Dateien unter ~/.config/avincelaunch, den Gruppenordnern oder den
Papierkorb treffen, auch nicht mit einer anderen Python- oder GLib-Fassung.
Kein eigener Test (der Name endet nicht auf -test.py).
"""

import os
import sys

_GLIB = {
    "XDG_CONFIG_HOME": "get_user_config_dir",
    "XDG_DATA_HOME": "get_user_data_dir",
    "HOME": "get_home_dir",
}


def _inside(path, work):
    path = os.path.realpath(path)
    return path == work or path.startswith(work + os.sep)


def pruefe(work, *names):
    work = os.path.realpath(work)
    wrong = []
    for name in names:
        value = os.environ.get(name, "")
        if not value or not _inside(value, work):
            wrong.append("%s=%r" % (name, value))
    try:
        from gi.repository import GLib
    except ImportError:
        GLib = None
    if GLib is not None:
        for name in names:
            getter = _GLIB.get(name)
            if getter and not _inside(getattr(GLib, getter)(), work):
                wrong.append("GLib.%s()=%r" % (getter, getattr(GLib, getter)()))
    if wrong:
        print("ABBRUCH: Umleitung in den Wegwerfordner %s greift nicht (%s) - "
              "nichts geschrieben." % (work, ", ".join(wrong)), file=sys.stderr)
        sys.exit(2)
