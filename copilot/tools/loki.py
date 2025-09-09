import time, re, requests, os
from requests.exceptions import RequestException

def _now_ns(): return int(time.time()*1e9)

def _vector(q, base="http://localhost:3100"):
    try:
        r = requests.get(f"{base}/loki/api/v1/query", params={"query": q}, timeout=8)
        r.raise_for_status()
        return r.json().get("data", {}).get("result", [])
    except RequestException:
        return []

def _range(q, minutes, base="http://localhost:3100"):
    end=_now_ns(); start=end-minutes*60*1_000_000_000
    try:
        r = requests.get(f"{base}/loki/api/v1/query_range",
            params={"query": q, "start": start, "end": end, "limit": 2000, "direction": "backward"}, timeout=10)
        r.raise_for_status()
        return r.json().get("data", {}).get("result", [])
    except RequestException:
        return []

def top_errors_by_pod(namespace="default", minutes=5, base_url=None):
    base = base_url or os.getenv("LOKI_URL","http://localhost:3100")
    q = f'sum by (pod) (rate({{namespace="{namespace}"}} |= "ERROR" [{minutes}m]))'
    res = _vector(q, base); out=[]
    for s in res:
        try:
            out.append({"pod": s.get("metric",{}).get("pod",""),
                        "rate": float(s.get("value",[0,"0"])[1])})
        except Exception:
            pass
    return sorted(out, key=lambda x: x["rate"], reverse=True)[:10]

def sample_error_signatures(namespace="default", minutes=5, base_url=None, limit=5):
    base = base_url or os.getenv("LOKI_URL","http://localhost:3100")
    q = f'{{namespace="{namespace}"}} |= "ERROR"'
    res = _range(q, minutes, base); counts={}
    for stream in res:
        for _, line in stream.get("values", []):
            msg=line.strip()
            msg=re.sub(r'\\b[0-9a-fA-F-]{12,}\\b','<id>',msg)
            msg=re.sub(r'\\b\\d+\\b','<n>',msg)
            counts[msg]=counts.get(msg,0)+1
    top=sorted(counts.items(), key=lambda x:x[1], reverse=True)[:limit]
    return [{"message":m, "count":c} for m,c in top]
