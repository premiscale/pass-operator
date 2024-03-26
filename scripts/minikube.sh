#! /usr/bin/env bash
# Manage a minikube cluster.


minikube start \
    -p pass-operator \
    --cpus 4 \
    --nodes 2 \
    --memory 8192 \
    --disk-size 30g \
    --kubernetes-version v1.28.3 \
    --extra-config=kubelet.runtime-request-timeout=40m \
    --addons=ingress \
    --addons=metallb \
    --addons=metrics-server

minikube kubectl -p pass-operator get nodes