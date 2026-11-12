import json
import subprocess
import sys

# docs/*.MD and the test-fixture credentials in test_tasks.py/test_security.py are known false
# positives (demo login examples and test env vars), not real secrets. reports/ is generated
# runtime output (contains commit SHAs, which look like high-entropy hex to the scanner).
EXCLUDE_FILES = r'docs/.*|tests/post-commit/test_tasks\.py|tests/post-commit/test_security\.py|reports/.*'


def test_detect_secrets_scan_passes():
    result = subprocess.run(
        [sys.executable, '-m', 'detect_secrets', 'scan', '--exclude-files', EXCLUDE_FILES],
        capture_output=True,
        text=True,
        check=False,
    )
    returncode = result.returncode  # avoid pytest reprinting the full CompletedProcess in the assert
    assert returncode == 0, result.stderr
    findings = json.loads(result.stdout)
    assert findings.get('results', {}) == {}, 'Potential secrets detected'
