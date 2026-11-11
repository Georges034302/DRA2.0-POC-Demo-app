# Glossary

| Term | Definition |
|------|-----------|
| AI-Broker | External policy engine analyzing evidence, returns PASS/FAIL/APPROVAL_REQUIRED/ERROR. Does not build, deploy, rollback, or monitor. |
| Approval gate | Protected GitHub environment (`dra-approval`) with required reviewers; required when broker returns APPROVAL_REQUIRED (exit 20). |
| Broker | See AI-Broker. |
| Build manifest | JSON record linking commit SHA to image digests. Used for deployment without rebuilding. |
| CI/CD | Continuous integration and delivery: testing, building, and releasing. |
| Container Apps | Azure service hosting application containers. |
| CRUD | Create, read, update, delete operations. |
| Evidence | Text data supplied for broker review: code diffs, dependencies, test results, logs. Pre-filter secrets before submission. |
| Exit code | Numeric broker result consumed by CI/CD; not a severity. See outcomes below. |
| Fail closed | Block deployment if review fails or cannot complete. Errors never authorize deployment. |
| Finding | Model-generated recommendation, not a verified vulnerability. Results may vary. |
| GHCR | GitHub Container Registry hosting broker image. Pin `BROKER_IMAGE_DIGEST` to approved digest, never floating tags. |
| Image digest | Immutable container identifier (SHA256 hash). Ensures exact reviewed code runs in production. |
| Immutable deployment | Deploy by approved digest only; no rebuild after approval. |
| OIDC | OpenID Connect, used by GitHub Actions to authenticate to Azure. |
| POC | Proof of concept. Proprietary, not open to external contributions. |
| Post-deployment review | Broker scans operational evidence after deployment; cannot automatically rollback. |
| Pre-deployment review | Broker scans code/build evidence before deployment. |
| Proprietary | Governed by license; public visibility grants no reuse rights. |
| Redaction | Pre-filter sensitive data (API keys, passwords, PII) before broker analysis. |
| Release governance | Policy-driven release gates using evidence review and human approval. |
| Secrets | Protected credentials (provider keys, tokens, passwords). Never commit or expose in evidence. |

## Policy Outcomes

| Outcome | Exit Code | Pre-Deploy | Post-Deploy |
|---------|-----------|-----------|------------|
| PASS | 0 | Broker passes; all other checks must also pass | Broker passes; deploy verified |
| APPROVAL_REQUIRED | 20 | Route to approval gate; human decision required | Not returned; approval findings trigger FAIL |
| FAIL | 10 | Block deployment | Block verification; no auto-rollback |
| ERROR | 30 | Block; review could not complete | Block; review could not complete |