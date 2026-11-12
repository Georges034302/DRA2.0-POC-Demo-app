#!/usr/bin/env bash
set -euo pipefail

: "${AZURE_RESOURCE_GROUP:?}" "${STAGE:?Set STAGE=dev or STAGE=prod}"
: "${INTERNAL_API_TOKEN:?}" "${DEMO_USERNAME:?}" "${DEMO_PASSWORD:?}"
: "${GITHUB_SHA:?}" "${BUILD_MANIFEST:?}"

if [[ "$STAGE" != dev && "$STAGE" != prod ]]; then
  echo 'STAGE must be dev or prod' >&2
  exit 1
fi

MANIFEST_COMMIT="$(jq -r '.commit' "$BUILD_MANIFEST")"
if [[ "$MANIFEST_COMMIT" != "$GITHUB_SHA" ]]; then
  echo 'Build manifest commit mismatch' >&2
  exit 1
fi

DB_IMAGE="$(jq -r '.images.database' "$BUILD_MANIFEST")"
BACK_IMAGE="$(jq -r '.images.backend' "$BUILD_MANIFEST")"
FRONT_IMAGE="$(jq -r '.images.frontend' "$BUILD_MANIFEST")"

DIGEST_RE='^[[:alnum:]_.-]+\.azurecr\.io/[[:alnum:]_.-]+@sha256:[a-f0-9]{64}$'
for image in "$DB_IMAGE" "$BACK_IMAGE" "$FRONT_IMAGE"; do
  if [[ ! "$image" =~ $DIGEST_RE ]]; then
    echo "Invalid image digest: $image" >&2
    exit 1
  fi
done

REGISTRY_NAME="$(az group show --name "$AZURE_RESOURCE_GROUP" --query 'tags.registryName' -o tsv)"
FRONTEND_APP_BASE="$(az group show --name "$AZURE_RESOURCE_GROUP" --query 'tags.frontendAppBase' -o tsv)"
BACKEND_APP_BASE="$(az group show --name "$AZURE_RESOURCE_GROUP" --query 'tags.backendAppBase' -o tsv)"
DATABASE_APP_BASE="$(az group show --name "$AZURE_RESOURCE_GROUP" --query 'tags.databaseAppBase' -o tsv)"
AZURE_CONTAINERAPPS_ENV="$(az group show --name "$AZURE_RESOURCE_GROUP" --query 'tags.envName' -o tsv)"

if [[ -z "$REGISTRY_NAME" || -z "$FRONTEND_APP_BASE" || -z "$BACKEND_APP_BASE" || -z "$DATABASE_APP_BASE" || -z "$AZURE_CONTAINERAPPS_ENV" ]]; then
  echo "Resource group $AZURE_RESOURCE_GROUP is missing deployment tags. Run scripts/env-setup.sh first." >&2
  exit 1
fi

FRONTEND_APP="${FRONTEND_APP_BASE}-${STAGE}"
BACKEND_APP="${BACKEND_APP_BASE}-${STAGE}"
DATABASE_APP="${DATABASE_APP_BASE}-${STAGE}"

REGISTRY="$(az acr show -n "$REGISTRY_NAME" --query loginServer -o tsv)"
ACR_ID="$(az acr show -n "$REGISTRY_NAME" --query id -o tsv)"

