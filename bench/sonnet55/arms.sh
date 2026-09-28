# Arm definitions: sets BENCH_* env for an arm name. One axis at a time vs the lane's control.
arm_env() {
  unset BENCH_MODEL BENCH_THINKING BENCH_EFFORT BENCH_TOOLCHOICE
  case "$1" in
    ship) ;;                                                  # the lane exactly as it ships today
    S5)   export BENCH_MODEL=claude-sonnet-5 BENCH_THINKING=disabled BENCH_EFFORT=none ;;  # old Sonnet verifier shape
    S55bt)   export BENCH_MODEL=claude-sonnet-5-5 BENCH_THINKING=between_tools BENCH_EFFORT=none BENCH_TOOLCHOICE=auto ;;
    S55low)  export BENCH_MODEL=claude-sonnet-5-5 BENCH_THINKING=adaptive BENCH_EFFORT=low BENCH_TOOLCHOICE=auto ;;
    S55med)  export BENCH_MODEL=claude-sonnet-5-5 BENCH_THINKING=adaptive BENCH_EFFORT=medium BENCH_TOOLCHOICE=auto ;;
    S55high) export BENCH_MODEL=claude-sonnet-5-5 BENCH_THINKING=adaptive BENCH_EFFORT=high BENCH_TOOLCHOICE=auto ;;
    *) echo "unknown arm $1" >&2; return 1 ;;
  esac
}
# 2026-09-28 extraction deep-dive: thinking on/off at matched effort, plus xhigh
arm_env2() {
  case "$1" in
    S55btlow) unset BENCH_MODEL BENCH_THINKING BENCH_EFFORT BENCH_TOOLCHOICE
              export BENCH_MODEL=claude-sonnet-5-5 BENCH_THINKING=between_tools BENCH_EFFORT=low BENCH_TOOLCHOICE=auto ;;
    S55xhigh) unset BENCH_MODEL BENCH_THINKING BENCH_EFFORT BENCH_TOOLCHOICE
              export BENCH_MODEL=claude-sonnet-5-5 BENCH_THINKING=adaptive BENCH_EFFORT=xhigh BENCH_TOOLCHOICE=auto ;;
    *) arm_env "$1" ;;
  esac
}
