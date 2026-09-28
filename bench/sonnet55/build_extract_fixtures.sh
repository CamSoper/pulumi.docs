#!/usr/bin/env bash
# Build extraction fixtures under $F from a TSV (id, base, head, kind). Idempotent. Usage: build_extract_fixtures.sh <tsv> <F>
set -uo pipefail
TSV=$1; F=$2; mkdir -p $F
git remote add upstream https://github.com/pulumi/docs.git 2>/dev/null
while IFS=$'\t' read fx base head kind; do
  [ -d $F/$fx/root ] && continue
  git fetch -q upstream $head 2>/dev/null || git cat-file -e "$head^{commit}" 2>/dev/null || echo "fetch head failed $fx"
  git worktree add -f -q $F/$fx/root $head || { echo "worktree fail $fx"; continue; }
  if [ "$kind" = pr ]; then
    (cd $F/$fx/root && git diff "$base" HEAD -- 'content/**/*.md' > ../patch.diff && git diff --name-only "$base" HEAD -- 'content/**/*.md' | paste -sd, > ../files.txt)
  else
    (cd $F/$fx/root && git diff --no-index /dev/null $kind | sed "s#a/dev/null#a/$kind#" > ../patch.diff; echo $kind > ../files.txt)
  fi
  echo "fixture $fx files=$(cat $F/$fx/files.txt) patch=$(wc -l < $F/$fx/patch.diff)"
done < $TSV
