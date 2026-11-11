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
        API["Flask API<br/>Authentication<br/>Task Routes"]
    end

    subgraph Database["Database Container (Flask)"]
        DB["CRUD API<br/>SQLite Task Storage"]
    end
    
    subgraph Governance["Governance (Future - Phase 3+)"]
        CI["GitHub Actions<br/>CI/CD Pipeline"]
        Broker["Broker Engine<br/>Policy Evaluation"]
    end
    
    Browser -->|HTTP/80| FE
    FE -->|Proxy /api<br/>http:5000| API
    API -->|HTTP :5001<br/>Internal token| DB
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
1. **Frontend** (Nginx): Reverse proxy, serves static HTML/CSS/JS, routes `/api/*` to backend
2. **Backend** (Flask): REST API with authentication, proxies task operations to database
3. **Database** (Flask + SQLite): CRUD API that manages task storage

**Networking:** Docker bridge network enables cross-container communication via service DNS. Ports: frontend 8080→80, backend 5000, database 5001. Health checks on `/health` endpoint.

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

### Frontend Service (Nginx)
- **Role**: Reverse proxy, static file serving, request routing
- **Port**: 80
- **Serves**:
  - Static assets: CSS (`style.css`), JavaScript (`app.js`)
  - Static HTML pages: login and dashboard
- **Proxies to**: Backend Flask API (`http://127.0.0.1:5000`)
- **Features**:
  - Gzip compression
  - Security headers (X-Frame-Options, X-Content-Type-Options)
  - Short-lived cache control for static assets
  - Health check endpoint (`/health`)

### Backend Service (Flask)
- **Role**: REST API, authentication, forwards task operations to the database service
- **Port**: 5000
- **Endpoints**:
  - `GET /health` — Health status
  - `POST /api/auth/login` — Checks `DEMO_USERNAME` / `DEMO_PASSWORD` and returns a signed token (valid 8 hours)
  - `GET /api/tasks` — List tasks
  - `POST /api/tasks` — Create task
  - `GET /api/tasks/<id>` — Get single task
  - `PATCH /api/tasks/<id>` — Update task
  - `DELETE /api/tasks/<id>` — Delete task
- **Features**:
  - Task routes require `Authorization: Bearer <token>`; tokens are signed with `SECRET_KEY`
  - Refuses to start unless `SECRET_KEY`, `INTERNAL_API_TOKEN`, `DEMO_USERNAME` and `DEMO_PASSWORD` are set
  - No direct database access: task requests go to the database service (`DATABASE_SERVICE_URL`, default `http://localhost:5001`)
  - Returns `502` when the database service is unreachable or rejects the internal token

### Database Service (Flask + SQLite)
- **Role**: Owns the data; offers CRUD APIs for the backend
- **Port**: 5001
- **Files**:
  - `init-db.py` — creates the schema and loads initial data (only into an empty table); run on container start
  - `app.py` — CRUD API
- **Endpoints**:
  - `GET /health` — Health status
  - `GET /api/tasks` — List tasks
  - `POST /api/tasks` — Create task
  - `GET /api/tasks/<id>` — Get single task
  - `PATCH /api/tasks/<id>` — Update task
  - `DELETE /api/tasks/<id>` — Delete task
- **Security**: `/api/*` requires the `X-Internal-Token` header matching `INTERNAL_API_TOKEN`
- **Location**: `/data/tasks.db` (Docker volume: `sqlite_data`)
- **Future**: Migrate to PostgreSQL for production

### Application Models
- **Task**:
  - `id` (integer, primary key)
  - `title` (string, 1-200 chars, required)
  - `description` (text, optional, up to 2000 chars)
  - `priority` (enum: low, medium, high; default medium)
  - `status` (enum: todo, in_progress, done; default todo)
  - `created_at` (datetime, auto-set)
  - `updated_at` (datetime, auto-update)

## Repository Structure

```
DRA2.0-POC-Demo-app/
├── frontend/                      # Nginx reverse proxy + static assets + templates
├── backend/                       # Flask API (calls the database service)
├── database/                      # Database microservice: init-db.py + CRUD API over SQLite
├── docs/                          # Documentation hub (architecture, guides, reference)
├── scripts/                       # Automation scripts (setup, build, deploy, verify)
├── .github/                       # GitHub Actions workflows (CI/CD, post-deploy)
├── docker-compose.yml            # 3-container orchestration config
├── README.md                      # Project overview and quick start
├── LICENSE                        # Proprietary license terms
├── .env.example                   # Environment variables template
├── .gitignore                     # Git exclusions
└── .git/                          # Git repository history
```

**Key Directories:**
- **frontend/**: Nginx (Dockerfile, nginx.conf) + static/ (css, js) + templates/ (HTML)
- **backend/**: Flask app (app.py, models.py) + requirements.txt + Dockerfile
- **docs/**: architecture.md, DEVELOPMENT.md, broker.md, operations.md, USAGE.MD, glossary.md, index.MD
- **scripts/**: setup.sh, build.sh, review.sh, deploy.sh, post-deploy.sh (future phases)
- **.github/workflows/**: ci-cd.yml, post-deployment.yml (future phases)

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
