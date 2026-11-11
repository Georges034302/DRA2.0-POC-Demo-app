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

**Prerequisites:** Python 3.12, pytest, flake8, bandit.

```sh
pip install -r backend/requirements.txt -r database/requirements.txt pytest flake8 bandit

pytest backend/tests database/tests -v
bash -n scripts/*.sh
bash scripts/build.sh
```

## CI/CD Release Workflow

**Dispatch:** Manual only via GitHub Actions UI (no automatic runs on main).

**Stages:**
1. Test
2. Build images (publish with `--publish`)
3. Collect evidence (redacted)
4. Broker review (pre-deployment)
5. Approval gate if APPROVAL_REQUIRED (human review)
6. Deploy (approved digest, no rebuild)
7. Post-deployment workflow collects evidence and runs stricter policy

**Outcomes:**
- `PASS` (0): Deploy
- `FAIL` (10): Block
- `APPROVAL_REQUIRED` (20): Route to `dra-approval` environment
- `ERROR` (30): Block

**Approval:** Protected GitHub environment (`dra-approval`) with required reviewers.

## Important Notes

- Never commit `.env`
- Never include secrets in evidence
- Data does not persist across container restarts in Azure (configure volume for production)
- Broker is external; does not build, deploy, rollback, or monitor
- Results are findings, not verified vulnerabilities

[Docs Index](index.MD)