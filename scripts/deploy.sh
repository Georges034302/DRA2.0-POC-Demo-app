#!/usr/bin/env bash
set -euo pipefail
: "${AZURE_RESOURCE_GROUP:?}" "${AZURE_CONTAINERAPPS_ENV:?}" "${AZURE_ACR_NAME:?}"
: "${AZURE_FRONTEND_APP:?}" "${AZURE_BACKEND_APP:?}" "${AZURE_DATABASE_APP:?}"
: "${INTERNAL_API_TOKEN:?}" "${DEMO_USERNAME:?}" "${DEMO_PASSWORD:?}"
: "${GITHUB_SHA:?}" "${BUILD_MANIFEST:?}"
# The ONLY deployable images are the previously built immutable digests from the approved commit.
python3 - "$BUILD_MANIFEST" "$GITHUB_SHA" <<'PYCODE'
import json,re,sys,pathlib
m=json.loads(pathlib.Path(sys.argv[1]).read_text())
assert m['commit']==sys.argv[2], 'Build manifest commit mismatch'
assert set(m['images'])=={'frontend','backend','database'}
for x in m['images'].values():assert re.fullmatch(r'[\w.-]+\.azurecr\.io/[\w.-]+@sha256:[a-f0-9]{64}',x), 'Invalid image digest'
PYCODE
readarray -t DIGESTS < <(python3 - "$BUILD_MANIFEST" <<'PYCODE'
import json,sys
m=json.load(open(sys.argv[1]))['images']
for k in ('database','backend','frontend'):print(m[k])
PYCODE
)
DB_IMAGE="${DIGESTS[0]}";BACK_IMAGE="${DIGESTS[1]}";FRONT_IMAGE="${DIGESTS[2]}"
REGISTRY="$(az acr show -n "$AZURE_ACR_NAME" --query loginServer -o tsv)"
ACR_ID="$(az acr show -n "$AZURE_ACR_NAME" --query id -o tsv)"
ensure_app() {
 local name="$1" port="$2" ingress="$3" image="$4"
 if ! az containerapp show -g "$AZURE_RESOURCE_GROUP" -n "$name" >/dev/null 2>&1; then
   # Bootstrap with an available ACR image, then attach pull identity.
   az containerapp create -g "$AZURE_RESOURCE_GROUP" -n "$name" \
     --environment "$AZURE_CONTAINERAPPS_ENV" --image mcr.microsoft.com/azuredocs/containerapps-helloworld:latest \
     --ingress "$ingress" --target-port "$port" --system-assigned \
     --min-replicas 1 --max-replicas 1 --output none
 fi
 local principal
 principal="$(az containerapp identity assign -g "$AZURE_RESOURCE_GROUP" -n "$name" --system-assigned --query principalId -o tsv)"
 if [[ -z "$principal" || "$principal" == None ]];then
   principal="$(az containerapp show -g "$AZURE_RESOURCE_GROUP" -n "$name" --query identity.principalId -o tsv)"
 fi
 [[ -n "$principal" && "$principal" != None ]] || { echo 'Managed identity missing' >&2;return 1; }
 # RBAC provisioning may require elevated Azure privileges; errors are not suppressed.
 if ! az role assignment list --assignee "$principal" --role AcrPull --scope "$ACR_ID" --query '[0].id' -o tsv | grep -q .;then
   az role assignment create --assignee-object-id "$principal" --assignee-principal-type ServicePrincipal --role AcrPull --scope "$ACR_ID" -o none
 fi
 az containerapp registry set -g "$AZURE_RESOURCE_GROUP" -n "$name" --server "$REGISTRY" --identity system -o none
}
ensure_app "$AZURE_DATABASE_APP" 5000 internal "$DB_IMAGE"
az containerapp secret set -g "$AZURE_RESOURCE_GROUP" -n "$AZURE_DATABASE_APP" --secrets "service-token=$INTERNAL_API_TOKEN" -o none
az containerapp update -g "$AZURE_RESOURCE_GROUP" -n "$AZURE_DATABASE_APP" --image "$DB_IMAGE" \
 --set-env-vars DATABASE_PATH=/data/tasks.db INTERNAL_API_TOKEN=secretref:service-token -o none
DB_FQDN="$(az containerapp show -g "$AZURE_RESOURCE_GROUP" -n "$AZURE_DATABASE_APP" --query properties.configuration.ingress.fqdn -o tsv)"
[[ -n "$DB_FQDN" ]] || exit 1
ensure_app "$AZURE_BACKEND_APP" 5000 internal "$BACK_IMAGE"
az containerapp secret set -g "$AZURE_RESOURCE_GROUP" -n "$AZURE_BACKEND_APP" --secrets "service-token=$INTERNAL_API_TOKEN" -o none
az containerapp update -g "$AZURE_RESOURCE_GROUP" -n "$AZURE_BACKEND_APP" --image "$BACK_IMAGE" \
 --set-env-vars "DATABASE_URL=https://$DB_FQDN" INTERNAL_API_TOKEN=secretref:service-token -o none
BACK_FQDN="$(az containerapp show -g "$AZURE_RESOURCE_GROUP" -n "$AZURE_BACKEND_APP" --query properties.configuration.ingress.fqdn -o tsv)"
[[ -n "$BACK_FQDN" ]] || exit 1
ensure_app "$AZURE_FRONTEND_APP" 8080 external "$FRONT_IMAGE"
az containerapp secret set -g "$AZURE_RESOURCE_GROUP" -n "$AZURE_FRONTEND_APP" --secrets "service-token=$INTERNAL_API_TOKEN" "demo-user=$DEMO_USERNAME" "demo-password=$DEMO_PASSWORD" -o none
az containerapp update -g "$AZURE_RESOURCE_GROUP" -n "$AZURE_FRONTEND_APP" --image "$FRONT_IMAGE" \
 --set-env-vars "BACKEND_URL=https://$BACK_FQDN" INTERNAL_API_TOKEN=secretref:service-token \
 DEMO_USERNAME=secretref:demo-user DEMO_PASSWORD=secretref:demo-password -o none
FQDN="$(az containerapp show -g "$AZURE_RESOURCE_GROUP" -n "$AZURE_FRONTEND_APP" --query properties.configuration.ingress.fqdn -o tsv)"
echo "Frontend: https://$FQDN"
