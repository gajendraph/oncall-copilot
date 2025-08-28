from copilot.tools.logs import tail_pod_logs, extract_errors
from copilot.tools.runbooks import keyword_search
from copilot.tools.kubectl_safe import run as k
import re

def _warnings_from_describe(pod: str, namespace: str|None):
    d = k("describe","pod", pod, namespace=namespace)
    text = (d.get("text") or d.get("error") or "")
    return re.findall(r"(?im)^\\s*Warning\\s+\\w+.*$", text)

def triage(pod: str, namespace: str | None = None, lines: int = 500) -> dict:
    logs = tail_pod_logs(pod, namespace, lines)
    errors = extract_errors(logs.get("text","")) if logs.get("ok") else []
    warn_lines = _warnings_from_describe(pod, namespace)
    pieces = [e["message"] for e in errors] + warn_lines
    query = " ".join(pieces) or "warning unhealthy readiness probe failed liveness http probe"
    runbook_hits = keyword_search(query)
    return {"logs": logs, "top_errors": errors, "warnings": warn_lines[:8], "runbooks": runbook_hits}
