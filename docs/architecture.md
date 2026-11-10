# Architecture: Release Governance Pipeline

This document describes the governance pipeline architecture and how the Broker controls release decisions.

## Overview

The POC demonstrates a release governance system where a Broker (policy engine) controls deployment by:
1. **Collecting evidence** from CI/CD pipelines and application state
2. **Evaluating policies** against that evidence
3. **Making deterministic decisions** (PASS, FAIL, APPROVAL_REQUIRED, ERROR)
4. **Enforcing approval gates** before deployment
5. **Verifying post-deployment state** and making stricter policy decisions

## System Architecture

```mermaid
graph TB
    subgraph Client["Client"]
        Browser["🌐 Browser"]
    end
    
    subgraph Frontend["Frontend Container (Nginx)"]
        FE["Reverse Proxy<br/>Static Assets<br/>Templates"]
    end
    
    subgraph Backend["Backend Container (Flask)"]
        API["Flask API<br/>Authentication<br/>CRUD Routes"]
        DB["SQLite Database<br/>Task Storage"]
    end
    
    subgraph Governance["Governance (Future - Phase 3+)"]
        CI["GitHub Actions<br/>CI/CD Pipeline"]
        Broker["Broker Engine<br/>Policy Evaluation"]
    end
    
    Browser -->|HTTP/80| FE
    FE -->|Proxy /api<br/>http:5000| API
    API -->|Read/Write| DB
    CI -->|Build, Test<br/>Publish| FE
    CI -->|Collect Evidence| Broker
    Broker -->|Policy Decision| CI
    
    style Browser fill:#4A90E2,stroke:#000,stroke-width:2px,color:#fff
    style FE fill:#7B68EE,stroke:#000,stroke-width:2px,color:#fff
    style API fill:#50C878,stroke:#000,stroke-width:2px,color:#fff
    style DB fill:#FF9800,stroke:#000,stroke-width:2px,color:#fff
    style CI fill:#E74C3C,stroke:#000,stroke-width:2px,color:#fff
    style Broker fill:#9B59B6,stroke:#000,stroke-width:2px,color:#fff
```

**Three-Container Deployment:**
1. **Frontend** (Nginx): Reverse proxy, static assets (CSS/JS), template serving
2. **Backend** (Flask): REST API, authentication, task CRUD, SQLite integration
3. **Database** (SQLite): Embedded in backend for POC; future migration to external database

**Network:** Docker bridge network (`dra-network`) with health checks on each container

## Release Governance Flow

```mermaid
graph LR
    A["📦 Build & Test"] -->|collect evidence| B["📋 Evidence Package"]
    B -->|JSON payload| C["🔍 Broker Policy Engine"]
    C -->|decision| D{"Exit Code"}
    D -->|0: PASS| E["✅ Auto-Deploy"]
    D -->|10: FAIL| F["❌ Block Release"]
    D -->|20: APPROVAL_REQUIRED| G["⏳ Human Approval Gate"]
    G -->|approved| E
    G -->|rejected| F
    E -->|deployed| H["📊 Application Runtime"]
    H -->|collect runtime evidence| I["📋 Runtime Evidence"]
    I -->|JSON payload| C
    C -->|stricter policy| D
    
    style A fill:#4A90E2,stroke:#000,stroke-width:2px,color:#fff
    style B fill:#9B59B6,stroke:#000,stroke-width:2px,color:#fff
    style C fill:#E74C3C,stroke:#000,stroke-width:2px,color:#fff
    style E fill:#27AE60,stroke:#000,stroke-width:2px,color:#fff
    style F fill:#E67E22,stroke:#000,stroke-width:2px,color:#fff
    style G fill:#F39C12,stroke:#000,stroke-width:2px,color:#fff
    style H fill:#16A085,stroke:#000,stroke-width:2px,color:#fff
    style D fill:#34495E,stroke:#000,stroke-width:2px,color:#fff
    style I fill:#9B59B6,stroke:#000,stroke-width:2px,color:#fff
```

## Exit Codes & Policy Outcomes

The Broker returns deterministic exit codes that drive deployment decisions:

| Exit Code | Outcome | Action | Notes |
|-----------|---------|--------|-------|
| 0 | PASS | Deploy immediately | All policies satisfied |
| 10 | FAIL | Block release | Policy violation; no approval gate |
| 20 | APPROVAL_REQUIRED | Route to human gate | Medium/minor findings; approval can override |
| 30 | ERROR | Block release | Validation failure or provider error |

