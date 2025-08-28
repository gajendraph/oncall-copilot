import os, re, glob

RUNBOOK_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "runbooks")

def keyword_search(query: str, k: int = 3) -> list[dict]:
    q = query.lower()
    hits = []
    for path in glob.glob(os.path.join(RUNBOOK_DIR, "*.md")):
        try:
            with open(path, "r", encoding="utf-8") as f:
                text = f.read()
            score = sum(text.lower().count(token) for token in re.findall(r'\w+', q))
            if score > 0:
                snippet = _first_snippet(text, q, 260)
                hits.append({"path": os.path.basename(path), "score": score, "snippet": snippet})
        except Exception:
            continue
    hits.sort(key=lambda x: x["score"], reverse=True)
    return hits[:k]

def _first_snippet(text: str, q: str, size: int) -> str:
    if not q.strip():
        return text[:size] + ("..." if len(text) > size else "")
    import re as _re
    tokens = _re.findall(r'\w+', q)
    token = tokens[0] if tokens else ""
    idx = text.lower().find(token.lower()) if token else -1
    if idx == -1:
        return text[:size] + ("..." if len(text) > size else "")
    start = max(0, idx - size//2)
    end = min(len(text), idx + size//2)
    return text[start:end] + ("..." if end < len(text) else "")
