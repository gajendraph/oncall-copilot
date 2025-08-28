import subprocess, re

def tail_pod_logs(pod: str, namespace: str | None = None, lines: int = 500) -> dict:
    cmd = ["kubectl", "logs", pod, "--tail", str(lines)]
    if namespace: cmd += ["-n", namespace]
    try:
        out = subprocess.check_output(cmd, stderr=subprocess.STDOUT, timeout=10).decode()
        return {"ok": True, "text": out}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def extract_errors(text: str, top_k: int = 3) -> list[dict]:
    errs = re.findall(r'(?im)(?:error|exception|timeout|fail(?:ed)?)[:\s].*', text)
    counts = {}
    for line in errs:
        key = line.strip()[:160]
        counts[key] = counts.get(key, 0) + 1
    ranked = sorted(counts.items(), key=lambda x: x[1], reverse=True)[:top_k]
    return [{"message": k, "count": v} for k, v in ranked]
