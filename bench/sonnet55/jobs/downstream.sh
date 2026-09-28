#!/usr/bin/env bash
# Downstream check: does the extractor config change what the REAL chain surfaces and costs?
# Per GT fixture: regex floor + URL pre-fetch once (shared), then per arm x rep: merge-claims.py -> verify-claims.py
# (shipping Opus 5.5 medium, no rewrites; shim only records usage).
set -uo pipefail
B=$PWD/bench/sonnet55; X=$B/out/extract2; O=$B/out/downstream; F=/tmp/exfx; mkdir -p $O
S=$PWD/.claude/commands/docs-review/scripts
ARMS=$(python3 -c "import json;print(json.load(open('$B/trigger.json')).get('ds_arms','ship S55bt S55med S55high'))")
DSREPS=$(python3 -c "import json;print(json.load(open('$B/trigger.json')).get('ds_reps','1 2'))")
grep -P '^ex-' $B/fixtures/extract2.tsv > /tmp/gt.tsv; bash $B/build_extract_fixtures.sh /tmp/gt.tsv $F
for d in $F/ex-*/; do fx=$(basename $d); mkdir -p $O/_shared/$fx
  [ -s $O/_shared/$fx/regex.json ] || (cd $d/root && python3 $S/extract-claims.py --patch-file ../patch.diff --out $O/_shared/$fx/regex.json --repo-root . >/dev/null 2>&1)
  [ -s $O/_shared/$fx/fetched.json ] || (cd $d/root && python3 $S/extract-urls-and-fetch.py --patch-file ../patch.diff --out $O/_shared/$fx/fetched.json >/dev/null 2>&1)
done
run() { arm=$1; rep=$2; for d in $F/ex-*/; do fx=$(basename $d); o=$O/$arm/r$rep/$fx; mkdir -p $o; [ -s $o/verified.json ] && continue
  ( cd $d/root
    python3 $S/merge-claims.py --regex $O/_shared/$fx/regex.json --llm $X/$arm/r$rep/$fx.atomic.json --llm $X/$arm/r$rep/$fx.holistic.json --repo-root . --out $o/merged.json > $o/merge.log 2>&1
    s=$(date +%s)
    BENCH_STATS=$o/verify.stats.json BENCH_TIMEOUT=300 python3 $B/shim.py $S/verify-claims.py --in $o/merged.json --fetched-urls $O/_shared/$fx/fetched.json --repo-root . --out $o/verified.json > $o/verify.log 2>&1
    echo $(( $(date +%s)-s )) > $o/wall_s )
done; }
for arm in $ARMS; do for rep in $DSREPS; do run $arm $rep & done; done; wait
python3 $B/score_downstream.py
echo DOWNSTREAM DONE
