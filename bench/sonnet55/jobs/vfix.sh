#!/usr/bin/env bash
# validator-fix.py matrix: 9 planted-violation fixtures (3 real bodies x 3 batch sizes), deterministic scoring.
set -uo pipefail
B=bench/sonnet55; O=$B/out/vfix; mkdir -p $O; source $B/arms.sh
CELLS=$(python3 -c "import json;print(json.load(open('$B/trigger.json')).get('cells','ship S55bt S55low S55med S55high'))")
REPS=$(python3 -c "import json;print(json.load(open('$B/trigger.json')).get('reps',3))")
run_cell() { c=$1; for r in $(seq 1 $REPS); do
  for fx in $B/fixtures/vfix/*.fixme.json; do n=$(basename $fx .fixme.json); d=$O/$c/r$r; mkdir -p $d
    [ -s $d/$n.result.json ] && continue
    cp $B/fixtures/vfix/$n.planted.md $d/$n.body.md
    ( arm_env $c; export BENCH_STATS=$d/$n.stats.json BENCH_TIMEOUT=600
      s=$(date +%s)
      python3 $B/shim.py .claude/commands/docs-review/scripts/validator-fix.py --body-file $d/$n.body.md --fix-me-json $fx > $d/$n.log 2>&1
      rc=$?
      python3 - "$d/$n.body.md" "$B/fixtures/vfix/$n.expected.md" "$B/fixtures/vfix/$n.planted.md" "$rc" "$(( $(date +%s)-s ))" > $d/$n.result.json <<'PY'
import sys, json, difflib
out, exp, pl = (open(p).read().split("\n") for p in sys.argv[1:4])
changed = [i for i,(a,b) in enumerate(zip(pl,exp)) if a!=b]
fixed = sum(1 for i in changed if i < len(out) and out[i] == exp[i]) if len(out)==len(exp) else None
collateral = sum(1 for i,(a,b) in enumerate(zip(out,exp)) if a!=b and i not in changed) if len(out)==len(exp) else None
print(json.dumps({"rc": int(sys.argv[4]), "wall_s": int(sys.argv[5]), "planted": len(changed), "fixed": fixed,
  "collateral_lines": collateral, "exact": out==exp, "len_out": len(out), "len_exp": len(exp),
  "unchanged_from_planted": out==pl}))
PY
    )
  done; done; }
for c in $CELLS; do run_cell $c & done; wait
echo VFIX DONE
