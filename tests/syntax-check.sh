#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-only
# Copyright (c) 2026 Angelo Vincenti, aVince Industrietechnik

# ---------------------------------------------------------------------------
# aVinceLaunch - Syntaxpruefung vor dem Einspielen
#
# Prueft, was sich ohne Cinnamon pruefen laesst:
#   Python  (Desklet, scripts, tests; auch Skripte ohne Endung) mit ast.parse
#   Shell   (scripts, tests) mit bash -n
#   JSON    (Desklet, scripts) auf gueltiges JSON
#   JS      (Desklet, tests) mit cjs, falls vorhanden (Laufzeit wie Cinnamon)
#
# Es wird nichts installiert und nichts geschrieben - auch kein __pycache__
# und keine Datei unter /tmp (Pruefung Phase 2, P70).
# Aufruf im Repository-Wurzelverzeichnis:  bash tests/syntax-check.sh
# ---------------------------------------------------------------------------

cd "$(dirname "$0")/.." || exit 1

FEHLER=0
GEPRUEFT=0

# melde <Rueckgabewert> <Datei> [Ausgabe]
melde() {
    if [ "$1" -eq 0 ]; then
        printf '  ok      %s\n' "$2"
    else
        printf '  FEHLER  %s\n' "$2"
        [ -n "$3" ] && printf '%s\n' "$3" | sed 's/^/          /'
        FEHLER=$((FEHLER + 1))
    fi
    GEPRUEFT=$((GEPRUEFT + 1))
}

echo "Python:"
while IFS= read -r f; do
    out=$(python3 -c "import ast,sys; ast.parse(open(sys.argv[1], encoding='utf-8').read(), sys.argv[1])" "$f" 2>&1)
    melde $? "$f" "$out"
done < <( { find Desklet scripts tests -name '*.py' -not -path '*/__pycache__/*' 2>/dev/null;
            grep -rlE '^#!.*python3?$' scripts tests 2>/dev/null | grep -v '\.py$'; } | sort -u)

echo
echo "Shell:"
while IFS= read -r f; do
    out=$(bash -n "$f" 2>&1)
    melde $? "$f" "$out"
done < <(grep -rl '^#!.*\(bash\|sh\)$' scripts tests 2>/dev/null | sort)

echo
echo "JSON:"
while IFS= read -r f; do
    out=$(python3 -c "import json,sys; json.load(open(sys.argv[1], encoding='utf-8'))" "$f" 2>&1)
    melde $? "$f" "$out"
done < <(find Desklet scripts -name '*.json' 2>/dev/null | sort)

echo
echo "JavaScript:"
if command -v cjs >/dev/null 2>&1; then
    # cjs kennt keinen reinen Syntaxmodus. Die Datei wird in einer
    # Funktion ausgewertet: Syntaxfehler fallen auf, ohne dass der
    # Code ausgefuehrt wird (Cinnamon-Objekte fehlen hier ohnehin).
    # Der Pfad kommt als Programmargument, nicht in den Quelltext.
    while IFS= read -r f; do
        out=$(cjs -c "
            const GLib = imports.gi.GLib;
            const [, bytes] = GLib.file_get_contents(ARGV[0]);
            try {
                new Function(new TextDecoder().decode(bytes));
            } catch (e) {
                if (e instanceof SyntaxError) { print('SYNTAX: ' + e.message); imports.system.exit(1); }
            }
        " "$f" 2>&1)
        melde $? "$f" "$out"
    done < <(find Desklet tests -name '*.js' 2>/dev/null | sort)
else
    echo "  cjs nicht vorhanden - JavaScript wird nicht geprueft"
fi

echo
echo "---------------------------------------------------------------"
echo "Geprueft: $GEPRUEFT Dateien, Fehler: $FEHLER"
echo "Hinweis: Eine bestandene Syntaxpruefung ersetzt keinen Funktionstest."
echo "         Alle Offline-Tests: bash tests/alle-tests.sh; am Geraet danach"
echo "         tests/PRUEFLISTE.md abarbeiten."
exit $((FEHLER > 0))
