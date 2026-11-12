#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

mkdir -p temp/reports
COMMIT="${GITHUB_SHA:-$(git rev-parse HEAD)}"
OVERALL_EXIT=0

declare -A SUITE_STATUS SUITE_TOTAL SUITE_PASSED SUITE_FAILED SUITE_ERRORS SUITE_SKIPPED SUITE_DURATION

run_suite() {
  local key="$1" file="$2" junit exit_code line
  junit="$(mktemp)"

  set +e
  python3 -m pytest "$file" -q --junit-xml="$junit"
  exit_code=$?
  set -e

  line="$(grep -m1 '<testsuite' "$junit")"
  local total failures errors skipped duration passed
  total="$(grep -oP 'tests="\K[0-9]+' <<< "$line")"
  failures="$(grep -oP 'failures="\K[0-9]+' <<< "$line")"
  errors="$(grep -oP 'errors="\K[0-9]+' <<< "$line")"
  skipped="$(grep -oP 'skipped="\K[0-9]+' <<< "$line")"
  duration="$(grep -oP 'time="\K[0-9.]+' <<< "$line")"
  passed=$((total - failures - errors - skipped))

  SUITE_TOTAL[$key]=$total
  SUITE_PASSED[$key]=$passed
  SUITE_FAILED[$key]=$failures
  SUITE_ERRORS[$key]=$errors
  SUITE_SKIPPED[$key]=$skipped
  SUITE_DURATION[$key]=$duration

  if [[ "$exit_code" == 0 ]]; then
    SUITE_STATUS[$key]=Success
  else
    SUITE_STATUS[$key]=Failed
    OVERALL_EXIT=1
  fi

  rm -f "$junit"
}

run_suite DB tests/post-commit/test_database.py
run_suite TASKS tests/post-commit/test_tasks.py
run_suite SECURITY tests/post-commit/test_security.py

{
  echo '# Test Report'
  echo
  if [[ "$OVERALL_EXIT" == 0 ]]; then
    echo 'Status: Success'
  else
    echo 'Status: Failed'
  fi
  echo "Commit: $COMMIT"
  echo "Timestamp: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo
  echo '## Results by Suite'
  echo
  echo '| Suite | Status | Passed | Failed | Errors | Skipped | Duration |'
  echo '|---|---|---|---|---|---|---|'
  for key in DB TASKS SECURITY; do
    echo "| $key | ${SUITE_STATUS[$key]} | ${SUITE_PASSED[$key]} | ${SUITE_FAILED[$key]} | ${SUITE_ERRORS[$key]} | ${SUITE_SKIPPED[$key]} | ${SUITE_DURATION[$key]}s |"
  done
} > temp/reports/test_report.md

cat temp/reports/test_report.md
exit "$OVERALL_EXIT"
