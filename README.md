# Repairable Error Contract Pattern (REC)

**Author:** Martin Koschi
**Version:** 0.1.0
**Status:** Draft RFC 9457 extension profile and reference-pattern proposal
**Short name:** REC

## One-sentence definition

A **Repairable Error Contract** is an RFC 9457 Problem Details profile that adds safe, structured repair and retry semantics so humans, SDKs, CLIs, workflows, services, and LLM agents know what failed, whether to retry, what to change, and what not to change.

## What is actually new here

REC intentionally reuses existing mechanisms instead of replacing them:

* the envelope is **RFC 9457 Problem Details** (`type`, `title`, `status`, `detail`, `instance`, `application/problem+json`),
* field-level diagnostics build on JSON Pointer / validation-error practice,
* `repair_patch` is **RFC 6902 JSON Patch**,
* `retry_after_ms` mirrors the HTTP `Retry-After` header when that header is present,
* `trace_id` and `diagnostic_id` follow normal correlation-ID practice.

The defensible REC contribution is narrower:

1. **`retry_policy.same_request`**: separates “retrying may help” from “retry this exact request unchanged.” This is the anti-mutation guard for agents and autonomous callers.
2. **Sanitized capsule → analyzer → policy gate**: an LLM may assist only from a private allowlisted diagnostic capsule, and its output is untrusted until schema-validated and policy-gated.
3. **`repair_patch` vs `repair_plan`**: distinguishes machine-applicable request changes from judgment-required recovery steps.

## Why this pattern exists

Modern APIs usually define successful requests and responses better than failures. A vague failure such as:

```json
{
  "error": "Bad Request"
}
```

forces a human to inspect logs and encourages an autonomous caller to guess. For an LLM agent, that guess may be harmful: the agent may mutate valid parameters after a dependency outage, retry a non-idempotent operation blindly, or invent fields that do not exist.

REC proposes a failure contract that answers:

* What failed?
* Is the caller, service, dependency, capacity limit, authorization context, or business precondition involved?
* Can the caller retry?
* Should the caller retry the exact same request unchanged?
* Which request fields are invalid?
* Is there a safe machine-applicable patch?
* Is a prerequisite operation or user decision required?
* Which details are safe to show publicly?
* How can the public error be correlated with private diagnostics?

## Core architecture

```text
Raw failure
  ↓
Diagnostic boundary
  ↓
Sanitized Diagnostic Capsule              private, allowlisted, no secrets
  ↓
Analyzer route                            deterministic / LLM-assisted / hybrid / fallback
  ↓
Schema validation + policy gate           analyzer output is untrusted until accepted
  ↓
RepairableProblem                         public application/problem+json response
```

The pattern does **not** require an LLM. Deterministic REC is the default. LLM-assisted REC is optional and should normally be disabled unless the capsule builder, schema validation, policy gate, timeout, fallback, and non-leakage tests are in place.

## Minimal public response example

```json
{
  "type": "https://api.example.com/problems/caller-contract-violation",
  "title": "Request does not match the operation contract.",
  "status": 400,
  "detail": "The request used 'url', but this operation expects 'post'.",
  "instance": "urn:diagnostic:diag_01HXAMPLE",
  "rec_version": "0.1.0",
  "operation_id": "postRedditThread",
  "diagnostic_id": "diag_01HXAMPLE",
  "classification": "caller_contract_violation",
  "request_repairable": true,
  "agent_policy": "modify_request",
  "retry_policy": {
    "can_retry": true,
    "same_request": false,
    "idempotency_required": false
  },
  "invalid_fields": [
    {
      "path": "/url",
      "problem": "alias_field",
      "suggestion": "Use /post instead."
    }
  ],
  "repair_patch": [
    {
      "op": "move",
      "from": "/url",
      "path": "/post"
    }
  ],
  "repair_patch_applicability": "machine_applicable",
  "patch_verified": true,
  "correct_request_example": {
    "post": "https://www.reddit.com/r/redditdev/comments/abc123/example/",
    "sort": "confidence",
    "maxComments": 10000
  },
  "caller_instruction": "Retry using field 'post'. Do not use 'url', 'redditUrl', or 'threadUrl'.",
  "safe_debug_summary": "Request body shape error before upstream call.",
  "analysis_mode": "deterministic"
}
```

REC responses SHOULD be returned with:

```http
Content-Type: application/problem+json
```

## Classification taxonomy

REC v0.1.0 defines these top-level classifications:

```text
caller_contract_violation
semantic_precondition_missing
resource_not_found
authorization_context_mismatch
version_skew
dependency_failure
capacity_or_timeout
service_bug_likely
security_suspicious
diagnostic_uncertain
```

Domain-specific systems may add `domain_code`, but the top-level `classification` should remain stable for SDKs, agents, alerting, and analytics.

## Retry and repair semantics

REC separates request repair from retry behavior:

