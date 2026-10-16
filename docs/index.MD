# Documentation

This proprietary proof of concept demonstrates a task-management application with AI-Broker evidence review in CI/CD. It is not production-ready and is not open to external contributions. Execution, testing, and deployment require prior written permission under the [license](../LICENSE).

| Guide | Contents |
| --- | --- |
| [Project overview](../README.md) | Application architecture, AI-Broker flow, and broker exit codes. |
| [Run locally](USAGE.MD#run-locally) | Docker Compose setup, authentication, and local storage. |
| [Test and build](USAGE.MD#test-and-build) | Prerequisites and application validation commands. |
| [Azure setup](USAGE.MD#azure-setup) | Azure resources, OIDC, private broker image access, variables, and secrets. |
| [Release review](USAGE.MD#release-review) | Pre-deployment gates, immutable image deployment, and separate post-deployment verification. |
| [Limitations](USAGE.MD#limitations) | Azure storage limitations, evidence privacy, and private broker availability. |
| [Contribution policy](CONTRIBUTING.md) | No external contributions; permission requirements and AI-Broker scope. |
| [Glossary](glossary.md) | Project terminology and review outcomes. |

## AI-Broker Boundary

The private AI-Broker is maintained separately and is not included in this repository. It analyzes selected evidence using Gemini or Groq and returns deterministic policy outcomes; the consuming workflows enforce release and approval gates and perform deployment.

Post-deployment review requires a separate invocation. The broker does not build, deploy, modify code, roll back, or provide continuous monitoring.

## Repository Map

- `frontend/`: authenticated Flask UI, Nginx, and HTMX.
- `backend/`: task API and validation.
- `database/`: CRUD API and SQLite storage.
- `scripts/`: setup, validation, build, review, deployment, and cleanup.
- `.github/workflows/`: release review, deployment, and verification.

[Back to overview](../README.md)