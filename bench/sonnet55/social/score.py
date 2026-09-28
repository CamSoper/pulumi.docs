#!/usr/bin/env python3
"""Score the social-review replay. Deterministic basis: expected per-platform verdicts come from the
critique rubric's mechanical hard-fail rules applied to planted (or, for real-onepara-jev, real) breaks.

Per run:
  verdict accuracy     heading verdict per platform vs expected (PASS / FAIL / missing)
  false FAIL           a platform expected PASS reported FAIL (noise for the blogger)
  missed FAIL          a platform expected FAIL reported PASS (the lane's one job)
  repair validity      each suggested copy block re-checked against the same mechanical rules
  file written         .social-review.md exists and starts with the marker
  critique adherence   sub-agents spawned (SKILL.md steps 5-6 require a critic/suggestions sub-agent)
Cost from the CLI's modelUsage token counters (repriced), not total_cost_usd.
"""
import collections, glob, json, os, re

S = os.path.dirname(os.path.abspath(__file__))
MAN = {m["id"]: m for m in json.load(open(os.path.join(S, "fixtures/manifest.json")))}
PRICE = {"claude-sonnet-5": (2, 10, 0.2, 2.5), "claude-sonnet-5-5": (2, 10, 0.2, 2.5), "claude-haiku-4-5": (1, 5, 0.1, 1.25),
         "claude-opus-5-5": (4, 20, 0.2, 5.0)}
LIM = {"X": 255, "LinkedIn": 2950, "Bluesky": 300}
ARMS = ["ship", "S55def", "S55low", "S55med", "S55high"]
PLAT = ("X", "LinkedIn", "Bluesky")


def hard_fail(plat, t):
    t = t.strip(); e = []
    if len(t) > LIM[plat]: e.append("length")
    if re.search(r"(^|\s)#\w", t): e.append("hashtag")
    if re.search(r"https?://", t): e.append("url")
    if re.search(r"\bI\b|\bI'm\b|\bI've\b|\bmy\b", t): e.append("i-voice")
    if re.search(r"\*\*|`|\[[^\]]+\]\(", t): e.append("markdown")
    if re.search(r"excited to announce|read our blog|our latest post|check out our latest", t, re.I): e.append("banned")
    if "\n\n" not in t: e.append("paragraphs")
    return e


def cost(mu):
    tot = 0.0; per = {}
    for m, v in mu.items():
        base = next((k for k in PRICE if m.startswith(k)), None)
        if not base: continue
        i, o, cr, cw = PRICE[base]
        c = (v.get("inputTokens", 0) * i + v.get("outputTokens", 0) * o + v.get("cacheReadInputTokens", 0) * cr
             + v.get("cacheCreationInputTokens", 0) * cw) / 1e6
        # 1h cache writes bill at 2x input, not 1.25x; the CLI writes 1h entries
        c += v.get("cacheCreationInputTokens", 0) * (2 * i - cw) / 1e6
        per[m] = round(c, 4); tot += c
    return tot, per


def parse(md):
    verdict = {}
    for p in PLAT:
        m = re.search(rf"^####\s+{p}\s+[—-]+\s+(PASS|FAIL|missing)", md, re.M | re.I)
        if m: verdict[p] = m.group(1).upper() if m.group(1).lower() != "missing" else "missing"
    if re.search(r"No social copy in the frontmatter yet", md): verdict = {p: "missing" for p in PLAT}
    copy = {}
    sec = md.split("### Suggested copy", 1)
    if len(sec) == 2:
        body = sec[1].split("### Suggestions (advisory)")[0]
        for p in PLAT:
            m = re.search(rf"\*\*{p}\*\*[^\n]*\n((?:>.*\n?)+)", body)
            if m:
                copy[p] = "\n".join(re.sub(r"^> ?", "", l) for l in m.group(1).rstrip("\n").split("\n"))
    return verdict, copy


