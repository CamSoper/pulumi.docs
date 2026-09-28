"""Social-review fixtures: real posts from pulumi/docs @ 8bd6efe with planted hard-rule breaks.
Expected verdicts follow critique-rubric.md's mechanical hard-fail rules."""
import json, os, re, shutil, sys, yaml
DOCS = sys.argv[1]; OUT = sys.argv[2]
P = lambda s: f"content/blog/{s}/index.md"
FIX = [
  ("clean-gittags", "trigger-deployments-on-git-tags", {}, {"X": "PASS", "LinkedIn": "PASS", "Bluesky": "PASS"}),
  ("clean-tfk8s", "terraform-kubernetes", {}, {"X": "PASS", "LinkedIn": "PASS", "Bluesky": "PASS"}),
  ("plant-hashtag-ivoice", "stop-tuning-prompts-build-a-harness",
     {"twitter": ("append", " #AIAgents"), "linkedin": ("prepend", "I have watched this happen on every team I have worked with. ")}, {"X": "FAIL", "LinkedIn": "FAIL", "Bluesky": "PASS"}),
  ("plant-overlen-url", "seven-rules-ai-native-software-factory",
     {"twitter": ("append", " Rule five is the one most teams skip, and it is the one that decides whether the factory keeps running."),
      "bluesky": ("append", " https://www.pulumi.com/blog/seven-rules-ai-native-software-factory/")},
     {"X": "FAIL", "LinkedIn": "PASS", "Bluesky": "FAIL"}),
  ("plant-md-banned-onepara", "sandboxing-coding-agents-yolo-mode",
     {"twitter": ("bold", None), "linkedin": ("prepend", "We're excited to announce a new guide. "), "bluesky": ("onepara", None)},
     {"X": "FAIL", "LinkedIn": "FAIL", "Bluesky": "FAIL"}),
  ("real-onepara-jev", "self-driving-infrastructure-pulumi-jev", {}, {"X": "FAIL", "LinkedIn": "PASS", "Bluesky": "FAIL"}),
  ("missing-bluesky", "rest-api-docs-from-openapi", {"bluesky": ("drop", None)}, {"X": "PASS", "LinkedIn": "PASS", "Bluesky": "missing"}),
]
NAME = {"twitter": ("X", 255), "linkedin": ("LinkedIn", 2950), "bluesky": ("Bluesky", 300)}
def mutate(v, op, arg):
    v = v.rstrip("\n")
    if op == "append": return v + arg
    if op == "prepend": return arg + v
    if op == "bold":
        w = v.split(" "); w[1] = f"**{w[1]}**"; return " ".join(w)
    if op == "onepara": return re.sub(r"\n\s*\n", " ", v)
    if op == "ivoice":
        v2 = re.sub(r"\bWe\b", "I", v, count=1); v2 = re.sub(r"\bwe\b", "I", v2, count=1)
        assert v2 != v, "no we to swap"; return v2
    raise ValueError(op)
man = []
for fid, slug, muts, exp in FIX:
    src = open(os.path.join(DOCS, P(slug))).read()
    _, fm, body = src.split("---", 2)
    d = yaml.safe_load(fm); soc = dict(d["social"])
    for k, (op, arg) in muts.items():
        if op == "drop": soc.pop(k, None)
        else: soc[k] = mutate(soc[k], op, arg)
    root = os.path.join(OUT, fid); os.makedirs(os.path.join(root, os.path.dirname(P(slug))), exist_ok=True)
    # rewrite only the social block in the original frontmatter text
    fm_lines = fm.split("\n"); i = fm_lines.index("social:"); j = i + 1
    while j < len(fm_lines) and (fm_lines[j].startswith(" ") or fm_lines[j] == ""): j += 1
    new_soc = "social:\n" + "".join(f"  {k}: |\n" + "".join(("    " + l if l else "") + "\n" for l in soc[k].rstrip("\n").split("\n")) for k in soc)
    fm2 = "\n".join(fm_lines[:i]) + "\n" + new_soc + "\n".join(fm_lines[j:])
    open(os.path.join(root, P(slug)), "w").write("---" + fm2 + "---" + body)
    chk = [f"== {P(slug)}", "status: not yet posted; publish date in the future", ""]
    for k in ("twitter", "linkedin", "bluesky"):
        nm, lim = NAME[k]
        if k not in soc: chk += [f"--- {nm}: NO social copy", ""]; continue
        t = soc[k].rstrip("\n")
        chk += [f"--- {nm} ({len(t)}/{lim} chars){' OVER LIMIT' if len(t) > lim else ''}:", t, ""]
    open(os.path.join(root, ".social-check-output.txt"), "w").write("\n".join(chk))
    shutil.copytree(os.path.join(DOCS, ".claude/commands/social-media-review"), os.path.join(root, ".claude/commands/social-media-review"), dirs_exist_ok=True)
    man.append({"id": fid, "post": P(slug), "expected": exp, "social": soc})
json.dump(man, open(os.path.join(OUT, "manifest.json"), "w"), indent=1, ensure_ascii=False)
print("\n".join(f"{m['id']}: {m['expected']}" for m in man))
