#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
"$ROOT/scripts/validate.sh" azure
"$ROOT/scripts/env-setup.sh"
cat <<'EOF'
Manual GitHub/Azure prerequisites (not automatically configured):
- Configure Azure OIDC federated identity for protected main/deployment jobs.
- Grant the workflow identity resource-group deployment and ACR push privileges.
- Configure each Azure Container App managed identity with AcrPull (script provisions
  these assignments if the deployment identity has role-assignment permission).
- Set repository variables and secrets listed in README.md; PIN the broker image digest.
- Configure required reviewers on environment dra-approval before enabling approval releases.
- Ensure private GHCR token has read:packages permission for the scanner image.
EOF
