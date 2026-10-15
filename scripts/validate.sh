#!/usr/bin/env bash
set -euo pipefail
for bin in git docker python3; do command -v "$bin" >/dev/null || { echo "Missing $bin" >&2; exit 1; }; done
if [[ "${1:-local}" == azure ]];then
 for bin in az gh;do command -v "$bin" >/dev/null || { echo "Missing $bin" >&2;exit 1; };done
 az account show >/dev/null
 : "${AZURE_RESOURCE_GROUP:?}" "${AZURE_LOCATION:?}" "${AZURE_ACR_NAME:?}" "${AZURE_CONTAINERAPPS_ENV:?}"
fi
echo 'Prerequisites OK.'
