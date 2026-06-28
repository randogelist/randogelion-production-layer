FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    APP_ENV=staging \
    AWS_REGION=eu-north-1 \
    RNG_PROVIDER=embedded_magazine \
    RNG_MAGAZINE_PATH=/app/data/rng_magazine.bin \
    RNG_MAGAZINE_MAX_REQUEST_BYTES=1024 \
    MAX_DIRECT_RESPONSE_BYTES=1024

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    bash \
    git \
    curl \
    wget \
    ca-certificates \
    jq \
    nano \
    vim-tiny \
    less \
    procps \
    iproute2 \
    iputils-ping \
    dnsutils \
    netcat-openbsd \
    unzip \
    tar \
    gzip \
    lsof \
    strace \
    tini \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --upgrade pip && pip install -r requirements.txt

ARG RNG_MAGAZINE_FILE=data/rng_magazine.bin
RUN mkdir -p /app/data /work /tmp/randogelion
COPY ${RNG_MAGAZINE_FILE} /app/data/rng_magazine.bin

COPY api ./api
COPY worker ./worker
COPY scripts ./scripts
COPY README.md ./README.md

EXPOSE 8080

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8080"]
