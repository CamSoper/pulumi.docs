#!/usr/bin/env python3
"""Blind-judge extract-claims-llm recall against the 24 known defects (2026-09-22 ground truth).
Judge prompt and model (claude-fable-5-1, effort medium) are copied verbatim from the 2026-09-22
harness so recall is comparable; arm labels never reach the judge. Judgements cached per cell."""
import concurrent.futures as cf, glob, json, os, re, sys, time, urllib.error, urllib.request
B = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(B, "out/extract")
GT = json.load(open(os.path.join(B, "fixtures/extract-ground-truth.json")))["extract"]
KEY = os.environ.get("ANTHROPIC_API_KEY", "")
JUDGE = "claude-fable-5-1"
ARMS = [a for a in ["ship", "S55bt", "S55low", "S55med", "S55high"] if os.path.isdir(os.path.join(OUT, a))]
MODEL = {a: ("claude-sonnet-5" if a == "ship" else "claude-sonnet-5-5") for a in ARMS}
PRICE = {"claude-sonnet-5": (2, 10, 0.2, 2.5), "claude-sonnet-5-5": (2, 10, 0.2, 2.5), "claude-fable-5-1": (10, 50, 1.0, 12.5)}
JU = {"input_tokens": 0, "output_tokens": 0, "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0}
EX_SYS = """You are grading the recall of a claim-extraction step in a documentation fact-checking pipeline.
A downstream verifier only checks claims that appear in the extracted claim list, so a known defect is
"covered" only if at least one extracted claim asserts the specific fact (or quotes/attributes the specific
statement) that the defect is about, closely enough that verifying that claim would expose the defect.
A claim about a different fact on the same line, or a vague claim that merely mentions the topic, does NOT cover it.

Known defects for this fixture:
{defects}

Return ONLY JSON: {{"defects": {{"<defect id>": {{"covered": true|false, "claim_ids": ["..."], "why": "<=20 words"}}}}}}"""


def cost(model, u):
    i, o, cr, cw = PRICE[model]
    return (u.get("input_tokens", 0) * i + u.get("output_tokens", 0) * o + u.get("cache_read_input_tokens", 0) * cr + u.get("cache_creation_input_tokens", 0) * cw) / 1e6


def call(system, user):
    body = {"model": JUDGE, "max_tokens": 16000, "output_config": {"effort": "medium"},
            "system": [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
            "messages": [{"role": "user", "content": user}]}
    last = None
    for attempt in range(5):
        try:
            req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=json.dumps(body).encode(),
                                         headers={"x-api-key": KEY, "anthropic-version": "2023-06-01", "content-type": "application/json"})
            with urllib.request.urlopen(req, timeout=600) as r:
                d = json.loads(r.read())
            for k in JU: JU[k] += int(d.get("usage", {}).get(k, 0) or 0)
            txt = "".join(b.get("text", "") for b in d.get("content", []) if b.get("type") == "text")
            return json.loads(re.search(r"\{.*\}", txt, re.S).group(0))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, AttributeError) as e:
            last = e; time.sleep(3 * (attempt + 1))
    raise RuntimeError(f"judge failed: {last}")


def judge(arm, rep, fx):
    jp = os.path.join(OUT, "judge", arm, f"r{rep}", fx + ".json")
    if os.path.exists(jp): return json.load(open(jp))
    claims = []
    for ps, tag in (("atomic", "A"), ("holistic", "H")):
        p = os.path.join(OUT, arm, f"r{rep}", f"{fx}.{ps}.json")
        if not os.path.exists(p): return None
        for i, c in enumerate(json.load(open(p))["claims"]):
            f = c.get("file", "")
            claims.append({"id": f"{tag}{i+1}", "file": "/".join(f.split("/")[-2:]), "line_range": c.get("line_range"), "type": c.get("type"), "text": c.get("text")})
    if not KEY: return None
    defects = "\n".join(f"- {d['id']} [{d['file']}]: {d['defect']}" for d in GT[fx])
    res = call(EX_SYS.format(defects=defects), "Extracted claims (JSON):\n" + json.dumps(claims, ensure_ascii=False))
    os.makedirs(os.path.dirname(jp), exist_ok=True); json.dump(res, open(jp, "w"), indent=1)
    return res


