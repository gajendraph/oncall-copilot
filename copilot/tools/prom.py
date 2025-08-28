import requests

def instant(query: str, base_url: str = "http://localhost:9090") -> float:
    url = f"{base_url}/api/v1/query"
    r = requests.get(url, params={"query": query}, timeout=5)
    r.raise_for_status()
    data = r.json()
    if data.get("status") != "success":
        return 0.0
    res = data.get("data", {}).get("result", [])
    if not res:
        return 0.0
    try:
        return float(res[0]["value"][1])
    except Exception:
        return 0.0
