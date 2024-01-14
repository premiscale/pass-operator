ARG IMAGE=python
ARG TAG=3.10.11

FROM ${IMAGE}:${TAG}

# https://github.com/opencontainers/image-spec/blob/main/annotations.md#pre-defined-annotation-keys
LABEL org.opencontainers.image.description "© PremiScale, Inc. 2023"
LABEL org.opencontainers.image.licenses "GPLv3"
LABEL org.opencontainers.image.authors "Emma Doyle <emma@premiscale.com>"
LABEL org.opencontainers.image.documentation "https://premiscale.com"

USER root

# https://github.com/krallin/tini
ARG TINI_VERSION=v0.19.0
ADD https://github.com/krallin/tini/releases/download/${TINI_VERSION}/tini /tini
RUN chmod +x /tini

ARG PASS_VERSION=1.7.3-2
RUN apt update \
    && apt list -a pass \
    && apt install -y pass="$PASS_VERSION" \
    && rm -rf /var/apt/lists/*

# Add 'operator' user and group.
RUN useradd -rm -d /opt/pass-operator -s /bin/bash -g operator -u 1001 operator

WORKDIR /opt/pass-operator

RUN chown -R operator:operator .
USER operator

ARG PYTHON_USERNAME
ARG PYTHON_PASSWORD
ARG PYTHON_REPOSITORY
ARG PYTHON_INDEX=https://${PYTHON_USERNAME}:${PYTHON_PASSWORD}@repo.ops.premiscale.com/repository/${PYTHON_REPOSITORY}/simple
ARG PYTHON_PACKAGE_VERSION=0.0.1

ENV PATH=${PATH}:/opt/pass-operator/.local/bin

# Install and initialize PremiScale.
RUN mkdir -p "$HOME"/.local/bin "$HOME"/.ssh \
    && pip install --upgrade pip \
    && pip install --no-cache-dir --no-input --extra-index-url="${PYTHON_INDEX}" pass-operator=="${PYTHON_PACKAGE_VERSION}"

ENV OPERATOR_INTERVAL=60 \
    OPERATOR_INITIAL_DELAY=3 \
    OPERATOR_PRIORITY=100 \
    OPERATOR_NAMESPACE=default \
    PASS_BINARY=/usr/bin/pass \
    PASS_DIRECTORY=repo \
    PASS_GPG_KEY_ID="" \
    PASS_GPG_KEY="" \
    PASS_GIT_URL="" \
    PASS_GIT_BRANCH=main \
    PASS_SSH_PRIVATE_KEY=""

COPY bin/entrypoint.sh /entrypoint.sh
COPY bin/ssh_config $HOME/.ssh/config
RUN chmod 400 $HOME/.ssh/config

ENTRYPOINT [ "/tini", "--", "/entrypoint.sh" ]