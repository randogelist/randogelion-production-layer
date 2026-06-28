#!/usr/bin/env bash
set -euo pipefail

REGION="${REGION:-eu-north-1}"
CLUSTER="${CLUSTER:-randogelion-test-cluster}"
SERVICE="${SERVICE:-randogelion-test-service}"
TASK_FAMILY="${TASK_FAMILY:-randogelion-production-layer}"

aws ecs update-service   --region "$REGION"   --cluster "$CLUSTER"   --service "$SERVICE"   --task-definition "$TASK_FAMILY"   --force-new-deployment
