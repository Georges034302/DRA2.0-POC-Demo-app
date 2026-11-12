# Documentation Index

DRA 2.0 POC — Release Governance Demo

**Status:** Proprietary. Prior written permission required for any use.

## Quick Navigation

| Document | Purpose |
|----------|---------|
| [Quick Start](USAGE.MD) | Local setup, testing, CI/CD workflow |
| [Development Guide](DEVELOPMENT.md) | Implementation phases, success criteria |
| [Architecture](architecture.md) | System design, broker flow, exit codes |
| [Operations](operations.md) | Setup, deployment, troubleshooting |
| [Broker Spec](broker.md) | Policy evaluation, review modes, results |
| [Glossary](glossary.md) | Terminology reference |

## Common Tasks

**Get running:** [Quick Start > Local Setup](USAGE.MD#local-setup)

**Understand the system:** [Architecture](architecture.md) | [Broker Spec](broker.md)

**Deploy:** [Operations > Setup & Prerequisites](operations.md#setup--prerequisites)

**Troubleshoot:** [Operations > Troubleshooting](operations.md#troubleshooting)

**Find a term:** [Glossary](glossary.md)

## Key Concepts

**Release Governance:** Policy-driven release gates using evidence review and human approval.

**Broker:** External policy engine analyzing code and deployment evidence, returns PASS/FAIL/APPROVAL_REQUIRED/ERROR.

**Immutable Digests:** Images reviewed by SHA256 digest; deployment uses exact reviewed digest (no rebuild).

**Pre-Deployment Review:** Analyzes changes before release; can block, require approval, or pass.

**Post-Deployment Verification:** Analyzes deployed state; cannot automatically rollback.

**Evidence Redaction:** Remove API keys, credentials, and PII before broker analysis.

**Pipeline Status:** Phase 2 (CI/CD + Azure deploy) active; Phase 3 (Broker pre-deploy invocation) pending — placeholder in `ci-cd.yml`; Phase 4 (post-deploy Broker governance) active. See [Development Guide](DEVELOPMENT.md).

## Repository Structure

```
frontend/             # Nginx reverse proxy, static UI
backend/              # Flask REST API
database/             # CRUD API, SQLite
scripts/              # build.sh, review.sh (Phase 3), deploy.sh, post-deploy.sh (Phase 4)
.github/workflows/    # ci-cd.yml, post-deployment.yml
docs/                 # Documentation (you are here)
```

## Important Notes

- **Not for Production:** POC only
- **Data Persistence:** Not configured in deployments; configure volume for production
- **Broker External:** Maintained separately; does not build, deploy, or rollback
- **Results:** Findings, not verified vulnerabilities
- **Credentials:** Never commit `.env` or include in evidence

---

**License:** Proprietary. See [LICENSE](../LICENSE).

© 2026 Dr. Georges Bou Ghantous
