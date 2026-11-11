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
| 2 | CI/CD automation | GitHub Actions pipeline builds, tests, publishes images with digests |
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
├─ frontend/
│  ├─ Dockerfile
│  ├─ nginx.conf
│  ├─ templates/
│  │  ├─ login.html
│  │  └─ dashboard.html
│  └─ static/
│     ├─ css/style.css
│     └─ js/app.js
├─ backend/
│  ├─ Dockerfile
│  ├─ requirements.txt
│  ├─ app.py (REST API + Bearer token auth)
│  └─ tests/
│     └─ test_tasks.py
├─ database/
│  ├─ Dockerfile
│  ├─ requirements.txt
│  ├─ app.py (CRUD API + X-Internal-Token auth)
│  ├─ init-db.py (create schema, load seed data)
│  └─ tests/
│     └─ test_database.py
├─ scripts/
│  ├─ setup.sh (environment setup)
│  ├─ env-setup.sh (configure .env variables)
│  ├─ build.sh (test, build Docker images)
│  ├─ review.sh (collect evidence for broker)
│  ├─ deploy.sh (deploy using image digest)
│  ├─ post-deploy.sh (post-deployment verification)
│  ├─ validate.sh (syntax and security checks)
│  └─ cleanup.sh (remove containers, volumes)
├─ .github/workflows/
│  ├─ ci-cd.yml (GitHub Actions: test → build → publish)
│  └─ post-deployment.yml (post-deployment verification)
├─ docs/
│  ├─ architecture.md (system diagrams & design)
│  ├─ DEVELOPMENT.md (this file)
│  ├─ USAGE.md (quick start guide)
│  ├─ broker.md (broker API reference)
│  ├─ operations.md (operational tasks)
│  ├─ glossary.md (terminology)
│  ├─ CONTRIBUTING.md (contribution guidelines)
│  └─ index.MD (documentation index)
├─ docker-compose.yml (local dev environment)
├─ .env.example (environment variables template)
├─ .gitignore
└─ README.md
```

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
- [ ] GitHub Actions CI/CD runs
- [ ] Tests pass automatically
- [ ] Docker images build and publish with digests
- [ ] Evidence collected in JSON format

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
- [Quick Start](./USAGE.md)
- [Glossary](./glossary.md)
