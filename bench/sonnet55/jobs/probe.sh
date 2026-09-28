#!/usr/bin/env bash
# Probe: which request shapes Sonnet 5.5 accepts, plus usage counters.
mkdir -p bench/sonnet55/out/probe
python3 - <<'PY'
import json, os, urllib.request, urllib.error
key=os.environ["ANTHROPIC_API_KEY"]
def call(body):
    req=urllib.request.Request("https://api.anthropic.com/v1/messages",data=json.dumps(body).encode(),headers={"x-api-key":key,"anthropic-version":"2023-06-01","content-type":"application/json"})
    try:
        with urllib.request.urlopen(req,timeout=120) as r: d=json.loads(r.read()); return {"ok":True,"stop":d.get("stop_reason"),"usage":d.get("usage"),"types":[b.get("type") for b in d.get("content",[])]}
    except urllib.error.HTTPError as e: return {"ok":False,"code":e.code,"err":e.read().decode()[:400]}
tool={"name":"t","description":"record answer","input_schema":{"type":"object","properties":{"a":{"type":"string"}},"required":["a"],"additionalProperties":False},"strict":True}
base={"model":"claude-sonnet-5-5","max_tokens":2048,"messages":[{"role":"user","content":"What is 17*23? Answer via the t tool."}],"tools":[tool]}
cases={
 "disabled":{**base,"thinking":{"type":"disabled"}},
 "between_tools":{**base,"thinking":{"type":"between_tools"}},
 "between_tools_low":{**base,"thinking":{"type":"between_tools"},"output_config":{"effort":"low"}},
 "adaptive_low":{**base,"thinking":{"type":"adaptive"},"output_config":{"effort":"low"}},
 "adaptive_high":{**base,"thinking":{"type":"adaptive"},"output_config":{"effort":"high"}},
 "forced_tool":{**base,"thinking":{"type":"between_tools"},"tool_choice":{"type":"tool","name":"t"}},
 "auto_tool":{**base,"thinking":{"type":"between_tools"},"tool_choice":{"type":"auto"}},
 "s5_control":{**base,"model":"claude-sonnet-5","thinking":{"type":"disabled"},"tool_choice":{"type":"tool","name":"t"}},
}
out={k:call(v) for k,v in cases.items()}
print(json.dumps(out,indent=1))
json.dump(out,open("bench/sonnet55/out/probe/probe.json","w"),indent=1)
PY
