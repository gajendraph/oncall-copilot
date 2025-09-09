import re, yaml
def _load_index(path="runbooks/index.yaml"):
    try: return yaml.safe_load(open(path,"r",encoding="utf-8")) or {}
    except Exception: return {}
def suggest(signatures, index_path="runbooks/index.yaml", limit=3):
    idx=_load_index(index_path); rules=idx.get("rules",[]); msgs=[s["message"].lower() for s in signatures]
    out, seen=[], set()
    for r in rules:
        pat=r.get("pattern",""); rb=r.get("runbook",""); summ=r.get("summary","")
        if not pat or not rb: continue
        try: rx=re.compile(pat, re.I)
        except re.error: rx=None
        if any((rx.search(m) if rx else pat.lower() in m) for m in msgs):
            if rb not in seen: out.append({"runbook":rb,"summary":summ}); seen.add(rb)
        if len(out)>=limit: break
    return out
