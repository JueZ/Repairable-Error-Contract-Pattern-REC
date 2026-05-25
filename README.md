# Repairable Error Contract Pattern

**Author:** Martin Koschi  
**Version:** 0.1.0  
**Wire profile:** REC v0.1  
**Status:** Draft pattern proposal  
**Short name:** REC

## One-sentence definition

A **Repairable Error Contract** is a draft API and service architecture pattern for safe, structured, actionable failure responses that tell callers what failed, whether retrying is safe, what should be changed, and what must not be changed.

## Positioning

REC is intended to complement existing API error-handling mechanisms, especially:

- RFC 9457 Problem Details for HTTP APIs
- JSON Schema
- JSON Patch and JSON Pointer
- OpenAPI Specification extensions
- gRPC richer error details
- Google-style API error models
- structured logging
- distributed tracing
- SDK and CLI diagnostics
- LLM tool-use and agent workflows

REC does **not** replace these mechanisms.

The core idea is to add explicit **repair semantics** to error responses:

- Is the request repairable by the caller?
- Is retrying allowed or useful?
- Should the exact same request be retried?
- Which fields are invalid?
- Is a deterministic repair patch safe?
- Is a higher-level repair plan needed?
- What should a human, SDK, CLI, workflow engine, service, or LLM agent do next?
- What should the caller avoid changing?

## Why this pattern exists

Modern APIs usually define successful requests and responses in detail. Failure behavior is often much less precise.

A typical vague error still looks like this:

```json
{
  "error": "Bad Request"
}
```

For a human developer, this is annoying.

For an SDK, CLI, workflow engine, service-to-service caller, or LLM agent, it can cause worse behavior:

- blind retries,
- guessed parameter names,
- mutation of unrelated fields,
- repeated failing calls,
- unsafe workarounds,
- or unnecessary escalation to logs and source code.

REC proposes that APIs should expose a **failure contract**, not only a success contract.

## Core idea

```text
Raw failure
  ↓
Diagnostic boundary
  ↓
Sanitized diagnostic capsule
  ↓
Analyzer route
  ↓
Schema validation + policy gate
  ↓
Public repairable error response
```

The analyzer route is intentionally pluggable.

It may be:

- deterministic,
- LLM-assisted,
- hybrid,
- fallback-only,
- or human-assisted in later operational workflows.

The pattern does **not** require an LLM. Deterministic validation should be preferred where possible. LLM assistance is optional and must be constrained by sanitized input, schema validation, and policy gates.

## Key distinction

REC separates two artifacts:

```text
Public Repairable Error Response
  Returned to the caller.

Private Diagnostic Capsule
  Sanitized evidence used for analysis.
```

The caller should not receive raw stack traces, raw logs, authorization headers, access tokens, cookies, environment variables, secrets, or raw upstream payloads.

## Minimal response example

```json
{
  "type": "https://api.example.com/problems/caller-contract-violation",
  "title": "Request does not match the operation contract.",
  "status": 400,
  "detail": "The request used 'url', but this operation expects 'post'.",
  "instance": "urn:diagnostic:diag_01HXAMPLE",
  "rec_version": "0.1",

  "operation_id": "postRedditThread",
  "diagnostic_id": "diag_01HXAMPLE",
  "classification": "caller_contract_violation",
  "repairable": true,
  "confidence": 0.93,

  "retry_policy": {
    "can_retry": true,
    "same_request": false,
    "idempotency_required": false
  },

  "invalid_fields": [
    {
      "path": "$.url",
      "problem": "alias_field",
      "suggestion": "Use '$.post' instead."
    }
  ],

  "repair_patch": [
    {
      "op": "move",
      "from": "/url",
      "path": "/post"
    }
  ],

  "correct_request_example": {
    "post": "https://www.reddit.com/r/redditdev/comments/abc123/example/",
    "sort": "confidence",
    "maxComments": 10000
  },

  "caller_instruction": "Retry the operation with field 'post'. Do not use 'url', 'redditUrl', or 'threadUrl'.",
  "safe_debug_summary": "Request body shape error before upstream call.",
  "analysis_mode": "deterministic"
}
```

## Classification taxonomy

REC v0.1 proposes a small stable taxonomy:

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

Domain-specific systems may add `domain_code`, but the top-level classification should remain stable.

## Repair semantics

REC separates three concepts that are often confused:

| Field | Meaning |
| --- | --- |
| `repairable` | Can the caller fix something and try again? |
| `retry_policy.can_retry` | Is retrying allowed or useful? |
| `retry_policy.same_request` | Should the caller retry the exact same request? |

Examples:

| Scenario | `repairable` | `can_retry` | `same_request` |
| --- | ---: | ---: | ---: |
| Missing required field | `true` | `true` | `false` |
| Invalid enum | `true` | `true` | `false` |
| Resource not found | `true` | `true` | `false` |
| Rate limit | `false` | `true` | `true` |
| Dependency outage | `false` | `true` | `true` |
| Internal bug | `false` | `false` or `true` | `true` |

