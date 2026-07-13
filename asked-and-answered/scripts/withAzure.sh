#!/usr/bin/env bash
set -euo pipefail

RESOURCE_NAME="asked-and-answered-openai"
RESOURCE_GROUP="rg-asked-and-answered"

# Fetch the primary key and endpoint from Azure CLI so no secrets are stored in source.
KEY=$(az cognitiveservices account keys list --name "$RESOURCE_NAME" --resource-group "$RESOURCE_GROUP" | jq -r '.key1')
ENDPOINT=$(az cognitiveservices account show --name "$RESOURCE_NAME" --resource-group "$RESOURCE_GROUP" --query 'properties.endpoint' -o tsv)

DEPLOYMENT="${1:-gpt-5-mini}"

export AA_EVAL_LLM=azure
export AZURE_OPENAI_ENDPOINT="$ENDPOINT"
export AZURE_OPENAI_API_KEY="$KEY"
export AZURE_OPENAI_DEPLOYMENT="$DEPLOYMENT"
export AZURE_OPENAI_API_VERSION="2024-08-01-preview"

shift || true
exec "$@"
