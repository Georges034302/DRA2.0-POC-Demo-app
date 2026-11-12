# Quick Start

**License:** Proprietary. Prior written permission required.

**Run from:** Repository root.

## Local Setup

**Prerequisites:** Docker Engine and Docker Compose.

**Steps:**
```sh
cp .env.example .env
# Edit .env: set DEMO_USERNAME, DEMO_PASSWORD, SECRET_KEY, INTERNAL_API_TOKEN

docker compose up --build

# Verify (in another terminal):
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"demo","password":"password123"}'
```

**Access:** http://localhost:8080

**Stop:** `docker compose down` (keep data) or `docker compose down -v` (delete data)

## Testing

**Prerequisites:** Python 3.12, pytest.

```sh
pip install -r backend/requirements.txt -r database/requirements.txt pytest

pytest tests/post-commit -v
bash -n scripts/*.sh
bash scripts/build.sh
```

**Pre-commit hooks (local, lint/secrets/dependency gates):**
```sh
pip install pre-commit
pre-commit install
# Runs automatically on every `git commit`; to run manually:
pre-commit run --all-files
```

## CI/CD Release Workflow

**Dispatch:** Manual only via GitHub Actions UI (no automatic runs on main).

**Stages:**
1. Test: DB/TASKS/SECURITY suites (`scripts/post-test.sh`) → `test_report.md`
2. Build images, push to ACR (`scripts/build.sh`) → `build_report.md`
3. Deploy to dev stage (`scripts/deploy.sh STAGE=dev`) → `deployment_report.md`
4. Post-deploy health check on dev stage (`scripts/post-deploy.sh STAGE=dev`) → `results.md`
5. Broker review — reads all 4 reports (`scripts/review.sh`)
6. Approval gate if APPROVAL_REQUIRED (human review)
7. Promote: same digest redeployed to prod stage (`scripts/deploy.sh STAGE=prod`) on PASS or an approved `APPROVAL_REQUIRED`

**Outcomes:**
- `PASS` (0): Promote dev digest to prod
- `FAIL` (10): Reject; prod untouched
- `APPROVAL_REQUIRED` (20): Route to `dra-approval` environment
- `ERROR` (30): Reject; prod untouched

**Approval:** Protected GitHub environment (`dra-approval`) with required reviewers.

## Important Notes

- Never commit `.env`
- Never include secrets in evidence
- Data does not persist across container restarts in Azure (configure volume for production)
- Broker is external; does not build, deploy, rollback, or monitor
- Results are findings, not verified vulnerabilities

[Docs Index](index.MD)