reps = sorted({int(os.path.basename(p)[1:]) for a in ARMS for p in glob.glob(os.path.join(OUT, a, "r*"))})
res = {}
with cf.ThreadPoolExecutor(8) as ex:
    fut = {ex.submit(judge, a, r, fx): (a, r, fx) for a in ARMS for r in reps for fx in GT}
    for f in cf.as_completed(fut):
        try: res[fut[f]] = f.result()
        except Exception as e: res[fut[f]] = None; print("JUDGE ERROR", fut[f], e, file=sys.stderr)
summary = {"judge": JUDGE, "judge_usage_this_run": JU, "arms": {}}
for a in ARMS:
    u = {k: 0 for k in JU}; ncl = []; errs = 0; stops = {}; notool = 0; refus = 0; http = {}; per_rep = []; hits_by = {}
    for r in reps:
        hit = tot = 0
        for fx, defs in GT.items():
            for ps in ("atomic", "holistic"):
                p = os.path.join(OUT, a, f"r{r}", f"{fx}.{ps}.json")
                if not os.path.exists(p): continue
                d = json.load(open(p)); m = d.get("meta", {})
                for k in u: u[k] += int(m.get(k, 0) or 0)
                ncl.append(len(d.get("claims", []))); errs += len(d.get("errors") or [])
                sp = p[:-5] + ".stats.json"
                if os.path.exists(sp):
                    s = json.load(open(sp)); notool += s.get("no_tool_use_when_tools", 0); refus += len(s.get("refusals") or [])
                    for k2, v in (s.get("stop_reasons") or {}).items(): stops[k2] = stops.get(k2, 0) + v
                    for k2, v in (s.get("http_errors") or {}).items(): http[k2] = http.get(k2, 0) + v
            j = res.get((a, r, fx))
            if not j: continue
            for dd in defs:
                cov = bool((j.get("defects", {}).get(dd["id"]) or {}).get("covered"))
                hit += cov; tot += 1; hits_by.setdefault(dd["id"], []).append(cov)
        per_rep.append((hit, tot))
    usd = cost(MODEL[a], u)
    summary["arms"][a] = {"model": MODEL[a], "recall_per_rep": [f"{h}/{t}" for h, t in per_rep],
        "recall_mean": round(sum(h for h, _ in per_rep) / max(1, sum(t for _, t in per_rep)), 3),
        "defects_hit_any_rep": sum(1 for v in hits_by.values() if any(v)), "n_defects": len(hits_by),
        "defect_stability": f"{sum(1 for v in hits_by.values() if len(set(v)) == 1)}/{len(hits_by)}",
        "claims_per_call": round(sum(ncl) / max(1, len(ncl)), 1), "file_calls": len(ncl), "errors": errs,
        "stop_reasons": stops, "no_tool_use": notool, "refusals": refus, "http_errors": http,
        "usage": u, "usd_total": round(usd, 3), "usd_per_file_call": round(usd / max(1, len(ncl)), 4),
        "missed": sorted(k for k, v in hits_by.items() if not all(v))}
summary["judge_usd_this_run"] = round(cost(JUDGE, JU), 3)
json.dump(summary, open(os.path.join(OUT, "summary.json"), "w"), indent=1)
for a, s in summary["arms"].items():
    print(f"{a:<8} recall {s['recall_mean']:.3f} {s['recall_per_rep']} any={s['defects_hit_any_rep']}/{s['n_defects']} claims/call={s['claims_per_call']} $/call={s['usd_per_file_call']} stops={s['stop_reasons']} notool={s['no_tool_use']} err={s['errors']} refu={s['refusals']}")
