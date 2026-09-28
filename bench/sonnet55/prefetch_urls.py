"""Pre-fetch every URL in the verifier corpus ONCE with the shipping fetcher, so
all cells route and read identical pass-2 evidence."""
import importlib.util, json, sys
spec = importlib.util.spec_from_file_location("euf", ".claude/commands/docs-review/scripts/extract-urls-and-fetch.py")
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
claims = json.load(open(sys.argv[1]))["claims"]
lines = [f"{c.get('text','')} {c.get('source_hint','')}" for c in claims]
urls = sorted(set(m.extract_urls(lines)))
print(len(urls), "urls")
out = [m.fetch_one(u) for u in urls]
json.dump(sorted(out, key=lambda r: r["url"]), open(sys.argv[2], "w"), indent=1)
