def burn_rate(error_rate: float, slo_target: float = 0.995, window_minutes: int = 5, period_minutes: int = 43200) -> dict:
    if error_rate < 0: return {"error":"error_rate must be >= 0"}
    if not (0 < slo_target < 1): return {"error":"slo_target must be between 0 and 1"}
    if window_minutes <= 0 or period_minutes <= 0: return {"error":"window_minutes and period_minutes must be > 0"}
    epsilon = 1.0 - slo_target
    allowed = epsilon * (window_minutes / period_minutes)
    if allowed <= 0: return {"error":"invalid parameters produce zero budget in window"}
    br = error_rate / allowed
    if br < 1: level, rec = "OK","Within budget."
    elif br < 2: level, rec = "Burning","Watch; check recent changes."
    elif br < 6: level, rec = "Fast burn","Investigate now; consider halting experiments."
    else: level, rec = "Page","Page on-call; likely impact if sustained."
    return {"window_minutes":window_minutes,"period_minutes":period_minutes,"slo_target":slo_target,"error_rate":error_rate,
            "allowed_error_rate_window":allowed,"burn_rate":br,"level":level,"recommendation":rec}

def multi_window(error_rates: dict, slo_target: float = 0.995, period_minutes: int = 43200) -> dict:
    out, worst = {}, {"burn_rate": -1}
    for w,e in error_rates.items():
        r = burn_rate(e, slo_target, int(w), period_minutes); out[int(w)] = r
        if "burn_rate" in r and r["burn_rate"] > worst.get("burn_rate",-1): worst = r | {"window_minutes": int(w)}
    return {"windows": out, "worst": worst}
