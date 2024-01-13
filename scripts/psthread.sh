#! /usr/bin/env bash
# Show threads on a process in a docker container.

if [ $# -ne 2 ]; then
    printf "Must provided a container name and PID to run ps against.\\n" >&2
    exit 1
fi

CONTAINER="${1}"
PID="${2}"

docker exec -it "$CONTAINER" ps -T -p "$PID"