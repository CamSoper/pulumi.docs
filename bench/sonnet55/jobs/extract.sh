#!/usr/bin/env bash
# extract-claims-llm.py matrix: 7 fixtures x (atomic+holistic) x reps. Fixtures rebuilt from pulumi/docs history.
set -uo pipefail
B=$PWD/bench/sonnet55; O=$B/out/extract; F=/tmp/exfx; mkdir -p $O $F; source $B/arms.sh
CELLS=$(python3 -c "import json;print(json.load(open('$B/trigger.json')).get('cells','ship S55bt S55low S55med S55high'))")
REPS=$(python3 -c "import json;print(json.load(open('$B/trigger.json')).get('reps',3))")
SCRIPT=$PWD/.claude/commands/docs-review/scripts/extract-claims-llm.py
git remote add upstream https://github.com/pulumi/docs.git 2>/dev/null
while IFS=$'\t' read fx base head kind; do
  git fetch -q upstream $head || echo "fetch head failed $fx"
  git worktree add -f -q $F/$fx/root $head || { echo "worktree fail $fx"; continue; }
  if [ "$kind" = pr ]; then
    git fetch -q upstream ${base%^} 2>/dev/null
    (cd $F/$fx/root && git diff "$base" HEAD -- 'content/**/*.md' > ../patch.diff && git diff --name-only "$base" HEAD -- 'content/**/*.md' | paste -sd, > ../files.txt)
  else
    (cd $F/$fx/root && git diff --no-index /dev/null $kind | sed "s#a/dev/null#a/$kind#" > ../patch.diff; echo $kind > ../files.txt)
  fi
  echo "fixture $fx files=$(cat $F/$fx/files.txt) patch=$(wc -l < $F/$fx/patch.diff)"
done < $B/fixtures/extract.tsv
for d in $F/*/; do cp $d/files.txt $O/$(basename $d).files.txt; cp $d/patch.diff $O/$(basename $d).patch.diff; done
run_cell() { c=$1; for r in $(seq 1 $REPS); do
  for d in $F/*/; do fx=$(basename $d); for ps in atomic holistic; do
    o=$O/$c/r$r/$fx.$ps.json; mkdir -p $(dirname $o); [ -s $o ] && continue
    ( arm_env $c; [ "$c" != ship ] && export BENCH_MAXTOK=32000; export BENCH_STATS=${o%.json}.stats.json BENCH_TIMEOUT=600
      cd $d/root && python3 $B/shim.py $SCRIPT --patch-file ../patch.diff --changed-files "$(cat ../files.txt)" --repo-root . --pass $ps --scrutiny standard --out $o > ${o%.json}.log 2>&1 ) &
  done; done; wait
done; }
for c in $CELLS; do run_cell $c & done; wait
echo EXTRACT DONE
