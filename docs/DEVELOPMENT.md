# Development Guide

## Project Focus

This POC demonstrates a broker-based policy engine controlling deployments through:
- Evidence collection from CI/CD pipelines
- Policy-based review decisions
- Human approval gates
- Immutable deployments (reviewed image digests only)
- Post-deployment verification with stricter policies

**Application is intentionally minimal** — focus is on the governance pipeline, not features.

## Development Phases

| Phase | Focus | Deliverable |
|-------|-------|-------------|
| 1 | Minimal working app | docker-compose up works, CRUD operations functional |
| 2 | Complete CI/CD pipeline | Build, test, publish digests, deploy to Azure; AI-Broker review step is an inert placeholder (`TODO in Phase 3`) — deploy proceeds automatically on a successful build, no gate yet |
| 3 | AI-Broker pre-deploy invocation | Replace the placeholder with the real Broker scan (`scripts/review.sh`); approval gate activates for `APPROVAL_REQUIRED` outcomes; deploy blocked on `FAIL`/`ERROR` |
| 4 | AI-Broker decision & governance | Post-deployment: stricter policy, runtime evidence collection, redaction/audit trail (as implemented in `post-deployment.yml`); full pipeline exercised end-to-end against live Azure infra, tests/lint/security green, docs finalized, demo rehearsed |

## Technology Stack

- **Frontend:** Nginx (reverse proxy, static assets)
- **Backend:** Flask (REST API with Bearer token auth)
- **Database:** Flask + SQLite (CRUD API, persistent storage)
- **Orchestration:** Docker & Docker Compose
- **CI/CD:** GitHub Actions
- **Testing:** pytest, flake8, Bandit

## Project Structure

```
DRA2.0-POC-Demo-app/
├── frontend/                       # Nginx reverse proxy + static assets + templates
├── backend/                        # Flask API (calls the database service)
├── database/                       # Flask CRUD API over SQLite
├── docs/                           # Documentation hub (architecture, guides, reference)
├── scripts/                        # Azure Container Apps setup/build/review/deploy/cleanup automation
├── .github/                        # GitHub Actions workflows (CI/CD, post-deploy)
├── docker-compose.yml              # 3-container orchestration config
├── README.md                       # Project overview and quick start
├── LICENSE                         # Proprietary license terms
├── .env.example                    # Environment variables template
├── .gitignore                      # Git ignore rules
└── .git/                           # Git repository history
```

