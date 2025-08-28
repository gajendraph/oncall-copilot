\# AI On‑Call Copilot — Architecture \& README Scaffold



A compact, one‑page architecture + a README skeleton to build an \*\*agentic on‑call copilot\*\* that detects anomalies in \*\*cluster health (metrics/events)\*\* and \*\*logs\*\*, then suggests next checks and drafts stakeholder updates.



---



\## Architecture (high level)



```mermaid

flowchart LR

&nbsp; %% Sources / Telemetry Plane

&nbsp; subgraph TP\[Telemetry Plane]

&nbsp;   P\[Prometheus

&nbsp;   (kube‑prometheus‑stack)]

&nbsp;   L\[Loki

&nbsp;   + Promtail]

&nbsp;   KS\[kube‑state‑metrics]

&nbsp;   EV\[Event Exporter

&nbsp;   (K8s events)]

&nbsp; end



&nbsp; %% Data access (read‑only tools)

&nbsp; subgraph DA\[Data Access Layer (read‑only)]

&nbsp;   PR\[PromQL client]

&nbsp;   LG\[LogQL client]

&nbsp;   K8\[Kubernetes API client

&nbsp;   (kubectl‑safe)]

&nbsp; end



&nbsp; %% Detection modules

&nbsp; subgraph DET\[Detection]

&nbsp;   BR\[SLO burn‑rate

&nbsp;   (multi‑window)]

&nbsp;   ST\[Stat anomalies

&nbsp;   (holt\_winters, predict\_linear)]

&nbsp;   LGAD\[Log spikes \& patterns

&nbsp;   (error ratios, new signatures)]

&nbsp;   EVS\[Event surges

&nbsp;   (CrashLoopBackOff,

&nbsp;   FailedScheduling)]

&nbsp;   CO\[Composite scoring \&

&nbsp;   correlation]

&nbsp; end



&nbsp; %% Reasoning / Agent

&nbsp; subgraph AG\[Reasoning Agent]

&nbsp;   OBS(Observe) --> ANA(Analyze) --> REC(Recommend)

&nbsp;   LLM\[LLM + rules

&nbsp;   + Runbook RAG]

&nbsp; end



&nbsp; %% Outputs

&nbsp; subgraph OUT\[Human Interfaces]

&nbsp;   CLI\[CLI (health, triage,

&nbsp;   slo‑prom, canary‑gate, cost)]

&nbsp;   CHAT\[Chat (Slack/Teams)]

&nbsp;   STAT\[Status draft for stakeholders]

&nbsp;   LINKS\[Deep links to Prom/Loki/Grafana]

&nbsp; end



&nbsp; %% Edges

&nbsp; P --> PR

&nbsp; KS --> PR

&nbsp; L --> LG

&nbsp; EV --> L

&nbsp; PR --> BR

&nbsp; PR --> ST

&nbsp; LG --> LGAD

&nbsp; K8 --> EVS

&nbsp; BR --> CO

&nbsp; ST --> CO

&nbsp; LGAD --> CO

&nbsp; EVS --> CO

&nbsp; CO --> LLM

&nbsp; LLM --> REC

&nbsp; REC --> OUT



&nbsp; %% Guardrails

&nbsp; classDef guard fill:#f6f6f6,stroke:#bbb,stroke-dasharray: 5 5;

&nbsp; class DA guard

```



> \*\*Security\*\*: least‑privilege RBAC; short‑lived tokens; redaction; read‑only by default.



---



\## README (scaffold)



\### 1) Overview



\*\*AI On‑Call Copilot\*\* observes Prometheus metrics, Kubernetes events, and logs (Loki/ELK) to detect anomalies, reason about likely causes, and recommend next checks—then drafts a concise stakeholder update. Actions are \*\*read‑only\*\* by default; any changes require a human in the loop.



\### 2) Key Components



\* \*\*Telemetry plane\*\*: Prometheus (or kube‑prometheus‑stack), kube‑state‑metrics, Loki + Promtail, Kubernetes Event Exporter.

\* \*\*Data access\*\*: tiny HTTP clients for PromQL/LogQL + a safe `kubectl` wrapper (list/describe/events only).

\* \*\*Detection\*\*: SLO burn (multi‑window), statistical PromQL (`holt\_winters`, `predict\_linear`), log spikes/new‑error patterns, event surges; composite scoring.

\* \*\*Reasoning Agent\*\*: rules + LLM with runbook retrieval (RAG) to propose next checks and draft updates.

\* \*\*Interfaces\*\*: CLI commands and/or chat bot; deep links to Grafana/Prometheus/Loki for evidence.



\### 3) Quickstart (local dev)



1\. \*\*Cluster\*\*: kind or Minikube.

2\. \*\*Metrics \& logs\*\*: install Prometheus \& Loki stack (Helm or minimal YAML). Port‑forward Prometheus to `localhost:9090`.

3\. \*\*CLI\*\*: run `health`, `triage`, `slo-prom`, `canary-gate`, `cost` to verify signals.

