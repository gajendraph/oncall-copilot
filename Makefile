SHELL := /bin/bash

KIND_NAME ?= oncall-sandbox
CLUSTER ?= kind-$(KIND_NAME)
NAMESPACE ?= default

sandbox:
	kind create cluster --name $(KIND_NAME) --image kindest/node:v1.29.2
	kubectl create deployment demo --image=nginx || true
	kubectl expose deployment demo --port 80 || true
	kubectl apply -f read-only.rbac.yaml
	kubectl apply -f - <<'YAML'
apiVersion: v1
kind: Pod
metadata:
  name: crashy
  namespace: $(NAMESPACE)
spec:
  restartPolicy: Always
  containers:
  - name: bad
    image: busybox
    command: ["sh","-c","echo starting; sleep 2; exit 1"]
YAML
	@echo "Minting read-only token and context…"
	@TOKEN=$$(kubectl -n $(NAMESPACE) create token oncall-copilot-ro); \
	kubectl config set-credentials oncall-copilot-user --token="$$TOKEN"; \
	kubectl config set-context oncall-copilot --cluster=$(CLUSTER) --namespace=$(NAMESPACE) --user=oncall-copilot-user; \
	kubectl config use-context oncall-copilot; \
	kubectl get pods -o wide

destroy:
	kind delete cluster --name $(KIND_NAME)

health:
	python cli.py health --namespace $(NAMESPACE)

triage:
	python cli.py triage --pod crashy --namespace $(NAMESPACE) --lines 400

status:
	python cli.py status-draft --namespace $(NAMESPACE)
