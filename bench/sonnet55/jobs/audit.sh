#!/usr/bin/env bash
# Independent audit (Fable 5.1) of every extract2 cell, plus an Opus 5.5 cross-audit subset, then scoring.
set -uo pipefail
B=$PWD/bench/sonnet55; F=/tmp/exfx
bash $B/build_extract_fixtures.sh $B/fixtures/extract2.tsv $F
python3 $B/audit.py --workers 10
python3 $B/audit.py --auditor claude-opus-5-5 --tag cross --arms "ship S55bt S55high" --reps 1 --fx-filter '^ex-' --workers 8
python3 $B/score_audit.py
