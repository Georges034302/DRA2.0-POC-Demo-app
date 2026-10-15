#!/usr/bin/env bash
set -euo pipefail
: "${AZURE_RESOURCE_GROUP:?}" "${AZURE_LOCATION:?}" "${AZURE_ACR_NAME:?}" "${AZURE_CONTAINERAPPS_ENV:?}"
az extension add --name containerapp --upgrade --yes >/dev/null
az group create --name "$AZURE_RESOURCE_GROUP" --location "$AZURE_LOCATION" --output none
az acr show --name "$AZURE_ACR_NAME" >/dev/null 2>&1 || az acr create --name "$AZURE_ACR_NAME" --resource-group "$AZURE_RESOURCE_GROUP" --sku Basic --admin-enabled false --output none
az containerapp env show -g "$AZURE_RESOURCE_GROUP" -n "$AZURE_CONTAINERAPPS_ENV" >/dev/null 2>&1 || az containerapp env create -g "$AZURE_RESOURCE_GROUP" -n "$AZURE_CONTAINERAPPS_ENV" -l "$AZURE_LOCATION" -o none
printf 'ACR_SERVER=%s\n' "$(az acr show --name "$AZURE_ACR_NAME" --query loginServer -o tsv)"
