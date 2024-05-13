ARG IMAGE=python
ARG TAG=3.10.13

FROM ${IMAGE}:${TAG}

SHELL [ "/bin/bash", "-c" ]

# https://github.com/opencontainers/image-spec/blob/main/annotations.md#pre-defined-annotation-keys
LABEL org.opencontainers.image.description "© PremiScale, Inc. 2024"
LABEL org.opencontainers.image.licenses "GPLv3"
LABEL org.opencontainers.image.authors "Emma Doyle <emma@premiscale.com>"
LABEL org.opencontainers.image.documentation "https://premiscale.com"

USER root

# https://github.com/krallin/tini
ARG TINI_VERSION=v0.19.0
ADD https://github.com/krallin/tini/releases/download/${TINI_VERSION}/tini /tini
RUN chmod +x /tini

ARG PASS_VERSION=1.7.4-6
RUN apt update \
    && apt list -a pass \
    && apt install -y pass="$PASS_VERSION" \
    && rm -rf /var/apt/lists/*

# Add 'passoperator' user and group.
# Funny enough, 'operator' is already a user in Linux.
RUN groupadd passoperator \
    && useradd -rm -d /opt/pass-operator -s /bin/bash -g operator -u 10001 operator

WORKDIR /opt/pass-operator

RUN chown -R passoperator:passoperator . \
    && mkdir /hooks \
    && printf "[pull]\\n    rebase = true\\n[core]\\n    hooksPath = /hooks" > /etc/gitconfig
COPY --chown=root:root --chmod=555 bin/pre-push.sh /hooks/pre-push

USER 10001

ARG PYTHON_USERNAME
ARG PYTHON_PASSWORD
ARG PYTHON_REPOSITORY
ARG PYTHON_INDEX=https://${PYTHON_USERNAME}:${PYTHON_PASSWORD}@${PYTHON_REPOSITORY}
ARG PYTHON_PACKAGE_VERSION=0.0.1

ENV PATH=${PATH}:/opt/pass-operator/.local/bin \
    PYTHONUNBUFFERED=1

# Set up SSH and install the pass-operator package from my private registry.
RUN mkdir -p "$HOME"/.local/bin "$HOME"/.ssh "$HOME"/.gnupg \
    && chmod 700 "$HOME"/.gnupg \
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
    PASS_GPG_PASSPHRASE="" \
    PASS_GIT_URL="" \
    PASS_GIT_BRANCH=main \
    PASS_SSH_PRIVATE_KEY=""

COPY --chown=passoperator:passoperator --chmod=550 bin/entrypoint.sh /entrypoint.sh

ENTRYPOINT [ "/tini", "--", "/entrypoint.sh" ]