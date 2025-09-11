#!/usr/bin/env bash
set -euo pipefail

cmd="${1:-help}"

# Defaults (override via env)
NS="${NS:-default}"
PROM_URL="${PROM_URL:-http://127.0.0.1:9090}"
LOKI_URL="${LOKI_URL:-http://127.0.0.1:3100}"
SLACK_WEBHOOK="${SLACK_WEBHOOK:-}"
BURST_LOGS="${BURST_LOGS:-false}"
CONFIRM="${CONFIRM:-false}"
REMEDIATION_ACTION="${REMEDIATION_ACTION:-rollout-restart}"
REMEDIATION_TARGET="${REMEDIATION_TARGET:-demo}"

case "$cmd" in
  cluster)
    kind delete cluster --name oncall-sandbox >/dev/null 2>&1 || true
    kind create cluster --name oncall-sandbox --image kindest/node:v1.29.2
    ;;

  monitoring)
    helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
    helm repo update
    mkdir -p deploy
    printf "grafana:\n  adminPassword: \"admin\"\n" > deploy/values-kps.yaml
    helm upgrade --install mon prometheus-community/kube-prometheus-stack \
      -n monitoring --create-namespace -f deploy/values-kps.yaml --wait
    ;;

  logging)
    kubectl apply -f deploy/loki-min.yaml
    helm repo add grafana https://grafana.github.io/helm-charts
    helm repo update
    helm upgrade --install promtail grafana/promtail \
      -n logging --create-namespace \
      --set config.clients[0].url="${LOKI_URL}/loki/api/v1/push"
    ;;

  workloads)
    kubectl apply -f deploy/workloads.yaml
    ;;

  pf-prom)
    kubectl -n monitoring port-forward svc/mon-kube-prometheus-stack-prometheus 9090:9090
    ;;

  pf-loki)
    kubectl -n logging port-forward svc/loki 3100:3100
    ;;

  agent)
    export PYTHONPATH="$PWD"
    python -m agent.run --namespace "$NS" --window-minutes 5 --output out/agent-report.md
    ;;

  score)
    PROM_URL="$PROM_URL" LOKI_URL="$LOKI_URL" NS="$NS" \
      python scripts/incident_score.py | tee out/incident-score.md
    ;;

  demo)
    # End-to-end: (optional) burst logs -> agent -> score -> Slack -> optional remediation
    BURST_LOGS="$BURST_LOGS" \
    PROM_URL="$PROM_URL" LOKI_URL="$LOKI_URL" NS="$NS" \
    SLACK_WEBHOOK="$SLACK_WEBHOOK" \
    CONFIRM="$CONFIRM" REMEDIATION_ACTION="$REMEDIATION_ACTION" \
    REMEDIATION_TARGET="$REMEDIATION_TARGET" \
      ./scripts/one_command_demo.sh
    ;;

  help|*)
    cat <<EOF
Usage: ./scripts/dev.sh <target>

Targets:
  cluster      create kind cluster (oncall-sandbox)
  monitoring   install kube-prometheus-stack (Prom/Grafana) in 'monitoring'
  logging      apply Loki + install Promtail in 'logging'
  workloads    deploy demo + crashy/noisy-crashy
  pf-prom      port-forward Prometheus (9090)
  pf-loki      port-forward Loki (3100)
  agent        run agent -> out/agent-report.md
  score        compute incident score -> out/incident-score.md
  demo         end-to-end demo (burst→agent→score→Slack→optional remediation)

Env vars:
  NS, PROM_URL, LOKI_URL, SLACK_WEBHOOK, BURST_LOGS, CONFIRM,
  REMEDIATION_ACTION (rollout-restart|restart-pod|bump-probe),
  REMEDIATION_TARGET
EOF
    ;;
esac
