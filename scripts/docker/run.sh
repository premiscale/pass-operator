#! /usr/bin/env bash
# Docker run the docker/PROJECT-directory.


VERSION="${1:-0.0.1}"
PROJECT="${2:-"pass-operator"}"
shift && shift


# docker run -itd --name "$PROJECT" docker.ops.premiscale.com/"$PROJECT":"$VERSION" "$@"

docker stop pass-operator && docker rm pass-operator
docker run -itd --name "${PROJECT}" docker-develop.ops.premiscale.com/"${PROJECT}":"${VERSION}" "$@"
docker exec -it "${PROJECT}" /bin/bash