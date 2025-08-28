import json

def compare(canary_ok:int, canary_total:int, base_ok:int, base_total:int,
            canary_p95_ms:float, base_p95_ms:float, max_latency_regress_pct: float = 5.0) -> dict:
    if min(canary_total, base_total) <= 0 or base_p95_ms <= 0:
        return {"error":"invalid inputs"}
    sr_canary = canary_ok / canary_total
    sr_base   = base_ok / base_total
    success_delta_pct = (sr_canary - sr_base) * 100.0
    p95_increase_pct  = ((canary_p95_ms - base_p95_ms) / base_p95_ms) * 100.0
    recommendation = "Continue"
    if success_delta_pct < 0 or p95_increase_pct > max_latency_regress_pct:
        recommendation = "Hold canary"
    return {"success_delta_pct": success_delta_pct, "p95_increase_pct": p95_increase_pct,
            "recommendation": recommendation}

def gate(co:int, ct:int, bo:int, bt:int, cp95:float, bp95:float,
         policy:dict, cp99:float|None=None, bp99:float|None=None) -> dict:
    # basic validation
    if min(ct, bt) <= 0 or bp95 <= 0:
        return {"error":"invalid inputs"}
    sr_c = co/ct; sr_b = bo/bt
    err_delta_pct = (sr_c - sr_b)*100.0
    p95_regress   = ((cp95 - bp95)/bp95)*100.0
    p99_regress   = None
    if cp99 is not None and bp99 not in (None, 0):
        p99_regress = ((cp99 - bp99)/bp99)*100.0

    reasons = []
    decision = "Continue"

    min_total = int(policy.get("min_total_per_arm", 0))
    if ct < min_total or bt < min_total:
        reasons.append(f"insufficient sample (canary {ct}, base {bt}, need = {min_total})")

    thresh_delta = float(policy.get("min_success_delta_pct", -1.0))  # e.g., -1.0 means allow 1% worse
    if err_delta_pct < thresh_delta:
        reasons.append(f"success delta {err_delta_pct:.2f}% < {thresh_delta:.2f}%")

    max_p95 = float(policy.get("max_p95_regress_pct", 5.0))
    if p95_regress > max_p95:
        reasons.append(f"p95 regression {p95_regress:.2f}% > {max_p95:.2f}%")

    max_p99 = policy.get("max_p99_regress_pct")
    if max_p99 is not None and p99_regress is not None and p99_regress > float(max_p99):
        reasons.append(f"p99 regression {p99_regress:.2f}% > {float(max_p99):.2f}%")

    if reasons:
        decision = "Hold canary"

    out = {
        "canary_success": sr_c, "base_success": sr_b,
        "success_delta_pct": err_delta_pct,
        "p95_regress_pct": p95_regress,
        "p99_regress_pct": p99_regress,
        "decision": decision, "reasons": reasons
    }
    return out

def load_policy(path:str)->dict:
    with open(path,"r",encoding="utf-8") as f:
        return json.load(f)
