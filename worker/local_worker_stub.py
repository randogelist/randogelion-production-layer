"""Local RNG worker stub.

This process runs on your local host. It opens outbound HTTPS connections to the
AWS API, claims jobs, generates bytes locally, uploads to S3 in production, and
marks jobs complete.

For local blueprint testing it only writes a local file and reports a fake S3 key.
"""

import hashlib
import os
import time
from pathlib import Path

import requests

API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8080")
WORKER_SHARED_TOKEN = os.getenv("WORKER_SHARED_TOKEN", "dev-worker-token-change-me")
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "./worker-output"))
POLL_SECONDS = float(os.getenv("POLL_SECONDS", "5"))


def headers() -> dict[str, str]:
    return {"x-worker-token": WORKER_SHARED_TOKEN}


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    while True:
        response = requests.get(f"{API_BASE_URL}/internal/worker/jobs/next", headers=headers(), timeout=30)
        response.raise_for_status()
        job = response.json()
        if not job.get("job_id"):
            print("no job; sleeping")
            time.sleep(POLL_SECONDS)
            continue

        job_id = job["job_id"]
        byte_count = int(job["bytes"])
        s3_key = job["s3_key"]
        print(f"claimed {job_id}: generating {byte_count} bytes")

        # Replace this with your real entropy/RNG pipeline.
        data = os.urandom(byte_count)
        sha256 = hashlib.sha256(data).hexdigest()
        local_path = OUTPUT_DIR / f"{job_id}.bin"
        local_path.write_bytes(data)

        # Production TODO: upload `local_path` to S3 bucket/key from the job.
        complete = requests.post(
            f"{API_BASE_URL}/internal/worker/jobs/{job_id}/complete",
            headers=headers(),
            json={"s3_key": s3_key, "bytes": byte_count, "sha256": sha256},
            timeout=30,
        )
        complete.raise_for_status()
        print(f"completed {job_id}: {sha256}")


if __name__ == "__main__":
    main()
