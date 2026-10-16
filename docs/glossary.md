# Glossary

| Term | Meaning |
| --- | --- |
| ACR | Azure Container Registry, which stores application images. |
| AcrPull | Azure role allowing a Container App's managed identity to pull images from ACR. |
| AI-Broker | Private, separately maintained evidence scanner using Gemini or Groq. It reports policy outcomes; it does not build, deploy, modify code, roll back, or monitor continuously. |
| Approval gate | Protected `dra-approval` environment with required reviewers. Approval-based releases also require `APPROVAL_GATE_ENABLED=true`. |
| Build manifest | JSON record linking a commit to immutable application image digests. `BUILD_MANIFEST` points to the record used for deployment without rebuilding. |
| CI/CD | Continuous integration and delivery or deployment: testing, packaging, and releasing changes. |
| Container Apps | Azure service hosting the application's containers. |
| Consuming workflow | GitHub Actions workflow that invokes AI-Broker and enforces release checks, approval gates, and deployment. |
| CRUD | Create, read, update, and delete operations. |
| Evidence | Explicitly selected UTF-8 text supplied for review, such as test results, source changes, or operational data. Pre-filter sensitive data before external inference. |
| Exit code | Numeric process result consumed by CI/CD, not a severity score. Broker codes are listed below. |
| Fail closed | Block release when review fails or cannot complete; an error never authorizes deployment. |
| Finding | Model-generated recommendation, not a verified vulnerability. Results may vary. |
| GHCR | GitHub Container Registry, which hosts the private broker image. |
| HTMX | Browser library used for task updates without full-page reloads. |
| Image digest | Immutable container image identifier, such as `sha256:...`. Pin `BROKER_IMAGE_DIGEST` to an approved GHCR digest, not a mutable tag. |
| Managed identity | Azure identity used by Container Apps to access resources such as ACR without stored registry credentials. |
| OIDC | OpenID Connect, used by GitHub Actions to authenticate to Azure. |
| POC | Proof of concept, not a production-ready product. This proprietary POC is not open to external contributions. |
| Policy | Deterministic rules mapping model findings to outcomes. Defaults fail critical/high findings; medium findings require pre-deployment approval and fail post-deployment review. |
| Post-deployment review | Separate `post_deploy` scan of operational evidence after deployment; not automatic rollback or continuous monitoring. |
| Pre-deployment review | `pre_deploy` scan of selected evidence before release. The workflow enforces its outcome alongside other required checks. |
| Proprietary | Governed by the [license](../LICENSE); public visibility grants no reuse permission. |
| Provider | External AI service, Gemini or Groq, selected through `AI_PROVIDER` with its model setting and API key. |
| Redaction | Best-effort removal of sensitive content before inference; not a substitute for pre-filtering evidence. |
| Secrets | Protected credentials, including provider keys, the GHCR token, and application credentials. Never commit them or expose them to untrusted pull requests. |
| SQLite | File-based database used for task storage. |
| Workflow dispatch | Manual GitHub Actions trigger. The release workflow currently uses this trigger; pushes to `main` do not start it automatically. |

## Review Outcomes

| Outcome | Broker exit code | Pre-deployment | Post-deployment |
| --- | --- | --- | --- |
| `PASS` | `0` | Broker check passes; all other required checks must also pass before deployment. | Broker check passes; operational checks must also pass. |
| `APPROVAL_REQUIRED` | `20` | Requires the enabled approval gate, human approval, and all other required checks. | Not returned; approval-level findings produce `FAIL`. |
| `FAIL` | `10` | Policy findings block deployment. | Policy findings fail verification; no automatic rollback. |
| `ERROR` | `30` | Scan could not complete, for example due to invalid evidence or a provider error; deployment is blocked. | Scan could not complete; verification fails with no automatic rollback. |

[Documentation index](index.MD)