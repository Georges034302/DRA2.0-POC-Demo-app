# Documentation Index

Complete reference for the DRA 2.0 POC Demo Application.

**Status:** Proprietary proof of concept. Not open to external contributions. Prior written permission required for any use beyond internal evaluation.

---

## Quick Navigation

| Document | Purpose | Audience |
|----------|---------|----------|
| **[README](../README.md)** | Project overview, quick start, at-a-glance architecture | Everyone |
| **[Development Guide](DEVELOPMENT.md)** | Implementation phases, success criteria, development roadmap | Developers, engineers |
| **[Architecture](architecture.md)** | Complete release governance flow, broker integration, exit codes | Engineers, architects |
| **[Broker Reference](broker.md)** | Policy evaluation, review modes, result format, redaction | Operators, reviewers |
| **[Operations](operations.md)** | Azure deployment, security, troubleshooting, performance | DevOps, operators |
| **[Getting Started](USAGE.MD)** | Local setup, Docker Compose, Azure scripts, validation | Developers |
| **[Glossary](glossary.md)** | Terminology and definitions | Reference |

---

## Common Tasks

### Getting Started

- **Run locally:** [Getting Started > Run Locally](USAGE.MD#run-locally)
- **Test the application:** [Getting Started > Test and Build](USAGE.MD#test-and-build)
- **Deploy to Azure:** [Operations > Azure Deployment](operations.md#azure-deployment)

### Understanding the System

- **How release governance works:** [Architecture](architecture.md)
- **What the Broker does:** [Broker Reference](broker.md)
- **Pre/Post-deployment review:** [Broker > Review Modes](broker.md#review-modes)
- **Policy outcomes:** [Broker > Exit Codes](broker.md#exit-codes--outcomes)
- **Development roadmap:** [Development Guide](DEVELOPMENT.md)

### Deployment & Operations

- **Secure credential handling:** [Operations > Security](operations.md#security--evidence-management)
- **Broker configuration:** [Operations > Broker Image Security](operations.md#broker-image-security)
- **Troubleshoot issues:** [Operations > Troubleshooting](operations.md#troubleshooting)
- **Performance guidelines:** [Operations > Performance](operations.md#performance-considerations)

### Reference

- **Find a term:** [Glossary](glossary.md)
- **View policy details:** [AI-Broker > Policy Evaluation](broker.md#policy-evaluation)
- **Check system boundaries:** [Architecture > Broker Boundary](architecture.md#broker-boundary)

---

## Key Concepts

**Release Governance:** Automated policy-driven release gates using Broker evidence review and human-controlled approvals.

**Broker:** External policy engine that analyzes code and deployment evidence, returning deterministic outcomes (PASS/FAIL/APPROVAL_REQUIRED/ERROR).

**Immutable Digests:** Application images are reviewed by SHA256 digest and deployed without rebuilding.

**Pre-Deployment Review:** Analyzes code changes before release; can block, require approval, or pass.

**Post-Deployment Verification:** Analyzes deployed state after release; can verify or flag issues (no automatic rollback).

**Evidence Redaction:** Sensitive data must be pre-filtered before broker analysis to protect credentials and PII.

**Approval Gate:** Protected GitHub environment requiring human review and approval for medium-severity findings.

See **[Glossary](glossary.md)** for complete terminology reference.

---

## Repository Structure

```
frontend/               # Nginx reverse proxy, Flask UI, HTMX
backend/                # Flask REST API, task validation
database/               # CRUD API, SQLite persistence
scripts/                # Automation: build, review, deploy, verify
  ├─ setup.sh          # Azure infrastructure provisioning
  ├─ build.sh          # Build and publish images
  ├─ review.sh         # Prepare evidence, invoke broker
  ├─ deploy.sh         # Deploy reviewed digests
  └─ post-deploy.sh    # Post-deployment verification
.github/workflows/      # GitHub Actions automation
  ├─ ci-cd.yml         # Release pipeline
  └─ post-deployment.yml   # Post-deployment verification
docs/                   # Complete documentation (you are here)
  ├─ index.MD          # Navigation hub
  ├─ README.md         # Project overview
  ├─ architecture.md   # Release governance flow
  ├─ broker.md         # AI-Broker reference
  ├─ operations.md     # Deployment and operations
  ├─ USAGE.MD          # Getting started
  ├─ CONTRIBUTING.md   # Contribution policy
  └─ glossary.md       # Terminology
```

---

## Security & Compliance

- **Credentials:** All secrets stored in protected GitHub Actions variables
- **Evidence Redaction:** Pre-filter sensitive data before broker analysis
- **Audit Trail:** Results retained for 30 days for investigation
- **Approval Gates:** Configurable human review via protected GitHub environments
- **Immutable Deployment:** Reviewed image digests prevent post-deployment tampering

---

## Important Limitations

- **Not for Production:** POC only; not hardened for production use
- **No Rollback:** Post-deployment verification cannot trigger automatic rollback
- **Data Persistence:** Azure deployment does not configure persistent database storage
- **Broker is External:** Maintained separately; not included in this repository
- **Model Findings:** AI-generated recommendations; not verified vulnerabilities

---

## License

**Proprietary.** Public visibility grants no usage rights. Prior written permission required from the copyright holder.

See **[LICENSE](../LICENSE)** for complete terms.

---

<p align="center">
	<sub><span style="color:#666">DRA 2.0 POC · Release Governance Demo · Dr. Georges Bou Ghantous © 2026</span></sub>
</p>
