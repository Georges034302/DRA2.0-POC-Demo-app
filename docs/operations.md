# Operations Guide

## Deployment Workflow

**Pipeline Status:** Phase 2 (CI/CD + Azure deploy) active; Phase 3 (Broker pre-deploy invocation) pending — `ci-cd.yml`'s review step is currently an inert placeholder; Phase 4 (post-deploy Broker governance) active. See [Development Guide](DEVELOPMENT.md).

**Immutable Digests:** Images published with SHA256 digests; broker approves digest, not code; deployment uses exact approved digest (no rebuild).

**Release Trigger:** Manual dispatch via GitHub Actions UI (no automatic runs on main).

**Approval Gate:** GitHub environment protection (`dra-approval`) with required reviewers for APPROVAL_REQUIRED decisions.

## Security

**Secrets:** Store all credentials in GitHub Actions protected secrets; never commit `.env` files or embed keys in source.

**Evidence Redaction:** Remove API keys, tokens, passwords, database credentials, SSH keys, and personal data before broker invocation. Broker attempts automatic masking but manual pre-filtering is required.

**Broker Image:** Pin to approved GHCR digest (SHA256); never use floating tags. GHCR token must have `read:packages` access only.

## Setup & Prerequisites

**Required Tools:**
```sh
docker --version        # Docker Engine
docker compose --version
python --version        # Python 3.12+
git --version
```

**Environment Variables:**

| Variable | Example | Purpose |
|----------|---------|---------|
| `DEMO_USERNAME` | `demo` | Login username |
| `DEMO_PASSWORD` | `password123` | Login password |
| `SECRET_KEY` | (random 32+ char) | Backend token signing key |
| `INTERNAL_API_TOKEN` | (random 32+ char) | Database authentication token |

## Installation & Running Locally

**Clone and setup:**
```sh
git clone https://github.com/Georges034302/DRA2.0-POC-Demo-app.git
cd DRA2.0-POC-Demo-app
cp .env.example .env
# Edit .env with credentials above
```

**Install dependencies:**
```sh
pip install -r backend/requirements.txt
pip install -r database/requirements.txt
pip install pytest flake8 bandit
```

**Run locally:**
```sh
docker compose up --build

# In another terminal, verify:
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"demo","password":"password123"}'
```

**Homepage:**
```
http://localhost:8080
```

**Stop services:**
```sh
docker compose down       # Keeps data
docker compose down -v    # Deletes all data
```

## Testing & Validation

**Run all tests:**
```sh
pytest backend/tests database/tests -v
```

**Lint shell scripts:**
```sh
bash -n scripts/*.sh
```

**Build images:**
```sh
bash scripts/build.sh
```

**View logs:**
```sh
docker compose logs -f frontend
docker compose logs -f backend
docker compose logs -f database
```

## Troubleshooting

**Application won't start:**
```sh
docker ps                              # Check daemon
docker compose up --build --force-recreate
docker compose logs --tail=100
```

**Port conflict:**
```sh
lsof -i :8080
lsof -i :5000
lsof -i :5001
```

**Broker returns ERROR (exit 30):** *(applies once Phase 3 is wired in; the Phase 2 placeholder always reports PASS)*
- Verify evidence JSON is valid: `cat broker-request.json | jq .`
- Check all paths are relative (no `../` escapes)
- Verify broker image digest exists and is accessible
- Check API quotas in provider dashboards

**Deployment blocked by APPROVAL_REQUIRED:**
- Verify `dra-approval` environment exists in repository settings
- Confirm required reviewers are configured
- Approve workflow run in GitHub Actions UI

**Data lost after container restart:**
This is expected; SQLite is ephemeral. Configure Docker volume for persistence:
```yaml
services:
  database:
    volumes:
      - db_data:/app/data
volumes:
  db_data:
```

## Performance

- Build & publish: 5-10 min
- Tests: 2-3 min
- Broker invocation: 2-5 min (provider-dependent; Phase 3, not yet active)
- Approval gate: 5-30 min (human-driven; Phase 3, not yet active)
- Deployment: 2-5 min
- **Total pipeline:** ~15-30 min per release

## References

[Architecture](./architecture.md) | [Broker Spec](./broker.md) | [Quick Start](./USAGE.md) | [Index](./index.MD)
