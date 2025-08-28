# Payments Timeout / Redis Refused — Triage
## Symptoms
- Repeated `ERROR: payments timeout` and `Exception: redis connection refused`
## Checks
1) kubectl describe pod <pod>
2) kubectl get ep payments
3) kubectl exec -it <pod> -- sh -c "nc -vz redis 6379 || true"
## Remediation
- Scale payments, verify svc name, check Redis readiness/PVC
