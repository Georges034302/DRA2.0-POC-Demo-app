# Glossary

| Term | Meaning |
| --- | --- |
| ACR | Azure Container Registry, which stores application images. |
| AI-Broker | Separately maintained scanner that reviews selected evidence using an AI provider and maps findings to policy outcomes. It does not build or deploy the app. |
| Approval gate | Protected `dra-approval` environment requiring human review for approval-based releases. |
| CI/CD | Continuous integration and delivery or deployment: testing, packaging, and releasing changes. |
| Container Apps | Azure service hosting the application's containers. |
| CRUD | Create, read, update, and delete operations. |
| Evidence | Selected source changes or operational data supplied for broker review. |
| GHCR | GitHub Container Registry, which hosts the private broker image. |
| HTMX | Browser library used for task updates without full-page reloads. |
| Image digest | Immutable container image identifier, such as `sha256:...`. |
| OIDC | OpenID Connect, used by GitHub Actions to authenticate to Azure. |
| POC | Proof of concept; a demonstration rather than a production-ready deployment. |
| SQLite | File-based database used for task storage. |

## Review Outcomes

| Outcome | Release behavior |
| --- | --- |
| `PASS` | Review permits deployment. |
| `APPROVAL_REQUIRED` | Deployment requires the enabled approval gate and human approval. |
| `FAIL` | Policy findings block deployment. |
| `ERROR` | Review could not complete successfully; deployment is blocked. |

[Documentation index](index.MD)