#!/usr/bin/env bash
set -euo pipefail

REGION="${REGION:-eu-north-1}"
ACCOUNT_ID="${ACCOUNT_ID:-224850140675}"
REPO="${REPO:-randogelion/production_layer}"
TAG="${TAG:-latest}"
IMAGE_URI="$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$REPO:$TAG"
EXECUTION_ROLE_ARN="${EXECUTION_ROLE_ARN:-arn:aws:iam::$ACCOUNT_ID:role/ecsTaskExecutionRole}"
TASK_FAMILY="${TASK_FAMILY:-randogelion-production-layer}"
LOG_GROUP="${LOG_GROUP:-/ecs/randogelion-production-layer}"

: "${WORKER_SHARED_TOKEN:?Set WORKER_SHARED_TOKEN first}"
: "${API_KEY_PEPPER:?Set API_KEY_PEPPER first}"

cat > /tmp/randogelion-taskdef-staging.json <<EOF
{
  "family": "$TASK_FAMILY",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "executionRoleArn": "$EXECUTION_ROLE_ARN",
  "containerDefinitions": [
    {
      "name": "production-layer",
      "image": "$IMAGE_URI",
      "essential": true,
      "portMappings": [{ "containerPort": 8080, "protocol": "tcp" }],
      "environment": [
        { "name": "APP_ENV", "value": "staging" },
        { "name": "AWS_REGION", "value": "$REGION" },
        { "name": "LOCAL_DEV_ALLOW_FAKE_MARKETPLACE", "value": "true" },
        { "name": "RNG_PROVIDER", "value": "embedded_magazine" },
        { "name": "RNG_MAGAZINE_PATH", "value": "/app/data/rng_magazine.bin" },
        { "name": "RNG_MAGAZINE_MAX_REQUEST_BYTES", "value": "1024" },
        { "name": "MAX_DIRECT_RESPONSE_BYTES", "value": "1024" },
        { "name": "WORKER_SHARED_TOKEN", "value": "$WORKER_SHARED_TOKEN" },
        { "name": "API_KEY_PEPPER", "value": "$API_KEY_PEPPER" }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "$LOG_GROUP",
          "awslogs-region": "$REGION",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
EOF

aws ecs register-task-definition   --region "$REGION"   --cli-input-json file:///tmp/randogelion-taskdef-staging.json   --query 'taskDefinition.taskDefinitionArn'   --output text
