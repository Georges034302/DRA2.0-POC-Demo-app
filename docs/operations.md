# Operations & Deployment

## Deployment Strategy

### Immutable Image Digests

- Images are built, tested, and published with exact SHA256 digests
- Broker review gates deployment of **specific digests**
- Deployment script re-uses reviewed digests; no rebuild
- Ensures exact reviewed code runs in production

### Manual Release Workflow

- Release workflow must be manually dispatched via GitHub Actions UI
- Automatic runs on `main` branch pushes are disabled
- All required checks must pass before deployment proceeds

### Approval Gates

Pre-deployment findings requiring approval are enforced via GitHub environment protection:
- **Environment Name:** `dra-approval`
- **Configuration:** Enable protection rules, add required reviewers
- **Flag:** `APPROVAL_GATE_ENABLED=true` in workflow
- **Approval:** Only authorized reviewers can approve or reject

## Security & Evidence Management

### Credential Handling

**Golden Rules:**
1. Store all credentials in GitHub Actions protected secrets
2. Never expose secrets to untrusted pull requests
3. Use separate secrets for each service (Gemini, Groq, GHCR)
4. Rotate credentials regularly

**In Code:**
- Never commit `.env` files
- Never embed API keys in source
- Use environment variable substitution only

### Evidence Redaction

**Pre-Submission Redaction (Required):**

Pre-filter evidence before broker invocation to remove:
- ✗ API keys, tokens, passwords
- ✗ Database credentials
- ✗ SSH private keys
- ✗ Personal data (names, emails, addresses)
- ✗ Proprietary or confidential algorithms
- ✗ Customer or business data

**Automatic Redaction (Best-Effort):**

Broker attempts to mask:
- Common patterns: `SECRET=*****`, `password=*****`
- Not guaranteed; always pre-filter manually

### Broker Image Security

- Pin broker image to **approved GHCR digest** (SHA256)
- Never use floating tags (`latest`, `v1.0`, etc.)
- GHCR token must have `read:packages` access only
- Verify image before deployment: `docker inspect <digest>`

## Azure Deployment

### Prerequisites

```sh
# Required tools
docker --version        # Docker Engine
docker compose --version
python --version        # Python 3.12+
git --version
az --version            # Azure CLI
gh --version            # GitHub CLI
```

### Environment Configuration

**Required for all scripts:**

| Variable | Example | Purpose |
|----------|---------|---------|
| `AZURE_SUBSCRIPTION_ID` | `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` | Azure subscription |
| `AZURE_RESOURCE_GROUP` | `dra-poc-demo-rg` | Resource group name |
| `AZURE_ACR_NAME` | `drapocdemo` | Container Registry name |
| `GITHUB_SHA` | `abc123def456` | Commit hash (from Actions) |
| `BROKER_IMAGE_DIGEST` | `ghcr.io/private/broker@sha256:abc...` | Approved broker image |

**Optional:**

| Variable | Purpose |
|----------|---------|
| `GITHUB_OWNER` | Repository owner (default: from git) |
| `GITHUB_REPO` | Repository name (default: from git) |
| `ENVIRONMENT` | Deployment environment (default: `production`) |

### Azure OIDC Federation

Configure OpenID Connect federation to allow GitHub Actions to authenticate to Azure:

1. Create Azure App Registration
2. Configure federated credentials for GitHub Actions
3. Grant minimal required roles (e.g., `AcrPull`, resource group access)
4. Verify authentication: `az login --service-principal ...`

See **scripts/env-setup.sh** for infrastructure provisioning.

### Storage Persistence

**⚠️ WARNING:** SQLite database is not configured for persistent storage in Azure.

- Container restarts may lose data
- For production: configure Azure Files or managed database
- Current deployment suitable only for POC/demo

## Local Development

### Quick Start

```sh
cp .env.example .env
# Edit .env with test credentials

docker compose up --build
curl http://localhost:8080/health
```

### Validation

```sh
# Install dependencies
python -m pip install \
  -r frontend/requirements.txt \
  -r backend/requirements.txt \
  -r database/requirements.txt

# Run tests
python -m pytest frontend/tests backend/tests database/tests -q

# Lint scripts
bash -n scripts/*.sh

# Build images locally
bash scripts/build.sh
```

### Data Management

```sh
# Start services with data persistence
docker compose up --build

# Stop without deleting data
docker compose down

# Stop and delete all data
docker compose down -v

# View logs
docker compose logs -f frontend
docker compose logs -f backend
docker compose logs -f database
```

## CI/CD Pipeline

### Release Workflow (ci-cd.yml)

**Stages:**
1. Checkout code
2. Run tests
3. Build application images
4. Publish to ACR (with `--publish` flag)
5. Prepare evidence (secrets redacted)
6. Invoke AI-Broker pre-deployment review
7. Route to approval gate if required
8. Deploy reviewed digests

**Triggers:**
- Manual dispatch only
- No automatic runs on `main` pushes

### Post-Deployment Workflow (post-deployment.yml)

**Stages:**
1. Collect deployed revision info
2. Gather container logs and health data
3. Prepare evidence for broker
4. Invoke AI-Broker post-deployment review
5. Report verification result

**Retention:**
- Evidence and logs retained for 30 days
- No automatic rollback on verification failure

## Troubleshooting

### Application Won't Start

```sh
# Check Docker daemon running
docker ps

# Rebuild from scratch
docker compose up --build --force-recreate

# View detailed logs
docker compose logs --tail=100

# Check port availability
lsof -i :8080
```

### Broker Returns ERROR (exit 30)

**Check 1: Request Validity**
```sh
# Inspect broker input
cat /path/to/broker-request.json | jq .

# Verify evidence paths are relative (no ../)
# Confirm all evidence is valid UTF-8
```

**Check 2: Broker Image**
```sh
# Verify image exists and is accessible
docker pull <BROKER_IMAGE_DIGEST>

# Check image size and layers
docker inspect <BROKER_IMAGE_DIGEST>
```

**Check 3: Provider Access**
```sh
# Test Gemini API
curl -X POST https://generativelanguage.googleapis.com/v1beta/models/...

# Check Groq API
curl -X POST https://api.groq.com/...

# Verify API quotas and rate limits in provider dashboards
```

### Deployment Blocked by APPROVAL_REQUIRED

1. Verify approval environment exists in repository settings
2. Check `APPROVAL_GATE_ENABLED=true` in workflow
3. Confirm required reviewers are configured
4. Approve the workflow run in GitHub Actions UI
5. Re-run job after approval

### Data Lost After Container Restart

This is expected; SQLite is in-container only.

For persistence:
```yaml
# docker-compose.yml: configure named volume for database
services:
  database:
    volumes:
      - db_data:/app/data

volumes:
  db_data:
```

## Performance Considerations

### Build & Publish
- Typical: 5-10 minutes
- Depends on: code complexity, test suite size, image layers

### Broker Invocation
- Typical: 2-5 minutes
- Depends on: evidence size, provider latency, queue depth

### Approval Gate
- Typical: 5-30 minutes (human-driven)
- Recommended timeout: 24 hours

### Deployment
- Typical: 2-5 minutes
- Depends on: Azure region, network conditions

### Total Pipeline
- Average: 15-30 minutes per release

---

**See Also:** [Architecture](architecture.md) | [AI-Broker Reference](broker.md) | [Getting Started](USAGE.MD)

[Documentation Index](index.MD)