ensure_app() {
  local name="$1" port="$2" ingress="$3"

  if ! az containerapp show -g "$AZURE_RESOURCE_GROUP" -n "$name" >/dev/null 2>&1; then
    az containerapp create -g "$AZURE_RESOURCE_GROUP" -n "$name" \
      --environment "$AZURE_CONTAINERAPPS_ENV" \
      --image mcr.microsoft.com/azuredocs/containerapps-helloworld:latest \
      --ingress "$ingress" --target-port "$port" --system-assigned \
      --min-replicas 1 --max-replicas 1 --output none
  fi

  local principal
  principal="$(az containerapp identity assign -g "$AZURE_RESOURCE_GROUP" -n "$name" --system-assigned --query principalId -o tsv)"

  if [[ -z "$principal" || "$principal" == None ]]; then
    principal="$(az containerapp show -g "$AZURE_RESOURCE_GROUP" -n "$name" --query identity.principalId -o tsv)"
  fi

  if [[ -z "$principal" || "$principal" == None ]]; then
    echo 'Managed identity missing' >&2
    return 1
  fi

  if ! az role assignment list --assignee "$principal" --role AcrPull --scope "$ACR_ID" --query '[0].id' -o tsv | grep -q .; then
    az role assignment create --assignee-object-id "$principal" --assignee-principal-type ServicePrincipal \
      --role AcrPull --scope "$ACR_ID" -o none
  fi

  az containerapp registry set -g "$AZURE_RESOURCE_GROUP" -n "$name" --server "$REGISTRY" --identity system -o none
}

ensure_app "$DATABASE_APP" 5000 internal
az containerapp secret set -g "$AZURE_RESOURCE_GROUP" -n "$DATABASE_APP" \
  --secrets "service-token=$INTERNAL_API_TOKEN" -o none
az containerapp update -g "$AZURE_RESOURCE_GROUP" -n "$DATABASE_APP" --image "$DB_IMAGE" \
  --set-env-vars DATABASE_PATH=/data/tasks.db INTERNAL_API_TOKEN=secretref:service-token -o none
DB_FQDN="$(az containerapp show -g "$AZURE_RESOURCE_GROUP" -n "$DATABASE_APP" --query properties.configuration.ingress.fqdn -o tsv)"
[[ -n "$DB_FQDN" ]] || exit 1

ensure_app "$BACKEND_APP" 5000 internal
az containerapp secret set -g "$AZURE_RESOURCE_GROUP" -n "$BACKEND_APP" \
  --secrets "service-token=$INTERNAL_API_TOKEN" -o none
az containerapp update -g "$AZURE_RESOURCE_GROUP" -n "$BACKEND_APP" --image "$BACK_IMAGE" \
  --set-env-vars "DATABASE_URL=https://$DB_FQDN" INTERNAL_API_TOKEN=secretref:service-token -o none
BACK_FQDN="$(az containerapp show -g "$AZURE_RESOURCE_GROUP" -n "$BACKEND_APP" --query properties.configuration.ingress.fqdn -o tsv)"
[[ -n "$BACK_FQDN" ]] || exit 1

ensure_app "$FRONTEND_APP" 8080 external
az containerapp secret set -g "$AZURE_RESOURCE_GROUP" -n "$FRONTEND_APP" \
  --secrets "service-token=$INTERNAL_API_TOKEN" "demo-user=$DEMO_USERNAME" "demo-password=$DEMO_PASSWORD" -o none
az containerapp update -g "$AZURE_RESOURCE_GROUP" -n "$FRONTEND_APP" --image "$FRONT_IMAGE" \
  --set-env-vars "BACKEND_URL=https://$BACK_FQDN" INTERNAL_API_TOKEN=secretref:service-token \
  DEMO_USERNAME=secretref:demo-user DEMO_PASSWORD=secretref:demo-password -o none
FQDN="$(az containerapp show -g "$AZURE_RESOURCE_GROUP" -n "$FRONTEND_APP" --query properties.configuration.ingress.fqdn -o tsv)"

mkdir -p temp/reports
cat > temp/reports/deployment_report.md <<EOF
# Deployment Report

Status: Success
Stage: $STAGE
Commit: $GITHUB_SHA
Timestamp: $(date -u +%Y-%m-%dT%H:%M:%SZ)

## Services

| Service | App Name | Image Digest | FQDN |
|---|---|---|---|
| database | $DATABASE_APP | $DB_IMAGE | $DB_FQDN |
| backend | $BACKEND_APP | $BACK_IMAGE | $BACK_FQDN |
| frontend | $FRONTEND_APP | $FRONT_IMAGE | $FQDN |
EOF

cat temp/reports/deployment_report.md
echo "Frontend ($STAGE): https://$FQDN"
