#!/usr/bin/env bash
set -e

PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format="value(projectNumber)" 2>/dev/null)
REGION="${REGION:-us-central1}"

if [ ! -f .engine_id ]; then
  echo "No .engine_id file found."
  exit 0
fi

AGENT_ENGINE_ID=$(cat .engine_id)

echo "Deleting Agent Engine $AGENT_ENGINE_ID..."
curl -s -X DELETE \
  -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  "https://${REGION}-aiplatform.googleapis.com/v1beta1/projects/${PROJECT_NUMBER}/locations/${REGION}/reasoningEngines/${AGENT_ENGINE_ID}?force=true"

rm -f .engine_id
echo "Deleted Agent Engine instance: $AGENT_ENGINE_ID"
