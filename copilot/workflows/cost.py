import json, re
from copilot.tools.kubectl_safe import run as k

def _j(txt:str):
    try: return json.loads(txt)
    except Exception: return {}

def _ratio(req:str|None, lim:str|None):
    # crude parser for cpu/mem strings like "50m", "500m", "64Mi", "512Mi"
    def to_num(x):
        if not x: return None
        s = str(x)
        if s.endswith("m"):   # cpu millicores
            return float(s[:-1]) / 1000.0
        if s.endswith("Mi"):  # mem Mi
            return float(s[:-2])
        if s.endswith("Gi"):
            return float(s[:-2]) * 1024.0
        try: return float(s)
        except: return None
    a = to_num(req); b = to_num(lim)
    if a and b and a > 0: return b / a
    return None

def scan(ns:str|None=None, skew_threshold:float=4.0, restart_threshold:int=5) -> dict:
    pods = k("get","pods",namespace=ns, output="json")
    if not pods.get("ok"): return {"ok": False, "error": pods.get("error","pods get failed")}
    data = _j(pods["text"])

    findings = []
    for item in data.get("items", []):
        name = item.get("metadata",{}).get("name","")
        phase = item.get("status",{}).get("phase","")
        cs = item.get("status",{}).get("containerStatuses",[]) or []
        spec_ctrs = (item.get("spec",{}) or {}).get("containers",[]) or []

        # Crash/backoff waste
        total_restarts = sum(int(c.get("restartCount",0)) for c in cs)
        waiting_reasons = [ (c.get("state",{}).get("waiting",{}) or {}).get("reason","") for c in cs ]
        if total_restarts >= restart_threshold or any("CrashLoopBackOff" in r for r in waiting_reasons):
            findings.append({
                "pod": name, "type": "crash/backoff",
                "detail": f"restarts={total_restarts}, reasons={','.join([r for r in waiting_reasons if r]) or '-'}",
                "action": "Inspect previous logs; check probes/images. Consider halting canary."
            })

        # Missing requests/limits & skew
        for c in spec_ctrs:
            cn = c.get("name","ctr")
            res = (c.get("resources") or {})
            req = (res.get("requests") or {})
            lim = (res.get("limits") or {})
            # CPU
            if "cpu" not in req or "cpu" not in lim or "memory" not in req or "memory" not in lim:
                findings.append({
                    "pod": name, "type": "unbounded",
                    "detail": f"container={cn} missing requests/limits",
                    "action": "Set cpu/memory requests & limits to protect cluster and control spend."
                })
            else:
                r_cpu, l_cpu = req.get("cpu"), lim.get("cpu")
                r_mem, l_mem = req.get("memory"), lim.get("memory")
                rc = _ratio(r_cpu, l_cpu); rm = _ratio(r_mem, l_mem)
                if (rc and rc >= skew_threshold) or (rm and rm >= skew_threshold):
                    findings.append({
                        "pod": name, "type": "skewed limits",
                        "detail": f"container={cn} ratio(cpu~{rc or '-'} mem~{rm or '-'}) = {skew_threshold}x",
                        "action": "Right-size: tighten limits or raise requests closer to observed needs."
                    })

        # Pending due to resources (FailedScheduling)
        if phase == "Pending":
            desc = k("describe","pod",name,namespace=ns)
            line = (desc.get("text") or "").splitlines()
            hit = next((L for L in line if re.search(r"FailedScheduling", L)), None)
            if hit:
                findings.append({
                    "pod": name, "type": "scheduling",
                    "detail": "FailedScheduling (possible resource/taint pressure)",
                    "action": "Check node resources/taints; adjust requests or cluster size."
                })

    return {"ok": True, "cmd": pods.get("cmd",""), "ms": pods.get("ms",0), "findings": findings}
