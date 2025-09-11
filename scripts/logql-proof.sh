#!/usr/bin/env bash
set -euo pipefail

# Config
LOKI_URL="${LOKI_URL:-http://127.0.0.1:3100}"
OUT_DIR="tmp"
RATE_JSON="$OUT_DIR/loki_rate.json"
LINES_JSON="$OUT_DIR/loki_lines.json"

mkdir -p "$OUT_DIR"

echo "==> Checking Loki readiness at: $LOKI_URL/ready"
code_and_size=$(curl -s -o "$OUT_DIR/ready.out" -w "%{http_code} %{size_download}\n" "$LOKI_URL/ready" || true)
echo "    /ready -> $code_and_size"
if ! echo "$code_and_size" | grep -q "^200 "; then
  echo "ERROR: Loki not ready (did you start: kubectl -n logging port-forward svc/loki 3100:3100 ?)"
  exit 1
fi

echo
echo "==> Query A: ERROR rate by pod (5m) -> $RATE_JSON"
curl -s --get "$LOKI_URL/loki/api/v1/query" \
  --data-urlencode 'query=sum by (pod) (rate({namespace="default"} |= "ERROR" [5m]))' \
  -o "$RATE_JSON"

echo "==> Summary (pod=rate /s)"
python - <<'PY'
import json, sys
p="tmp/loki_rate.json"
txt=open(p,"r",encoding="utf-8").read().strip()
if not txt:
    print("(empty response)"); sys.exit(0)
try:
    data=json.loads(txt).get("data",{}).get("result",[])
except Exception as e:
    print("RAW(first 200):", txt[:200], "..."); raise
if not data:
    print("(no results)"); sys.exit(0)
for r in data:
    pod=r.get("metric",{}).get("pod","")
    val=(r.get("value") or ["","0"])[1]
    print(f"{pod}={val} /s")
PY

echo
echo "==> Query B: Raw ERROR lines (limit 120) -> $LINES_JSON"
curl -s --get "$LOKI_URL/loki/api/v1/query_range" \
  --data-urlencode 'query={namespace="default"} |= "ERROR"' \
  --data 'limit=120' \
  -o "$LINES_JSON"

echo "==> First 20 ERROR lines"
python - <<'PY'
import json
res=json.load(open("tmp/loki_lines.json","r",encoding="utf-8")).get("data",{}).get("result",[])
n=0
for s in res:
    for _, line in s.get("values",[]):
        print(line); n+=1
        if n>=20: raise SystemExit
if n==0: print("(no lines)")
PY

echo
echo "==> Files saved:"
ls -lh "$RATE_JSON" "$LINES_JSON" | sed 's/^/    /'
echo "Done."
