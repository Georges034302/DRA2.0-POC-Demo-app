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

# Evidence is the build/test/deploy/health reports produced earlier in this same pipeline run
# (scripts/build.sh, scripts/post-test.sh, scripts/deploy.sh STAGE=dev, scripts/post-deploy.sh STAGE=dev).
REPORTS=(build_report.md test_report.md deployment_report.md results.md)
for report in "${REPORTS[@]}"; do
  if [[ ! -f "temp/reports/$report" ]]; then
    echo "Missing temp/reports/$report — run build.sh, post-test.sh, deploy.sh, and post-deploy.sh first" >&2
    exit 1
  fi
done

IN="${BROKER_INPUT_DIR:-${RUNNER_TEMP:-/tmp}/dra-broker-input}"
OUT="${BROKER_OUTPUT_DIR:-${RUNNER_TEMP:-/tmp}/dra-broker-output}"
mkdir -p "$IN" "$OUT"
chmod 700 "$IN" "$OUT"

for report in "${REPORTS[@]}"; do
  # Broker accepts UTF-8 evidence <= 128 KiB per file.
  head -c 120000 "temp/reports/$report" > "$IN/$report"
done

# mode=pre_deploy is used deliberately even though this review happens after the dev-stage
# deployment: per docs/broker.md, only pre_deploy policy supports APPROVAL_REQUIRED, which
# this pipeline needs to gate promotion to prod. post_deploy policy has no approval tier.
jq -n \
  --arg mode pre_deploy \
  --arg repository "$GITHUB_REPOSITORY" \
  --arg commit "$GITHUB_SHA" \
  --argjson evidence "$(printf '%s\n' "${REPORTS[@]}" | jq -R . | jq -s .)" \
  '{mode: $mode, repository: $repository, commit: $commit, evidence: $evidence}' \
  > "$IN/request.json"

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
decision='ERROR'
if outcome="$(jq -r '.outcome // "ERROR"' "$OUT/result.json" 2>/dev/null)"; then
  case "$outcome" in
    PASS) expected_code=0 ;;
    FAIL) expected_code=10 ;;
    APPROVAL_REQUIRED) expected_code=20 ;;
    ERROR) expected_code=30 ;;
    *) expected_code=-1 ;;
  esac
  if [[ "$expected_code" == "$exit_code" ]]; then
    decision="$outcome"
  fi
fi

if [[ -n "${GITHUB_OUTPUT:-}" ]]; then
  echo "decision=$decision" >> "$GITHUB_OUTPUT"
fi

echo "Governance outcome: $decision"
if [[ "$decision" == ERROR ]]; then
  exit 1
fi
