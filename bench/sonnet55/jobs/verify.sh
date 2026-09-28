#!/usr/bin/env bash
# verify-claims.py matrix: ledger-50 floor, evidence base pinned to 4d85a74fb0, 3 reps/cell.
set -uo pipefail
B=bench/sonnet55; O=$B/out/verify; mkdir -p $O
source $B/arms.sh
CELLS="${CELLS:-$(python3 -c "import json;print(json.load(open('$B/trigger.json')).get('cells','ship S5 S55bt S55low S55med S55high'))")}"
REPS=$(python3 -c "import json;print(json.load(open('$B/trigger.json')).get('reps',3))")
EV=/tmp/evidence; git worktree add -f $EV 4d85a74fb0 >/dev/null 2>&1 || { echo "worktree failed"; exit 1; }
[ -s $O/fetched-urls.json ] || python3 $B/prefetch_urls.py $B/fixtures/verify/corpus-claims.json $O/fetched-urls.json
run_cell() { c=$1; for r in $(seq 1 $REPS); do
    f=$O/$c-r$r.json; [ -s $f ] && continue
    ( arm_env $c; export BENCH_STATS=$O/$c-r$r.stats.json BENCH_TIMEOUT=300
      s=$(date +%s)
      python3 $B/shim.py .claude/commands/docs-review/scripts/verify-claims.py --in $B/fixtures/verify/corpus-claims.json \
        --fetched-urls $O/fetched-urls.json --out $f --repo-root $EV > $O/$c-r$r.log 2>&1
      echo "$c r$r rc=$? $(( $(date +%s)-s ))s" >> $O/wall.txt )
  done; }
for c in $CELLS; do run_cell $c & done; wait
echo VERIFY DONE; cat $O/wall.txt
