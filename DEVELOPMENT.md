# DRA 2.0 POC - Development Guide

## Project Vision

**Goal:** Demonstrate how a real application integrates with AI-Broker for AI-driven release governance.

**What It Is:**
- A working task management system (CRUD operations)
- Multi-tier architecture (Frontend, Backend, Database)
- Complete CI/CD pipeline with evidence review and approval gates
- Proof that AI-driven governance + human control works together

**What It's NOT:**
- Not production-ready
- Not a complex business application
- Not meant for continuous monitoring or auto-rollback
- Not enterprise-scale

## Application Features

### User-Facing Features
- **Authentication:** Login with demo credentials from `.env`
- **Task Management:** Create, read, update, delete tasks
- **Real-Time Updates:** HTMX-powered live updates without page reloads
- **Persistent Storage:** SQLite database

### Technical Architecture
```
Public:    Browser → Frontend (Nginx + Flask on port 8080)
Internal:                  ↓
                        Backend (Flask REST API)
                          ↓
                    Database (SQLite)
```

### REST API Endpoints
```
POST   /api/tasks          Create task
GET    /api/tasks          List all tasks
GET    /api/tasks/:id      Get task by ID
PUT    /api/tasks/:id      Update task
DELETE /api/tasks/:id      Delete task
GET    /health             Health check
```

## Release Governance Flow

The POC demonstrates this complete cycle:

1. **Build** — Tests, lint, build images, publish with digest
2. **Pre-Deploy Review** — AI-Broker analyzes code evidence
3. **Gate Decision** — PASS / FAIL / APPROVAL_REQUIRED / ERROR
4. **Approval** (if needed) — Human review via protected environment
5. **Deployment** — Deploy reviewed digests (no rebuild)
6. **Post-Deploy Verify** — AI-Broker re-scan with stricter policy

## Development Roadmap

### Phase 1: Foundation (Week 1)
- Database schema and migrations
- Backend Flask app with API structure
- Frontend Flask app with templates
- Unit tests for models and API

**Deliverable:** App skeleton + API working locally

### Phase 2: Features (Week 2)
- Authentication flow
- Task CRUD UI with HTMX
- Complete API implementation
- Integration tests

**Deliverable:** Fully functional task management

### Phase 3: Deployment (Week 3)
- Dockerfiles for all services
- docker-compose.yml
- GitHub Actions CI/CD pipeline
- Evidence collection scripts (review.sh, deploy.sh, etc.)

**Deliverable:** docker-compose up fully working

### Phase 4: Quality (Week 4)
- Unit test suite (80%+ coverage)
- Integration tests
- Linting (flake8)
- Security scanning (Bandit)

**Deliverable:** All quality gates passing

### Phase 5: Integration (Week 5)
- AI-Broker integration stubs
- Monitoring and observability
- Final documentation
- Demo readiness

**Deliverable:** Full end-to-end governance demo

## Technology Stack

**Frontend:**
- Nginx (reverse proxy)
- Flask (web framework)
- HTMX 2.0.4 (real-time updates from CDN)
- HTML5 + CSS3 (responsive design)

**Backend:**
- Flask (REST API)
- Python 3.12+
- SQLAlchemy (ORM) or sqlite3
- Pydantic (validation)

**Testing:**
- pytest (unit & integration tests)
- flake8 (linting)
- Bandit (security)

**DevOps:**
- Docker & Docker Compose
- GitHub Actions (CI/CD)
- Bash scripting (automation)
- Azure Container Apps (deployment target)

## Success Criteria

### Functional
- [ ] Users can create, read, update, delete tasks
- [ ] HTMX updates work without full page reload
- [ ] Data persists across sessions
- [ ] Authentication with demo credentials works

### Technical
- [ ] All tests pass (80%+ coverage)
- [ ] Linting and security checks pass
- [ ] Docker images build cleanly
- [ ] docker-compose up works end-to-end

### Governance
- [ ] CI/CD pipeline runs successfully
- [ ] Evidence collection works
- [ ] Broker integration points are stubbed
- [ ] Gate decisions are enforced

### Documentation
- [ ] README explains purpose clearly
- [ ] Getting started is simple (3 commands)
- [ ] Architecture is documented
- [ ] Troubleshooting guide included

## Important Design Decisions

### By Design (Not Bugs)
- **SQLite not persistent in Azure** — Data may reset on container restart. Acceptable for POC. (Production would use managed database.)
- **Demo credentials only** — No OAuth/LDAP. Simple `.env` file authentication.
- **No auto-rollback** — Post-deployment can fail but won't trigger automatic rollback.
- **No advanced UI** — Functional, not beautiful. Focus on governance, not UX polish.
- **Logs only, no monitoring** — No continuous alerting or metrics dashboards.

### Deliberate Scope Limits
- Simple task model (title, description, status)
- Single-user per login (no multi-user authorization levels)
- Local development focus (Azure deployment docs only)
- POC-quality, not production-ready

## How to Begin

### Prerequisites
```sh
git --version           # Git
python --version        # Python 3.12+
docker --version        # Docker
docker compose --version
```

### Phase 1 Start
```sh
# 1. Create database module
#    - Define User and Task models
#    - Write migrations
#    - Unit tests for CRUD

# 2. Create backend module
#    - Flask app structure
#    - Authentication middleware
#    - API endpoints (stubs)

# 3. Create frontend module
#    - Templates (login, task list)
#    - Static assets
#    - Nginx config

# 4. Set up docker-compose.yml (basic)
#    - Bring services together
#    - Test locally
```

## Testing Strategy

### Unit Tests
- Database model CRUD
- API endpoint request/response
- Authentication validation
- Input validation

### Integration Tests
- Full request cycle (create → read → update → delete)
- Authentication flow
- Error scenarios
- Database transactions

### Quality Checks
- Linting (flake8)
- Security (Bandit)
- Coverage (80%+ target)
- Dependency audit

## Debugging Tips

### Common Issues
1. **Port conflicts** — Port 8080 already in use
2. **SQLite locked** — Multiple processes accessing database
3. **HTMX not updating** — Incorrect endpoint URLs or response format
4. **Tests failing** — Database not initialized or fixtures missing

### Quick Checks
```sh
# Check if port 8080 is available
netstat -an | grep 8080

# View docker logs
docker compose logs -f frontend

# Run tests with verbose output
pytest -v --tb=short

# Run linting
flake8 .
```

## Documentation Requirements

Each module should have:
- [ ] Docstrings for classes and functions
- [ ] README with setup instructions
- [ ] Example requests/responses for APIs
- [ ] Architecture diagram (updated in docs/)

## Deployment Workflow (Post-POC)

```
Local Development
    ↓
git push → GitHub Actions (test, build, publish)
    ↓
Manual Review & Approval
    ↓
Deployment to Azure Container Apps
    ↓
Post-Deployment Verification
```

## Contact & Questions

If questions arise during development:
1. Check existing documentation (docs/*)
2. Review similar features already implemented
3. Consult phase deliverables for scope
4. Ask before deviating from planned architecture

---

**Status:** Ready to begin Phase 1  
**Next:** Database & Backend Foundation  
**Timeline:** 5 weeks to complete demo