This is especially important for LLM agents and autonomous workflows. If an upstream dependency fails, the caller should not invent alternative parameters.

## `repair_patch` vs. `repair_plan`

REC supports two repair forms.

Use `repair_patch` only when the repair is deterministic and mechanically safe. `repair_patch` is modeled as RFC 6902-style JSON Patch operations and therefore uses JSON Pointer paths:

```json
{
  "repair_patch": [
    {
      "op": "move",
      "from": "/url",
      "path": "/post"
    }
  ]
}
```

Use `repair_plan` when a missing value, user decision, prerequisite operation, or business decision is required:

```json
{
  "repair_plan": [
    {
      "action": "replace_invalid_value",
      "path": "$.post",
      "value_hint": "Use a canonical /comments/<id> URL, redd.it URL, t3 fullname, or raw article ID.",
      "reason": "The Reddit share URL could not be resolved."
    }
  ]
}
```

## Relationship to existing standards and mechanisms

REC should be treated as a profile or pattern layered on top of existing mechanisms.

### RFC 9457 Problem Details

REC uses the familiar Problem Details shape:

- `type`
- `title`
- `status`
- `detail`
- `instance`

REC adds extension members for repair semantics:

- `rec_version`
- `operation_id`
- `diagnostic_id`
- `classification`
- `repairable`
- `confidence`
- `retry_policy`
- `invalid_fields`
- `repair_patch`
- `repair_plan`
- `correct_request_example`
- `caller_instruction`
- `safe_debug_summary`
- `analysis_mode`

### JSON Schema

REC schemas define the public response and the private diagnostic capsule.

### JSON Patch and JSON Pointer

`repair_patch` is restricted to deterministic mechanical changes and uses JSON Patch-style operations with JSON Pointer paths.

### OpenAPI

REC can be documented with an `x-repairable-error` extension and linked to problem response schemas.

### Observability

REC does not replace logs, traces, metrics, or incident management. It exposes safe caller guidance and correlation identifiers.

### LLM agents

REC can make LLM tool-use safer by giving explicit recovery instructions and by preventing unsafe mutation after dependency, capacity, or authorization failures.

## Non-goals

REC does not:

- replace RFC 9457 Problem Details;
- replace OpenAPI, JSON Schema, JSON Patch, gRPC, or Google-style API error models;
- expose internal logs, stack traces, headers, tokens, secrets, or raw upstream payloads;
- guarantee that an LLM-generated repair is correct;
- require LLMs;
- perform automatic remediation by itself;
- define a universal error taxonomy for all domains;
- replace validation, authentication, authorization, logging, tracing, observability, or incident management;
- remove the need for human review in production systems.

## Repository contents

- `spec/rec-v0.1.md` — pattern and candidate specification
- `schemas/repairable-problem.schema.json` — public REC response schema
- `schemas/diagnostic-capsule.schema.json` — private diagnostic capsule schema
- `examples/reddit-api/` — Reddit API case study
- `examples/generic-invoice-api/` — generic business API example
- `examples/invalid/` — examples that must fail schema validation
- `tests/validate-examples.mjs` — schema validation test runner
- `paper/repairable-error-contract.md` — draft position paper
- `CITATION.cff` — citation metadata

## Validation

Install dependencies and validate the examples:

```bash
npm install
npm test
```

The validation script checks that:

- valid public REC examples match `schemas/repairable-problem.schema.json`;
- valid diagnostic capsule examples match `schemas/diagnostic-capsule.schema.json`;
- invalid examples are rejected;
- no stale `rec_version: "1.0"` examples remain.

## Maturity levels

```text
Level 0: Traditional vague errors
Level 1: Structured Problem Details
Level 2: Repairable Error Contract
Level 3: Analyzer route
Level 4: LLM-assisted REC
Level 5: Diagnostic feedback loop
```

Automatic issue creation, clustering, and repository remediation are useful later extensions, but they are not part of the core REC v0.1 pattern.

## Current status

REC is currently a **draft pattern proposal**.

The current goal is not standardization. The current goal is to provide:

- a precise vocabulary,
- a safe public/private diagnostic boundary,
- machine-readable schemas,
- concrete examples,
- and a basis for discussion, implementation experiments, and evaluation.

## License

Specification, documentation, and diagrams are provided under **Creative Commons Attribution 4.0 International (CC BY 4.0)**.

Code examples, schemas, and test snippets may be used under the **MIT-style permission grant** described in `LICENSE.md`.

## Citation

If you reference this pattern, please cite:

```text
Martin Koschi. Repairable Error Contract Pattern. Version 0.1.0. 2026.
```

See `CITATION.cff`.
