#! /usr/bin/env bash
# Docker build.


PYTHON_PACKAGE_VERSION="${1:-0.0.1}"
PYTHON_USERNAME="${2:-$(pass show premiscale/nexus/username)}"
PYTHON_PASSWORD="${3:-$(pass show premiscale/nexus/password)}"
PYTHON_REPOSITORY="${4:-python-develop}"


docker build . -t docker.ops.premiscale.com/pass-operator:"$PYTHON_PACKAGE_VERSION" --build-arg=PYTHON_PACKAGE_VERSION="$PYTHON_PACKAGE_VERSION" --build-arg=PYTHON_USERNAME="$PYTHON_USERNAME" --build-arg=PYTHON_PASSWORD="$PYTHON_PASSWORD" --build-arg=PYTHON_REPOSITORY="$PYTHON_REPOSITORY" -f ./Dockerfile