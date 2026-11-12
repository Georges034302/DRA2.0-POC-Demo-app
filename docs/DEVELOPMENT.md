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
| 2 | CI automation + evidence schema | GitHub Actions pipeline builds, tests, publishes images with digests; emits a Broker-ready evidence package (no Broker container invoked yet) |
| 3 | Broker integration | Policy evaluation, approval gates, decision enforcement |
| 4 | Deployment & verification | Immutable deployment by digest, post-deploy checks with stricter policy |
| 5 | Polish & documentation | Tests, security checks, documentation, demo-ready |

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
1. Test: Run pytest
2. Build: Docker images with digest tracking
3. Publish: Push images to registry
4. Evidence: Collect code diff, dependencies, test results, build logs
5. Broker Review: Evaluate policies against evidence
6. Policy Decision: PASS / FAIL / APPROVAL_REQUIRED / ERROR
7. Approval Gate: If APPROVAL_REQUIRED, route to human review
8. Deploy: Approved digest deployed (no rebuild)
9. Post-Deploy: Collect runtime evidence, verify with stricter policy
```

### Evidence Collection

**Collected at Build Time:**
- Source code diff
- Dependencies and versions
- Test results
- Build logs
- Container image digest (SHA256)

**Collected After Deployment:**
- Runtime configuration
- System metrics
- Application logs
- Service health
- Security scan results

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
- [ ] GitHub Actions CI runs (build, test, publish images with digests)
- [ ] Tests pass automatically
- [ ] Docker images build and publish with digests
- [ ] Evidence package matches the Broker's input schema (no Broker container invoked in this phase):
  - `request.json`: `{"mode": "pre_deploy", "repository": "<owner/repo>", "commit": "<sha>", "evidence": ["<relative-filenames>"]}`
  - Evidence files use relative paths only (no `../`, no absolute paths), valid UTF-8, ≤120 KiB each
  - See [AI-Broker Reference](./broker.md#input-validation) for the full schema Phase 3 will consume

### Phase 3
- [ ] Broker invocation works with evidence payload
- [ ] Policy decisions returned correctly (PASS/FAIL/APPROVAL_REQUIRED/ERROR)
- [ ] Approval gate routing functional
- [ ] Decisions enforced (block/approve/deploy)

### Phase 4
- [ ] Deployments use approved digest only
- [ ] No image rebuild after approval
- [ ] Post-deployment workflow runs
- [ ] Post-deployment policy correctly blocks/approves

### Phase 5
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
