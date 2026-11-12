#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ "${1:-}" != '--publish' ]]; then
  for part in frontend backend database; do
    docker build -t "dra20-${part}:local" "./${part}"
  done
  echo 'Built three local application images.'
  exit 0
fi

: "${AZURE_RESOURCE_GROUP:?}" "${GITHUB_SHA:?}" "${BUILD_MANIFEST:?}"

if [[ ! "$GITHUB_SHA" =~ ^[0-9a-f]{40}$ ]]; then
  echo 'GITHUB_SHA must be the checked-out commit SHA' >&2
  exit 1
fi

if [[ "$(git rev-parse HEAD)" != "$GITHUB_SHA" ]]; then
  echo 'Checkout differs from GITHUB_SHA' >&2
  exit 1
fi

# Registry name is generated once by env-setup.sh and stored as a resource-group tag.
REGISTRY_NAME="$(az group show --name "$AZURE_RESOURCE_GROUP" --query 'tags.registryName' -o tsv)"

if [[ -z "$REGISTRY_NAME" ]]; then
  echo "Resource group $AZURE_RESOURCE_GROUP is missing deployment tags. Run scripts/env-setup.sh first." >&2
  exit 1
fi

REGISTRY="$(az acr show -n "$REGISTRY_NAME" --query loginServer -o tsv)"

if [[ "$REGISTRY" != *.azurecr.io ]]; then
  echo 'Unexpected ACR registry server' >&2
  exit 1
fi

az acr login --name "$REGISTRY_NAME" >/dev/null

declare -A DIGESTS

for part in frontend backend database; do
  tag="$REGISTRY/dra20-$part:$GITHUB_SHA"
  docker build --pull -t "$tag" "./$part"
  docker push "$tag" >/dev/null
  docker pull "$tag" >/dev/null
  digest="$(docker image inspect --format '{{index .RepoDigests 0}}' "$tag")"

  if [[ "$digest" != "$REGISTRY/dra20-$part@sha256:"* ]]; then
    echo "Cannot resolve $part image digest" >&2
    exit 1
  fi

  DIGESTS[$part]="$digest"
done

mkdir -p "$(dirname "$BUILD_MANIFEST")"
cat > "$BUILD_MANIFEST" <<EOF
{
  "commit": "$GITHUB_SHA",
  "images": {
    "frontend": "${DIGESTS[frontend]}",
    "backend": "${DIGESTS[backend]}",
    "database": "${DIGESTS[database]}"
  }
}
EOF

mkdir -p temp/reports
cat > temp/reports/build_report.md <<EOF
# Build Report

Commit: $GITHUB_SHA
Timestamp: $(date -u +%Y-%m-%dT%H:%M:%SZ)

## Images

| Service | Image Digest |
|---|---|
| frontend | ${DIGESTS[frontend]} |
| backend | ${DIGESTS[backend]} |
| database | ${DIGESTS[database]} |
EOF

printf 'Published application images at immutable digests to %s\n' "$BUILD_MANIFEST"
