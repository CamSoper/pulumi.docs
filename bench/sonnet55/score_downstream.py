#!/usr/bin/env python3
"""Score the downstream chain per extractor arm on the 7 GT fixtures.
For each of 24 human-fixed defects, a blind judge (claude-fable-5-1, medium) reads the VERIFIED claims and decides
whether the chain FLAGGED it (a claim covering the defect got contradicted/mismatch/framing-drift) or RAISED it
(covered, verdict unverifiable), else MISSED. Also: merged claims fed to the verifier and verification $."""
import collections, json, os, re, time, urllib.request
from pathlib import Path
B = Path(__file__).resolve().parent; O = B / "out/downstream"; KEY = os.environ.get("ANTHROPIC_API_KEY", "")
GT = json.load(open(B / "fixtures/extract-ground-truth.json"))["extract"]
FLAG = {"contradicted", "mismatch", "framing-drift"}
SYS = """You are grading whether a documentation fact-checking pipeline surfaced known defects.
Known defects (each was later fixed by the page's human author):
{defects}

You will get the pipeline's verified claims: id, claim text, verdict, and a short evidence excerpt.
For each defect decide:
 - "flagged": some claim asserts the specific defective fact AND its verdict is contradicted, mismatch or framing-drift
   with evidence that points at the actual problem;
 - "raised": some claim covers the defective fact but the verdict is unverifiable (a human would be asked to check);
 - "missed": no claim covers it, or covering claims were marked verified / not-a-claim / matches.
Return ONLY JSON: {{"defects": {{"<id>": {{"outcome": "flagged|raised|missed", "claim_ids": ["..."], "why": "<=15 words"}}}}}}"""


def call(system, user):
    body = {"model": "claude-fable-5-1", "max_tokens": 16000, "output_config": {"effort": "medium"},
            "system": [{"type": "text", "text": system}], "messages": [{"role": "user", "content": user}]}
    for att in range(5):
        try:
            req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=json.dumps(body).encode(),
                                         headers={"x-api-key": KEY, "anthropic-version": "2023-06-01", "content-type": "application/json"})
            d = json.loads(urllib.request.urlopen(req, timeout=600).read())
            txt = "".join(b.get("text", "") for b in d["content"] if b.get("type") == "text")
            return json.loads(re.search(r"\{.*\}", txt, re.S).group(0))
        except Exception:
            time.sleep(5 * (att + 1))
    return None


out = {}
for armdir in sorted(p for p in O.iterdir() if p.is_dir() and not p.name.startswith("_")):
    arm = armdir.name; agg = collections.Counter(); usage = collections.Counter(); walls = []; per_rep = collections.defaultdict(collections.Counter)
    for fxdir in sorted(armdir.glob("r*/*")):
        rep, fx = fxdir.parts[-2], fxdir.name
        vp, mp = fxdir / "verified.json", fxdir / "merged.json"
        if not vp.exists(): continue
        v = json.load(open(vp)); m = json.load(open(mp)) if mp.exists() else {}
        agg["merged_claims"] += len(m.get("claims") or []); agg["stances"] += len(m.get("stances") or [])
        agg["verdicts"] += len(v.get("verdicts") or []); agg["verify_errors"] += len(v.get("errors") or [])
        meta = v.get("meta") or {}
        usage.update({k: meta.get(k, 0) for k in ("input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")})
        if (fxdir / "wall_s").exists(): walls.append(int((fxdir / "wall_s").read_text().strip() or 0))
        jp = fxdir / "judge.json"
        if not jp.exists() and KEY:
            vv = [{"id": f"V{i+1}", "text": x.get("text"), "verdict": x.get("verdict"), "evidence": (x.get("evidence") or "")[:300]} for i, x in enumerate(v.get("verdicts") or [])]
            res = call(SYS.format(defects="\n".join(f"- {d['id']}: {d['defect']}" for d in GT[fx])), "Verified claims (JSON):\n" + json.dumps(vv, ensure_ascii=False))
            if res: jp.write_text(json.dumps(res, indent=1))
        if jp.exists():
            j = json.load(open(jp))
            for d in GT[fx]:
                oc = ((j.get("defects") or {}).get(d["id"]) or {}).get("outcome", "missed")
                agg[oc] += 1; per_rep[rep][oc] += 1
    usd = (usage["input_tokens"] * 4 + usage["output_tokens"] * 20 + usage["cache_read_input_tokens"] * 0.2 + usage["cache_creation_input_tokens"] * 5) / 1e6
    n = len(per_rep) or 1
    out[arm] = {"reps": len(per_rep), "flagged": agg["flagged"], "raised": agg["raised"], "missed": agg["missed"], "of": 24 * len(per_rep),
                "flagged_per_rep": {r: c["flagged"] for r, c in per_rep.items()},
                "merged_claims_per_rep": round(agg["merged_claims"] / n, 1), "stances_per_rep": round(agg["stances"] / n, 1),
                "verify_usd_per_rep": round(usd / n, 3), "verify_usage": dict(usage), "verify_errors": agg["verify_errors"],
                "wall_s_per_fixture": round(sum(walls) / max(1, len(walls)), 1)}
json.dump(out, open(O / "summary.json", "w"), indent=1)
for a, s in out.items():
    print(f"{a:<8} flagged {s['flagged']}/{s['of']} raised {s['raised']} missed {s['missed']} | claims/rep {s['merged_claims_per_rep']} | verify $/rep {s['verify_usd_per_rep']} | {s['flagged_per_rep']}")
