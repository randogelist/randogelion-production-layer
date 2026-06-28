#!/usr/bin/env bash
set -euo pipefail

mkdir -p data

if [[ -z "${RNG_CHUNK_SOURCE:-}" ]]; then
  echo "RNG_CHUNK_SOURCE not set. Creating zero-filled 10 MiB placeholder at ./data/rng_magazine.bin"
  dd if=/dev/zero of=./data/rng_magazine.bin bs=1M count=10 status=none
else
  test -f "$RNG_CHUNK_SOURCE"
  echo "Copying first 10 MiB from $RNG_CHUNK_SOURCE to ./data/rng_magazine.bin"
  dd if="$RNG_CHUNK_SOURCE" of=./data/rng_magazine.bin bs=1M count=10 status=progress
fi

stat -c "magazine=%n bytes=%s" ./data/rng_magazine.bin
sha256sum ./data/rng_magazine.bin > ./data/rng_magazine.bin.sha256
cat ./data/rng_magazine.bin.sha256
