#!/usr/bin/env bash
# Local replay of claude-social-review.yml's claude-code-action step through the same CLI,
# isolated HOME (no user settings/plugins/CLAUDE.md), one fresh fixture copy per run.
S=$(cd "$(dirname "$0")" && pwd); W=/tmp/claude-0/social-runs; mkdir -p $W $S/out
PROMPT="$(cat $S/prompt.txt)"
MCP='{"mcpServers": {"pulumi-brand": {"type": "http", "url": "https://brand.pulumi.com/mcp"}}}'
TOOLS="Read,Glob,Grep,Agent,mcp__pulumi-brand__get_guidelines,mcp__pulumi-brand__search_guidelines,Write,Bash(python3:*),Bash(gh pr view:*),Bash(gh pr diff:*),Bash(date:*)"
declare -A A=([ship]="--model claude-sonnet-5" [S55def]="--model claude-sonnet-5-5" [S55low]="--model claude-sonnet-5-5 --effort low" [S55med]="--model claude-sonnet-5-5 --effort medium" [S55high]="--model claude-sonnet-5-5 --effort high")
one() { arm=$1 rep=$2 fx=$3; o=$S/out/$arm/r$rep/$fx; [ -s $o/result.json ] && return; mkdir -p $o
  d=$W/$arm-r$rep-$fx; rm -rf -- "$W/$arm-r$rep-$fx"; cp -r $S/fixtures/$fx $d; cd $d || return 1
  s=$(date +%s)
  env -u CLAUDE_EFFORT -u CLAUDE_ADDITIONAL_DIRECTORIES -u CLAUDE_CODE_ADDITIONAL_DIRECTORIES_CLAUDE_MD -u MAX_THINKING_TOKENS HOME=/tmp/claude-0/fakehome \
    timeout 900 claude -p "$PROMPT" ${A[$arm]} --mcp-config "$MCP" --allowed-tools "$TOOLS" --output-format json > $o/result.raw.json 2> $o/stderr.txt
  echo $(( $(date +%s)-s )) > $o/wall_s
  cp .social-review.md $o/ 2>/dev/null; mv $o/result.raw.json $o/result.json; }
export -f one; export S W PROMPT MCP TOOLS
jobs=()
if [ -n "${ONLY:-}" ]; then jobs=("$ONLY"); else
for rep in 1 2 3; do for arm in ship S55def S55low S55med S55high; do for fx in $(ls $S/fixtures | grep -v manifest); do jobs+=("$arm $rep $fx"); done; done; done; fi
printf '%s\n' "${jobs[@]}" | xargs -P ${PAR:-8} -L1 bash -c 'declare -A A=([ship]="--model claude-sonnet-5" [S55def]="--model claude-sonnet-5-5" [S55low]="--model claude-sonnet-5-5 --effort low" [S55med]="--model claude-sonnet-5-5 --effort medium" [S55high]="--model claude-sonnet-5-5 --effort high"); one "$@"' _
echo SOCIAL DONE
