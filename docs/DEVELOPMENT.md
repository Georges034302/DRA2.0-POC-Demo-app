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
| 2 | Test, build, deploy (dev) | `post-test.sh` (DB/TASKS/SECURITY suites), `build.sh` (ACR push), `deploy.sh STAGE=dev` — each produces a report |
| 3 | AI-Broker review & promotion | `review.sh` sends all 4 reports to the Broker; PASS/approved `APPROVAL_REQUIRED` promotes the same digest to prod via `deploy.sh STAGE=prod`; FAIL/ERROR leaves prod untouched |
| 4 | Live Azure rollout | Provision real dev/prod infra (`env-setup.sh`), configure OIDC/secrets (`auth-setup.sh`), exercise the full pipeline end-to-end against live Azure, tests/lint/security green, docs finalized, demo rehearsed |

## Technology Stack

- **Frontend:** Nginx (reverse proxy, static assets)
- **Backend:** Flask (REST API with Bearer token auth)
- **Database:** Flask + SQLite (CRUD API, persistent storage)
- **Orchestration:** Docker & Docker Compose
- **CI/CD:** GitHub Actions (single `ci-cd.yml` pipeline)
- **Pre-commit (local only):** ruff, detect-secrets, pip-audit, via `.pre-commit-config.yaml`
- **Post-commit (CI):** pytest — DB, TASKS, SECURITY suites

## Project Structure

```
DRA2.0-POC-Demo-app/
├── frontend/                       # Nginx reverse proxy + static assets + templates
├── backend/                        # Flask API (calls the database service)
├── database/                       # Flask CRUD API over SQLite
├── tests/                          # pre-commit/ (lint/secrets/audit) + post-commit/ (DB/TASKS/SECURITY)
├── docs/                           # Documentation hub (architecture, guides, reference)
├── scripts/                        # auth/env setup, test/build/deploy/post-deploy/review/cleanup
├── .github/                        # GitHub Actions workflow (ci-cd.yml)
├── .pre-commit-config.yaml         # Wires tests/pre-commit/ into git's pre-commit hook
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
4. Commit (pre-commit hook runs ruff/detect-secrets/pip-audit)
5. Push
```

### CI/CD Pipeline (GitHub Actions, `ci-cd.yml`)
```
1. Test: DB/TASKS/SECURITY suites (scripts/post-test.sh) → test_report.md
2. Build: Images with digest tracking, push to ACR (scripts/build.sh) → build_report.md
3. Deploy (dev): Deploy digest to dev-stage Container Apps (scripts/deploy.sh STAGE=dev) → deployment_report.md
4. Post-Deploy (dev): Collect dev-stage health evidence (scripts/post-deploy.sh STAGE=dev) → results.md
5. Review: Broker reads all 4 reports (scripts/review.sh), returns a decision
6. Policy Decision: PASS / FAIL / APPROVAL_REQUIRED / ERROR
7. Approval Gate: If APPROVAL_REQUIRED, route to human review (dra-approval environment)
8. Promote: PASS or approved APPROVAL_REQUIRED redeploys the same digest to prod (scripts/deploy.sh STAGE=prod)
```

### Evidence Collection

All evidence is Markdown, written to `temp/reports/` during the pipeline run and uploaded as GitHub Actions artifacts:

| Report | Script | Contents |
|--------|--------|----------|
| `temp/reports/test_report.md` | `scripts/post-test.sh` | Status + pass/fail/error/skip counts per suite: DB, TASKS, SECURITY |
| `temp/reports/build_report.md` | `scripts/build.sh` | Per-service image digest |
| `temp/reports/deployment_report.md` | `scripts/deploy.sh STAGE=dev` | Per-service app name, image digest, FQDN |
| `temp/reports/results.md` | `scripts/post-deploy.sh STAGE=dev` | Per-service revision/status, log counts, frontend `/health` result |

See [AI-Broker Reference](./broker.md#input-validation) for the evidence/request schema these reports must satisfy.

### AI-Broker Outputs & Decisions

`scripts/review.sh` packages the 4 reports above into a `request.json` (`mode: pre_deploy` — chosen because only this mode supports `APPROVAL_REQUIRED`, which this pipeline needs to gate promotion) and invokes the Broker container, which returns `result.json`:
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
    "evidence_items_analyzed": 4,
    "scan_duration_ms": 2345,
    "model_used": "gemini-2.0-flash|groq-large"
  }
}
```

`review.sh` maps `outcome` to the Broker's exit code (`PASS`→0, `FAIL`→10, `APPROVAL_REQUIRED`→20, `ERROR`→30) and treats any mismatch as `ERROR` (fail-closed). See [AI-Broker Reference](./broker.md#result-format) for full policy mapping rules.

## Policy Decision Outcomes

| Exit Code | Outcome | Action |
|-----------|---------|--------|
| 0 | PASS | Promote dev digest to prod |
| 10 | FAIL | Reject; prod untouched |
| 20 | APPROVAL_REQUIRED | Route to human review |
| 30 | ERROR | Reject; prod untouched (validation failure) |

**Post-deployment uses stricter policy:** Medium/High/Critical findings trigger FAIL instead of APPROVAL_REQUIRED.

## Key Principles

**Immutable Deployments:** Broker approves the image digest (SHA256), not code. The same digest is deployed to dev, reviewed, then promoted unchanged to prod — no rebuild.

**Evidence-Driven Decisions:** Policies evaluate concrete evidence from the test, build, deploy, and post-deploy stages. Reproducible, auditable, no guessing.

**Dev/Prod Staging:** The Broker only controls promotion — it never blocks the initial dev deployment, and a rejected release simply never reaches prod.

## Success Criteria

### Phase 1
- [x] docker-compose up succeeds
- [x] Login with demo credentials works
- [x] CRUD operations work (create, read, update, delete)
- [x] Data persists across container restarts

### Phase 2
- [ ] Azure infra provisioned (`env-setup.sh`)
  - resource group, ACR, Container Apps environment, Log Analytics workspace
  - dev/prod app-name pairs generated and tagged on the resource group
- [ ] Azure OIDC secrets/vars configured (`auth-setup.sh`)
- [ ] CI/CD pipeline runs end-to-end
  - test (DB/TASKS/SECURITY) → build → deploy to dev stage
  - unconditional on successful tests/build, no gate yet
- [ ] Each stage produces its Markdown report in `temp/reports/`

### Phase 3
- [ ] GHCR and AI provider secrets/vars configured in GitHub
- [ ] `review.sh` sends all 4 reports to the real AI-Broker container
  - see [AI-Broker Reference](./broker.md) for the evidence/request schema
- [ ] Broker returns PASS/FAIL/APPROVAL_REQUIRED/ERROR from the evidence payload
- [ ] Approval gate activates
  - routes `APPROVAL_REQUIRED` outcomes to human review
- [ ] Prod untouched on FAIL/ERROR
- [ ] Prod promoted (`deploy.sh STAGE=prod`) on PASS or an approved `APPROVAL_REQUIRED`

### Phase 4
- [ ] Full pipeline exercised end-to-end against live Azure dev/prod infra
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
