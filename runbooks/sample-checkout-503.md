# Checkout 503 Runbook

## Symptoms
- Elevated 5xx (HTTP 503) on /checkout
- Spikes in upstream timeouts

## Quick Checks
1. `kubectl get pods -n checkout` — look for CrashLoopBackOff
2. Check readiness/liveness probe failures in pod describe
3. Confirm dependency: `payments` service reachable

## Remediation
- If failing probes: increase initialDelaySeconds by +10s and redeploy
- If timeouts to payments: verify service/endpoints, scale payments by +1

## Rollback
- If error budget is burning >1.0x over 15m, roll back the last deployment
