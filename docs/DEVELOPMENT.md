# Development Guide — Release Governance POC

## Focus: Governance Pipeline, Not Application Features

This POC proves that a broker-based policy engine can control deployments through:
1. Evidence collection from builds
2. Policy-based review decisions
3. Human approval gates
4. Immutable deployment (reviewed digests only)
5. Post-deployment verification

**The application is intentionally minimal.** All effort goes to the governance pipeline.

## What We're Building

### The Application (20% effort)
A minimal task tracker:
- Simple SQLite schema (tasks table)
- Basic Flask REST API (create, list, delete)
- Plain HTML form (no fancy UI)
- Demo authentication (credentials from .env)
- Enough to have something real to deploy

### The Governance Pipeline (80% effort)
- Build automation (test, build, publish images with digests)
- Evidence collection (code, dependencies, logs)
- Broker integration (policy review, decisions)
- Approval gates (human decision routing)
- Immutable deployment (digest-based, no rebuilds)
- Post-deployment verification (state check, stricter policy)

## Development Phases

### Phase 1: Minimal App (3-4 days)
Create a simple, working application:
- Database: Task model (id, title, status)
- API: GET /tasks, POST /tasks, DELETE /tasks/:id
- Frontend: HTML form + list view
- Docker: Dockerfile for each service
- Local: docker-compose.yml

**Deliverable:** App works locally, API responds, tasks can be created/deleted

### Phase 2: CI/CD Pipeline (4-5 days)
Build the governance infrastructure:
- GitHub Actions workflow (ci-cd.yml)
- Test stage (pytest)
- Build stage (docker images)
- Publish stage (digest tracking)
- Evidence collection script (review.sh)
- Deploy script (deploy.sh)

**Deliverable:** Pipeline runs, builds images, publishes digests, collects evidence

### Phase 3: Broker Integration (3-4 days)
Connect evidence to policy decisions:
- Broker invocation (mock or real)
- Policy evaluation (PASS/FAIL/APPROVAL_REQUIRED/ERROR)
- Evidence formatting (JSON schema)
- Decision routing (gate decisions)
- Approval gate setup (GitHub environment)

**Deliverable:** Broker can be called, decisions are enforced, approvals work

### Phase 4: Deployment & Verification (2-3 days)
Complete the governance flow:
- Immutable deployment (deploy by digest, no rebuild)
- Post-deployment workflow (post-deployment.yml)
- Evidence re-collection
- Post-deployment broker invocation (stricter policy)
- Verification reporting

**Deliverable:** Full end-to-end flow works, from build to post-deploy

### Phase 5: Polish & Documentation (2-3 days)
Finalize for demo:
- Tests and quality gates
- Error handling
- Documentation updates
- Troubleshooting guide
- Demo readiness

**Deliverable:** Ready to demo the governance pipeline

## Technology Stack

**Application:**
- Flask (Python 3.12+)
- SQLite
- Nginx (reverse proxy)
- Plain HTML (no framework)

**Governance:**
- GitHub Actions
- Docker & Docker Compose
- Bash scripts
- Broker API (external service)

**Testing:**
- pytest
- flake8
- Bandit (security)

## Application Structure

```
frontend/
  ├─ Dockerfile
  ├─ requirements.txt (Flask, Jinja2)
  ├─ app.py (Flask server, render templates)
  ├─ templates/
  │  ├─ base.html
  │  ├─ login.html
  │  └─ tasks.html
  └─ static/
     └─ style.css

backend/
  ├─ Dockerfile
  ├─ requirements.txt (Flask, SQLAlchemy)
  ├─ app.py (Flask API)
  ├─ models.py (Task model)
  └─ tests/
     └─ test_api.py

database/
  ├─ Dockerfile
  ├─ requirements.txt (Flask)
  ├─ app.py (CRUD API)
  ├─ schema.py (database schema)
  └─ migrations/ (schema versions)

scripts/
  ├─ build.sh (test, build, publish)
  ├─ review.sh (collect evidence, invoke broker)
  ├─ deploy.sh (deploy by digest)
  └─ post-deploy.sh (verification)

.github/workflows/
  ├─ ci-cd.yml (build, test, review, deploy)
  └─ post-deployment.yml (verification)
```

