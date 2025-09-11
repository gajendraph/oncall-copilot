import os, subprocess, requests, statistics, json
from datetime import datetime, timezone

PROM = os.getenv("PROM_URL", "http://127.0.0.1:9090")
LOKI = os.getenv("LOKI_URL", "http://127.0.0.1:3100")
NS   = os.getenv("NS", "default")

def prom(q: str) -> float:
    r = requests.get(f"{PROM}/api/v1/query", params={"query": q}, timeout=8)
    r.raise_for_status()
    d = r.json().get("data", {}).get("result", [])
    if not d:
        return 0.0
    v = d[0].get("value", ["", "0"])[1]
    try:
        return float(v)
    except Exception:
        return 0.0

def loki_rate() -> dict:
    q = f'sum by (pod) (rate({{namespace="{NS}"}} |= "ERROR" [5m]))'
    r = requests.get(f"{LOKI}/loki/api/v1/query", params={"query": q}, timeout=8)
    r.raise_for_status()
    res = r.json().get("data", {}).get("result", [])
    out = {}
    for s in res:
        pod = s.get("metric", {}).get("pod", "")
        val = s.get("value", ["", "0"])[1]
        try:
            out[pod] = float(val)
        except Exception:
            out[pod] = 0.0
    return out

def restarts() -> dict:
    j = subprocess.check_output(["kubectl", "-n", NS, "get", "pods", "-o", "json"], text=True)
    data = json.loads(j).get("items", [])
    m = {}
    for it in data:
        pod = it.get("metadata", {}).get("name", "")
        st  = (it.get("status", {}).get("containerStatuses") or [{}])[0]
        m[pod] = int(st.get("restartCount", 0) or 0)
    return m

def zscores(x: dict) -> dict:
    vals = [v for v in x.values() if v is not None]
    if len(vals) < 2:
        return {k: 0.0 for k in x}
    mu = statistics.mean(vals)
    sd = statistics.pstdev(vals) or 1.0
    return {k: (v - mu) / sd for k, v in x.items()}

# Inputs
err_pct = 100 * prom('(sum(rate(apiserver_request_total{code=~"5.."}[5m])) or on() vector(0)) / clamp_min(sum(rate(apiserver_request_total[5m])), 1e-12)')
rates   = loki_rate()
rests   = restarts()
zr      = zscores(rates)
zc      = zscores(rests)

# Score: 50% err%, 30% (max z of ERROR rate), 20% (max z of restarts)
score = min(100.0, max(0.0,
    0.5 * err_pct +
    0.3 * (max(zr.values() or [0.0]) * 20) +
    0.2 * (max(zc.values() or [0.0]) * 20)
))

# Top pods by combined “noisiness”
pods_sorted = sorted(
    set(list(rates) + list(rests)),
    key=lambda p: (rates.get(p, 0.0), rests.get(p, 0)),
    reverse=True
)[:5]

ts = datetime.now(timezone.utc).isoformat()

print(f"# Incident score report — {ts}")
print(f"Namespace: {NS}")
print(f"Incident score: {score:.1f}/100")
print(f"- Prometheus error% (5m): {err_pct:.3f}%")
if rates:
    tops = ", ".join([f"{p}={rates[p]:.3f}/s" for p in pods_sorted if p in rates])
    print(f"- Top ERROR rate (5m): {tops}")
if rests:
    tops = ", ".join([f"{p}={rests[p]}" for p in pods_sorted if p in rests])
    print(f"- Restart counts: {tops}")