## Evidence Collection

Evidence is collected at two points in the pipeline:

### Pre-Deployment Evidence
Collected during CI/CD pipeline (build, test, publish stages):
- **Code diff**: Changes between base and current branch (relative paths only)
- **Dependencies**: Installed packages and versions
- **Test results**: Pass/fail counts, coverage metrics
- **Build logs**: Compilation output, build time
- **Container image**: Digest (SHA256), base images, layers

**Format**: JSON payload with relative paths only (no absolute paths, no `../` escapes)

### Post-Deployment Evidence
Collected after deployment to production:
- **Runtime configuration**: Environment variables, feature flags
- **System state**: Memory, CPU, disk usage
- **Application logs**: Errors, warnings, performance metrics
- **Service dependencies**: Connected services, versions
- **Security scan results**: Vulnerability assessments

**Format**: Same JSON structure as pre-deployment evidence

## Policy Decision Flow

```mermaid
graph TD
    A["Evidence Collected"] -->|JSON payload| B["Broker: Validate Input"]
    B -->|valid| C["Broker: Evaluate Policies"]
    B -->|invalid| D["❌ EXIT 30: ERROR"]
    C -->|all pass| E["✅ EXIT 0: PASS"]
    C -->|critical findings| F["❌ EXIT 10: FAIL"]
    C -->|medium findings| G{Pre vs Post Deploy?}
    G -->|pre-deploy| H["⏳ EXIT 20: APPROVAL_REQUIRED"]
    G -->|post-deploy| I["❌ EXIT 10: FAIL (stricter)"]
    E -->|immutable deploy| J["Deploy by image digest<br/>not rebuild"]
    H -->|human approves| J
    
    style A fill:#9B59B6,stroke:#000,stroke-width:2px,color:#fff
    style B fill:#E74C3C,stroke:#000,stroke-width:2px,color:#fff
    style C fill:#E74C3C,stroke:#000,stroke-width:2px,color:#fff
    style D fill:#E67E22,stroke:#000,stroke-width:2px,color:#fff
    style E fill:#27AE60,stroke:#000,stroke-width:2px,color:#fff
    style F fill:#E67E22,stroke:#000,stroke-width:2px,color:#fff
    style G fill:#34495E,stroke:#000,stroke-width:2px,color:#fff
    style H fill:#F39C12,stroke:#000,stroke-width:2px,color:#fff
    style I fill:#E67E22,stroke:#000,stroke-width:2px,color:#fff
    style J fill:#27AE60,stroke:#000,stroke-width:2px,color:#fff
```

## Immutable Deployment Principle

Once code is reviewed and approved, deployment uses the exact Docker image digest (SHA256 hash) that was reviewed—**never rebuilt**. This ensures:

- **What was reviewed is what runs** — no drift between CI and production
- **Reproducible deployments** — same digest always produces same behavior
- **Audit trail** — every deployment linked to exact code review and Broker decision
- **Policy enforcement** — Broker controls which digests can deploy

Example flow:
1. Build produces image digest `sha256:abc123def456...`
2. Image is published and evidence collected (includes digest)
3. Broker evaluates policy against evidence (digest included)
4. If approved, deployment pulls exact `sha256:abc123def456...` from registry
5. No rebuild, no recompilation—exact image that was reviewed runs in production

## System Components

### Runtime Tier
- **Application Pod**: Simple task tracker (minimal feature set)
- **Database**: SQLite (persistent volume)
- **Nginx**: Reverse proxy and static file serving

### Governance Tier
- **CI/CD Pipeline**: GitHub Actions (test → build → publish → evidence → Broker → approval → deploy)
- **Broker Engine**: Policy evaluation and decision making (can be mocked initially)
- **Evidence Collector**: Gathers build artifacts, test results, container metadata
- **Approval Gate**: Human review interface and decision routing
- **Post-Deploy Monitor**: Collects runtime evidence and triggers stricter policy review

### External Integrations
- **Docker Registry**: Stores and serves container images by digest
- **GitHub Actions**: Orchestrates CI/CD workflow, approval routing
- **Broker API**: Receives evidence, returns policy decisions (exit codes)

