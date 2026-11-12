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

: "${AZURE_ACR_NAME:?}" "${GITHUB_SHA:?}" "${BUILD_MANIFEST:?}"

if [[ ! "$GITHUB_SHA" =~ ^[0-9a-f]{40}$ ]]; then
  echo 'GITHUB_SHA must be the checked-out commit SHA' >&2
  exit 1
fi

if [[ "$(git rev-parse HEAD)" != "$GITHUB_SHA" ]]; then
  echo 'Checkout differs from GITHUB_SHA' >&2
  exit 1
fi

REGISTRY="$(az acr show -n "$AZURE_ACR_NAME" --query loginServer -o tsv)"

if [[ "$REGISTRY" != *.azurecr.io ]]; then
  echo 'Unexpected ACR registry server' >&2
  exit 1
fi

az acr login --name "$AZURE_ACR_NAME" >/dev/null

TMP="$(mktemp)"
trap 'rm -f "$TMP"' EXIT
printf '%s\n' '{}' > "$TMP"

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

  python3 - "$TMP" "$part" "$digest" <<'PYCODE'
import json
import sys
import pathlib

path = pathlib.Path(sys.argv[1])
data = json.loads(path.read_text())
data[sys.argv[2]] = sys.argv[3]
path.write_text(json.dumps(data))
PYCODE
done

python3 - "$TMP" "$BUILD_MANIFEST" "$GITHUB_SHA" <<'PYCODE'
import json
import sys
import pathlib

images = json.loads(pathlib.Path(sys.argv[1]).read_text())
manifest = pathlib.Path(sys.argv[2])
manifest.parent.mkdir(parents=True, exist_ok=True)
manifest.write_text(json.dumps({'commit': sys.argv[3], 'images': images}, indent=2) + '\n')
PYCODE

printf 'Published application images at immutable digests to %s\n' "$BUILD_MANIFEST"
