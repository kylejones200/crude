#!/usr/bin/env bash
set -euo pipefail

# Crude Assay — build & deploy to Databricks Apps (E2 Field-Eng)
PROFILE="e2-field-eng"
APP_NAME="crude-assay-kjones"
APP_URL="https://${APP_NAME}-1444828305810485.aws.databricksapps.com"
WORKSPACE_PATH="/Workspace/Users/k.jones@databricks.com/crude-assay"
ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "▸ Syncing to workspace..."
databricks sync "$ROOT_DIR" "$WORKSPACE_PATH" --profile "$PROFILE"

echo "▸ Deploying app..."
databricks apps deploy "$APP_NAME" \
  --source-code-path "$WORKSPACE_PATH" \
  --profile "$PROFILE"

echo "▸ Waiting for deployment..."
sleep 5
for i in $(seq 1 30); do
  DEPLOY_STATE=$(databricks apps list-deployments "$APP_NAME" --profile "$PROFILE" 2>/dev/null | python3 -c "
import json,sys
try:
    d = json.load(sys.stdin)
    deps = d.get('deployments',[])
    if deps:
        print(deps[0].get('status',{}).get('state',''))
except: print('')
" 2>/dev/null || true)
  if [ "$DEPLOY_STATE" = "SUCCEEDED" ]; then
    echo "✓ Deployed: $APP_URL"
    exit 0
  elif [ "$DEPLOY_STATE" = "FAILED" ]; then
    echo "✗ Deployment failed. Check logs at $APP_URL/logz"
    exit 1
  fi
  sleep 5
done
echo "⚠ Deployment still in progress. Check status with: databricks apps get $APP_NAME --profile $PROFILE"
