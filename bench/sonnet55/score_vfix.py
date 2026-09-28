#!/usr/bin/env python3
"""Score validator-fix.py: deterministic byte comparison against the clean original body.
  fixed        planted lines restored exactly
  collateral   lines changed that were never planted (drift introduced by the echo)
  exact        output byte-identical to the original (the only fully correct outcome)
  rc           validator-fix exit code (0 = applied; 1 = splice rejected -> body untouched, soft-floor)
"""
import collections, glob, json, os
B = os.path.dirname(os.path.abspath(__file__)); O = os.path.join(B, "out/vfix")
PRICE = {"claude-sonnet-5": (2, 10, 0.2, 2.5), "claude-sonnet-5-5": (2, 10, 0.2, 2.5)}
MODEL = {"ship": "claude-sonnet-5"}
out = {}
for arm in ["ship", "S55bt", "S55low", "S55med", "S55high"]:
    rs = sorted(glob.glob(os.path.join(O, arm, "r*", "*.result.json")))
    if not rs: continue
    agg = collections.Counter(); u = collections.Counter(); stops = collections.Counter(); per = collections.defaultdict(list); walls = []
    for r in rs:
        d = json.load(open(r)); n = os.path.basename(r).replace(".result.json", "")
        agg["runs"] += 1; agg["planted"] += d["planted"]; agg["exact"] += d["exact"]; agg["rc0"] += d["rc"] == 0
        agg["rejected"] += d["rc"] != 0; agg["fixed"] += d["fixed"] or 0; agg["collateral"] += d["collateral_lines"] or 0
        agg["len_mismatch"] += d["fixed"] is None
        walls.append(d["wall_s"]); per[n.split(".")[1]].append(d["exact"])
        sp = r.replace(".result.json", ".stats.json")
        if os.path.exists(sp):
            s = json.load(open(sp)); u.update(s["usage"]); stops.update(s["stop_reasons"])
    i, o, cr, cw = PRICE[MODEL.get(arm, "claude-sonnet-5-5")]
    usd = (u["input_tokens"] * i + u["output_tokens"] * o + u["cache_read_input_tokens"] * cr + u["cache_creation_input_tokens"] * cw) / 1e6
    out[arm] = {**agg, "exact_rate": f"{agg['exact']}/{agg['runs']}", "fix_rate": f"{agg['fixed']}/{agg['planted']}",
                "exact_by_size": {k: f"{sum(v)}/{len(v)}" for k, v in per.items()}, "usage": dict(u), "stop_reasons": dict(stops),
                "usd_total": round(usd, 3), "usd_per_call": round(usd / max(1, agg["runs"]), 4), "wall_s_mean": round(sum(walls) / len(walls), 1),
                "out_tokens_per_call": round(u["output_tokens"] / max(1, agg["runs"]))}
json.dump(out, open(os.path.join(O, "summary.json"), "w"), indent=1)
for a, s in out.items():
    print(f"{a:<8} exact {s['exact_rate']:<6} fixed {s['fix_rate']:<7} collateral {s['collateral']:<3} rejected {s['rejected']:<3} "
          f"by-size {s['exact_by_size']} $/call {s['usd_per_call']} out/call {s['out_tokens_per_call']} wall {s['wall_s_mean']}s stops {s['stop_reasons']}")
