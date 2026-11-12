#!/usr/bin/env bash
set -euo pipefail

# Git pre-commit hook: lint + secret scan + dependency audit. Install with:
#   ln -sf ../../scripts/pre-test.sh .git/hooks/pre-commit

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

for bin in ruff detect-secrets pip-audit; do
  if ! command -v "$bin" >/dev/null; then
    echo "Missing $bin — install with: pip install ruff detect-secrets pip-audit" >&2
    exit 1
  fi
done

echo '=== ruff ==='
ruff check backend database tests

echo '=== detect-secrets ==='
if [[ ! -f .secrets.baseline ]]; then
  echo 'No .secrets.baseline found — generating one from current findings (review it before committing).'
  detect-secrets scan --exclude-files '\.git/' > .secrets.baseline
fi

STAGED_FILES="$(git diff --staged --name-only --diff-filter=ACM)"
if [[ -n "$STAGED_FILES" ]]; then
  # shellcheck disable=SC2086
  detect-secrets-hook --baseline .secrets.baseline $STAGED_FILES
else
  echo 'No staged files to scan.'
fi

echo '=== pip-audit ==='
pip-audit -r backend/requirements.txt -r database/requirements.txt

if [[ -n "$(find tests/pre-commit -type f ! -name '.gitkeep' 2>/dev/null)" ]]; then
  echo '=== pytest (tests/pre-commit) ==='
  python3 -m pytest tests/pre-commit -q
else
  echo 'No tests in tests/pre-commit yet — skipping.'
fi

echo '=== pre-test checks passed ==='
