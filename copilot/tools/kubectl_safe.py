import subprocess, shlex, re, time

ALLOWED = {
  "get": ["pods", "nodes", "events", "deployments", "services", "ingress", "replicasets"],
  "describe": ["pod", "node", "deployment", "service"]
}

REDACT_PATTERNS = [
    (r'(?i)(password|passwd|pwd)\s*[:=]\s*\S+', r'\1=REDACTED'),
    (r'(?i)(api[_-]?key|token|secret|authorization)\s*[:=]\s*\S+', r'\1=REDACTED'),
    (r'(?i)Bearer\s+[A-Za-z0-9._\-]+', 'Bearer REDACTED'),
]

def _redact(s: str) -> str:
    for pat, repl in REDACT_PATTERNS:
        s = re.sub(pat, repl, s)
    return s

def run(action: str, kind: str, name: str | None = None, namespace: str | None = None,
        output: str | None = None, extra_args: list[str] | None = None) -> dict:
    if action not in ALLOWED or kind not in ALLOWED[action]:
        return {"ok": False, "error": "Not allowed", "action": action, "kind": kind}
    parts = ["kubectl", action, kind]
    if name: parts.append(name)
    if namespace: parts += ["-n", namespace]
    if action == "get" and kind in ["pods", "nodes"] and not output:
        parts += ["-o", "wide"]
    if output: parts += ["-o", output]
    if extra_args: parts += list(extra_args)
    started = time.time()
    try:
        out = subprocess.check_output(parts, stderr=subprocess.STDOUT, timeout=10)
        text = _redact(out.decode(errors="ignore"))
        return {"ok": True, "cmd": " ".join(shlex.quote(p) for p in parts),
                "ms": int((time.time()-started)*1000), "text": text}
    except subprocess.CalledProcessError as e:
        return {"ok": False, "cmd": " ".join(parts), "ms": int((time.time()-started)*1000),
                "error": e.output.decode(errors="ignore")}
    except FileNotFoundError:
        return {"ok": False, "cmd": " ".join(parts), "ms": int((time.time()-started)*1000),
                "error": "kubectl not found in PATH (stub environment)."}