## Policy Evaluation (Simplified)

The Broker evaluates evidence against policies. Example policy logic:

```
IF test_results.failures > 0 THEN
  RETURN FAIL (exit 10)
END

IF dependencies.has_known_vulnerabilities THEN
  RETURN FAIL (exit 10)
END

IF code_diff.lines_changed > 5000 THEN
  RETURN APPROVAL_REQUIRED (exit 20)
END

IF all_checks_pass THEN
  RETURN PASS (exit 0)
END
```

Post-deployment policies are stricter (treat MEDIUM findings as FAIL instead of routing to approval).

## Deployment Workflow

### Pre-Deployment Gate (CI/CD)
```
1. Code pushed to branch
2. GitHub Actions triggered
3. Run tests → Build image → Publish to registry
4. Collect evidence (diff, dependencies, test results, image digest)
5. Invoke Broker with evidence
6. Broker returns exit code
   - EXIT 0 (PASS) → Deploy immediately
   - EXIT 10 (FAIL) → Stop, notify developers
   - EXIT 20 (APPROVAL_REQUIRED) → Create approval ticket, wait for human review
   - EXIT 30 (ERROR) → Stop, investigate error
7. If approved or PASS, deploy using image digest
```

### Post-Deployment Verification
```
1. Application deployed and running
2. Wait 5 minutes for stabilization
3. Collect runtime evidence (logs, metrics, health checks)
4. Invoke Broker with runtime evidence (uses stricter policy)
5. Broker returns exit code
   - EXIT 0 (PASS) → Release verified, mark as stable
   - EXIT 10 (FAIL) → Trigger rollback, create incident
   - EXIT 20/30 → Escalate (no approval gate in post-deploy)
```

## Key Design Decisions

1. **Evidence as JSON** — Structured, machine-readable, easy to version and audit
2. **Relative paths only** — Security: prevents path traversal attacks and accidental exposure of absolute paths
3. **Deterministic exit codes** — Clear, unambiguous decisions (no string parsing, no ambiguity)
4. **Two-policy model** — Pre-deploy: can route to approval; post-deploy: stricter, no approval
5. **Immutable deployments** — By digest, not by tag—ensures reviewed code actually runs
6. **Broker is stateless** — No side effects, only policy evaluation; evidence is the source of truth

## System Components

### Frontend Service (Nginx)
- **Role**: Reverse proxy, static file serving, request routing
- **Port**: 80
- **Serves**:
  - Static assets: CSS (`style.css`), JavaScript (`app.js`)
  - Templates: HTML templates (Jinja2)
  - Login page, dashboard, task forms
- **Proxies to**: Backend Flask API (`http://backend:5000`)
- **Features**:
  - Gzip compression
  - Security headers (X-Frame-Options, CSP)
  - Cache control for static assets
  - Health check endpoint (`/health`)

### Backend Service (Flask)
- **Role**: REST API, session management, authentication, business logic
- **Port**: 5000
- **Endpoints**:
  - `GET /health` — Health status
  - `POST /login` — User authentication
  - `POST /logout` — Session termination
  - `GET /` — Dashboard page
  - `GET /api/tasks` — List tasks (JSON or HTMX fragment)
  - `POST /api/tasks` — Create task
  - `GET /api/tasks/<id>` — Get single task
  - `PATCH /api/tasks/<id>` — Update task
  - `DELETE /api/tasks/<id>` — Delete task
  - `GET /api/tasks/<id>/edit` — Edit form (HTMX)
- **Features**:
  - Session-based authentication (demo: `user` / `password`)
  - HTMX-friendly responses (HTML fragments)
  - JSON API for programmatic access
  - SQLAlchemy ORM with SQLite
  - Automatic table creation on startup

### Database Service (SQLite)
- **Type**: Embedded SQLite (in backend for POC)
- **Location**: `/data/tasks.db` (Docker volume: `sqlite_data`)
- **Schema**:
  - `tasks` table: id, title, description, status, created_at, updated_at
- **Status**: Pending, In Progress, Completed
- **Future**: Migrate to PostgreSQL for production

### Application Models
- **Task**:
  - `id` (integer, primary key)
  - `title` (string, 1-200 chars, required)
  - `description` (text, optional)
  - `status` (enum: pending, in_progress, completed)
  - `created_at` (datetime, auto-set)
  - `updated_at` (datetime, auto-update)

