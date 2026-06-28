# Randogelion AWS RNG API blueprint — embedded magazine edition

This is a pseudo-production AWS test API for ECS/Fargate.

Current mode:

- One ECS/Fargate container.
- Customer-style calls go through the public AWS endpoint.
- Fake AWS Marketplace registration is allowed for staging.
- Direct random requests are capped at 1024 bytes.
- The Docker image embeds a 10 MiB magazine at `/app/data/rng_magazine.bin`.
- The included magazine is zero-filled placeholder data, not real randomness.
- Internal worker/admin interface is kept for later diagnostics.

## Replace the embedded magazine

Default: the project already contains `./data/rng_magazine.bin` as a 10 MiB zero-filled placeholder.

To replace it with the first 10 MiB of a real local file:

```bash
export RNG_CHUNK_SOURCE="/absolute/path/to/your/random_chunk.bin"
./scripts/prepare_magazine.sh
```

If `RNG_CHUNK_SOURCE` is not set, the script recreates the zero-filled placeholder.

## Build and push to ECR

```bash
export REGION="eu-north-1"
export ACCOUNT_ID="224850140675"
export REPO="randogelion/production_layer"
export TAG="latest"
./scripts/build_push_ecr.sh
```

## Register staging task definition

```bash
export WORKER_SHARED_TOKEN="$(openssl rand -hex 32)"
export API_KEY_PEPPER="$(openssl rand -hex 32)"
./scripts/ecs_register_taskdef_staging.sh
```

## Update existing ECS service

```bash
./scripts/ecs_update_service.sh
```

## Test public API

```bash
curl "$API_URL/health"

export API_KEY=$(curl -s -X POST "$API_URL/aws/marketplace/register"   -H "content-type: application/json"   -d '{"token":"dev-demo-customer"}' | jq -r '.api_key')

curl -s -X POST "$API_URL/v1/random"   -H "authorization: Bearer $API_KEY"   -H "content-type: application/json"   -d '{"bytes":1024,"delivery":"direct"}' | jq

curl -s "$API_URL/v1/usage" -H "authorization: Bearer $API_KEY" | jq
```

## Check magazine status

```bash
curl -s "$API_URL/internal/worker/magazine/status"   -H "x-worker-token: $WORKER_SHARED_TOKEN" | jq
```

## Important

This is not full Marketplace production yet. Real production still needs:

- Real `ResolveCustomer` flow.
- SNS signature verification.
- Durable database instead of in-memory state.
- Real `BatchMeterUsage` scheduling.
- HTTPS domain / load balancer / API Gateway.
- External no-duplicate ledger before running multiple containers from the same embedded magazine image.
