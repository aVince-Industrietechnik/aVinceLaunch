#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-only
# Copyright (c) 2026 Angelo Vincenti, aVince Industrietechnik

# ---------------------------------------------------------------------------
# aVinceLaunch - alle Offline-Tests auf einmal (Pruefung Phase 2, A9)
#
# Erst die Syntaxpruefung, dann jeder Test tests/*-test.js (cjs) und
# tests/*-test.py (python3), am Ende eine Zusammenfassung.
#
# Laeuft ohne laufendes Cinnamon und beruehrt das Live-System nicht:
#   LANGUAGE=C                 Meldungen englisch (Tests vergleichen Texte)
#   DBUS_SESSION_BUS_ADDRESS   ungueltig - kein Test erreicht das laufende
#                              Cinnamon oder andere Dienste der Sitzung
#   PYTHONDONTWRITEBYTECODE=1  kein __pycache__ neben den Quelldateien
# Jeder Test arbeitet in eigenen Wegwerfordnern und bricht mit Code 2 ab,
# wenn deren Umleitung nicht greift (tests/umleitung.py).
#
# Aufruf im Repository-Wurzelverzeichnis:  bash tests/alle-tests.sh
# Rueckgabewert 0 = alles bestanden.  --liste: nur die Tests auflisten.
# ---------------------------------------------------------------------------

cd "$(dirname "$0")/.." || exit 1

# Reihenfolge nach Bytes (LC_ALL=C) - wie Pythons sorted() in a9-test.py;
# nach Sprache sortiert stand n12-test vor n1-position-test (N12, 10.10.).
alle_tests() {
    find tests -maxdepth 1 \( -name '*-test.js' -o -name '*-test.py' \) | LC_ALL=C sort
}

if [ "${1:-}" = "--liste" ]; then
    alle_tests
    exit 0
fi

export LANGUAGE=C
export DBUS_SESSION_BUS_ADDRESS="unix:path=/nonexistent/avincelaunch-test"
export PYTHONDONTWRITEBYTECODE=1

GESAMT=0
FEHLGESCHLAGEN=()
PRUEFUNGEN=0

echo "== Syntaxpruefung"
if syntax=$(bash tests/syntax-check.sh 2>&1); then
    echo "   $(printf '%s\n' "$syntax" | grep '^Geprueft:')"
else
    printf '%s\n' "$syntax" | grep -E 'FEHLER|^Geprueft:' | sed 's/^/   /'
    FEHLGESCHLAGEN+=("tests/syntax-check.sh")
fi

echo "== Offline-Tests"
while IFS= read -r t; do
    case "$t" in
        *.js) out=$(cjs "$t" 2>&1) ;;
        *.py) out=$(python3 "$t" 2>&1) ;;
    esac
    rc=$?
    GESAMT=$((GESAMT + 1))
    summary=$(printf '%s\n' "$out" | grep -E '^Geprueft: [0-9]+, Fehler: [0-9]+$' | tail -1)
    n=$(printf '%s\n' "$summary" | sed -n 's/^Geprueft: \([0-9]*\),.*/\1/p')
    PRUEFUNGEN=$((PRUEFUNGEN + ${n:-0}))
    if [ "$rc" -eq 0 ] && [ -n "$summary" ]; then
        printf '   ok      %-32s %s\n' "${t#tests/}" "$summary"
    else
        printf '   FEHLER  %-32s %s (Rueckgabewert %s)\n' "${t#tests/}" "${summary:-ohne Zusammenfassung}" "$rc"
        printf '%s\n' "$out" | grep -E 'FEHLER|ABBRUCH|Traceback|Error' | head -8 | sed 's/^/             /'
        FEHLGESCHLAGEN+=("$t")
    fi
done < <(alle_tests)

echo "---------------------------------------------------------------"
echo "Tests: $GESAMT, Pruefungen: $PRUEFUNGEN, fehlgeschlagen: ${#FEHLGESCHLAGEN[@]}"
if [ "${#FEHLGESCHLAGEN[@]}" -gt 0 ]; then
    printf '  - %s\n' "${FEHLGESCHLAGEN[@]}"
    exit 1
fi
echo "Alles bestanden."
exit 0
