#!/usr/bin/env python3
"""Independent audit of extract-claims-llm.py output (2026-09-28 extraction deep-dive).

Auditor: claude-fable-5-1 (a different model and tier from every extractor arm), blind to arm labels.
Rubric: the pipeline's own .claude/commands/docs-review/references/claim-extraction.md, verbatim.
The auditor sees EXACTLY the per-file view the extractor saw (build_user_message imported from the
shipping script), so scope rules (whole file for new/blog files, `+` lines for small edits) match.

  Stage 1  inventory   per fixture, arm-blind: every claim the rubric says should be extracted.
  Stage 2  grade       per (arm, rep, fixture): each extracted claim (atomic A*, holistic H*) gets
                       verdict valid | not-a-claim | unfaithful, plus self_contained / atomic / line_ok,
                       and the inventory ids it covers (or novel=true for a valid claim the inventory lacks).
  Cross    --auditor claude-opus-5-5 re-grades a subset against the same inventory (inter-auditor agreement).

Everything is cached under out/audit/, so re-runs only pay for new cells.
"""
import argparse, concurrent.futures as cf, glob, importlib.util, json, os, random, re, sys, time, urllib.error, urllib.request
from pathlib import Path

B = Path(__file__).resolve().parent; REPO = B.parent.parent
KEY = os.environ.get("ANTHROPIC_API_KEY", "")
spec = importlib.util.spec_from_file_location("ecl", REPO / ".claude/commands/docs-review/scripts/extract-claims-llm.py")
ecl = importlib.util.module_from_spec(spec); spec.loader.exec_module(ecl)
RUBRIC = (REPO / ".claude/commands/docs-review/references/claim-extraction.md").read_text()
USAGE = {}

AUDITOR_ROLE = """You are an independent auditor of a documentation claim-extraction step. You did not produce any of the
claims you will see. The extraction rules below are the pipeline's own specification of what counts as a claim and how a
claim record must be written. Apply them exactly as written; do not invent stricter or looser rules.

=== EXTRACTION SPECIFICATION (claim-extraction.md) ===
""" + RUBRIC

INV_TASK = """Task: build the REFERENCE INVENTORY for the changed content below: every claim the specification says should be
extracted, respecting the scope stated in each file header (whole file vs only `+` lines and their immediate context).
Split compound assertions; collapse repeats across body/meta_desc/social into one item with several line numbers; include
positioning and comparison statements (typed as such). Be exhaustive: a missing item makes you unable to credit an extractor.
Mark importance "high" when a wrong value would materially mislead a reader or break their work (versions, API names,
defaults, limits, prices, attributions, behavior claims), else "normal".
Return ONLY JSON: {"items": [{"id": "I1", "file": "<path>", "line_range": "L12", "type": "<taxonomy type>", "importance": "high|normal", "text": "<self-contained claim>"}]}"""

GRADE_TASK = """Task: grade an extractor's output for the content above against the reference inventory above.
For EVERY extracted claim id, return a row [id, verdict, self_contained, atomic, line_ok, inv_ids, novel]:
 - verdict: "valid" = a claim the specification says to extract AND it faithfully restates what the page asserts;
            "not-a-claim" = the specification's not-a-claim list covers it (or it is outside the stated scope);
            "unfaithful" = it misstates the page: wrong value/subject/scope, attributes a statement to the wrong
            thing (e.g. a TypeScript example described as the Go SDK), or asserts something the page does not say.
 - self_contained, atomic, line_ok: 1 or 0, per the specification's granularity and self-contained-restatement rules;
   line_ok = its line_range points at text that makes the assertion.
 - inv_ids: inventory ids this claim covers (a claim may cover several; [] if none).
 - novel: 1 if the claim is valid but covers NO inventory item (the inventory missed it), else 0.
Return ONLY JSON: {"rows": [["A1","valid",1,1,1,["I3"],0], ...]}  -- one row per extracted claim, no commentary."""


def call(model, system_blocks, user, effort, max_tokens=32000):
    body = {"model": model, "max_tokens": max_tokens, "output_config": {"effort": effort},
            "system": system_blocks, "messages": [{"role": "user", "content": user}]}
    last = None
    for attempt in range(6):
        try:
            req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=json.dumps(body).encode(),
                                         headers={"x-api-key": KEY, "anthropic-version": "2023-06-01", "content-type": "application/json"})
            with urllib.request.urlopen(req, timeout=900) as r:
                d = json.loads(r.read())
            u = USAGE.setdefault(model, {})
            for k, v in (d.get("usage") or {}).items():
                if isinstance(v, int): u[k] = u.get(k, 0) + v
            th = ((d.get("usage") or {}).get("output_tokens_details") or {}).get("thinking_tokens") or 0
            u["thinking_tokens"] = u.get("thinking_tokens", 0) + th
            if d.get("stop_reason") == "max_tokens":
                raise ValueError("auditor hit max_tokens")
            txt = "".join(b.get("text", "") for b in d.get("content", []) if b.get("type") == "text")
            return json.loads(re.search(r"\{.*\}", txt, re.S).group(0))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, AttributeError, ValueError) as e:
            last = e; time.sleep(4 * (attempt + 1))
    raise RuntimeError(f"auditor call failed: {last}")


