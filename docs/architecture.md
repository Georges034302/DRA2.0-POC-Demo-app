# Architecture & Release Governance Flow

## System Overview

### Application Runtime

```
Browser (Public)
   ↓ HTTPS
Frontend (Nginx + Flask + HTMX)
   ↓ Internal
Backend (Flask REST API)
   ↓ Internal
Database (SQLite + CRUD API)
```

**Network Boundaries:**
- Frontend is publicly exposed on port 8080
- Backend and database communicate internally
- External: only browser-to-frontend traffic

### Release Governance Pipeline

```
Code Commit
   ↓
[Build & Test] → Publish immutable digests
   ↓
[Pre-Deploy Evidence] → Pre-filter, redact secrets
   ↓
[AI-Broker Analysis] ⚙️ → Scan evidence (Gemini/Groq)
   ↓
[Policy Evaluation] → Exit code: 0/10/20/30
   ↓
[Decision Gate]
├─ PASS (0) → Check all other required tests
├─ FAIL (10) → Block release
├─ APPROVAL_REQUIRED (20) → Request human approval
└─ ERROR (30) → Block release (provider failure)
   ↓
[Deployment] → Deploy reviewed digests (no rebuild)
   ↓
[Post-Deploy Verification] → Collect logs, health evidence
   ↓
[AI-Broker Re-scan] ⚙️ → Stricter policy (medium findings fail)
   ↓
[Verification Result] → PASS/FAIL (no rollback)
```

## Release Stages

### 1. Build & Publish

- Run unit tests, lint, SAST checks
- Build containerized images
- Publish to registry with immutable digest tracking
- Failed tests block pipeline

### 2. Pre-Deployment Review

**Evidence Preparation:**
- Extract: source changes, dependency manifest, SBOM, scan results
- Pre-filter: remove secrets, credentials, PII
- Redaction: best-effort automatic redaction

**AI-Broker Analysis:**
- Input validation: JSON structure, file paths, UTF-8 encoding, size limits
- Model scan: evidence sent to Gemini or Groq for analysis
- Policy evaluation:
  - `CRITICAL/HIGH` → `FAIL` (exit 10)
  - `MEDIUM` → `APPROVAL_REQUIRED` (exit 20)
  - `LOW/INFO` → `PASS` (exit 0)

**Gate Outcome:**
- `PASS`: Proceed to other required checks
- `FAIL`: Block release
- `APPROVAL_REQUIRED`: Route to approval environment (human review required)
- `ERROR`: Block release (validation or provider failure)

### 3. Approval Gate (if required)

- Human reviewer examines broker findings
- Approval requires protected GitHub environment (`dra-approval`) and authorized reviewer
- Rejection or timeout: blocks deployment
- Approval: allows deployment to proceed

### 4. Deployment

- Verify all required checks passed (tests, lint, broker, approvals)
- Deploy reviewed image digests by SHA256
- **No rebuild** — exact reviewed code runs in production

### 5. Post-Deployment Verification

**Separate Workflow:**
- Triggered after successful deployment
- Collects: revision info, container logs, health checks
- Prepares evidence for broker re-scan

**AI-Broker Re-scan (Stricter Policy):**
- Same evidence analysis
- Policy evaluation:
  - `CRITICAL/HIGH/MEDIUM` → `FAIL` (exit 10) ← Stricter than pre-deploy
  - `LOW/INFO` → `PASS` (exit 0)

**Verification Result:**
- `PASS`: Verification complete, deployment verified
- `FAIL`: Verification failed (no automatic rollback; manual intervention required)
- `ERROR`: Verification incomplete

## Exit Codes

| Code | Outcome | Pre-Deploy | Post-Deploy | Action |
|------|---------|-----------|------------|--------|
| `0` | PASS | Continue to other checks | Verification passed | ✓ Proceed |
| `10` | FAIL | Block release | Verification failed | 🚫 Block |
| `20` | APPROVAL_REQUIRED | Route to approval gate | N/A | ⏳ Wait approval |
| `30` | ERROR | Block release | Verification failed | 🚫 Block |

**Key:** Broker exit codes are policy decisions, not severity scores.

## Key Design Principles

1. **Immutable Digests**  
   Reviewed images are deployed by exact SHA256; no rebuilds after review

2. **Deterministic Policy**  
   Findings are evaluated against fixed rules; no arbitrary decisions

3. **Separation of Concerns**  
   Broker analyzes evidence; workflows enforce gates; humans approve

4. **Non-Destructive**  
   Post-deployment can verify or alert, but does not rollback

5. **Evidence Privacy**  
   Pre-filter sensitive data before external analysis; redaction is best-effort

6. **Audit Trail**  
   All results retained for 30 days; evidence recovered for investigation

## Broker Boundary

**What AI-Broker Does:**
- ✓ Analyzes code, build, and deployment evidence
- ✓ Generates findings and recommendations
- ✓ Returns deterministic policy outcome
- ✓ Provides metrics and analysis details

**What AI-Broker Does NOT Do:**
- ✗ Build, compile, or execute code
- ✗ Deploy or modify the application
- ✗ Roll back or perform automatic remediation
- ✗ Guarantee finding accuracy (model-generated)
- ✗ Replace security audits or penetration testing

## Configuration

See **[Operations & Limits](operations.md)** for:
- Azure deployment setup
- Credential management
- Evidence redaction guidelines
- Broker image pinning
- Workflow permissions

See **[AI-Broker Details](broker.md)** for:
- Review modes and policy details
- Input validation rules
- Result format and metrics
- Error handling

---

**Next:** [AI-Broker Details](broker.md) | [Operations](operations.md) | [Documentation Index](index.MD)
