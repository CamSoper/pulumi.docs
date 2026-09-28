#!/usr/bin/env python3
"""Score the 2026-09-28 verify-claims matrix (out/verify/<cell>-r<rep>.json).

Bases:
  adjudicated_real   10 claims adjudicated REAL defects: the 8 REAL items in the 2026-09-22
                     ADJUDICATION.json (4 of them independently fixed by merged human PRs) plus the
                     2 remaining pulumi/docs#20348 anchors. Hit = verdict in the flag set.
  adjudicated_fp     4 claims adjudicated FALSE-POSITIVE when flagged (same file). Hit = flagged (bad).
  gate / errors      deterministic
  determinism        self-consistency
Flags on claims outside the adjudicated set are counted and listed for hand adjudication.
"""
import collections, glob, json, os, re, statistics, sys

B = os.path.dirname(os.path.abspath(__file__))
RUNS = os.path.join(B, "out/verify")
ADJ = json.load(open(os.path.join(B, "fixtures/verify/ADJUDICATION.json")))["items"]
FLAG = ("contradicted", "mismatch", "framing-drift")
PRICES = {"claude-sonnet-5": (2.0, 10.0, 0.20, 2.50), "claude-sonnet-5-5": (2.0, 10.0, 0.20, 2.50),
          "claude-opus-5-5": (4.0, 20.0, 0.20, 5.00)}
CELL_MODEL = {"ship": "claude-opus-5-5", "S5": "claude-sonnet-5", "S55bt": "claude-sonnet-5-5",
              "S55low": "claude-sonnet-5-5", "S55med": "claude-sonnet-5-5", "S55high": "claude-sonnet-5-5"}
ORDER = ["ship", "S5", "S55bt", "S55low", "S55med", "S55high"]
key = lambda t: re.sub(r"\s+", " ", re.sub(r"^[-*]\s+", "", (t or "").strip()))[:70]
REAL = {key(x["claim"]): x["claim"][:60] for x in ADJ if x["adjudication"] == "REAL"}
REAL[key("Source-based packages referenced directly from a `Pulumi.yaml` file can use any Git ref")] = "Git ref (#20348)"
FP = {key(x["claim"]): x["claim"][:60] for x in ADJ if x["adjudication"] == "FALSE-POSITIVE"}
# 2026-09-28 additions (agent-adjudicated against source; see raw/<id>/ADJUDICATION-ADDENDUM.md):
REAL[key("There exists a `terraform.state.S3Reference` construct/class")] = "S3Reference class (#20348 fabricated API)"
REAL[key("An 'AWS Installation & Configuration' page exists as an example of registry provider authentication")] = "AWS I&C link target (retargeted upstream)"
FP[key("The Automation API Go SDK's `stack.SetConfig` method accepts a boolean `true` argument")] = "Go SetConfig bool (extractor misattribution)"


def match(table, text):
    k = key(text)
    for kk in table:
        if k.startswith(kk[:50]) or kk.startswith(k[:50]):
            return kk
    return None


def speak_anchor(text):
    return "Speak at meetups and conferences" in (text or "")


def cost(model, u):
    i, o, cr, cw = PRICES[model]
    return (u.get("input_tokens", 0) * i + u.get("output_tokens", 0) * o
            + u.get("cache_read_input_tokens", 0) * cr + u.get("cache_creation_input_tokens", 0) * cw) / 1e6


wall = collections.defaultdict(list)
if os.path.exists(os.path.join(RUNS, "wall.txt")):
    for line in open(os.path.join(RUNS, "wall.txt")):
        p = line.split(); wall[p[0]].append(int(p[-1].rstrip("s")))

