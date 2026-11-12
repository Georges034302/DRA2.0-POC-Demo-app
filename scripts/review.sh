#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

: "${BROKER_IMAGE_DIGEST:?Set the private GHCR image by immutable digest}"
: "${GHCR_READ_TOKEN:?}" "${GHCR_USER:?}" "${GITHUB_SHA:?}" "${GITHUB_REPOSITORY:?}"
: "${AI_PROVIDER:?}"

case "$AI_PROVIDER" in
  gemini)
    : "${GEMINI_API_KEY:?}" "${GEMINI_MODEL:?}"
    ;;
  groq)
    : "${GROQ_API_KEY:?}" "${GROQ_MODEL:?}"
    ;;
  *)
    echo 'AI_PROVIDER must be gemini or groq' >&2
    exit 1
    ;;
esac

if [[ ! "$BROKER_IMAGE_DIGEST" =~ ^ghcr\.io/[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+@sha256:[a-f0-9]{64}$ ]]; then
  echo 'BROKER_IMAGE_DIGEST must be a GHCR sha256 digest' >&2
  exit 1
fi

# Evidence is the test/deploy/health reports produced earlier in this same pipeline run
# (scripts/post-test.sh, scripts/deploy.sh STAGE=dev, scripts/post-deploy.sh STAGE=dev).
for report in test-report.md deploy-report.md health-report.md; do
  if [[ ! -f "reports/$report" ]]; then
    echo "Missing reports/$report — run post-test.sh, deploy.sh, and post-deploy.sh first" >&2
    exit 1
  fi
done

IN="${BROKER_INPUT_DIR:-${RUNNER_TEMP:-/tmp}/dra-broker-input}"
OUT="${BROKER_OUTPUT_DIR:-${RUNNER_TEMP:-/tmp}/dra-broker-output}"
mkdir -p "$IN" "$OUT"
chmod 700 "$IN" "$OUT"

for report in test-report.md deploy-report.md health-report.md; do
  cp "reports/$report" "$IN/$report"
done

python3 - "$IN" "$GITHUB_REPOSITORY" "$GITHUB_SHA" <<'PYCODE'
import json
import pathlib
import sys

p = pathlib.Path(sys.argv[1])
evidence = ['test-report.md', 'deploy-report.md', 'health-report.md']

# Broker accepts UTF-8 evidence <= 128 KiB per file. Exclude invalid bytes and cap at 120 KiB.
for name in evidence:
    f = p / name
    text = f.read_bytes()[:120_000].decode('utf8', 'replace')
    f.write_text(text, encoding='utf8')

# mode=pre_deploy is used deliberately even though this review happens after the dev-stage
# deployment: per docs/broker.md, only pre_deploy policy supports APPROVAL_REQUIRED, which
# this pipeline needs to gate promotion to prod. post_deploy policy has no approval tier.
request = {
    'mode': 'pre_deploy',
    'repository': sys.argv[2],
    'commit': sys.argv[3],
    'evidence': evidence,
}
(p / 'request.json').write_text(json.dumps(request))
PYCODE

printf '%s' "$GHCR_READ_TOKEN" | docker login ghcr.io -u "$GHCR_USER" --password-stdin >/dev/null
docker pull "$BROKER_IMAGE_DIGEST" >/dev/null

set +e
docker run --rm --user "$(id -u):$(id -g)" --read-only --cap-drop=ALL \
  --security-opt=no-new-privileges \
  -v "$IN:/evidence:ro" -v "$IN/request.json:/request.json:ro" -v "$OUT:/output" \
  -e AI_PROVIDER -e GEMINI_API_KEY -e GEMINI_MODEL -e GROQ_API_KEY -e GROQ_MODEL \
  "$BROKER_IMAGE_DIGEST" --request /request.json --evidence-dir /evidence \
  --output /output/result.json --provider "$AI_PROVIDER"
exit_code=$?
set -e

# Outcome is treated as untrusted until it matches the scanner's exit code contract.
python3 - "$OUT/result.json" "$exit_code" "${GITHUB_OUTPUT:-}" <<'PYCODE'
import json
import pathlib
import sys

expected = {'PASS': 0, 'FAIL': 10, 'APPROVAL_REQUIRED': 20, 'ERROR': 30}

try:
    r = json.loads(pathlib.Path(sys.argv[1]).read_text())
    decision = r.get('outcome', 'ERROR')
    if decision not in expected or expected[decision] != int(sys.argv[2]):
        decision = 'ERROR'
except (ValueError, OSError, TypeError):
    decision = 'ERROR'

if sys.argv[3]:
    with open(sys.argv[3], 'a', encoding='utf8') as f:
        f.write(f'decision={decision}\n')

print('Governance outcome:', decision)
if decision == 'ERROR':
    sys.exit(1)
PYCODE