4\. \*\*Agent (optional)\*\*: run `agent-run --once` to print TL;DR, findings, next checks, status draft.



> Keep credentials out of repo; prefer short‑lived tokens and `.env` files.



\### 4) CLI (example commands)



\* `health --namespace default` → pods/nodes/events + \*\*Next checks\*\*

\* `triage --pod <name> --lines 300` → top errors + runbook suggestions

\* `slo-prom --err <PromQL> --tot <PromQL> --window-minutes 5 --slo-target 0.995` → live burn rate

\* `canary-gate --co … --ct … --bo … --bt … --cp95 … --bp95 …` → Continue/Hold with reasons

\* `cost --namespace <ns>` → crash/backoff waste, missing limits, skewed limits\\:requests, scheduling issues



\### 5) Configuration \& Policy



\* \*\*SLOs\*\*: target availability, windows (5/30/60m), burn thresholds.

\* \*\*Canary policy\*\*: min sample size, max p95/p99 regression, min success‑delta.

\* \*\*Runbooks\*\*: mapping (event/log signature → next checks \& rollback steps).

\* \*\*Ownership\*\*: namespace/app → team (for routing/escalation).



\### 6) Security \& Governance



\* RBAC: read‑only cluster roles; non‑resource `/metrics` access for apiserver scraping.

\* Token lifetime \& rotation; audit logs; PII redaction; retention/cost controls (log sampling, label cardinality limits).



\### 7) Extensibility



\* Detectors are plugins (metrics/logs/events/custom). Add cloud hooks (node autoscaler, load balancer health) or eBPF/system signals as needed.



\### 8) Repo Layout (suggested)



```

/cli.py                     # Typer CLI (health, triage, slo-prom, canary-gate, cost, agent-run)

/copilot/tools/             # prom.py (PromQL), log.py (LogQL), kubectl\_safe.py, slo.py, canary.py

/copilot/workflows/         # health.py, triage.py, cost.py, events.py, detect.py

/agent/                     # agent\_loop.py, runbook\_rag.py, policy/

/policies/                  # slo.json, canary\_policy.json, runbooks/

/docs/                      # architecture.md, queries/

```



\### 9) Minimal Agent Loop (pseudocode)



```python

sig = collect\_signals(prom, loki, k8s)

findings = detect(sig)            # burn, stats, logs, events → composite

report = reason(findings, runbooks)  # LLM + rules → TL;DR, next checks, status

emit(report, channels=\[cli, slack])

```



\### 10) Roadmap (examples)



\* Wire `canary-prom` (metrics‑driven canary vs baseline).

\* Add log new‑pattern detection + similarity search.

\* Confidence scoring + auto‑link evidence (saved queries, pod names, timestamps).

\* Optional: create tickets/slack threads; still require human approval for any change.



---



\*\*How to use this page\*\*: paste the Mermaid block into your repo’s README (GitHub renders it), and copy the sections above into your `README.md`. Replace placeholders with your actual commands/filenames as you implement.



---



\## Sample Helm `values.yaml`



> Copy these into your repo (e.g., `deploy/values-kps.yaml` and `deploy/values-loki.yaml`). They’re minimal but production‑shaped for local/dev.



\### A) kube‑prometheus‑stack (`values-kps.yaml`)



```yaml

grafana:

&nbsp; enabled: false  # enable if you want dashboards



kubeApiServer:

&nbsp; enabled: true   # ensure apiserver target is scraped



rbac:

&nbsp; create: true



prometheus:

&nbsp; service:

&nbsp;   type: ClusterIP

&nbsp; prometheusSpec:

&nbsp;   retention: 2d

&nbsp;   scrapeInterval: 15s

&nbsp;   evaluationInterval: 15s

&nbsp;   resources:

&nbsp;     requests:

&nbsp;       cpu: 100m

&nbsp;       memory: 256Mi

&nbsp;   ruleSelectorNilUsesHelmValues: false

&nbsp;   serviceMonitorSelectorNilUsesHelmValues: false

&nbsp;   podMonitorSelectorNilUsesHelmValues: false



\# Optional: burn‑rate alerts (API server as an example, 99.5% SLO)

additionalPrometheusRulesMap:

&nbsp; slo-burn:

&nbsp;   groups:

&nbsp;     - name: slo-burn

&nbsp;       rules:

&nbsp;         - alert: HighErrorBudgetBurn\_5m\_99\_5

&nbsp;           for: 2m

&nbsp;           labels:

&nbsp;             severity: page

&nbsp;             window: "5m"

&nbsp;           annotations:

&nbsp;             summary: "High error‑budget burn (5m window)"

&nbsp;             runbook: "Check recent deploys/canary; inspect logs and probes"

&nbsp;           expr: |

&nbsp;             (

&nbsp;               sum(rate(apiserver\_request\_total{code=~"5.."}\[5m]))

&nbsp;               /

&nbsp;               sum(rate(apiserver\_request\_total\[5m]))

&nbsp;             )

&nbsp;             / ( (1 - 0.995) \* (5 / 43200) ) > 6

&nbsp;         - alert: ErrorBudgetBurn\_30m\_99\_5

&nbsp;           for: 10m

&nbsp;           labels:

&nbsp;             severity: warn

&nbsp;             window: "30m"

&nbsp;           annotations:

&nbsp;             summary: "Elevated error‑budget burn (30m)"

&nbsp;           expr: |

&nbsp;             (

&nbsp;               sum(rate(apiserver\_request\_total{code=~"5.."}\[30m]))

&nbsp;               /

&nbsp;               sum(rate(apiserver\_request\_total\[30m]))

&nbsp;             )

&nbsp;             / ( (1 - 0.995) \* (30 / 43200) ) > 1

```



