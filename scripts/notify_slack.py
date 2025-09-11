import os, sys, json, requests, re
url = os.getenv("SLACK_WEBHOOK")
if not url: sys.exit("Set SLACK_WEBHOOK env var")
msg = "*On-Call Copilot update*"
if len(sys.argv) > 1 and os.path.exists(sys.argv[1]):
    t = open(sys.argv[1],"r",encoding="utf-8").read()
    # extract Stakeholder update section if present
    m = re.search(r"## Stakeholder update.*?\n([\s\S]+)", t)
    if m: msg = m.group(1).strip()
payload = {"text": msg}
r = requests.post(url, data=json.dumps(payload), headers={"Content-Type":"application/json"}, timeout=8)
print("Slack", r.status_code, r.text[:200])
