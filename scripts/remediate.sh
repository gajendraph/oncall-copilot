#!/usr/bin/env bash
set -euo pipefail
NAMESPACE="${NAMESPACE:-default}"
ACTION="${1:-help}"
POD="${2:-}"
CONFIRM="${CONFIRM:-false}"

dry() { [ "$CONFIRM" = "true" ] || echo "[DRY-RUN] $*"; }
doit(){ [ "$CONFIRM" = "true" ] && eval "$*" || echo "[SKIP] $*"; }

case "$ACTION" in
  restart-pod)
    [ -n "$POD" ] || { echo "Usage: remediate.sh restart-pod <pod>"; exit 1; }
    dry kubectl -n "$NAMESPACE" delete pod "$POD"
    doit kubectl -n "$NAMESPACE" delete pod "$POD"
    ;;
  rollout-restart)
    DEP="${POD:?usage: remediate.sh rollout-restart <deployment>}"
    dry kubectl -n "$NAMESPACE" rollout restart deploy/"$DEP"
    doit kubectl -n "$NAMESPACE" rollout restart deploy/"$DEP"
    ;;
  bump-probe)
    POD="${POD:?usage: remediate.sh bump-probe <deployment>}"
    # +10s to initialDelaySeconds for demo
    patch='[{"op":"add","path":"/spec/template/spec/containers/0/readinessProbe/initialDelaySeconds","value":15}]'
    dry kubectl -n "$NAMESPACE" patch deploy "$POD" --type=json -p "$patch"
    doit kubectl -n "$NAMESPACE" patch deploy "$POD" --type=json -p "$patch"
    ;;
  *)
    echo "Actions: restart-pod <pod> | rollout-restart <deployment> | bump-probe <deployment>"; exit 1;;
esac