rows = collections.defaultdict(list)
for arm in ARMS:
    for rd in sorted(glob.glob(os.path.join(S, "out", arm, "r[1-9]", "*"))):
        fx = os.path.basename(rd); exp = MAN[fx]["expected"]
        r = {"fx": fx, "rep": rd.split("/")[-2]}
        try:
            res = json.load(open(os.path.join(rd, "result.json")))
        except Exception:
            r["crash"] = True; rows[arm].append(r); continue
        r["usd"], r["usd_by_model"] = cost(res.get("modelUsage", {}))
        r["reported_usd"] = res.get("total_cost_usd"); r["turns"] = res.get("num_turns")
        r["subagents"] = (res.get("subagent_stats") or {}).get("spawned", 0)
        r["wall_s"] = int(open(os.path.join(rd, "wall_s")).read().strip() or 0)
        r["is_error"] = res.get("is_error")
        mdp = os.path.join(rd, ".social-review.md")
        md = open(mdp).read() if os.path.exists(mdp) else ""
        r["written"] = md.startswith("<!-- social-review -->")
        r["advisory_eligible"] = any(exp[p] == "PASS" for p in PLAT)
        r["advisory"] = "### Suggestions (advisory)" in md
        v, copy = parse(md)
        r["correct"] = sum(v.get(p) == exp[p] for p in PLAT)
        r["false_fail"] = sum(exp[p] == "PASS" and v.get(p) == "FAIL" for p in PLAT)
        r["missed_fail"] = sum(exp[p] == "FAIL" and v.get(p) == "PASS" for p in PLAT)
        r["unparsed"] = sum(p not in v for p in PLAT)
        need = [p for p in PLAT if exp[p] in ("FAIL", "missing")]
        r["repairs_needed"] = len(need)
        r["repairs_present"] = sum(p in copy for p in need)
        r["repairs_valid"] = sum(p in copy and not hard_fail(p, copy[p]) for p in need)
        r["repair_errors"] = {p: hard_fail(p, copy[p]) for p in need if p in copy and hard_fail(p, copy[p])}
        rows[arm].append(r)

summary = {}
for arm, rs in rows.items():
    ok = [r for r in rs if not r.get("crash")]
    n = len(ok); sm = lambda k: sum(r.get(k, 0) or 0 for r in ok)
    summary[arm] = {"runs": len(rs), "crashes": len(rs) - n, "written": sum(r["written"] for r in ok),
                    "verdict_acc": f"{sm('correct')}/{3 * n}", "false_fail": sm("false_fail"), "missed_fail": sm("missed_fail"),
                    "unparsed": sm("unparsed"), "repairs_valid": f"{sm('repairs_valid')}/{sm('repairs_needed')}",
                    "repairs_present": f"{sm('repairs_present')}/{sm('repairs_needed')}",
                    "usd_per_run": round(sm("usd") / max(1, n), 4), "reported_usd_per_run": round(sm("reported_usd") / max(1, n), 4),
                    "wall_s_per_run": round(sm("wall_s") / max(1, n), 1), "turns_per_run": round(sm("turns") / max(1, n), 1),
                    "runs_with_subagent": sum(1 for r in ok if r["subagents"]),
                    "advisory": f"{sum(1 for r in ok if r['advisory'] and r['advisory_eligible'])}/{sum(1 for r in ok if r['advisory_eligible'])}", "subagents_total": sm("subagents"),
                    "repair_errors": [(r["fx"], r["rep"], r["repair_errors"]) for r in ok if r["repair_errors"]],
                    "misses": [(r["fx"], r["rep"]) for r in ok if r["missed_fail"] or r["false_fail"] or r["unparsed"]]}
json.dump({"summary": summary, "rows": rows}, open(os.path.join(S, "out/summary.json"), "w"), indent=1)
for a, s in summary.items():
    print(a, {k: v for k, v in s.items() if k not in ("repair_errors", "misses")})
    if s["misses"]: print("   misses:", s["misses"])
    if s["repair_errors"]: print("   repair errors:", s["repair_errors"])
