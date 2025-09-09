# Runbook: CrashLoopBackOff
- kubectl logs <pod> --previous --tail=200
- kubectl describe pod <pod> (probe failures? OOMKilled?)
- Consider +10s initialDelaySeconds; rollback if needed.
