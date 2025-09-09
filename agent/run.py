import os
from datetime import datetime
from copilot.tools.prom import instant as promq
from copilot.tools.k8s import pods, events, worst_pod, logs
from copilot.tools.loki import top_errors_by_pod, sample_error_signatures
from agent.history import load_latest, save_signatures, diff_signatures
from agent.runbooks import suggest as suggest_runbooks

SLO_TARGET = float(os.getenv("SLO_TARGET", "0.995"))
PERIOD_MIN = 43200  # 30d

def burn_rate(err_rate, win, slo=SLO_TARGET, period=PERIOD_MIN):
    allowed = (1.0 - slo) * (win / period)
    return (err_rate / allowed) if allowed > 0 else 0.0

def gather(namespace="default", window_min=5):
    # Prometheus (error % + burn)
    err_q = f'(sum(rate(apiserver_request_total{{code=~"5.."}}[{window_min}m])) or on() vector(0))'
    tot_q = f'clamp_min(sum(rate(apiserver_request_total[{window_min}m])), 1e-12)'
    e = promq(err_q); t = promq(tot_q)
    err_rate = (e / t) if t > 0 else 0.0
    br = burn_rate(err_rate, window_min)

    # K8s (crash/backoff)
    pjson = pods(namespace); crashies = []
    for it in pjson.get("items", []):
        name = it.get("metadata", {}).get("name", "")
        st = it.get("status", {})
        rest = sum(int(c.get("restartCount", 0)) for c in st.get("containerStatuses", []) or [])
        reasons = [(c.get("state", {}).get("waiting", {}) or {}).get("reason", "")
                   for c in st.get("containerStatuses", []) or []]
        if "CrashLoopBackOff" in ",".join(reasons) or rest >= 5:
            crashies.append({"pod": name, "restarts": rest, "reasons": [r for r in reasons if r]})

    # K8s Warning events
    ev = events(namespace); reasons = {}
    for it in ev.get("items", []):
        if it.get("type", "") != "Warning":
            continue
        r = it.get("reason", "Unknown")
        reasons[r] = reasons.get(r, 0) + int(it.get("count", 1))
    top_warn = sorted(reasons.items(), key=lambda x: x[1], reverse=True)[:5]

    # Loki (spikes + signatures)
    by_pod = top_errors_by_pod(namespace, window_min)
    sigs = sample_error_signatures(namespace, window_min, limit=10)

    # History (diff new/rising)
    prev = load_latest().get("signatures", [])
    delta = diff_signatures(prev, sigs)
    save_signatures(namespace, sigs)

    # Runbook suggestions
    rb_suggestions = suggest_runbooks(sigs, index_path="runbooks/index.yaml")

    # Worst pod tail
    worst = worst_pod(namespace)
    log_tail = logs(worst, namespace, tail=120) if worst else ""

    return {
        "ts": datetime.utcnow().isoformat() + "Z",
        "namespace": namespace,
        "window_min": window_min,
        "slo_target": SLO_TARGET,
        "error_rate": err_rate,
        "burn_rate": br,
        "crashy_pods": crashies,
        "top_warning_events": top_warn,
        "loki_error_rate_by_pod": by_pod,
        "loki_top_error_signatures": sigs,
        "delta": delta,
        "runbooks": rb_suggestions,
        "worst_pod": worst,
        "worst_logs_tail": log_tail[-2000:] if log_tail else ""
    }

def classify(br):
    if br < 1: return "OK"
    if br < 2: return "Burning"
    if br < 6: return "Fast burn"
    return "Page"

def render(r):
    lvl = classify(r["burn_rate"]); ns = r["namespace"]; win = r["window_min"]
    tl = f"{lvl} — burn={r['burn_rate']:.2f}x over {win}m, err_rate={r['error_rate']:.3%}, ns={ns}"

    find = [f"SLO burn: {r['burn_rate']:.2f}x → {lvl}"]
    for c in r["crashy_pods"][:5]:
        find.append(f"Crash/backoff: {c['pod']} restarts={c['restarts']} reasons={','.join(c['reasons']) or '-'}")

    if r["top_warning_events"]:
        find.append("Recent Warning events: " +
                    ", ".join([f"{x}×{n}" for x, n in r["top_warning_events"]]))

    if r["loki_error_rate_by_pod"]:
        top = ", ".join([f"{x['pod']}={x['rate']:.3f}/s"
                         for x in r["loki_error_rate_by_pod"][:3]])
        find.append(f"Log spikes (ERROR rate {win}m): {top}" if top else "No ERROR spikes")

    if r["loki_top_error_signatures"]:
        sigs = "; ".join([f"“{s['message'][:70]}”×{s['count']}"
                          for s in r["loki_top_error_signatures"][:5]])
        find.append(f"Top error signatures: {sigs}")

    if r["delta"].get("new"):
        find.append("New signatures: " +
                    "; ".join([f"“{s['message'][:60]}”×{s['count']}"
                               for s in r["delta"]["new"]]))

    if r["delta"].get("rising"):
        find.append("Rising signatures: " +
                    "; ".join([f"“{s['message'][:60]}” {s['prev']}→{s['now']}"
                               for s in r["delta"]["rising"]]))

    next_checks = [
        f'LogQL (ERROR {win}m): sum by(pod) (rate({{namespace="{ns}"}} |= "ERROR" [{win}m]))',
        'LogQL (Exception): {namespace="<ns>"} |= "Exception"',
        f'PromQL (err % {win}m): 100 * (sum(rate(apiserver_request_total{{code=~"5.."}}[{win}m])) or on() vector(0)) / clamp_min(sum(rate(apiserver_request_total[{win}m])), 1e-12)',
        'kubectl describe pod <pod>',
        'kubectl logs <pod> --previous --tail=200'
    ]

    status = (
        f"TL;DR: {lvl} burn over {win}m in namespace {ns}. Error rate is {r['error_rate']:.2%}. " +
        ("Some workloads show error spikes or crashloops; investigating logs and events. "
         if (r['loki_error_rate_by_pod'] or r['crashy_pods']) else
         "No major log spikes or crashloops observed. ") +
        "Next update in 30 minutes or sooner if status changes."
    )

    md = [f"# On-Call Copilot — Agent Report ({r['ts']})\n",
          f"**TL;DR**: {tl}\n",
          "## Findings"]
    md += [f"- {x}" for x in find]

    if r["runbooks"]:
        md.append("\n## Suggested runbooks")
        for s in r["runbooks"]:
            md.append(f"- **{s['runbook']}** — {s.get('summary','')}")

    md.append("\n## Next checks")
    md += [f"- {x}" for x in next_checks]

    if r["worst_logs_tail"]:
        md.append("\n## Logs (tail) — worst pod\n```")
        md.append(r["worst_logs_tail"])
        md.append("```")

    md.append("\n## Stakeholder update (draft)\n" + status)
    return "\n".join(md)

def main(namespace="default", window_min=5, outfile="out/agent-report.md"):
    os.makedirs(os.path.dirname(outfile), exist_ok=True)
    text = render(gather(namespace, window_min))
    with open(outfile, "w", encoding="utf-8") as f:
        f.write(text)
    print(text)
    print(f"\n[Saved] {outfile}")

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--namespace", default="default")
    ap.add_argument("--window-minutes", type=int, default=5)
    ap.add_argument("--output", default="out/agent-report.md")
    a = ap.parse_args()
    main(namespace=a.namespace, window_min=a.window_minutes, outfile=a.output)
