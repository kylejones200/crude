#!/usr/bin/env bash
set -euo pipefail

# Stages sample CSVs into a Unity Catalog Volume using Databricks CLI.
# Usage: bash scripts/stage_uc_volume.sh
# Prereqs:
#  - Databricks CLI configured (databricks configure --token)
#  - Volume exists: CREATE VOLUME IF NOT EXISTS crude.assay.assay_data;
#  - You have WRITE on the volume (or are the owner)

BASE_LOCAL_DIR="resources/sample_data"
DEST_BASE="/Volumes/crude/assay/assay_data"

echo "[info] Verifying Volume access at ${DEST_BASE}..."
if ! databricks fs ls "${DEST_BASE}" >/dev/null 2>&1; then
  echo "[warn] Cannot list ${DEST_BASE}. This may be a permissions issue."
  echo "[hint] Ensure the Volume exists and you have WRITE:"
  echo "       GRANT READ, WRITE ON VOLUME crude.assay.assay_data TO `<your-user-or-group>`;"
  echo "[hint] If you just created the volume, try again in a few seconds."
  # We continue; cp may still succeed if the path exists.
fi

# Copy files
declare -A FILES=(
  ["assays.csv"]="assays.csv"
  ["prices.csv"]="prices.csv"
  ["freight_routes.csv"]="freight_routes.csv"
  ["blend_supply.csv"]="blend_supply.csv"
)

for src in "${!FILES[@]}"; do
  dst="${FILES[$src]}"
  echo "[info] Copying ${BASE_LOCAL_DIR}/${src} -> ${DEST_BASE}/${dst}"
  databricks fs cp "${BASE_LOCAL_DIR}/${src}" "${DEST_BASE}/${dst}" --overwrite
done

echo "[ok] Staged files at ${DEST_BASE}:"
databricks fs ls "${DEST_BASE}" || true

cat <<'MSG'
Next steps:
1) In your DLT pipeline settings, set Spark config:
   assay.data.base_path = /Volumes/crude/assay/assay_data
2) Start the pipeline. Tables will land in crude.assay.
3) Run notebooks/02_optimize_blends to generate blend outputs.
4) In SQL Editor, run sql/dashboard_views.sql to create dashboard views.
MSG
