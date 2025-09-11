#!/usr/bin/env bash
set -euo pipefail

# --- Config (override via env) ---
NS="${NS:-default}"
PROM_URL="${PROM_URL:-http://127.0.0.1:9090}"
LOKI_URL="${LOKI_URL:-http://127.0.0.1:3100}"
SLACK_WEBHOOK="${SLACK_WEBHOOK:-https://hooks.slack.com/services/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}"     # Incoming Webhook URL
CONFIRM="${CONFIRM:-false}"            # true to allow remediation
REMEDIATION_ACTION="${REMEDIATION_ACTION:-rollout-restart}"  # restart-pod|rollout-restart|bump-probe
REMEDIATION_TARGET="${REMEDIATION_TARGET:-demo}"             # pod or deployment name
RO_CONTEXT="${RO_CONTEXT:-oncall-copilot}"
ADMIN_CONTEXT="${ADMIN_CONTEXT:-kind-oncall-sandbox}"
BURST_LOGS="${BURST_LOGS:-false}"      # true -> generate short ERROR burst for screenshots
BURST_POD="${BURST_POD:-noisy-proof}"  # name of the short-lived burst pod
BURST_LINES="${BURST_LINES:-30}"       # how many lines to emit
SAVE_LOGQL="${SAVE_LOGQL:-true}"       # save LogQL proofs to tmp/

# --- Paths ---
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PYTHONPATH="$REPO_ROOT"
OUT_DIR="$REPO_ROOT/out"
TMP_DIR="$REPO_ROOT/tmp"
mkdir -p "$OUT_DIR" "$TMP_DIR"

stamp() { date -u +"%Y-%m-%dT%H-%M-%SZ"; }
T="$(stamp)"

echo "==> Namespace=$NS | Confirm=$CONFIRM | RO=$RO_CONTEXT | ADMIN=$ADMIN_CONTEXT"
command -v kubectl >/dev/null || { echo "ERROR: kubectl not found"; exit 1; }
command -v python  >/dev/null || { echo "ERROR: python not found"; exit 1; }

# --- 0) Best-effort readiness checks (PFs should already be running) ---
curl -s -o /dev/null -w "Prometheus /-/ready -> %{http_code}\n"  "$PROM_URL/-/ready" || true
curl -s -o /dev/null -w "Loki /ready        -> %{http_code}\n"  "$LOKI_URL/ready" || true

# --- 1) (Optional) generate a brief ERROR burst so LogQL has fresh data ---
if [[ "$BURST_LOGS" == "true" ]]; then
  echo "==> BURST_LOGS=true: emitting ${BURST_LINES} ERROR lines via $BURST_POD (admin context)"
  kubectl config use-context "$ADMIN_CONTEXT" >/dev/null
  kubectl -n "$NS" delete pod "$BURST_POD" --ignore-not-found
  kubectl -n "$NS" run "$BURST_POD" --image=busybox --restart=Never --command -- \
    sh -c "i=0; while [ \$i -lt ${BURST_LINES} ]; do echo \"ERROR: proof demo id=\$i\"; i=\$((i+1)); sleep 1; done" >/dev/null
  echo "   (Letting logs stream for ~5s...)"
  sleep 5
fi

# --- 2) Save LogQL proofs (optional but great for screenshots) ---
if [[ "$SAVE_LOGQL" == "true" ]]; then
  echo "==> Gathering LogQL proofs into tmp/"
  curl -s --get "$LOKI_URL/loki/api/v1/query" \
    --data-urlencode "query=sum by (pod) (rate({namespace=\"$NS\"} |= \"ERROR\" [5m]))" \
    -o "$TMP_DIR/loki_rate.json" || true

  curl -s --get "$LOKI_URL/loki/api/v1/query_range" \
    --data-urlencode "query={namespace=\"$NS\"} |= \"ERROR\"" \
    --data "limit=120" \
    -o "$TMP_DIR/loki_lines.json" || true
fi

# --- 3) Switch to RO context and run the agent ---
echo "==> Running agent in RO context: $RO_CONTEXT"
kubectl config use-context "$RO_CONTEXT" >/dev/null
AGENT_OUT="$OUT_DIR/agent-report-$T.md"
python -m agent.run --namespace "$NS" --window-minutes 5 --output "$AGENT_OUT" || echo "WARN: agent.run failed"

# --- 4) Compute incident score (Prom + Loki + restarts) ---
echo "==> Computing incident score"
SCORE_OUT="$OUT_DIR/incident-score-$T.md"
PROM_URL="$PROM_URL" LOKI_URL="$LOKI_URL" NS="$NS" \
  python "$REPO_ROOT/scripts/incident_score.py" | tee "$SCORE_OUT" || echo "WARN: incident_score failed"

# --- 5) Post Stakeholder update to Slack (if configured) ---
if [[ -n "$SLACK_WEBHOOK" ]]; then
  echo "==> Posting Stakeholder update to Slack"
  SLACK_WEBHOOK="$SLACK_WEBHOOK" python "$REPO_ROOT/scripts/notify_slack.py" "$AGENT_OUT" || echo "WARN: Slack post failed"
else
  echo "==> SLACK_WEBHOOK not set — skipping Slack notification"
fi

# --- 6) Optional remediation (admin only, explicit confirm) ---
if [[ "$CONFIRM" == "true" ]]; then
  echo "==> CONFIRM=true: switching to admin for remediation"
  kubectl config use-context "$ADMIN_CONTEXT" >/dev/null
  echo "==> Remediation: $REMEDIATION_ACTION $REMEDIATION_TARGET (ns=$NS)"
  NAMESPACE="$NS" CONFIRM=true "$REPO_ROOT/scripts/remediate.sh" "$REMEDIATION_ACTION" "$REMEDIATION_TARGET" || echo "WARN: remediation failed"
else
  echo "==> Dry-run mode (no cluster mutations). To execute: CONFIRM=true ..."
fi

echo
echo "==> Artifacts:"
echo "    $AGENT_OUT"
echo "    $SCORE_OUT"
if [[ "$SAVE_LOGQL" == "true" ]]; then
  ls -lh "$TMP_DIR"/loki_*.json 2>/dev/null || true
fi
echo "Done."
