#!/usr/bin/env bash
set -euo pipefail
: "${AZURE_RESOURCE_GROUP:?}" "${AZURE_FRONTEND_APP:?}" "${AZURE_BACKEND_APP:?}" "${AZURE_DATABASE_APP:?}"
: "${BROKER_IMAGE_DIGEST:?}" "${GHCR_READ_TOKEN:?}" "${GHCR_USER:?}" "${GITHUB_REPOSITORY:?}" "${GITHUB_SHA:?}" "${AI_PROVIDER:?}"
case "$AI_PROVIDER" in
 gemini) : "${GEMINI_API_KEY:?}" "${GEMINI_MODEL:?}";;
 groq) : "${GROQ_API_KEY:?}" "${GROQ_MODEL:?}";;
 *) exit 1;;
esac
[[ "$BROKER_IMAGE_DIGEST" =~ ^ghcr\.io/[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+@sha256:[a-f0-9]{64}$ ]] || { echo 'Invalid pinned scanner digest' >&2; exit 1; }
IN="${BROKER_INPUT_DIR:-${RUNNER_TEMP:-/tmp}/dra-post-input}"
OUT="${BROKER_OUTPUT_DIR:-${RUNNER_TEMP:-/tmp}/dra-post-output}"
mkdir -p "$IN" "$OUT";chmod 700 "$IN" "$OUT"
status=ok
for part in FRONTEND BACKEND DATABASE; do
 var="AZURE_${part}_APP"; app="${!var}"
 if ! az containerapp revision list -g "$AZURE_RESOURCE_GROUP" -n "$app" --query '[].{name:name,active:properties.active,health:properties.healthState,running:properties.runningState}' -o json > "$IN/${part,,}-revisions.json"; then
   echo '{"error":"revision query failed"}' > "$IN/${part,,}-revisions.json";status=unhealthy
 fi
 if ! az containerapp show -g "$AZURE_RESOURCE_GROUP" -n "$app" --query '{provisioning:properties.provisioningState,fqdn:properties.configuration.ingress.fqdn}' -o json > "$IN/${part,,}-status.json"; then
   echo '{"error":"app query failed"}' > "$IN/${part,,}-status.json";status=unhealthy
 fi
 timeout 20s az containerapp logs show -g "$AZURE_RESOURCE_GROUP" -n "$app" --tail 40 > "$IN/${part,,}-logs.txt" 2>&1 || echo 'Log collection unavailable' > "$IN/${part,,}-logs.txt"
done
fqdn="$(az containerapp show -g "$AZURE_RESOURCE_GROUP" -n "$AZURE_FRONTEND_APP" --query properties.configuration.ingress.fqdn -o tsv 2>/dev/null || true)"
if [[ -n "$fqdn" ]] && curl -fsS --max-time 25 "https://$fqdn/health" -o "$IN/health.json" && python3 - "$IN/health.json" <<'PYCODE'
import json,sys
assert json.load(open(sys.argv[1]))['status']=='ok'
PYCODE
then :;else status=unhealthy; echo '{"status":"unhealthy"}' > "$IN/health.json";fi
STATUS="$status" python3 - "$IN" "$GITHUB_REPOSITORY" "$GITHUB_SHA" <<'PYCODE'
import json,os,pathlib,sys
p=pathlib.Path(sys.argv[1]);files=sorted(x.name for x in p.iterdir() if x.is_file() and x.name!='request.json')
for name in files:
 f=p/name;f.write_text(f.read_bytes()[:12_000].decode('utf8','replace'),encoding='utf8')
(p/'status.txt').write_text('deterministic health: '+os.environ['STATUS'])
files.append('status.txt')
(p/'request.json').write_text(json.dumps({'mode':'post_deploy','repository':sys.argv[2],'commit':sys.argv[3],'evidence':files}))
PYCODE
printf '%s' "$GHCR_READ_TOKEN" | docker login ghcr.io -u "$GHCR_USER" --password-stdin >/dev/null
docker pull "$BROKER_IMAGE_DIGEST" >/dev/null
set +e
docker run --rm --user "$(id -u):$(id -g)" --read-only --cap-drop=ALL --security-opt=no-new-privileges \
 -v "$IN:/evidence:ro" -v "$IN/request.json:/request.json:ro" -v "$OUT:/output" \
 -e AI_PROVIDER -e GEMINI_API_KEY -e GEMINI_MODEL -e GROQ_API_KEY -e GROQ_MODEL \
 "$BROKER_IMAGE_DIGEST" --request /request.json --evidence-dir /evidence --output /output/result.json --provider "$AI_PROVIDER"
code=$?
set -e
python3 - "$OUT/result.json" "$code" "$status" <<'PYCODE'
import json,pathlib,sys
p=pathlib.Path(sys.argv[1]);mapping={'PASS':0,'FAIL':10,'APPROVAL_REQUIRED':20,'ERROR':30}
try:r=json.loads(p.read_text()); outcome=r.get('outcome'); valid=mapping.get(outcome)==int(sys.argv[2])
except (OSError,ValueError,TypeError):outcome='ERROR';valid=False
if sys.argv[3]!='ok':outcome='FAIL'
if not valid and sys.argv[3]=='ok':outcome='ERROR'
print('Post-deployment verification:',outcome)
if outcome!='PASS':sys.exit(1)
PYCODE
