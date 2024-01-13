#! /usr/bin/env bash
# Get the process tree on a pod.

if [ $# -ne 1 ]; then
    printf "Must provided a pod name to run ps against.\\n" >&2
    exit 1
fi

POD="${1}"

#docker exec -it "$CONTAINER" ps -ef --forest
kubectl exec -it "$POD" -- /bin/bash -c 'ps -ef --forest'