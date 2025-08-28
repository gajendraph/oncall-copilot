# OOMKilled / Memory Pressure — Triage
## Symptoms
- Exit code 137, "OOMKilled"
- Node/pod memory pressure warnings
## Checks
1) kubectl describe pod <pod>  # look for OOMKilled
2) kubectl top pod <pod>  # if metrics-server is present
3) Compare memory requests/limits vs usage
## Remediation
- Increase limits or tune GC; add requests; check HPA scaling rules
