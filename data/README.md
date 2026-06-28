# Embedded RNG magazine placeholder

`rng_magazine.bin` is a 10 MiB zero-filled placeholder so the Docker build works immediately.

For a real pseudo-production test, replace this file before building:

```bash
cp /path/to/your/random_chunk.bin ./data/rng_magazine.bin
# or copy only the first 10 MiB:
dd if=/path/to/your/random_chunk.bin of=./data/rng_magazine.bin bs=1M count=10 status=progress
```

Never use the included zero-filled placeholder as real randomness.