## Success Criteria

### Phase 1: Application Works
- [ ] `docker-compose up --build` succeeds
- [ ] Can login with demo credentials
- [ ] Can create task
- [ ] Can list tasks
- [ ] Can delete task
- [ ] Data persists across restarts

### Phase 2: Pipeline Works
- [ ] GitHub Actions workflow runs
- [ ] Tests pass (pytest)
- [ ] Docker images build cleanly
- [ ] Images are published with digests
- [ ] Evidence is collected in JSON

### Phase 3: Broker Integration Works
- [ ] Broker can be invoked with evidence
- [ ] Policy decisions are returned (PASS/FAIL/APPROVAL_REQUIRED)
- [ ] Decisions are enforced (block/approve/deploy)
- [ ] Approval gate routing works
- [ ] Human can approve/reject

### Phase 4: Deployment Works
- [ ] Approved digests are deployed
- [ ] No rebuild occurs (digest used directly)
- [ ] Post-deployment workflow runs
- [ ] Post-deployment evidence collected
- [ ] Stricter post-deploy policy applied

### Phase 5: Ready to Demo
- [ ] All tests passing
- [ ] Linting/security checks passing
- [ ] Complete documentation
- [ ] Runbook for operators
- [ ] Demo scenario documented

## Key Implementation Notes

### Evidence Collection
Evidence includes:
- Source code diff
- Dependencies (requirements.txt, etc.)
- Test results
- Build logs
- Image metadata

Format: JSON with explicit paths (no absolute paths, no `../`)

### Policy Outcomes
- `PASS` (0): Proceed to other checks
- `FAIL` (10): Block release
- `APPROVAL_REQUIRED` (20): Route to approval gate
- `ERROR` (30): Block release (validation/provider failure)

### Post-Deployment Policy (Stricter)
- `CRITICAL/HIGH/MEDIUM` findings → FAIL
- (vs. pre-deploy: `MEDIUM` → APPROVAL_REQUIRED)

### Immutable Deployment
- Image digest from approved build
- No rebuild after approval
- Exactly what was reviewed runs in production

## Deployment Workflow

```
Local Development
    ↓
git push → GitHub Actions
    ├─ Test
    ├─ Build (publish digest)
    ├─ Collect evidence
    ├─ Broker review (pre-deploy)
    ↓
Policy Decision
    ├─ PASS → proceed
    ├─ FAIL → block
    └─ APPROVAL_REQUIRED → human gate
    ↓
Approval Gate (if needed)
    ├─ Human reviews findings
    ├─ Approves or rejects
    ↓
Deployment
    ├─ Deploy reviewed digest (no rebuild)
    ↓
Post-Deployment Verification
    ├─ Collect state evidence
    ├─ Broker review (post-deploy, stricter)
    ├─ Verify or fail
    ↓
Done
```

## Testing Strategy

### Unit Tests
- Model CRUD
- API endpoints
- Validation logic

### Integration Tests
- Full request cycles
- Database transactions
- Authentication flow

### Governance Tests
- Evidence collection correctness
- Broker invocation format
- Decision enforcement
- Approval routing

## Important: This Is Not Production

- POC-quality code
- Demo-grade security
- Not for enterprise use
- Acceptable for governance proof-of-concept

## Questions?

Refer to:
1. [Architecture & Release Flow](docs/architecture.md)
2. [Broker Reference](docs/broker.md)
3. [Operations Guide](docs/operations.md)
4. [Getting Started](docs/USAGE.MD)

---

**Status:** Ready to begin Phase 1  
**Next:** Create minimal application structure  
**Timeline:** 2-3 weeks to complete demo
