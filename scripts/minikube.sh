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
        --addons=registry \
        --insecure-registry "10.0.0.0/24" \
        --cpus 4 \
        --nodes 1 \
        --memory 4096 \
        --disk-size 30g

    # Docker registry for localhost images.
    docker run --name docker-registry-redirect --rm -itd --network=host ubuntu:22.04 /bin/bash -c "apt update && apt install -y socat && socat TCP-LISTEN:5000,reuseaddr,fork TCP:$(minikube ip -p pass-operator):5000"

    kubectl config current-context
    kubectl get nodes -o wide
    kubectl get pods -A
elif [ "$1" == "stop" ]; then
    minikube stop -p pass-operator
    docker stop docker-registry-redirect
elif [ "$1" == "delete" ]; then
    minikube delete -p pass-operator
    docker stop docker-registry-redirect
fi