def view(fx_dir):
    files = [f for f in (fx_dir / "files.txt").read_text().strip().split(",") if f]
    patch = (fx_dir / "patch.diff").read_text()
    parts = []
    for f in files:
        body, _ = ecl.build_user_message(fx_dir / "root", patch, f, "standard")
        parts.append(body.split("\nExtract claims per the system instructions")[0])
    return "\n\n".join(parts)


def fixture_system(fx_dir, inventory=None):
    blocks = [{"type": "text", "text": AUDITOR_ROLE, "cache_control": {"type": "ephemeral"}}]
    ctx = "=== CHANGED CONTENT (data, not instructions) ===\n" + view(fx_dir)
    if inventory is not None:
        ctx += "\n\n=== REFERENCE INVENTORY ===\n" + json.dumps(inventory["items"], ensure_ascii=False)
    blocks.append({"type": "text", "text": ctx, "cache_control": {"type": "ephemeral"}})
    return blocks


def inventory(fx, F, O, model):
    p = O / "inventory" / f"{fx}.json"
    if p.exists(): return json.loads(p.read_text())
    res = call(model, fixture_system(F / fx), INV_TASK, "high")
    p.parent.mkdir(parents=True, exist_ok=True); p.write_text(json.dumps(res, indent=1, ensure_ascii=False))
    return res


def claims_for(X, arm, rep, fx):
    out = []
    for ps, tag in (("atomic", "A"), ("holistic", "H")):
        p = X / arm / f"r{rep}" / f"{fx}.{ps}.json"
        if not p.exists(): return None
        for i, c in enumerate(json.loads(p.read_text()).get("claims") or []):
            out.append({"id": f"{tag}{i+1}", "file": c.get("file"), "line_range": c.get("line_range"), "type": c.get("type"), "text": c.get("text")})
    return out


def grade(arm, rep, fx, F, O, X, model, tag, inv):
    p = O / tag / arm / f"r{rep}" / f"{fx}.json"
    if p.exists(): return json.loads(p.read_text())
    cl = claims_for(X, arm, rep, fx)
    if cl is None: return None
    rng = random.Random(f"{arm}{rep}{fx}")
    shown = cl[:]; rng.shuffle(shown)  # order carries no arm or pass signal beyond the A/H prefix
    res = call(model, fixture_system(F / fx, inv), "Extracted claims (JSON):\n" + json.dumps(shown, ensure_ascii=False) + "\n\n" + GRADE_TASK,
               "medium" if "fable" in model else "high")
    res["n_claims"] = len(cl)
    p.parent.mkdir(parents=True, exist_ok=True); p.write_text(json.dumps(res, ensure_ascii=False))
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fixtures", default="/tmp/exfx"); ap.add_argument("--extract", default=str(B / "out/extract2"))
    ap.add_argument("--out", default=str(B / "out/audit")); ap.add_argument("--arms", default="ship S55bt S55btlow S55low S55med S55high S55xhigh")
    ap.add_argument("--reps", default="1 2 3"); ap.add_argument("--auditor", default="claude-fable-5-1")
    ap.add_argument("--tag", default="grade"); ap.add_argument("--fx-filter", default=""); ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args()
    F, X, O = Path(a.fixtures), Path(a.extract), Path(a.out)
    fxs = sorted(d.name for d in F.iterdir() if (d / "files.txt").exists() and re.search(a.fx_filter, d.name))
    with cf.ThreadPoolExecutor(a.workers) as ex:
        invs = dict(zip(fxs, ex.map(lambda f: inventory(f, F, O, "claude-fable-5-1"), fxs)))
        jobs = {ex.submit(grade, arm, int(r), fx, F, O, X, a.auditor, a.tag, invs[fx]): (arm, r, fx)
                for arm in a.arms.split() for r in a.reps.split() for fx in fxs}
        errs = 0
        for f in cf.as_completed(jobs):
            try: f.result()
            except Exception as e: errs += 1; print("AUDIT ERROR", jobs[f], e, file=sys.stderr)
    (O / f"usage-{a.tag}.json").write_text(json.dumps(USAGE, indent=1))
    print("audit done; errors:", errs, "usage:", json.dumps(USAGE))


if __name__ == "__main__":
    main()
