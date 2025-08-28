import re

def heuristic(pods_get_text: str) -> list[dict]:
    # Very rough heuristic (placeholder): flag crash/backoff or many restarts
    suspects = []
    for line in pods_get_text.splitlines():
        if re.search(r'CrashLoopBackOff|ImagePullBackOff', line):
            suspects.append({"pod_line": line.strip(), "reason": "Crashing/backoff"})
        if re.search(r'\b([2-9][0-9])/?[0-9]* restarts\b', line, re.I):
            suspects.append({"pod_line": line.strip(), "reason": "High restarts"})
    return suspects[:10]
