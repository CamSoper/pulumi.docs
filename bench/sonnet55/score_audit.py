#!/usr/bin/env python3
"""Score the extraction deep-dive: auditor grades + thinking cost + inventory sanity + inter-auditor agreement.

Outputs out/audit/summary.json. Cost is from shim counters (Sonnet $2/$10, cache read 0.1x, 5m write 1.25x);
thinking tokens are a subset of output_tokens, so thinking $ = thinking_tokens x $10/MTok.
"""
import collections, glob, json, os, re, statistics as st, urllib.request, time
from pathlib import Path

B = Path(__file__).resolve().parent; X = B / "out/extract2"; O = B / "out/audit"
ARMS = ["ship", "S55bt", "S55btlow", "S55low", "S55med", "S55high", "S55xhigh"]
P = {"claude-sonnet-5": (2, 10, 0.2, 2.5), "claude-sonnet-5-5": (2, 10, 0.2, 2.5)}
GT = json.load(open(B / "fixtures/extract-ground-truth.json"))["extract"]
KEY = os.environ.get("ANTHROPIC_API_KEY", "")
FLAGS = ("valid", "not-a-claim", "unfaithful")


def usd(model, u):
    i, o, cr, cw = P[model]
    return (u.get("input_tokens", 0) * i + u.get("output_tokens", 0) * o + u.get("cache_read_input_tokens", 0) * cr + u.get("cache_creation_input_tokens", 0) * cw) / 1e6


def pctl(xs, q):
    xs = sorted(xs); return xs[min(len(xs) - 1, int(round(q * (len(xs) - 1))))] if xs else None


summary = {"arms": {}, "notes": []}
inv = {p.stem: json.load(open(p))["items"] for p in (O / "inventory").glob("*.json")}
for arm in ARMS:
    if not (X / arm).exists(): continue
    model = "claude-sonnet-5" if arm == "ship" else "claude-sonnet-5-5"
    u = collections.Counter(); lat = []; calls = 0; stops = collections.Counter(); notool = 0; errs = 0; ncl = []; per_set = collections.defaultdict(lambda: collections.Counter())
    for sp in X.glob(f"{arm}/r*/*.stats.json"):
        s = json.load(open(sp)); u.update({k: v for k, v in s["usage"].items() if isinstance(v, int)})
        stops.update(s.get("stop_reasons") or {}); notool += s.get("no_tool_use_when_tools", 0)
        for c in s.get("per_call") or []: lat.append(c["s"]); calls += 1
        fx = sp.name.split(".")[0]; st_ = "gt" if fx.startswith("ex-") else "breadth"
        per_set[st_]["out"] += s["usage"].get("output_tokens", 0); per_set[st_]["think"] += s["usage"].get("thinking_tokens", 0)
    for cp in X.glob(f"{arm}/r*/*.json"):
        if cp.name.endswith(".stats.json"): continue
        d = json.load(open(cp)); ncl.append(len(d.get("claims") or [])); errs += sum(1 for e in (d.get("errors") or []) if "small edit" not in e and "rename" not in e)
    total = usd(model, u); think_usd = u["thinking_tokens"] * 10 / 1e6
    g = collections.Counter(); inv_cov = []; inv_cov_hi = []; novel = 0; dup = 0; graded = 0; by_pass = collections.defaultdict(collections.Counter); by_set = collections.defaultdict(collections.Counter)
    for gp in (O / "grade" / arm).glob("r*/*.json"):
        fx = gp.stem; rows = json.load(open(gp)).get("rows") or []; items = inv.get(fx, []); sset = "gt" if fx.startswith("ex-") else "breadth"
        covered = set(); seen_pass = {"A": [], "H": []}
        for r in rows:
            if len(r) < 7: continue
            cid, verdict, sc, at, lo, ids, nov = r[:7]; graded += 1
            g[verdict] += 1; g["self_contained"] += int(sc); g["atomic"] += int(at); g["line_ok"] += int(lo); novel += int(nov)
            by_pass[cid[0]][verdict] += 1; by_pass[cid[0]]["n"] += 1; by_set[sset][verdict] += 1; by_set[sset]["n"] += 1
            if verdict == "valid":
                covered.update(ids or [])
                key = tuple(sorted(ids or []))
                if key and key in seen_pass[cid[0]]: dup += 1
                seen_pass[cid[0]].append(key)
        if items:
            inv_cov.append((len(covered & {i["id"] for i in items}), len(items), sset))
            hi = {i["id"] for i in items if i.get("importance") == "high"}
            if hi: inv_cov_hi.append((len(covered & hi), len(hi), sset))
    rate = lambda k: round(g[k] / graded, 3) if graded else None
    rec = lambda xs, s=None: round(sum(a for a, b, t in xs if s in (None, t)) / max(1, sum(b for a, b, t in xs if s in (None, t))), 3)
    summary["arms"][arm] = {
        "model": model, "file_calls": len(ncl), "api_calls": calls, "errors": errs, "stop_reasons": dict(stops), "missing_tool_call": notool,
        "usd_total": round(total, 3), "usd_per_file_call": round(total / max(1, len(ncl)), 4),
        "output_tokens": u["output_tokens"], "thinking_tokens": u["thinking_tokens"],
        "thinking_share_of_output": round(u["thinking_tokens"] / max(1, u["output_tokens"]), 3),
        "thinking_usd": round(think_usd, 3), "thinking_share_of_cost": round(think_usd / max(1e-9, total), 3),
        "thinking_share_by_set": {k: round(v["think"] / max(1, v["out"]), 3) for k, v in per_set.items()},
        "latency_s_p50": pctl(lat, 0.5), "latency_s_p95": pctl(lat, 0.95), "latency_s_max": max(lat) if lat else None,
        "claims_per_file_call": round(sum(ncl) / max(1, len(ncl)), 1),
        "graded_claims": graded, "valid_rate": rate("valid"), "not_a_claim_rate": rate("not-a-claim"), "unfaithful_rate": rate("unfaithful"),
        "unfaithful_count": g["unfaithful"], "self_contained_rate": rate("self_contained"), "atomic_rate": rate("atomic"), "line_ok_rate": rate("line_ok"),
        "inventory_recall": rec(inv_cov), "inventory_recall_gt": rec(inv_cov, "gt"), "inventory_recall_breadth": rec(inv_cov, "breadth"),
        "inventory_recall_high": rec(inv_cov_hi), "novel_valid_claims": novel, "within_pass_duplicates": dup,
        "valid_claims_per_file_call": round(g["valid"] / max(1, len(ncl)), 1),
        "by_pass": {k: {kk: round(v[kk] / v["n"], 3) for kk in FLAGS} | {"n": v["n"]} for k, v in by_pass.items()},
        "by_set": {k: {kk: round(v[kk] / v["n"], 3) for kk in FLAGS} | {"n": v["n"]} for k, v in by_set.items()},
    }

