#!/usr/bin/env bash
set -euo pipefail
IN=infra/kibana/dashboard_applylens.ndjson
OUT=infra/kibana/dashboard_applylens.patched.ndjson
EMAILS_ID=${1:?"Lens Emails ID required"}
TRAFFIC_ID=${2:?"Lens Traffic ID required"}

# Build a panelsJSON array with two Lens panels
PANELS=$(cat <<JSON
[
  {"version":"8","type":"lens","gridData":{"x":0,"y":0,"w":24,"h":16,"i":"1"},"panelIndex":"1","embeddableConfig":{},"panelRefName":"panel_0"},
  {"version":"8","type":"lens","gridData":{"x":0,"y":16,"w":24,"h":12,"i":"2"},"panelIndex":"2","embeddableConfig":{},"panelRefName":"panel_1"}
]
JSON
)

# Recompose a single NDJSON line with references
DASH=$(jq -c --arg pj "$PANELS" '.attributes.panelsJSON=$pj' "$IN")
REFS=$(jq -c -n --arg a "$EMAILS_ID" --arg b "$TRAFFIC_ID" '{references:[{"type":"lens","name":"panel_0","id":$a},{"type":"lens","name":"panel_1","id":$b}]}' )

# Merge attributes and references
jq -s '.[0] * .[1]' <(echo "$DASH") <(echo "$REFS") > "$OUT"
echo "Patched dashboard → $OUT"