| Field | Meaning |
|---|---|
| `request_repairable` | The caller can make progress by changing request data, credentials, visible resource reference, or a prerequisite state. |
| `retry_policy.can_retry` | Re-invoking the same operation may be useful after following the REC guidance. |
| `retry_policy.same_request` | Only valid when `can_retry` is true. `true` means retry the exact same request payload and parameters; do not mutate request data. |
| `agent_policy` | Closed machine-action hint such as `modify_request`, `retry_unchanged`, `call_prerequisite`, or `report_diagnostic_id`. |

Examples:

| Scenario | `request_repairable` | `can_retry` | `same_request` | `agent_policy` |
|---|---:|---:|---:|---|
| Missing required field | true | true | false | `modify_request` |
| Invalid enum | true | true | false | `modify_request` |
| Missing business prerequisite | true | true | false | `call_prerequisite` |
| Rate limit | false | true | true | `retry_unchanged` |
| Dependency outage | false | true | true | `retry_unchanged` |
| Internal bug | false | false | absent | `report_diagnostic_id` |
| Suspicious request | false | false | absent | `abort_task` |

This is especially important for LLM agents. If a valid request fails because a dependency is unavailable, `same_request: true` tells the agent not to invent alternative parameters.

## `repair_patch` vs `repair_plan`

Use `repair_patch` only when the repair is deterministic or server-side verified:

```json
{
  "repair_patch": [
    {
      "op": "move",
      "from": "/url",
      "path": "/post"
    }
  ],
  "repair_patch_applicability": "machine_applicable",
  "patch_verified": true
}
```

Use `repair_plan` when a missing value, user decision, prerequisite operation, authorization refresh, or business decision is required:

```json
{
  "repair_plan": [
    {
      "action": "replace_invalid_value",
      "path": "/post",
      "value_hint": "Use a canonical /comments/<id> URL, redd.it URL, t3 fullname, or raw article ID.",
      "reason": "The Reddit share URL could not be resolved deterministically."
    }
  ]
}
```

## Public/private diagnostic split

REC uses two artifacts:

```text
Public RepairableProblem
  Returned to the caller as application/problem+json.

Private Diagnostic Capsule
  Sanitized evidence used by analyzers and never returned directly.
```

The caller should not receive raw stack traces, raw logs, authorization headers, access tokens, cookies, environment variables, secrets, raw upstream payloads, or caller-supplied data echoed into instructions.

## Repository contents

* `spec/rec-v0.1.md` — draft profile and pattern specification
* `schemas/repairable-problem.schema.json` — public REC response schema
* `schemas/diagnostic-capsule.schema.json` — private diagnostic capsule schema
* `src/rec/` — minimal Python reference core: fallback builder, deterministic helper, JSON Patch utility, policy gate, and optional FastAPI adapter
* `tests/` — schema, retry-semantics, non-leakage, and policy-gate tests
* `openapi.yaml` — OpenAPI 3.1 example using `application/problem+json` and `x-repairable-error`
* `examples/reddit-api/README.md` — Reddit API case study
* `examples/generic-invoice-api/README.md` — business API scenarios
* `examples/status-catalog/README.md` — 401, 403/hidden-404, 404, and 500 examples
* `examples/fastapi-middleware/README.md` — optional FastAPI handler sketch
* `benchmarks/agent-recovery/README.md` — proposed benchmark harness design
* `paper/repairable-error-contract.md` — draft paper with prior-art positioning
* `GOVERNANCE.md` — taxonomy, action registry, and versioning process
* `CHANGELOG.md` — release notes
* `REVIEW-REMEDIATION.md` — mapping from review findings to changes
* `CITATION.cff` — citation metadata

## Maturity levels

```text
Level 0: Traditional vague errors
Level 1: RFC 9457 Problem Details
Level 2: REC-Core Problem Details extensions
Level 3: Deterministic REC analyzer route
Level 4: LLM-assisted REC behind a capsule and policy gate
Level 5: Diagnostic feedback loop into issues, tests, docs, and remediation workflows
```

Level 5 is intentionally outside REC-Core. Error clustering and remediation workflows are useful operational extensions, not the public error contract itself.

## What REC is not

REC is not a replacement for RFC 9457, OpenAPI, JSON Schema, tracing, logging, authentication, authorization, incident response, or secure exception handling. It is also not a claim that LLM analysis is automatically safe. REC is a profile and safety architecture for returning better failures when a system already has enough safe evidence to do so.

## License

Specification, documentation, and diagrams are provided under **Creative Commons Attribution 4.0 International (CC BY 4.0)**.

Code examples, JSON Schemas, OpenAPI snippets, and reference implementation files may be used under the **MIT-style permission grant** described in `LICENSE.md`.

## Citation

```text
Martin Koschi. Repairable Error Contract Pattern. Version 0.1.0. 2026.
```

See `CITATION.cff`.
