#!/usr/bin/env bash
set -euo pipefail

BASE="${BASE:-http://127.0.0.1:8080}"

echo "1) health"
curl -s "$BASE/health" | python -m json.tool

echo "2) fake Marketplace registration"
REG=$(curl -s -X POST "$BASE/aws/marketplace/register" \
  -H 'content-type: application/json' \
  -d '{"token":"dev-demo-customer"}')
echo "$REG" | python -m json.tool
API_KEY=$(python - <<PY
import json
print(json.loads('''$REG''')['api_key'])
PY
)

echo "3) activate fake subscription via SNS webhook"
curl -s -X POST "$BASE/aws/marketplace/sns" \
  -H 'content-type: application/json' \
  -d '{"Message":"{\"action\":\"subscribe-success\",\"customer-identifier\":\"customer-demo-customer\"}"}' | python -m json.tool

echo "4) direct random request"
curl -s -X POST "$BASE/v1/random" \
  -H "authorization: Bearer $API_KEY" \
  -H 'content-type: application/json' \
  -d '{"bytes":32,"delivery":"direct"}' | python -m json.tool

echo "5) async job request"
JOB=$(curl -s -X POST "$BASE/v1/random" \
  -H "authorization: Bearer $API_KEY" \
  -H 'content-type: application/json' \
  -d '{"bytes":2048,"delivery":"job"}')
echo "$JOB" | python -m json.tool
