import sys
# usage: python scripts/canary_gate.py <canary_err%> <base_err%> <canary_p95_ms> <base_p95_ms>
c_err=float(sys.argv[1]); b_err=float(sys.argv[2]); c_p95=float(sys.argv[3]); b_p95=float(sys.argv[4])
err_rel = (c_err - b_err) / max(b_err, 0.1)   # avoid div0
lat_rel = (c_p95 - b_p95) / max(b_p95, 1.0)
score = 0.6*err_rel + 0.4*lat_rel
decision = "HOLD" if (c_err>0.5 or c_p95> b_p95*1.25 or score>0.3) else "CONTINUE"
print(f"canary_err%={c_err:.2f} base_err%={b_err:.2f} canary_p95={c_p95:.0f} base_p95={b_p95:.0f} -> {decision} (score={score:.2f})")
