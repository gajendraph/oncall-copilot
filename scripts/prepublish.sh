#!/usr/bin/env bash
set -euo pipefail

RED=$'\e[31m'; GRN=$'\e[32m'; YLW=$'\e[33m'; NC=$'\e[0m'
FAIL=0
OUT_DIR="tmp/prepublish"
mkdir -p "$OUT_DIR"

say() { printf "%s\n" "$*"; }
ok()  { printf "${GRN}✔ %s${NC}\n" "$*"; }
warn(){ printf "${YLW}! %s${NC}\n" "$*"; }
bad() { printf "${RED}✖ %s${NC}\n" "$*"; FAIL=1; }

say "==> Pre-publish checks (secrets, scanners, ignore rules)"

# 0) Basic repo sanity
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || { bad "Not inside a git repo"; exit 1; }
BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")
say "   Branch: $BRANCH"

# 1) Grep for obvious secrets
say "==> Grep patterns (quick heuristic)"
PATTERN='token|password|secret|webhook|apikey|bearer|Authorization|BEGIN PRIVATE KEY|AKIA|hooks\.slack\.com'
grep -RIn --binary-files=without-match -E "$PATTERN" . \
  | grep -vE '\.git/|tmp/|out/|node_modules/|venv/|__pycache__/' \
  > "$OUT_DIR/grep_findings.txt" || true

if [[ -s "$OUT_DIR/grep_findings.txt" ]]; then
  bad "Potential secrets found (see $OUT_DIR/grep_findings.txt)"; head -n 12 "$OUT_DIR/grep_findings.txt"
else
  ok "No obvious secrets via grep"
fi

# 2) Gitleaks (via Docker if available)
say "==> Gitleaks scan"
if command -v docker >/dev/null 2>&1; then
  docker run --rm -v "$PWD:/repo" zricethezav/gitleaks:latest detect --source=/repo --redact \
    --report-format=json --report-path=/repo/"$OUT_DIR/gitleaks.json" >/dev/null 2>&1 || true
  if grep -q '"leaks":\s*\[' "$OUT_DIR/gitleaks.json" && ! grep -q '"leaks":\s*\[\s*\]' "$OUT_DIR/gitleaks.json"; then
    bad "Gitleaks found issues (see $OUT_DIR/gitleaks.json)"
  else
    ok "Gitleaks clean (or not installed)"
  fi
else
  warn "Docker not found; skipping gitleaks container scan"
fi

# 3) Trufflehog (optional, if installed)
say "==> Trufflehog (optional)"
if command -v trufflehog >/dev/null 2>&1; then
  trufflehog filesystem --no-update --json . > "$OUT_DIR/trufflehog.json" || true
  if [[ -s "$OUT_DIR/trufflehog.json" ]]; then
    bad "Trufflehog emitted findings (see $OUT_DIR/trufflehog.json)"
  else
    ok "Trufflehog emitted no findings"
  fi
else
  warn "trufflehog not installed; skipping"
fi

# 4) Check tracked files for stuff that should be ignored
say "==> .gitignore hygiene"
cat > "$OUT_DIR/_should_ignore.txt" <<EOF
out/
tmp/
.env
*.secret.yaml
.kube/
**/*.kubeconfig
*.log
EOF

TRACKED_ISSUES=0
while read -r path; do
  [[ -z "$path" ]] && continue
  if git ls-files --error-unmatch $path >/dev/null 2>&1; then
    say "   tracked: $path"
    TRACKED_ISSUES=$((TRACKED_ISSUES+1))
  fi
done < "$OUT_DIR/_should_ignore.txt"

if (( TRACKED_ISSUES > 0 )); then
  bad "Files that should be ignored appear tracked (see list above). Add to .gitignore and untrack."
else
  ok ".gitignore looks sane (based on default set)"
fi

# 5) Direct Slack URL check
say "==> Slack webhooks"
if grep -RIn "https://hooks.slack.com/services/" . | grep -vE '\.git/|tmp/|out/' > "$OUT_DIR/slack_urls.txt"; then
  bad "Slack webhook URL(s) present in repo (see $OUT_DIR/slack_urls.txt) — remove & rotate."
else
  ok "No Slack webhook URLs found in tracked files"
fi

# 6) Exit code
echo
if (( FAIL == 0 )); then
  ok "Pre-publish checks PASSED"
  say "   You can safely share the repo link. Still sanitize screenshots (blur tokens/URLs)."
  exit 0
else
  bad "Pre-publish checks FAILED"
  cat <<'TIP'
Next steps:
  1) Open the referenced files and remove/redact secrets (use env vars instead).
  2) If a real secret was ever committed, ROTATE it (Slack/Webhooks, API keys, etc).
  3) Purge from git history (e.g., git filter-repo) before pushing:
     python -m pip install git-filter-repo
     git filter-repo --path .env --invert-paths
     git filter-repo --replace-text <(echo 'regex:https://hooks\.slack\.com/services/[^ ]+=***REDACTED***')
     git push --force
TIP
  exit 1
fi
