# Runbook: Redis connection refused
- kubectl -n default get ep,svc | findstr /i redis
- kubectl -n default get netpol
- Check Redis readiness/liveness probes.
