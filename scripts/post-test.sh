#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

mkdir -p temp/reports
JUNIT_FILE="$(mktemp)"
COMMIT="${GITHUB_SHA:-$(git rev-parse HEAD)}"

set +e
python3 -m pytest tests/post-commit -q --junit-xml="$JUNIT_FILE"
PYTEST_EXIT=$?
set -e

SUITE_LINE="$(grep -m1 '<testsuite' "$JUNIT_FILE")"
TOTAL="$(grep -oP 'tests="\K[0-9]+' <<< "$SUITE_LINE")"
FAILURES="$(grep -oP 'failures="\K[0-9]+' <<< "$SUITE_LINE")"
ERRORS="$(grep -oP 'errors="\K[0-9]+' <<< "$SUITE_LINE")"
SKIPPED="$(grep -oP 'skipped="\K[0-9]+' <<< "$SUITE_LINE")"
DURATION="$(grep -oP 'time="\K[0-9.]+' <<< "$SUITE_LINE")"
PASSED=$((TOTAL - FAILURES - ERRORS - SKIPPED))

if [[ "$PYTEST_EXIT" == 0 ]]; then
  STATUS=Success
else
  STATUS=Failed
fi

cat > temp/reports/test_report.md <<EOF
# Test Report

Status: $STATUS
Commit: $COMMIT
Timestamp: $(date -u +%Y-%m-%dT%H:%M:%SZ)

## Results

- Total: $TOTAL
- Passed: $PASSED
- Failed: $FAILURES
- Errors: $ERRORS
- Skipped: $SKIPPED
- Duration: ${DURATION}s
EOF

rm -f "$JUNIT_FILE"
cat temp/reports/test_report.md
exit "$PYTEST_EXIT"