out = {}
for cell in ORDER:
    files = sorted(f for f in glob.glob(os.path.join(RUNS, f"{cell}-r*.json")) if not f.endswith(".stats.json"))
    if not files:
        continue
    model = CELL_MODEL[cell]
    per = collections.defaultdict(list); mix = collections.Counter(); gate = collections.Counter()
    costs, toks, errs, stops, refusals, http = [], collections.Counter(), 0, collections.Counter(), 0, collections.Counter()
    notool = 0; capx = 0
    for f in files:
        d = json.load(open(f)); m = d.get("meta") or {}
        u = {k: m.get(k, 0) for k in ("input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")}
        costs.append(cost(model, u)); toks.update(u)
        errs += len(d.get("errors") or [])
        sp = f[:-5] + ".stats.json"
        if os.path.exists(sp):
            s = json.load(open(sp)); stops.update(s.get("stop_reasons") or {}); refusals += len(s.get("refusals") or [])
            http.update(s.get("http_errors") or {}); notool += s.get("no_tool_use_when_tools", 0)
        for v in d.get("verdicts") or []:
            t = v.get("text") or ""
            per[t].append(v.get("verdict")); mix[v.get("verdict")] += 1
            if v.get("source_discipline_gate"): gate[v["source_discipline_gate"]] += 1
            if v.get("turn_cap_exhausted"): capx += 1
    n = len(files)
    real_hits, real_detail, fp_hits, fp_detail, other_flags = 0, {}, 0, {}, collections.Counter()
    for t, vs in per.items():
        flagged = sum(v in FLAG for v in vs)
        r = match(REAL, t) or ("speak" if speak_anchor(t) else None)
        fpk = match(FP, t)
        if r:
            real_hits += flagged; real_detail[(REAL.get(r) or "Speak at meetups (#20348)")] = vs
        elif fpk:
            fp_hits += flagged; fp_detail[FP[fpk]] = vs
        elif flagged:
            other_flags[t[:110]] = flagged
    real_n = len(REAL) + 1
    maj_real = sum(1 for vs in real_detail.values() if sum(v in FLAG for v in vs) * 2 > len(vs))
    stable = sum(1 for vs in per.values() if len(vs) == n and len(set(vs)) == 1)
    mean = lambda xs: sum(xs) / max(1, len(xs))
    out[cell] = {
        "model": model, "reps": n, "claims": len(per),
        "cost_per_run_usd": round(mean(costs), 4), "cost_sd": round(statistics.pstdev(costs), 4) if n > 1 else 0,
        "cost_per_claim_usd": round(mean(costs) / max(1, len(per)), 5), "tokens_total": dict(toks),
        "wall_s_per_run": round(mean(wall.get(cell, [])), 1) if wall.get(cell) else None,
        "adjudicated_real_hits": f"{real_hits}/{real_n * n}", "adjudicated_real_majority": f"{maj_real}/{real_n}",
        "adjudicated_fp_flags": f"{fp_hits}/{len(FP) * n}",
        "unadjudicated_flags_per_run": round(sum(other_flags.values()) / n, 2), "unadjudicated_flags": dict(other_flags),
        "flagged_per_run": round(sum(mix[v] for v in FLAG) / n, 2),
        "unverifiable_per_run": round(mix["unverifiable"] / n, 2), "verdict_mix": dict(mix),
        "determinism_pct": round(100 * stable / max(1, len(per)), 1),
        "source_discipline_gate": sum(gate.values()), "turn_cap_exhausted": capx, "errors": errs,
        "stop_reasons": dict(stops), "refusals": refusals, "http_errors": dict(http), "no_tool_turns": notool,
        "real_detail": real_detail, "fp_detail": fp_detail,
    }
json.dump(out, open(os.path.join(RUNS, "summary.json"), "w"), indent=1)
print(f"{'cell':<8}{'n':>3}{'$/run':>8}{'$/clm':>8}{'wall':>6}{'real':>8}{'maj':>6}{'fp':>6}{'oth/r':>6}{'unv/r':>6}{'det%':>6}{'gate':>5}{'cap':>4}{'err':>4}{'refu':>5}")
for c, s in out.items():
    print(f"{c:<8}{s['reps']:>3}{s['cost_per_run_usd']:>8.3f}{s['cost_per_claim_usd']:>8.4f}{(s['wall_s_per_run'] or 0):>6.0f}"
          f"{s['adjudicated_real_hits']:>8}{s['adjudicated_real_majority']:>6}{s['adjudicated_fp_flags']:>6}"
          f"{s['unadjudicated_flags_per_run']:>6.1f}{s['unverifiable_per_run']:>6.1f}{s['determinism_pct']:>6.0f}"
          f"{s['source_discipline_gate']:>5}{s['turn_cap_exhausted']:>4}{s['errors']:>4}{s['refusals']:>5}")