\*\*Install\*\*



```bash

helm repo add prometheus-community https://prometheus-community.github.io/helm-charts

helm repo update

helm upgrade --install mon prometheus-community/kube-prometheus-stack \\

&nbsp; -n monitoring --create-namespace -f deploy/values-kps.yaml

\# Port-forward Prometheus:

kubectl -n monitoring port-forward svc/mon-kube-prometheus-stack-prometheus 9090:9090

```



\### B) Loki stack (`values-loki.yaml`)



```yaml

grafana:

&nbsp; enabled: false  # set true if you want Grafana from this chart



prometheus:

&nbsp; enabled: false  # we already have Prometheus from kube‑prometheus‑stack



loki:

&nbsp; enabled: true

&nbsp; auth\_enabled: false

&nbsp; service:

&nbsp;   type: ClusterIP

&nbsp; config:

&nbsp;   server:

&nbsp;     http\_listen\_port: 3100

&nbsp;   common:

&nbsp;     path\_prefix: /var/loki

&nbsp;     storage:

&nbsp;       filesystem:

&nbsp;         chunks\_directory: /var/loki/chunks

&nbsp;         rules\_directory: /var/loki/rules

&nbsp;   schema\_config:

&nbsp;     configs:

&nbsp;       - from: 2020-10-24

&nbsp;         store: boltdb-shipper

&nbsp;         object\_store: filesystem

&nbsp;         schema: v11

&nbsp;         index:

&nbsp;           prefix: index\_

&nbsp;           period: 24h

&nbsp;   ruler:

&nbsp;     enable\_api: true

&nbsp;     alertmanager\_url: http://mon-kube-prometheus-stack-alertmanager.monitoring:9093

&nbsp;     storage:

&nbsp;       type: local

&nbsp;       local:

&nbsp;         directory: /var/loki/rules



promtail:

&nbsp; enabled: true

&nbsp; config:

&nbsp;   server:

&nbsp;     http\_listen\_port: 9080

&nbsp;     grpc\_listen\_port: 0

&nbsp;   positions:

&nbsp;     filename: /var/log/positions.yaml

&nbsp;   clients:

&nbsp;     - url: http://loki:3100/loki/api/v1/push

&nbsp;   scrape\_configs:

&nbsp;     - job\_name: kubernetes-pods

&nbsp;       pipeline\_stages:

&nbsp;         - cri: {}

&nbsp;         # example redaction (tweak to your needs)

&nbsp;         - replace:

&nbsp;             expression: '(Authorization: )Bearer \[A-Za-z0-9-.\_~+/]+=\*'

&nbsp;             replace: '$1<redacted>'

&nbsp;       kubernetes\_sd\_configs:

&nbsp;         - role: pod

&nbsp;       relabel\_configs:

&nbsp;         - source\_labels: \[\_\_meta\_kubernetes\_pod\_node\_name]

&nbsp;           target\_label: node

&nbsp;         - source\_labels: \[\_\_meta\_kubernetes\_namespace]

&nbsp;           target\_label: namespace

&nbsp;         - source\_labels: \[\_\_meta\_kubernetes\_pod\_name]

&nbsp;           target\_label: pod

&nbsp;         - source\_labels: \[\_\_meta\_kubernetes\_container\_name]

&nbsp;           target\_label: container

&nbsp;         - action: replace

&nbsp;           replacement: /var/log/pods/\*/\*/\*.log

&nbsp;           target\_label: \_\_path\_\_

```



\*\*Install\*\*



```bash

helm repo add grafana https://grafana.github.io/helm-charts

helm repo update

helm upgrade --install loki grafana/loki-stack -n logging --create-namespace -f deploy/values-loki.yaml

\# Port-forward Loki (if you want to hit the API directly):

kubectl -n logging port-forward svc/loki 3100:3100

```



> \*\*Notes\*\*

>

> \* These values are conservative for local/dev. For production, add persistence and tune retention.

> \* If the kube‑prometheus‑stack service name differs (chart version change), adjust the port‑forward svc name accordingly.

> \* The burn‑rate alerts use the API server as a simple example; point them at your app’s HTTP metrics once available.



