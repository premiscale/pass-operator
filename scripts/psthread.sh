#! /usr/bin/env bash
# Show threads on a process in a docker container.

if [ $# -ne 2 ]; then
    printf "Must provided a pod name and PID to run ps against.\\n" >&2
    exit 1
fi

POD="${1}"
PID="${2}"

kubectl exec -it "$POD" -- /bin/bash -c "ps -T -p $PID"