# inter-auditor agreement (Opus 5.5 cross-grade vs Fable on the same cells)
agree = collections.Counter()
for cp in (O / "cross").glob("*/r*/*.json"):
    arm, rep, fx = cp.parts[-3], cp.parts[-2], cp.stem
    fp = O / "grade" / arm / rep / f"{fx}.json"
    if not fp.exists(): continue
    a = {r[0]: r for r in json.load(open(fp)).get("rows") or [] if len(r) >= 7}
    b = {r[0]: r for r in json.load(open(cp)).get("rows") or [] if len(r) >= 7}
    for cid in a.keys() & b.keys():
        agree["n"] += 1; agree["verdict"] += a[cid][1] == b[cid][1]
        agree["valid_binary"] += (a[cid][1] == "valid") == (b[cid][1] == "valid")
        agree["covers_any"] += bool(a[cid][5]) == bool(b[cid][5])
        agree[f"fable:{a[cid][1]}|opus:{b[cid][1]}"] += 1
summary["inter_auditor"] = {k: (round(v / agree["n"], 3) if k in ("verdict", "valid_binary", "covers_any") else v) for k, v in agree.items()}

# inventory sanity: does the auditor's own inventory cover the 24 human-fixed defects? (blind judge, 2026-09-22 prompt)
EX_SYS = open(B / "score_extract.py").read().split('EX_SYS = """')[1].split('"""')[0]
if KEY or os.environ.get("AUDIT_BACKEND") == "cli":
    covp = O / "inventory_gt_coverage.json"
    if not covp.exists():
        res = {}
        for fx, defs in GT.items():
            items = [{"id": i["id"], "file": i.get("file"), "line_range": i.get("line_range"), "type": i.get("type"), "text": i.get("text")} for i in inv.get(fx, [])]
            body = {"model": "claude-fable-5-1", "max_tokens": 16000, "output_config": {"effort": "medium"},
                    "system": [{"type": "text", "text": EX_SYS.replace("{{", "{").replace("}}", "}").replace("{defects}", "\n".join(f"- {d['id']} [{d['file']}]: {d['defect']}" for d in defs))}],
                    "messages": [{"role": "user", "content": "Extracted claims (JSON):\n" + json.dumps(items, ensure_ascii=False)}]}
            if os.environ.get("AUDIT_BACKEND") == "cli":
                import sys; sys.path.insert(0, str(B)); from audit import call_cli
                try: res[fx] = call_cli("claude-fable-5-1", body["system"], body["messages"][0]["content"], "medium")
                except Exception: pass
                continue
            for att in range(4):
                try:
                    req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=json.dumps(body).encode(), headers={"x-api-key": KEY, "anthropic-version": "2023-06-01", "content-type": "application/json"})
                    d = json.loads(urllib.request.urlopen(req, timeout=600).read())
                    txt = "".join(b.get("text", "") for b in d["content"] if b.get("type") == "text")
                    res[fx] = json.loads(re.search(r"\{.*\}", txt, re.S).group(0)); break
                except Exception:
                    time.sleep(5)
        covp.write_text(json.dumps(res, indent=1))
    cov = json.load(open(covp))
    hit = sum(1 for fx, defs in GT.items() for dd in defs if ((cov.get(fx) or {}).get("defects", {}).get(dd["id"]) or {}).get("covered"))
    summary["inventory_gt_coverage"] = f"{hit}/{sum(len(v) for v in GT.values())}"
summary["inventory_items"] = {fx: len(v) for fx, v in sorted(inv.items())}
json.dump(summary, open(O / "summary.json", "w"), indent=1)
for a, s in summary["arms"].items():
    print(f"{a:<9} $/call {s['usd_per_file_call']:.4f} think {s['thinking_share_of_cost']:.0%} of $  p50 {s['latency_s_p50']}s p95 {s['latency_s_p95']}s | "
          f"claims {s['claims_per_file_call']} valid {s['valid_rate']} unfaith {s['unfaithful_rate']} nac {s['not_a_claim_rate']} | "
          f"inv-recall {s['inventory_recall']} (hi {s['inventory_recall_high']}, gt {s['inventory_recall_gt']}, br {s['inventory_recall_breadth']}) novel {s['novel_valid_claims']} dup {s['within_pass_duplicates']}")
print("inter-auditor:", summary["inter_auditor"]); print("inventory GT coverage:", summary.get("inventory_gt_coverage"))