## Repository Structure

```
DRA2.0-POC-Demo-app/
│
├── frontend/                      # Nginx reverse proxy container
│   ├── Dockerfile                # Alpine Nginx image
│   ├── nginx.conf                # Reverse proxy config, security headers, caching
│   ├── static/                   # Static assets (served by Nginx)
│   │   ├── css/
│   │   │   └── style.css         # Modern dark/light theme CSS (17.5 KB)
│   │   └── js/
│   │       └── app.js            # HTMX, theme toggle, modal management (9.7 KB)
│   └── templates/                # Jinja2 templates (served by Flask, cached)
│       ├── base.html             # Master template with header, sidebar
│       ├── login.html            # Authentication page
│       ├── dashboard.html        # Task manager interface
│       ├── task_list.html        # Reusable task list fragment
│       └── task_form.html        # Edit task modal form
│
├── backend/                       # Flask API container
│   ├── Dockerfile                # Python 3.12 + gunicorn
│   ├── app.py                    # Flask routes, auth, CRUD endpoints (170 lines)
│   ├── models.py                 # SQLAlchemy Task model, db initialization
│   ├── requirements.txt           # Flask, SQLAlchemy, gunicorn
│   └── __pycache__/              # Python bytecode (gitignored)
│
├── database/                      # Database placeholder (future PostgreSQL)
│   └── .gitkeep                  # Placeholder for external DB setup
│
├── docs/                          # Documentation hub
│   ├── index.MD                  # Navigation and quick links
│   ├── architecture.md           # This file (system design, components, governance)
│   ├── broker.md                 # Broker policy reference
│   ├── DEVELOPMENT.md            # Phase breakdown and roadmap
│   ├── operations.md             # Deployment, security, troubleshooting
│   ├── USAGE.MD                  # Getting started, local setup
│   └── glossary.md               # Terminology reference
│
├── scripts/                       # Automation scripts (future use)
│   ├── setup.sh                  # Environment provisioning
│   ├── build.sh                  # Docker image builds
│   ├── review.sh                 # Evidence collection, Broker invocation
│   ├── deploy.sh                 # Immutable deployment by digest
│   └── post-deploy.sh            # Post-deployment verification
│
├── .github/
│   └── workflows/                # GitHub Actions automation
│       ├── ci-cd.yml             # Build → Test → Publish → Broker → Deploy
│       └── post-deployment.yml   # Runtime verification, stricter policy
│
├── docker-compose.yml            # 3-container orchestration
├── README.md                      # Project overview, quick start
├── LICENSE                        # Proprietary license
├── .env.example                   # Environment variables template
├── .gitignore                     # Git exclusions
└── .git/                          # Git repository
```

**Directory Summary:**
- **frontend/**: Nginx + Static assets (CSS, JS) + Templates (~30 KB total)
- **backend/**: Flask API + SQLite ORM + CRUD logic (~200 lines)
- **docs/**: Complete documentation (guides, reference, governance flow)
- **scripts/**: CI/CD automation (future phases)
- **.github/workflows/**: GitHub Actions pipelines (future phases)

## Integration Points

- **GitHub Actions**: Calls Broker API with evidence, receives exit code, routes to approval or deployment
- **Broker API**: Stateless service that evaluates policies and returns exit codes
- **Approval gate**: GitHub issue creation, PR comment, or custom interface (out of scope for this POC)
- **Docker Registry**: Stores images; deployments reference exact digest
- **Application logs**: Post-deploy monitoring collects evidence for stricter policy review

## Testing Strategy

- **Unit tests**: Policy evaluation logic, evidence validation
- **Integration tests**: Broker API mocking, full CI/CD flow with fake evidence
- **End-to-end tests**: Real app deployment, evidence collection, Broker integration (can mock Broker initially)

## Security Considerations

- **Evidence integrity**: Evidence collected in CI/CD (trusted) pipeline; cannot be forged in production
- **No hardcoded credentials**: All secrets in environment variables or GitHub Secrets
- **Policy as code**: Policies should be version-controlled and auditable
- **Audit trail**: Every decision logged with evidence payload, timestamp, decision, and rationale
- **Approval routing**: Clear escalation path for human review (GitHub issue or custom UI)
