#! /usr/bin/env bash
# Docker run the docker/PROJECT-directory.

PROJECT="${1:-base_python}"
VERSION="${2:-0.1.0}"
shift && shift


# docker run -itd --name "$PROJECT" docker.ops.premiscale.com/"$PROJECT":"$VERSION" "$@"

docker stop base_python && docker rm base_python
docker run -itd --name "${PROJECT}" -e DOPPLER_TOKEN="$(pass show premiscale/doppler/development-service-token)" docker-develop.ops.premiscale.com/"${PROJECT}":"${VERSION}" "$@"
docker exec -it "${PROJECT}" /bin/bash