# DRA 2.0 POC Demo App

- Containerized task-management demo with pre- and post-deployment AI-Broker evidence review.
- Proprietary proof of concept, not a production-ready product.
- Not open to external contributions; see the [contribution policy](docs/CONTRIBUTING.md).

## What’s inside

| Service | Responsibility |
| --- | --- |
| Frontend | Authenticated task UI, served by Nginx and Flask; HTMX powers task updates. |
| Backend | Internal REST API and task validation. |
| Database | Internal CRUD API with SQLite storage. |

- Only the frontend is publicly exposed; backend and database APIs are internal.

## Application and Release Flow

```mermaid
flowchart LR
    subgraph Runtime[Application runtime]
        Browser --> Frontend[Frontend<br/>Nginx + Flask]
        Frontend --> Backend[Backend<br/>Flask API]
        Backend --> Database[Database<br/>Flask + SQLite]
    end

    subgraph Workflow[Consuming CI/CD workflows]
        Build[Test, build and publish<br/>immutable application image digests]
        Pre[Prepare pre_deploy request<br/>and selected, pre-filtered evidence]
        PreGate{Pre-deploy outcome}
        Approval[Separately authorized approval gate<br/>Protected dra-approval environment]
        Checks{All other checks passed?}
        Deploy[Deploy reviewed image digests<br/>without rebuilding]
        Block[Block release]
        Post[Separate post-deployment workflow<br/>Collect revision and health evidence<br/>Prepare post_deploy request]
        PostGate{Post-deploy outcome}
        Verified[Verification passed]
        Failed[Verification failed<br/>No automatic rollback]
    end

    subgraph Broker[AI-Broker container - pinned approved GHCR digest]
        Input[Validate JSON request and explicitly listed evidence<br/>Check relative paths, UTF-8 text and size limits]
        Scan[Best-effort redaction<br/>Gemini or Groq evidence analysis]
        Policy[Deterministic policy evaluation<br/>Default: critical/high fail, medium needs approval<br/>Medium fails in post_deploy mode]
        Result[JSON result and exit code<br/>Outcome, summary, findings, policy version, metrics]
        Input --> Scan --> Policy --> Result
        Input -->|Invalid input| Result
        Scan -->|Provider error| Result
    end

    Build --> Pre --> Input
    Result --> Mode{Request mode}
    Mode -->|pre_deploy| PreGate
    PreGate -->|PASS - exit code 0| Checks
    PreGate -->|APPROVAL_REQUIRED - exit code 20| Approval
    PreGate -->|FAIL - exit code 10| Block
    PreGate -->|ERROR - exit code 30| Block
    Approval -->|Approved and gate enabled| Checks
    Approval -->|Rejected or gate disabled| Block
    Checks -->|Yes| Deploy
    Checks -->|No| Block
    Deploy -.-> Runtime
    Deploy --> Post --> Input
    Mode -->|post_deploy| PostGate
    PostGate -->|PASS - exit code 0| Verified
    PostGate -->|FAIL - exit code 10| Failed
    PostGate -->|ERROR - exit code 30| Failed
```

## Broker Review

- AI-Broker is private, maintained separately, and not included in this repository.
- It reviews selected evidence using Gemini or Groq and maps findings to policy outcomes.
- Workflows enforce release gates and retain results; the broker does not build, deploy, or modify code.
- Post-deployment review is a separate invocation, not continuous monitoring or automatic rollback.
- Findings are model-generated recommendations, not verified vulnerabilities.

### Outcomes

- Numbers are broker process exit codes, not severity scores.
- `PASS` (`0`): broker check passes; all other required checks must also pass.
- `APPROVAL_REQUIRED` (`20`): pre-deployment review requires an enabled, protected approval gate and human approval.
- `FAIL` (`10`): findings trigger a policy failure, including approval-level findings in post-deployment mode.
- `ERROR` (`30`): the scan could not complete, for example due to invalid evidence or a provider error.
- `FAIL` and `ERROR` block release or fail post-deployment verification; errors never authorize deployment.

## Operation and Limits

- Use the [usage guide](docs/USAGE.MD) for local execution and Azure script entry points.
- Manually dispatch the release workflow; automatic runs on pushes to `main` are disabled.
- Deploy reviewed, immutable image digests without rebuilding; the deployment script alone does not enforce review gates.
- Pin the private broker image to an approved GHCR digest.
- Pre-filter sensitive evidence before external inference; redaction is best-effort.
- Keep credentials in protected CI secrets and never expose them to untrusted pull requests.
- Azure SQLite storage is not configured for persistence; container restarts or replacement may lose data.

## Documentation

- [Documentation index](docs/index.MD)
- [Usage and script reference](docs/USAGE.MD)
- [Contribution policy](docs/CONTRIBUTING.md)
- [Glossary](docs/glossary.md)

## License

- Public visibility grants no reuse permission; see the [proprietary license](LICENSE).
- Execution, testing, and deployment require prior written permission.
- Third-party packages remain subject to their own licenses.

---

<p align="center">
	<sub><sup><span style="color:#9aa0a6">👨‍🎓 Author: Dr. Georges Bou Ghantous © 2026</span></sup></sub>
</p>
