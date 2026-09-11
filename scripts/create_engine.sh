#!/usr/bin/env bash
set -e

PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
if [ -z "$PROJECT_ID" ]; then
  echo "Error: PROJECT_ID could not be determined. Please run: gcloud config set project YOUR_PROJECT_ID"
  exit 1
fi

PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format="value(projectNumber)" 2>/dev/null)
REGION="${REGION:-us-central1}"

echo "Provisioning Agent Engine in project $PROJECT_ID ($REGION) with AGENT_IDENTITY..."

RESPONSE=$(curl -s -X POST \
  -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  -H "Content-Type: application/json" \
  "https://${REGION}-aiplatform.googleapis.com/v1beta1/projects/${PROJECT_ID}/locations/${REGION}/reasoningEngines" \
  -d '{"spec": {"identityType": "AGENT_IDENTITY"}}')

AGENT_ENGINE_ID=$(echo "$RESPONSE" | grep -o 'reasoningEngines/[0-9]*' | cut -d'/' -f2 | head -n1)

if [ -z "$AGENT_ENGINE_ID" ]; then
  echo "Failed to create Agent Engine. API Response:"
  echo "$RESPONSE"
  exit 1
fi

echo "$AGENT_ENGINE_ID" > .engine_id

echo "--------------------------------------------------------"
echo "Agent Engine created with AGENT_IDENTITY!"
echo "Agent Engine ID: $AGENT_ENGINE_ID"
echo "--------------------------------------------------------"
