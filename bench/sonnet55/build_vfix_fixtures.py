"""Plant surgical validator violations into three real (clean) pinned review bodies.
Ground truth = the original body, so scoring is a byte diff. One fix-me JSON per
(body, rule) because validator-fix batches one call per rule_id."""
import json, re, sys, pathlib
SRC = pathlib.Path(sys.argv[1]); OUT = pathlib.Path(sys.argv[2])
BODIES = {"b239": "control-pr239/pinned.md", "b240": "change-pr240/pinned.md", "b241": "final-pr241/pinned.md"}
LEGACY = {"✅": "🟢", "➖": "⚪", "🤷": "⚠️", "❌": "🚨", "⚔️": "🚨", "🌀": "⚠️"}
BADWORD = {"verified": "confirmed", "contradicted": "refuted", "unverifiable": "unconfirmed", "not-a-claim": "no-claim",
           "mismatch": "mismatched", "framing-drift": "drifted"}
TRAIL = re.compile(r"^(- (L[\d\-–]+) in .*?→ )(✅|🤝|➖|🤷|❌|⚔️|🌀) ([a-z-]+)(.*)$")
BUCKET = re.compile(r"^- \*\*\[(L[\d\-–]+)\]\*\* (.*)$")
for bid, rel in BODIES.items():
    orig = (SRC / rel).read_text()
    lines = orig.split("\n")
    trail_idx = [i for i, l in enumerate(lines) if TRAIL.match(l)]
    bucket_idx = [i for i, l in enumerate(lines) if BUCKET.match(l)]
    # Only bucket-bullet-line-range-prefix reaches the model lane in production: splicer.py
    # applies the trail-emoji / verdict-word rules deterministically and defers this one.
    # Three batch sizes per body: 1 violation, 3, and every bucket bullet.
    plans = {"n1": bucket_idx[1:2], "n3": bucket_idx[:3], "all": bucket_idx}
    for size, idxs in plans.items():
        rule = "bucket-bullet-line-range-prefix"
        pl = list(lines); viol = []
        for i in idxs:
            if rule == "trail-per-verdict-emoji":
                m = TRAIL.match(pl[i]); pre, ref, emo, word, rest = m.groups()
                pl[i] = f"{pre}{LEGACY[emo]} {word}{rest}"
                viol.append({"rule_id": rule, "line_ref": ref,
                             "expected": f"trail line for {ref} renders `{emo}` for verdict `{word}`",
                             "actual": f"renders `{LEGACY[emo]}` (legacy bucket emoji)",
                             "hint": f"use the per-verdict glyph `{emo}` for `{word}`"})
            elif rule == "trail-canonical-verdict-word":
                m = TRAIL.match(pl[i]); pre, ref, emo, word, rest = m.groups()
                pl[i] = f"{pre}{emo} {BADWORD[word]}{rest}"
                viol.append({"rule_id": rule, "line_ref": ref,
                             "expected": "one of the canonical verdict words",
                             "actual": f"token `{BADWORD[word]}` after `{emo}`",
                             "hint": f"use `{word}` (the canonical word for {emo})"})
            else:
                m = BUCKET.match(pl[i]); ref, rest = m.groups()
                pl[i] = f"- {rest}"
                viol.append({"rule_id": rule, "line_ref": ref, "expected": "bullet starts with `- **[L<range>]**`",
                             "actual": f"- {rest[:120]}", "hint": f"trail anchor for this bullet is `{ref}`"})
        name = f"{bid}.{size}"
        (OUT / f"{name}.planted.md").write_text("\n".join(pl))
        (OUT / f"{name}.expected.md").write_text(orig)
        (OUT / f"{name}.fixme.json").write_text(json.dumps({"violations": viol}, ensure_ascii=False, indent=1))
        print(name, len(viol), "planted; changed lines", sum(a != b for a, b in zip(pl, lines)))
