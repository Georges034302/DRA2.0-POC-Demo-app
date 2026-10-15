#!/usr/bin/env bash
set -euo pipefail
: "${AZURE_RESOURCE_GROUP:?}"
[[ "${CONFIRM_DELETE:-}" == "$AZURE_RESOURCE_GROUP" ]] || { echo "To delete resource group set CONFIRM_DELETE=$AZURE_RESOURCE_GROUP" >&2; exit 1; }
az group delete --name "$AZURE_RESOURCE_GROUP" --yes --no-wait
echo "Azure resource group deletion requested: $AZURE_RESOURCE_GROUP"
