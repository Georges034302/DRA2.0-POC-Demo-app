#!/usr/bin/env bash
set -euo pipefail

: "${AZURE_RESOURCE_GROUP:?}" "${AZURE_LOCATION:?}"

echo '=== DRA 2.0 Environment Setup ==='

echo 'Registering required resource providers (skips if already registered)...'
az provider register --namespace Microsoft.App --wait
az provider register --namespace Microsoft.OperationalInsights --wait

EXISTING_REGISTRY="$(az group show --name "$AZURE_RESOURCE_GROUP" --query 'tags.registryName' -o tsv 2>/dev/null || true)"

if [[ -n "$EXISTING_REGISTRY" ]]; then
  echo "Resource group $AZURE_RESOURCE_GROUP is already configured — reusing existing names."
  az group show --name "$AZURE_RESOURCE_GROUP" --query tags -o table
  exit 0
fi

SUFFIX="$RANDOM"
REGISTRY_NAME="dra2registry${SUFFIX}"
ENV_NAME="dra2-env-${SUFFIX}"
LOG_WORKSPACE_NAME="dra2-logs-${SUFFIX}"
FRONTEND_APP_BASE="dra2-frontend-${SUFFIX}"
BACKEND_APP_BASE="dra2-backend-${SUFFIX}"
DATABASE_APP_BASE="dra2-database-${SUFFIX}"

echo 'Creating resource group...'
az group create --name "$AZURE_RESOURCE_GROUP" --location "$AZURE_LOCATION"

echo 'Creating Log Analytics workspace...'
az monitor log-analytics workspace create \
  --resource-group "$AZURE_RESOURCE_GROUP" \
  --workspace-name "$LOG_WORKSPACE_NAME" \
  --location "$AZURE_LOCATION" \
  --output none

WORKSPACE_ID="$(az monitor log-analytics workspace show \
  --resource-group "$AZURE_RESOURCE_GROUP" \
  --workspace-name "$LOG_WORKSPACE_NAME" \
  --query customerId -o tsv)"
WORKSPACE_KEY="$(az monitor log-analytics workspace get-shared-keys \
  --resource-group "$AZURE_RESOURCE_GROUP" \
  --workspace-name "$LOG_WORKSPACE_NAME" \
  --query primarySharedKey -o tsv)"

echo 'Creating Container Apps environment...'
az containerapp env create \
  --name "$ENV_NAME" \
  --resource-group "$AZURE_RESOURCE_GROUP" \
  --location "$AZURE_LOCATION" \
  --logs-workspace-id "$WORKSPACE_ID" \
  --logs-workspace-key "$WORKSPACE_KEY" \
  --output none

echo 'Creating Azure Container Registry...'
az acr create \
  --name "$REGISTRY_NAME" \
  --resource-group "$AZURE_RESOURCE_GROUP" \
  --sku Basic \
  --admin-enabled false \
  --output none

echo 'Tagging resource group with deployment names...'
az group update \
  --name "$AZURE_RESOURCE_GROUP" \
  --tags \
    registryName="$REGISTRY_NAME" \
    envName="$ENV_NAME" \
    logWorkspaceName="$LOG_WORKSPACE_NAME" \
    frontendAppBase="$FRONTEND_APP_BASE" \
    backendAppBase="$BACKEND_APP_BASE" \
    databaseAppBase="$DATABASE_APP_BASE" \
    location="$AZURE_LOCATION" \
  --output none

echo '=== Environment Setup Complete ==='
az group show --name "$AZURE_RESOURCE_GROUP" --query tags -o table
printf 'ACR_SERVER=%s\n' "$(az acr show --name "$REGISTRY_NAME" --query loginServer -o tsv)"
