#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

REPORT_FILE="reports/test-report.md"
JUNIT_FILE="$(mktemp)"
COMMIT="${GITHUB_SHA:-$(git rev-parse HEAD)}"

mkdir -p reports

set +e
python3 -m pytest tests/post-commit -q --junit-xml="$JUNIT_FILE"
PYTEST_EXIT=$?
set -e

python3 - "$JUNIT_FILE" "$REPORT_FILE" "$COMMIT" "$PYTEST_EXIT" <<'PYCODE'
import datetime
import pathlib
import sys
import xml.etree.ElementTree as ET

junit_path, report_path, commit, pytest_exit = sys.argv[1:5]

root = ET.parse(junit_path).getroot()
suite = root if root.tag == 'testsuite' else root.find('testsuite')

total = int(suite.get('tests', 0))
failures = int(suite.get('failures', 0))
errors = int(suite.get('errors', 0))
skipped = int(suite.get('skipped', 0))
duration = float(suite.get('time', 0))
passed = total - failures - errors - skipped

status = 'Success' if pytest_exit == '0' else 'Failed'

failed_cases = []
for case in suite.iter('testcase'):
    for tag in ('failure', 'error'):
        node = case.find(tag)
        if node is not None:
            failed_cases.append(f"{case.get('classname')}::{case.get('name')}")

lines = [
    '# Test Report',
    '',
    f'Status: {status}',
    f'Commit: {commit}',
    f'Timestamp: {datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}',
    '',
    '## Results',
    '',
    f'- Total: {total}',
    f'- Passed: {passed}',
    f'- Failed: {failures}',
    f'- Errors: {errors}',
    f'- Skipped: {skipped}',
    f'- Duration: {duration:.2f}s',
]

if failed_cases:
    lines += ['', '## Failed Cases', '']
    lines += [f'- {name}' for name in failed_cases]

pathlib.Path(report_path).write_text('\n'.join(lines) + '\n')
PYCODE

cat "$REPORT_FILE"
exit "$PYTEST_EXIT"
