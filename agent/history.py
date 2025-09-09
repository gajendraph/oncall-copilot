import os, json
from datetime import datetime
def _ts(): return datetime.utcnow().strftime("%Y%m%d-%H%M%S")
def save_signatures(namespace, signatures, out_dir="out/signatures"):
    os.makedirs(out_dir, exist_ok=True)
    payload={"namespace":namespace,"signatures":signatures}
    open(os.path.join(out_dir,"latest.json"),"w",encoding="utf-8").write(json.dumps(payload,indent=2))
    snap=os.path.join(out_dir,f"{_ts()}-{namespace}.json")
    open(snap,"w",encoding="utf-8").write(json.dumps(payload,indent=2))
    return snap
def load_latest(out_dir="out/signatures"):
    p=os.path.join(out_dir,"latest.json")
    if not os.path.exists(p): return {"namespace":"","signatures":[]}
    try: return json.load(open(p,"r",encoding="utf-8"))
    except Exception: return {"namespace":"","signatures":[]}
def diff_signatures(prev, curr):
    p={s["message"]:s["count"] for s in prev}; c={s["message"]:s["count"] for s in curr}
    new=[{"message":m,"count":c[m]} for m in c.keys() if m not in p][:5]
    rising=[{"message":m,"prev":p[m],"now":c[m]} for m in c.keys() if m in p and c[m]>p[m]]
    rising.sort(key=lambda x:(x["now"]-x["prev"]), reverse=True)
    return {"new":new[:5],"rising":rising[:5]}
