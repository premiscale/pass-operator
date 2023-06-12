#! /usr/bin/env bash
# Docker build of the docker/PROJECT-directory.

VERSION="${1:-latest}"


docker build . -t docker.ops.premiscale.com/mysql:"$VERSION" --build-arg=VERSION="$VERSION" -f docker/mysql/Dockerfile