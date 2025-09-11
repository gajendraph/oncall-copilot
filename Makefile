SHELL := /usr/bin/bash
NS ?= default
PROM_URL ?= http://127.0.0.1:9090
LOKI_URL ?= http://127.0.0.1:3100

.PHONY: cluster up monitoring logging workloads pf-prom pf-loki agent score slack

cluster:
	kind delete cluster --name oncall-sandbox >/dev/null 2>&1 || true
	kind create cluster --name oncall-sandbox --image kindest/node:v1.29.2

monitoring:
	helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
	helm repo update
	mkdir -p deploy
	echo "grafana:\n  adminPassword: \"admin\"" > deploy/values-kps.yaml
	helm upgrade --install mon prometheus-community/kube-prometheus-stack -n monitoring --create-namespace -f deploy/values-kps.yaml --wait

logging:
	kubectl apply -f deploy/loki-min.yaml
	helm repo add grafana https://grafana.github.io/helm-charts
	helm repo update
	helm upgrade --install promtail grafana/promtail -n logging --create-namespace --set config.clients[0].url=$(LOKI_URL)/loki/api/v1/push

workloads:
	kubectl apply -f deploy/workloads.yaml

pf-prom:
	kubectl -n monitoring port-forward svc/mon-kube-prometheus-stack-prometheus 9090:9090

pf-loki:
	kubectl -n logging port-forward svc/loki 3100:3100

agent:
	PYTHONPATH=$(PWD) python -m agent.run --namespace $(NS) --window-minutes 5 --output out/agent-report.md

score:
	PROM_URL=$(PROM_URL) LOKI_URL=$(LOKI_URL) python scripts/incident_score.py | tee out/incident-score.md
