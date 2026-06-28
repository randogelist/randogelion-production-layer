#!/usr/bin/env bash
set -euo pipefail

REGION="${REGION:-eu-north-1}"
ACCOUNT_ID="${ACCOUNT_ID:-224850140675}"
REPO="${REPO:-randogelion/production_layer}"
TAG="${TAG:-latest}"
IMAGE_URI="$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$REPO:$TAG"

aws ecr get-login-password --region "$REGION" | sudo docker login --username AWS --password-stdin "$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com"
sudo docker build --build-arg RNG_MAGAZINE_FILE=data/rng_magazine.bin -t "$REPO:$TAG" .
sudo docker tag "$REPO:$TAG" "$IMAGE_URI"
sudo docker push "$IMAGE_URI"

echo "IMAGE_URI=$IMAGE_URI"
