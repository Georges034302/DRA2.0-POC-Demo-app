# DRA 2.0 — Release Governance with AI Policy Engine

Demonstrates policy-driven release gates using AI evidence analysis and human approval.

**Status:** Proprietary POC. Prior written permission required.

## Overview

**What It Proves:**
- AI policy engine (Broker) reviews evidence from code builds
- Evidence-based decisions block, require approval, or pass releases
- Human reviewers approve when policy requires it
- Deployed code matches exactly what was reviewed (by digest)
- Post-deployment verification enforces stricter policy

**Key Principles:**
- Immutable deployments by SHA256 digest
- Evidence-driven decisions (no guessing)
- Fail closed (errors block, never authorize)
- Human approval gates for approval-required findings

## AI Policy Engine Workflow

```mermaid
flowchart LR
    A["Test & Build"] 
    B["Deploy<br/>Dev Stage"]
    C["AI Broker<br/>Analyze Reports"]
    D{{"Decision<br/>PASS/FAIL/APPROVE"}}
    E["Approval<br/>Human Review"]
    F["Promote<br/>Same Digest → Prod"]
    
    A -->|Reports| B
    B -->|Reports| C
    C -->|Result| D
    D -->|PASS| F
    D -->|APPROVE| E
    E -->|Approved| F
    D -->|FAIL| X["Reject"]
    
    style A fill:#4A90E2,stroke:#000,stroke-width:2px,color:#fff,font-size:14px
    style B fill:#16A085,stroke:#000,stroke-width:2px,color:#fff,font-size:14px
    style C fill:#E74C3C,stroke:#000,stroke-width:2px,color:#fff,font-size:14px
    style D fill:#F39C12,stroke:#000,stroke-width:2px,color:#fff,font-size:14px
    style E fill:#F39C12,stroke:#000,stroke-width:2px,color:#fff,font-size:14px
    style F fill:#27AE60,stroke:#000,stroke-width:2px,color:#fff,font-size:14px
    style X fill:#C0392B,stroke:#000,stroke-width:2px,color:#fff,font-size:14px
```

## System Architecture

```mermaid
graph LR
    UI["🌐 Browser"]
    APP["📦 Application<br/>Dev / Prod"]
    TEST["🧪 Test<br/>DB/TASKS/SECURITY"]
    BUILD["🔨 Build<br/>Push to ACR"]
    DEPLOY["🚀 Deploy<br/>Dev Stage"]
    BROKER["🤖 AI Broker<br/>Policy Analysis"]
    GATE["🔐 Approval<br/>Gate"]
    
    UI -->|Access| APP
    TEST --> BUILD --> DEPLOY
    DEPLOY -.->|deploys| APP
    DEPLOY -->|Reports| BROKER
    BROKER -->|Decision| GATE
    GATE -->|Promote| APP
    
    style UI fill:#4A90E2,stroke:#000,stroke-width:2px,color:#fff,font-size:12px
    style APP fill:#7B68EE,stroke:#000,stroke-width:2px,color:#fff,font-size:12px
    style TEST fill:#FF6B6B,stroke:#000,stroke-width:2px,color:#fff,font-size:12px
    style BUILD fill:#FF6B6B,stroke:#000,stroke-width:2px,color:#fff,font-size:12px
    style DEPLOY fill:#16A085,stroke:#000,stroke-width:2px,color:#fff,font-size:12px
    style BROKER fill:#E74C3C,stroke:#000,stroke-width:2px,color:#fff,font-size:12px
    style GATE fill:#F39C12,stroke:#000,stroke-width:2px,color:#fff,font-size:12px
```

## The Application

Task tracker: minimal app to verify governance pipeline works with real code.

- **Frontend:** Nginx (login, dashboard)
- **Backend:** Flask REST API (authentication, task CRUD)
- **Database:** CRUD API over SQLite
- **UI:** Plain HTML, no framework

**Run Locally:**
```sh
cp .env.example .env
docker compose up --build
open http://localhost:8080
```

## Key Design Decisions

| Aspect | Decision | Reason |
|--------|----------|--------|
| **App** | Minimal (tasks only) | Focus on governance, not features |
| **Deployment** | By digest (SHA256) | Ensures exact reviewed code runs |
| **Policy** | AI-based | Demonstrates automated governance |
| **Human Gate** | For approval findings | Humans control medium-severity releases |
| **Dev/Prod Staging** | Deploy to dev, promote on approval | Broker never blocks the dev deploy, only prod promotion |
| **Scope** | POC only | Not production-ready; demonstrates concept |

## Documentation

Complete guides and references for setup, deployment, and operations.

- **[Quick Start](docs/USAGE.MD)** — Local setup, testing, CI/CD workflow
- **[Architecture](docs/architecture.md)** — System design, broker flow, policy outcomes
- **[Broker Spec](docs/broker.md)** — Policy evaluation, evidence format, results
- **[Operations](docs/operations.md)** — Setup, deployment, troubleshooting
- **[Index](docs/index.MD)** — Complete documentation navigation

## License

**Proprietary.** Prior written permission required. See [LICENSE](LICENSE).
