# DRA 2.0 POC Demo App

A containerized task-management demo with DRA 2.0 AI-Broker integration for pre- and post-deployment evidence review.

## What’s inside

| Service | Responsibility |
| --- | --- |
| Frontend | Authenticated task UI, served by Nginx and Flask; HTMX powers task updates. |
| Backend | Internal REST API and task validation. |
| Database | Internal CRUD API with SQLite storage. |

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
        Input[Validate JSON request and explicitly listed evidence<br/>Relative UTF-8 files: 128 KiB each, 384 KiB total]
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
    PreGate -->|PASS: 0| Checks
    PreGate -->|APPROVAL_REQUIRED: 20| Approval
    PreGate -->|FAIL: 10 or ERROR: 30| Block
    Approval -->|Approved and gate enabled| Checks
    Approval -->|Rejected or gate disabled| Block
    Checks -->|Yes| Deploy
    Checks -->|No| Block
    Deploy -.-> Runtime
    Deploy --> Post --> Input
    Mode -->|post_deploy| PostGate
    PostGate -->|PASS: 0| Verified
    PostGate -->|FAIL: 10 or ERROR: 30| Failed
```

Only the frontend is exposed publicly. The separately maintained AI-Broker reviews selected evidence using Gemini or Groq; it does not build or deploy software.

The broker scans evidence and reports policy outcomes; the consuming workflows enforce release gates and retain results. Pre-filter sensitive data before external inference, keep provider credentials in protected CI secrets, and never expose them to untrusted pull requests. Post-deployment review requires a separate invocation; it is not continuous monitoring and does not trigger rollback. Model findings are recommendations, not verified vulnerabilities.

## Documentation

- [Documentation index](docs/index.MD)
- [Usage and setup](docs/USAGE.MD)
- [Contributions](docs/CONTRIBUTING.md)
- [Glossary](docs/glossary.md)

This is a proof of concept, not a production deployment. See the usage guide for storage and evidence-privacy limitations.

## License

This repository is publicly visible, but its [proprietary license](LICENSE) grants no reuse permission. Third-party packages remain subject to their own licenses.

---

<p align="center">
	<sub><sup><span style="color:#9aa0a6">👨‍🎓 Author: Dr. Georges Bou Ghantous © 2026</span></sup></sub>
</p>
