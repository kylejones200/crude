#!/usr/bin/env bash
set -euo pipefail

# Bootstrap script for the crude assay project on Databricks (no Git required)
# - Imports app notebook
# - Creates/updates the DLT pipeline from conf/pipeline.json
# - Starts the pipeline (requires Pipelines CLI)
# - Prints follow-up steps
#
# Usage:
#   bash scripts/bootstrap_databricks.sh 
# Prereqs:
#   - databricks CLI configured with a PAT for your workspace
#   - You created catalog/schema crude.assay and volume crude.assay.assay_data
#   - You granted yourself READ VOLUME, WRITE VOLUME on that volume

WORKSPACE_BASE="/Workspace/Users/k.jones@databricks.com/assay"
APP_NOTEBOOK_LOCAL="/Users/k.jones/Desktop/assay/notebooks/app_streamlit.py"
APP_NOTEBOOK_WS="${WORKSPACE_BASE}/notebooks/app_streamlit"
PIPELINE_JSON_LOCAL="/Users/k.jones/Desktop/assay/conf/pipeline.json"

echo "[1/4] Import app notebook -> ${APP_NOTEBOOK_WS}"
databricks workspace import \
  "${APP_NOTEBOOK_WS}" \
  --file "${APP_NOTEBOOK_LOCAL}" \
  --language PYTHON \
  --format AUTO \
  --overwrite

# Create or update the pipeline
# If your CLI supports 'databricks pipelines', this will work. Otherwise do this step in the UI.
echo "[2/4] Create or update DLT pipeline from ${PIPELINE_JSON_LOCAL}"
if databricks pipelines -h >/dev/null 2>&1; then
  # Try to create, if exists then update
  if databricks pipelines create --json-file "${PIPELINE_JSON_LOCAL}" >/tmp/assay_pipeline_create.json 2>/dev/null; then
    PIPELINE_ID=$(cat /tmp/assay_pipeline_create.json | sed -n 's/.*"pipeline_id":"\([^"]*\)".*/\1/p')
    echo "Created pipeline: ${PIPELINE_ID}"
  else
    echo "[info] Create may have failed because the pipeline exists; attempting update..."
    databricks pipelines edit --json-file "${PIPELINE_JSON_LOCAL}" >/tmp/assay_pipeline_update.json || true
    PIPELINE_ID=$(cat /tmp/assay_pipeline_update.json | sed -n 's/.*"pipeline_id":"\([^"]*\)".*/\1/p')
    echo "Updated pipeline: ${PIPELINE_ID}"
  fi
else
  echo "[warn] Pipelines CLI not available. Please create/start the pipeline in the UI using conf/pipeline.json"
  PIPELINE_ID=""
fi

# Start the pipeline if we have an ID
if [[ -n "${PIPELINE_ID}" ]]; then
  echo "[3/4] Starting pipeline: ${PIPELINE_ID}"
  databricks pipelines start --pipeline-id "${PIPELINE_ID}" --full-refresh || true
else
  echo "[skip] Start step skipped (no pipeline id)."
fi

cat <<'MSG'
[4/4] Next steps:
- Stage seed data if not already done. You can run the staging notebook:
  /Workspace/Users/k.jones@databricks.com/assay/notebooks/00_stage_volume_via_notebook
- Ensure your pipeline Spark config includes:
  assay.data.base_path = /Volumes/crude/assay/assay_data
- Install optimization libs once on the cluster used by the app:
  %pip install pyomo highspy
- Launch the app:
  Apps > New App > Notebook > /Workspace/Users/k.jones@databricks.com/assay/notebooks/app_streamlit
MSG
