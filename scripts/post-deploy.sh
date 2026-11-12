#!/usr/bin/env bash
set -euo pipefail

: "${AZURE_RESOURCE_GROUP:?}" "${STAGE:?Set STAGE=dev or STAGE=prod}"

if [[ "$STAGE" != dev && "$STAGE" != prod ]]; then
  echo 'STAGE must be dev or prod' >&2
  exit 1
fi

FRONTEND_APP_BASE="$(az group show --name "$AZURE_RESOURCE_GROUP" --query 'tags.frontendAppBase' -o tsv)"
BACKEND_APP_BASE="$(az group show --name "$AZURE_RESOURCE_GROUP" --query 'tags.backendAppBase' -o tsv)"
DATABASE_APP_BASE="$(az group show --name "$AZURE_RESOURCE_GROUP" --query 'tags.databaseAppBase' -o tsv)"

if [[ -z "$FRONTEND_APP_BASE" || -z "$BACKEND_APP_BASE" || -z "$DATABASE_APP_BASE" ]]; then
  echo "Resource group $AZURE_RESOURCE_GROUP is missing deployment tags. Run scripts/env-setup.sh first." >&2
  exit 1
fi

declare -A APP_NAMES=(
  [frontend]="${FRONTEND_APP_BASE}-${STAGE}"
  [backend]="${BACKEND_APP_BASE}-${STAGE}"
  [database]="${DATABASE_APP_BASE}-${STAGE}"
)

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
overall_status=ok

for service in frontend backend database; do
  app="${APP_NAMES[$service]}"

  if ! az containerapp revision list -g "$AZURE_RESOURCE_GROUP" -n "$app" \
    --query '[].{name:name,active:properties.active,health:properties.healthState,running:properties.runningState}' \
    -o json > "$TMP/${service}-revisions.json"; then
    echo '{"error":"revision query failed"}' > "$TMP/${service}-revisions.json"
    overall_status=unhealthy
  fi

  if ! az containerapp show -g "$AZURE_RESOURCE_GROUP" -n "$app" \
    --query '{provisioning:properties.provisioningState,fqdn:properties.configuration.ingress.fqdn}' \
    -o json > "$TMP/${service}-status.json"; then
    echo '{"error":"app query failed"}' > "$TMP/${service}-status.json"
    overall_status=unhealthy
  fi

  if ! timeout 20s az containerapp logs show -g "$AZURE_RESOURCE_GROUP" -n "$app" --tail 40 > "$TMP/${service}-logs.txt" 2>&1; then
    echo 'Log collection unavailable' > "$TMP/${service}-logs.txt"
  fi
done

fqdn="$(az containerapp show -g "$AZURE_RESOURCE_GROUP" -n "${APP_NAMES[frontend]}" --query properties.configuration.ingress.fqdn -o tsv 2>/dev/null || true)"
health_status='unreachable'

if [[ -n "$fqdn" ]] && curl -fsS --max-time 25 "https://$fqdn/health" -o "$TMP/health.json"; then
  if jq -e '.status == "ok"' "$TMP/health.json" >/dev/null 2>&1; then
    health_status='ok'
  else
    health_status='unhealthy'
    overall_status=unhealthy
  fi
else
  overall_status=unhealthy
fi

mkdir -p temp/reports
{
  echo '# Deployment Health Results'
  echo
  echo "Stage: $STAGE"
  echo "Timestamp: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "Overall Status: $overall_status"
  if [[ -n "$fqdn" ]]; then
    echo "Frontend URL: https://$fqdn"
  else
    echo 'Frontend URL: (unavailable)'
  fi
  echo "Health Endpoint: $health_status"
  echo
  echo '## Revisions'
  echo

  for service in frontend backend database; do
    echo "### $service"
    echo

    if revisions="$(jq -c '.' "$TMP/${service}-revisions.json" 2>/dev/null)"; then
      echo "- Revisions: $revisions"
    else
      echo '- Revisions: unavailable'
    fi

    if status="$(jq -c '.' "$TMP/${service}-status.json" 2>/dev/null)"; then
      echo "- Status: $status"
    else
      echo '- Status: unavailable'
    fi

    if [[ -s "$TMP/${service}-logs.txt" ]]; then
      log_lines="$(wc -l < "$TMP/${service}-logs.txt")"
      echo "- Recent logs ($log_lines lines captured)"
    else
      echo '- Recent logs: unavailable'
    fi

    echo
  done
} > temp/reports/results.md

cat temp/reports/results.md

if [[ "$overall_status" != ok ]]; then
  exit 1
fi
