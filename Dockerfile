ARG IMAGE=python
ARG TAG=3.10.8

FROM ${IMAGE}:${TAG}

ENV DOPPLER_TOKEN="notset"

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

# Install the Doppler CLI via apt for secrets retrieval.
RUN curl -Ls --tlsv1.2 --proto "=https" --retry 3 https://cli.doppler.com/install.sh | sh

RUN apt update && \
    rm -rf /var/apt/lists/* && \
    python -m venv /opt/premiscale

RUN useradd -rm -d /opt/premiscale -s /bin/bash -g root -G sudo -u 1001 premiscale

COPY ./cmd.sh /opt/premiscale/

WORKDIR /opt/premiscale

RUN chmod +x cmd.sh && chown -R premiscale:root .
USER premiscale

ARG PYTHON_USERNAME
ARG PYTHON_PASSWORD
ARG PYTHON_REPOSITORY
ARG PYTHON_INDEX=https://${PYTHON_USERNAME}:${PYTHON_PASSWORD}@repo.ops.premiscale.com/repository/${PYTHON_REPOSITORY}/simple
ARG PYTHON_PACKAGE_VERSION=0.0.1

ENV PATH=${PATH}:/opt/premiscale/.local/bin

# Install and initialize PremiScale.
RUN mkdir -p "$HOME"/.local/bin && \
    . bin/activate && \
    pip install --upgrade pip && \
    pip install --no-cache-dir --no-input --extra-index-url="${PYTHON_INDEX}" base_python=="${PYTHON_PACKAGE_VERSION}"

ENTRYPOINT [ "/tini", "--", "doppler", "run", "--" ]
CMD [ "./cmd.sh" ]
