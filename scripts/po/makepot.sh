#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-only
# Copyright (c) 2026 Angelo Vincenti, aVince Industrietechnik
#
# Uebersetzungsvorlage der Helfer neu erzeugen (Schritt 4, V3b / K9).
# Aufruf im Repository-Wurzelverzeichnis:  bash scripts/po/makepot.sh [ZIEL.pot]
# Ohne Ziel: scripts/po/avincelaunch-helfer.pot. Fundstellen ohne Zeilennummern,
# damit die Vorlage nur bei geaenderten Texten neu entsteht.
set -euo pipefail
cd "$(dirname "$0")/../.."
OUT="${1:-scripts/po/avincelaunch-helfer.pot}"
TMP="$(mktemp -d)"
xgettext --from-code=UTF-8 -L Python --keyword=_ --keyword=ngettext:1,2 \
    --add-comments=TRANSLATORS --no-location --sort-output \
    --package-name=aVinceLaunch-Helfer --package-version=0.1.0 \
    -o "$TMP/py.pot" scripts/launcher-watch scripts/launcher-add scripts/launcher-move \
    scripts/desktop-clean-shortcut scripts/avincelaunch_rules.py scripts/avincelaunch-helfer
xgettext --from-code=UTF-8 -L Shell --keyword=t --no-location --sort-output \
    --join-existing -o "$TMP/py.pot" scripts/desktop-clean-toggle
# Kein Erstellungsdatum - sonst waere die Datei bei jedem Lauf anders.
sed -e '/^"POT-Creation-Date:/d' \
    -e 's/^# SOME DESCRIPTIVE TITLE\./# aVinceLaunch-Helfer - translation template/' \
    -e 's/^# Copyright (C) YEAR THE PACKAGE.S COPYRIGHT HOLDER/# Copyright (C) 2026 Angelo Vincenti, aVince Industrietechnik/' \
    -e 's/the PACKAGE package/aVinceLaunch-Helfer (GPL-3.0-only)/' \
    -e 's/PACKAGE VERSION/aVinceLaunch-Helfer 0.1.0/' "$TMP/py.pot" > "$OUT"
rm -r "$TMP"
