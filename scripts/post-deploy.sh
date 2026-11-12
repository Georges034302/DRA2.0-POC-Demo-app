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
  if python3 -c "import json,sys; sys.exit(0 if json.load(open(sys.argv[1]))['status']=='ok' else 1)" "$TMP/health.json"; then
    health_status='ok'
  else
    health_status='unhealthy'
    overall_status=unhealthy
  fi
else
  overall_status=unhealthy
fi

mkdir -p reports
python3 - "$TMP" reports/health-report.md "$STAGE" "$overall_status" "$health_status" "$fqdn" <<'PYCODE'
import datetime
import json
import pathlib
import sys

tmp_dir, report_path, stage, overall_status, health_status, fqdn = sys.argv[1:7]
tmp = pathlib.Path(tmp_dir)

lines = [
    '# Health Report',
    '',
    f'Stage: {stage}',
    f'Timestamp: {datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}',
    f'Overall Status: {overall_status}',
    f'Frontend URL: https://{fqdn}' if fqdn else 'Frontend URL: (unavailable)',
    f'Health Endpoint: {health_status}',
    '',
    '## Revisions',
    '',
]

for service in ('frontend', 'backend', 'database'):
    revisions_path = tmp / f'{service}-revisions.json'
    status_path = tmp / f'{service}-status.json'
    logs_path = tmp / f'{service}-logs.txt'

    lines.append(f'### {service}')
    lines.append('')

    try:
        revisions = json.loads(revisions_path.read_text())
        lines.append(f'- Revisions: {json.dumps(revisions)}')
    except (OSError, ValueError):
        lines.append('- Revisions: unavailable')

    try:
        status = json.loads(status_path.read_text())
        lines.append(f'- Status: {json.dumps(status)}')
    except (OSError, ValueError):
        lines.append('- Status: unavailable')

    try:
        log_lines = logs_path.read_text().strip().splitlines()
        lines.append(f'- Recent logs ({len(log_lines)} lines captured)')
    except OSError:
        lines.append('- Recent logs: unavailable')

    lines.append('')

pathlib.Path(report_path).write_text('\n'.join(lines) + '\n')
PYCODE

cat reports/health-report.md

if [[ "$overall_status" != ok ]]; then
  exit 1
fi
