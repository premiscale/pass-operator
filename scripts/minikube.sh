#! /usr/bin/env bash
# Manage a minikube cluster.


set -eo pipefail
shopt -s nullglob


if ! command -v minikube &> /dev/null; then
    printf "ERROR: executable 'minikube' could not be found" >&2
    exit 1
fi


if [ "$1" != "start" ] && [ "$1" != "stop" ] && [ "$1" != "delete" ]; then
    printf "ERROR: Usage: %s { start | stop | delete }\\n" "$0" >&2
    exit 1
fi


if [ "$1" == "start" ]; then
    minikube start \
        -p pass-operator \
        --kubernetes-version v1.28.3 \
        --extra-config=kubelet.runtime-request-timeout=40m \
        --addons=ingress \
        --addons=metallb \
        --addons=metrics-server \
        --cpus 4 \
        --nodes 2 \
        --memory 4096 \
        --disk-size 30g \

    kubectl config current-context
    kubectl get nodes -o wide
    kubectl get pods -A
elif [ "$1" == "stop" ]; then
    minikube stop -p pass-operator
elif [ "$1" == "delete" ]; then
    minikube delete -p pass-operator
fi