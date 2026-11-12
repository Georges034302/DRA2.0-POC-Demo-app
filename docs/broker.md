# AI-Broker Reference

## Overview

**AI-Broker** is an external, independently maintained policy engine that analyzes application evidence and returns deterministic release governance decisions.

- **Maintained Separately:** Not included in this repository
- **Evidence Analysis:** Reviews code, build, and deployment data using Gemini or Groq
- **Policy Enforcement:** Maps findings to outcomes: PASS, FAIL, APPROVAL_REQUIRED, ERROR
- **Non-Constructive:** Makes recommendations; does not deploy, rollback, or modify code
- **Model Findings:** Results are model-generated; not verified vulnerabilities

## Review Modes

The Broker supports two modes; **this pipeline only ever uses `pre_deploy`** (see [Workflow Integration](#workflow-integration) below) because only that mode supports `APPROVAL_REQUIRED`, which the pipeline needs to gate promotion to prod.

### Pre-Deployment Review

Analyzes code changes and build evidence **before deployment**.

| Aspect | Details |
|--------|---------|
| **Trigger** | After the dev-stage deployment and health check complete |
| **Evidence** | `test_report.md`, `build_report.md`, `deployment_report.md`, `results.md` (see [DEVELOPMENT.md](./DEVELOPMENT.md#evidence-collection)) |
| **Policy** | CRITICAL/HIGH → FAIL; MEDIUM → APPROVAL_REQUIRED; LOW/INFO → PASS |
| **Gate** | Can block, require approval, or pass |
| **Duration** | Completes before the promote-to-prod decision |

### Post-Deployment Review

Analyzes deployed state and runtime evidence **after deployment succeeds**; a Broker capability this pipeline does not currently invoke (see note above).

| Aspect | Details |
|--------|---------|
| **Trigger** | N/A for this pipeline — documented for completeness |
| **Evidence** | Runtime/health evidence, same shape as `results.md` |
| **Policy** | CRITICAL/HIGH/MEDIUM → FAIL; LOW/INFO → PASS (stricter) |
| **Gate** | Verification passes or fails (no rollback) |
| **Purpose** | Confirm deployed state matches reviewed expectations |

## Exit Codes & Outcomes

AI-Broker returns exit codes that represent policy decisions (not severity scores):

| Code | Outcome | Meaning | Action |
|------|---------|---------|--------|
| `0` | `PASS` | Findings comply with policy | Proceed to next stage |
| `10` | `FAIL` | Findings violate policy | Block release / Fail verification |
| `20` | `APPROVAL_REQUIRED` | Pre-deployment needs approval | Route to approval gate |
| `30` | `ERROR` | Scan incomplete or invalid | Block release / Fail verification |

**Notes:**
- Exit codes apply to policy, not individual findings
- Errors never authorize deployment
- APPROVAL_REQUIRED only appears in pre-deployment mode

## Policy Evaluation

### Pre-Deployment Policy (Default)

```
Finding Severity  →  Decision
─────────────────────────────
CRITICAL          →  FAIL (exit 10)
HIGH              →  FAIL (exit 10)
MEDIUM            →  APPROVAL_REQUIRED (exit 20)
LOW               →  PASS (exit 0)
INFO              →  PASS (exit 0)
```

**Outcome:** Block release, require human approval, or pass.

### Post-Deployment Policy (Default)

```
Finding Severity  →  Decision
─────────────────────────────
CRITICAL          →  FAIL (exit 10)
HIGH              →  FAIL (exit 10)
MEDIUM            →  FAIL (exit 10)  ← Stricter than pre-deploy
LOW               →  PASS (exit 0)
INFO              →  PASS (exit 0)
```

**Outcome:** Verification passes or fails. Does not trigger rollback.

## Input Validation

Broker validates all requests before analysis:

| Check | Purpose | Failure |
|-------|---------|---------|
| **JSON Schema** | Request structure is valid | ERROR (exit 30) |
| **File Paths** | Evidence paths are relative (no `..` or absolute paths) | ERROR (exit 30) |
| **Text Encoding** | Evidence is valid UTF-8 | ERROR (exit 30) |
| **Size Limits** | Evidence items within size constraints | ERROR (exit 30) |

Invalid input returns ERROR immediately without analysis.

## Analysis Process

```
1. Input Validation
   └─ Check JSON, paths, encoding, sizes
   └─ If invalid → return ERROR (exit 30)

2. Redaction (Best-Effort)
   └─ Scan for and mask: API keys, tokens, passwords, PII

3. Model Analysis
   └─ Send redacted evidence to Gemini or Groq
   └─ Generate findings and recommendations

4. Policy Mapping
   └─ Evaluate findings against policy
   └─ Determine exit code

5. Return Result
   └─ JSON: outcome, summary, findings, policy version, metrics
```

**Redaction:** Pre-filter sensitive data before submission. Automatic redaction is best-effort and not guaranteed.

## Result Format

Broker returns JSON with complete analysis:

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
    "evidence_items_analyzed": 5,
    "scan_duration_ms": 2345,
    "model_used": "gemini-2.0-flash|groq-large"
  }
}
```

## Sensitive Data Handling

### Pre-Submission Redaction

**MUST be pre-filtered before broker invocation:**
- API keys, tokens, passwords
- Database credentials
- Private SSH keys
- Personal information (names, emails)
- Proprietary algorithms
- Customer data

### Best-Effort Redaction

Broker attempts to redact common patterns:
- `SECRET=*****`
- `password=*****`
- `api_key=*****`

**Never rely on automatic redaction.** Pre-filter manually.

## Error Handling

| Error | Cause | Recovery |
|-------|-------|----------|
| `Invalid JSON` | Malformed request | Check request structure in review script |
| `Path traversal` | Evidence path contains `../` or absolute path | Use relative paths only |
| `Encoding error` | Invalid UTF-8 in evidence | Ensure all text is valid UTF-8 |
| `Size limit exceeded` | Evidence item too large | Reduce size or pre-filter content |
| `Provider error` | Gemini/Groq API failure | Check API availability and quotas |
| `Unknown error` | Unexpected failure | Check broker container logs and image digest |

## Workflow Integration

Invoked by: **ci-cd.yml** workflow  
Script: **scripts/review.sh**  
Triggered: After the dev-stage deploy and health check complete  
Mode: Always `pre_deploy` (see [Review Modes](#review-modes))  
On PASS/approved APPROVAL_REQUIRED: `scripts/deploy.sh STAGE=prod` promotes the same digest

### Configuration

- Broker image pinned to approved GHCR digest
- Provider keys (Gemini, Groq) in protected CI secrets
- Evidence reports pre-filtered before submission (plain Markdown, no secrets by construction)

## Limitations

**What Broker Does NOT Do:**
- Build, compile, or execute code
- Deploy or modify the running application
- Roll back deployments
- Provide continuous monitoring
- Replace security audits or penetration testing
- Guarantee finding accuracy

**What Findings Are:**
- Model-generated recommendations
- Evidence-based analysis, not verified vulnerabilities
- Starting point for human review and decision-making

---

**See Also:** [Architecture](architecture.md) | [Operations](operations.md) | [Getting Started](USAGE.MD)

[Documentation Index](index.MD)
