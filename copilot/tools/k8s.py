import json, subprocess

def _run(args, ns=None):
    cmd = ["kubectl"] + args + (["-n", ns] if ns else [])
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        return p.returncode, p.stdout, p.stderr
    except Exception as e:
        return 1, "", str(e)

def get_json(kind, ns=None):
    code, out, err = _run(["get", kind, "-o", "json"], ns)
    if code != 0: return {}
    try: return json.loads(out)
    except: return {}

def pods(ns):
    return get_json("pods", ns)

def events(ns):
    return get_json("events", ns)

def worst_pod(ns):
    data = pods(ns)
    best = None
    for item in data.get("items", []):
        name = item.get("metadata", {}).get("name")
        st = item.get("status", {})
        restarts = sum(int(c.get("restartCount",0)) for c in st.get("containerStatuses",[]) or [])
        waiting = [(c.get("state",{}).get("waiting",{}) or {}).get("reason","") for c in st.get("containerStatuses",[]) or []]
        score = restarts + (5 if any("CrashLoopBackOff" in r for r in waiting) else 0)
        if best is None or score > best[2]:
            best = (name, st, score)
    return best[0] if best else None

def logs(pod, ns, tail=200, previous=False):
    if not pod: return ""
    args = ["logs", pod, "--tail", str(tail)]
    if previous: args.append("--previous")
    code, out, err = _run(args, ns)
    return out if code == 0 else ""
