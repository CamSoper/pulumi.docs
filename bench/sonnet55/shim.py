#!/usr/bin/env python3
"""Run a SHIPPING docs-review script unmodified, rewriting its Messages API
requests in flight. One axis per arm, applied at the wire, so every lane runs
the exact code that ships and only the knobs under test move.

    python3 shim.py <script.py> [script args...]

Env knobs (unset = leave the shipped request untouched):
  BENCH_MODEL        model id
  BENCH_THINKING     adaptive | between_tools | disabled | omit
  BENCH_EFFORT       low | medium | high | xhigh | max | none (none = drop output_config.effort)
  BENCH_MAXTOK       int; floor for max_tokens (never lowers the shipped value)
  BENCH_TOOLCHOICE   auto  -> rewrite forced tool_choice {type: tool|any} to auto
  BENCH_TIMEOUT      seconds; floor for the urlopen timeout
  BENCH_STATS        path; per-call wire stats written here at exit
"""
import atexit
import io
import json
import os
import runpy
import sys
import threading
import time
import urllib.error
import urllib.request

_real_urlopen = urllib.request.urlopen
_lock = threading.Lock()
STATS = {"calls": 0, "http_errors": {}, "stop_reasons": {}, "refusals": [], "no_tool_use_when_tools": 0,
         "usage": {"input_tokens": 0, "output_tokens": 0, "cache_read_input_tokens": 0,
                   "cache_creation_input_tokens": 0, "thinking_tokens": 0},
         "rewrites": {}, "per_call": []}


def _bump(d, k, n=1):
    d[k] = d.get(k, 0) + n


def _rewrite(body: dict) -> dict:
    env = os.environ
    rw = {}
    if env.get("BENCH_MODEL"):
        body["model"] = env["BENCH_MODEL"]; rw["model"] = body["model"]
    th = env.get("BENCH_THINKING")
    if th == "omit":
        body.pop("thinking", None); rw["thinking"] = "omit"
    elif th:
        body["thinking"] = {"type": th}; rw["thinking"] = th
    ef = env.get("BENCH_EFFORT")
    if ef == "none":
        oc = body.get("output_config") or {}
        oc.pop("effort", None)
        if oc: body["output_config"] = oc
        else: body.pop("output_config", None)
        rw["effort"] = "none"
    elif ef:
        body["output_config"] = {**(body.get("output_config") or {}), "effort": ef}; rw["effort"] = ef
    if env.get("BENCH_MAXTOK"):
        floor = int(env["BENCH_MAXTOK"])
        if int(body.get("max_tokens", 0)) < floor:
            body["max_tokens"] = floor; rw["max_tokens"] = floor
    if env.get("BENCH_TOOLCHOICE") == "auto":
        tc = body.get("tool_choice") or {}
        if tc.get("type") in ("tool", "any"):
            body["tool_choice"] = {"type": "auto"}; rw["tool_choice"] = "auto"
    return rw


class _Resp(io.BytesIO):
    def __init__(self, data, status):
        super().__init__(data); self.status = status
    def getcode(self): return self.status
    def __enter__(self): return self
    def __exit__(self, *a): self.close(); return False


def _urlopen(req, data=None, timeout=None, *a, **kw):
    url = req.full_url if isinstance(req, urllib.request.Request) else str(req)
    if "api.anthropic.com" not in url or not isinstance(req, urllib.request.Request) or req.data is None:
        return _real_urlopen(req, data, timeout, *a, **kw) if timeout is not None else _real_urlopen(req, data, *a, **kw)
    body = json.loads(req.data)
    rw = _rewrite(body)
    new = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST",
                                 headers={k: v for k, v in req.header_items()})
    if os.environ.get("BENCH_TIMEOUT"):
        timeout = max(float(timeout or 0), float(os.environ["BENCH_TIMEOUT"]))
    t0 = time.time()
    try:
        with _real_urlopen(new, timeout=timeout) as r:
            raw = r.read(); status = r.status
    except urllib.error.HTTPError as e:
        with _lock:
            _bump(STATS["http_errors"], str(e.code))
            if e.code == 400:
                try:
                    msg = e.read().decode()[:300]
                except Exception:  # noqa: BLE001
                    msg = ""
                STATS.setdefault("http_400_samples", [])
                if len(STATS["http_400_samples"]) < 5:
                    STATS["http_400_samples"].append(msg)
                raise urllib.error.HTTPError(e.url, e.code, e.msg, e.hdrs, io.BytesIO(msg.encode()))
        raise
    d = json.loads(raw)
    with _lock:
        STATS["calls"] += 1
        for k, v in rw.items():
            STATS["rewrites"][k] = v
        sr = str(d.get("stop_reason"))
        _bump(STATS["stop_reasons"], sr)
        if sr == "refusal":
            STATS["refusals"].append(d.get("stop_details"))
        u = d.get("usage") or {}
        for k in STATS["usage"]:
            if isinstance(u.get(k), int):
                STATS["usage"][k] += u[k]
        th = int(((u.get("output_tokens_details") or {}).get("thinking_tokens")) or 0)
        STATS["usage"]["thinking_tokens"] += th
        types = [b.get("type") for b in d.get("content", []) or []]
        if body.get("tools") and "tool_use" not in types and sr != "max_tokens":
            STATS["no_tool_use_when_tools"] += 1
        STATS["per_call"].append({"stop": sr, "out": u.get("output_tokens"), "in": u.get("input_tokens"),
                                  "cr": u.get("cache_read_input_tokens"), "cw": u.get("cache_creation_input_tokens"),
                                  "think": th, "s": round(time.time() - t0, 1), "types": types})
    return _Resp(raw, status)


urllib.request.urlopen = _urlopen


def _dump():
    p = os.environ.get("BENCH_STATS")
    if p:
        os.makedirs(os.path.dirname(p) or ".", exist_ok=True)
        with open(p, "w") as f:
            json.dump(STATS, f, indent=1)


atexit.register(_dump)

if __name__ == "__main__":
    script = sys.argv[1]
    sys.argv = [script] + sys.argv[2:]
    sys.path.insert(0, os.path.dirname(os.path.abspath(script)))
    try:
        runpy.run_path(script, run_name="__main__")
    except SystemExit as e:
        _dump()
        raise