> For the fully expanded, file-by-file layout, see [Repository Structure in architecture.md](./architecture.md#repository-structure).

## Development Workflow

### Local Development
```
1. Make code changes
2. Run: docker-compose up --build
3. Test locally: http://localhost:8080
4. Run unit tests: pytest
5. Commit and push
```

### CI/CD Pipeline (GitHub Actions)
```
1. Test: Run pytest (frontend, backend, database)
2. Build: Docker images with digest tracking (scripts/build.sh)
3. Publish: Push images to registry, write images.json (scripts/build.sh --publish)
4. Evidence: Collect code diff, write request.json (scripts/review.sh, Phase 3)
5. Broker Review: Evaluate policies against evidence, return result.json
6. Policy Decision: PASS / FAIL / APPROVAL_REQUIRED / ERROR
7. Approval Gate: If APPROVAL_REQUIRED, route to human review
8. Deploy: Approved digest deployed (no rebuild) (scripts/deploy.sh)
9. Post-Deploy: Collect runtime evidence (scripts/post-deploy.sh), verify with stricter policy
```

### Evidence Collection

**Build-time** (Phase 2, [scripts/build.sh](../scripts/build.sh)):
- `images.json` (`build-manifest` artifact) — `{"commit": "<sha>", "images": {"frontend": "...@sha256:...", "backend": "...", "database": "..."}}`

**Pre-deployment** (Phase 3, [scripts/review.sh](../scripts/review.sh)):
- `changes.diff` — git diff of `frontend/`, `backend/`, `database/` between the previous and current commit
- `request.json` — `{"mode": "pre_deploy", "repository": "...", "commit": "...", "evidence": ["changes.diff"]}`

**Post-deployment** (Phase 4, [scripts/post-deploy.sh](../scripts/post-deploy.sh)):
- `<service>-revisions.json` — Azure CLI revision health/state, per service (frontend/backend/database)
- `<service>-status.json` — Azure CLI provisioning state + ingress FQDN, per service
- `<service>-logs.txt` — last 40 log lines, per service
- `health.json` — frontend `/health` endpoint response
- `status.txt` — deterministic health verdict (`ok`/`unhealthy`)
- `request.json` — `{"mode": "post_deploy", "repository": "...", "commit": "...", "evidence": [<above filenames>]}`

See [AI-Broker Reference](./broker.md#input-validation) for the full evidence/request schema these reports must satisfy.

### AI-Broker Outputs & Decisions

The Broker reads a report set above and returns `result.json`:
```json
{
  "outcome": "PASS|FAIL|APPROVAL_REQUIRED|ERROR",
  "exit_code": 0,
  "summary": "Human-readable summary of key findings",
  "findings": [
    {
      "severity": "CRITICAL|HIGH|MEDIUM|LOW|INFO",
      "category": "Security|Compliance|Performance|Quality",
      "title": "Finding title",
      "description": "Detailed explanation",
      "recommendation": "How to address this finding"
    }
  ],
  "policy_version": "1.0.0",
  "metrics": {
    "evidence_items_analyzed": 5,
    "scan_duration_ms": 2345,
    "model_used": "gemini-2.0-flash|groq-large"
  }
}
```

The CI scripts map `outcome` to a Broker exit code (`PASS`→0, `FAIL`→10, `APPROVAL_REQUIRED`→20, `ERROR`→30) and treat a mismatch between the two as `ERROR`. See [AI-Broker Reference](./broker.md#result-format) for full policy mapping rules.

## Policy Decision Outcomes

| Exit Code | Outcome | Action |
|-----------|---------|--------|
| 0 | PASS | Deploy |
| 10 | FAIL | Block (no approval) |
| 20 | APPROVAL_REQUIRED | Route to human review |
| 30 | ERROR | Block (validation failure) |

**Post-deployment uses stricter policy:** Medium/High/Critical findings trigger FAIL instead of APPROVAL_REQUIRED.

## Key Principles

**Immutable Deployments:** Broker approves the image digest (SHA256), not code. Deployment uses exact approved digest—no rebuild means what was reviewed is what runs.

**Evidence-Driven Decisions:** Policies evaluate concrete evidence collected from CI/CD and runtime. Reproducible, auditable, no guessing.

**Two-Tier Policy:** Pre-deploy routes medium findings to approval. Post-deploy fails on medium/high/critical findings (no approval gate).

## Success Criteria

### Phase 1
- [x] docker-compose up succeeds
- [x] Login with demo credentials works
- [x] CRUD operations work (create, read, update, delete)
- [x] Data persists across container restarts

### Phase 2
- [ ] Azure infra provisioned (`env-setup.sh`)
  - resource group, ACR, Container Apps environment
- [ ] Azure OIDC secrets/vars configured in GitHub
- [ ] CI/CD pipeline runs end-to-end
  - test → build → publish digests → deploy to Azure
  - unconditional on successful build, no gate
- [ ] Deploy to Azure Container Apps
  - uses published digest
  - no rebuild
- [ ] Broker step is inert placeholder only
  - echoes "TODO in Phase 3"
  - outputs `decision=PASS`
  - no real scan, no approval gate

### Phase 3
- [ ] GHCR and AI provider secrets/vars configured in GitHub
- [ ] Placeholder review step replaced with real AI-Broker invocation (`scripts/review.sh`)
  - see [AI-Broker Reference](./broker.md) for the evidence/request schema
- [ ] Broker returns PASS/FAIL/APPROVAL_REQUIRED/ERROR from the evidence payload
- [ ] Approval gate activates
  - routes `APPROVAL_REQUIRED` outcomes to human review
- [ ] Deploy blocked on FAIL/ERROR
- [ ] Deploy proceeds on PASS or an approved `APPROVAL_REQUIRED`

### Phase 4
- [ ] Post-deployment workflow runs after a successful deploy
- [ ] Runtime evidence collected (revisions, status, logs, health)
- [ ] Broker re-invoked with the stricter post-deploy policy
- [ ] Post-deployment policy correctly blocks/approves
- [ ] Full pipeline (Phases 2-4) exercised end-to-end against live Azure infra
  - produces at least one real PASS outcome
  - produces at least one real FAIL outcome
  - produces at least one real APPROVAL_REQUIRED outcome
- [ ] All tests passing
- [ ] Linting and security checks passing
- [ ] Documentation complete
- [ ] Demo scenario documented

## Important Notes

- POC-grade code, not production-ready
- Demo-grade security
- Focus on governance pipeline, not application features
- Phase 1 complete

## References

- [Architecture & System Diagrams](./architecture.md)
- [Broker Specification](./broker.md)
- [Operations Guide](./operations.md)
- [Quick Start](./USAGE.MD)
- [Glossary](./glossary.md)
