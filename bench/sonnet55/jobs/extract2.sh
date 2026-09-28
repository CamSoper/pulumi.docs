#!/usr/bin/env bash
# Extraction deep-dive: 15 fixtures x (atomic+holistic) x 7 arms x 3 reps; thinking tokens + latency per call via shim.
set -uo pipefail
B=$PWD/bench/sonnet55; O=$B/out/extract2; F=/tmp/exfx; mkdir -p $O; source $B/arms.sh
CELLS=$(python3 -c "import json;print(json.load(open('$B/trigger.json')).get('cells','ship S55bt S55btlow S55low S55med S55high S55xhigh'))")
REPS=$(python3 -c "import json;print(json.load(open('$B/trigger.json')).get('reps',3))")
SCRIPT=$PWD/.claude/commands/docs-review/scripts/extract-claims-llm.py
bash $B/build_extract_fixtures.sh $B/fixtures/extract2.tsv $F
for d in $F/*/; do cp $d/files.txt $O/$(basename $d).files.txt; cp $d/patch.diff $O/$(basename $d).patch.diff; done
run_cell() { c=$1; n=0; for r in $(seq 1 $REPS); do
  for d in $F/*/; do fx=$(basename $d); n=$((n+1)); [ $((n % 5)) -eq 0 ] && wait; for ps in atomic holistic; do
    o=$O/$c/r$r/$fx.$ps.json; mkdir -p $(dirname $o); [ -s $o ] && continue
    ( arm_env2 $c; [ "$c" != ship ] && export BENCH_MAXTOK=32000; export BENCH_STATS=${o%.json}.stats.json BENCH_TIMEOUT=900
      cd $d/root && python3 $B/shim.py $SCRIPT --patch-file ../patch.diff --changed-files "$(cat ../files.txt)" --repo-root . --pass $ps --scrutiny standard --out $o > ${o%.json}.log 2>&1 ) &
  done; done
done; wait; }
for c in $CELLS; do run_cell $c & done; wait
echo EXTRACT2 DONE
