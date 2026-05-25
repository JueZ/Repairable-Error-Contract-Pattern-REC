# Repairable Error Contract Pattern

**Author:** Martin Koschi
**Version:** 0.1.0
**Status:** Draft pattern proposal
**Short name:** REC

## One-sentence definition

A **Repairable Error Contract** is an API and service architecture pattern that turns failures into safe, structured, actionable error responses so humans, services, SDKs, CLIs, workflows, and LLM agents can understand what failed, whether to retry, what to change, and what not to change.

## Why this pattern exists

Modern APIs usually define what successful requests and responses look like. They often do not define failures with the same precision.

A typical API failure still looks like this:

```json
{
  "error": "Bad Request"
}
```

For a human developer, that is annoying.

For an LLM agent or autonomous workflow, it is worse: the caller may retry blindly, invent new parameters, change the wrong field, or give up.

The Repairable Error Contract Pattern proposes that APIs should expose a **failure contract**, not only a success contract.

A failure response should answer:

* What failed?
* Where did it fail?
* Was the request malformed?
* Is the failure caused by the caller, the service, a dependency, rate limiting, authorization, or missing business preconditions?
* Can the caller retry?
* Should the caller retry the exact same request?
* Should the caller change parameters?
* Which fields are invalid?
* Is there a safe example of a valid request?
* What should an LLM agent, SDK, CLI, service, or human do next?
* How can the failure be correlated with traces and logs?

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
Repairable error response
```

The analyzer route is intentionally pluggable.

It may be:

* deterministic,
* LLM-assisted,
* hybrid,
* fallback-only,
* or human-assisted in later operational workflows.

The pattern does **not** require an LLM. It only makes LLM analysis safe and useful when an implementation chooses to use it.

## Key distinction

The pattern separates two artifacts:

```text
Public Repairable Error Response
  Returned to the caller.

Private Diagnostic Capsule
  Sanitized evidence used for analysis.
```

The caller should not receive raw stack traces, raw logs, authorization headers, access tokens, environment variables, secrets, or raw upstream payloads.

## Minimal response example

```json
{
  "type": "https://api.example.com/problems/caller-contract-violation",
  "title": "Request does not match the operation contract.",
  "status": 400,
  "detail": "The request used 'url', but this operation expects 'post'.",
  "instance": "urn:diagnostic:diag_01HXAMPLE",
  "rec_version": "1.0",

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

  "repair_plan": [
    {
      "action": "retry_with_modified_request",
      "reason": "The endpoint requires the Reddit input in field 'post'."
    }
  ],

  "correct_request_example": {
    "post": "https://www.reddit.com/r/redditdev/comments/abc123/example/",
    "sort": "confidence",
    "maxComments": 10000
  },

  "caller_instruction": "Retry the operation with field 'post'. Do not use 'url', 'redditUrl', or 'threadUrl'.",
  "safe_debug_summary": "Request body shape error before upstream call.",
  "analysis_mode": "llm_assisted"
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

| Field                       | Meaning                                         |
| --------------------------- | ----------------------------------------------- |
| `repairable`                | Can the caller fix something and try again?     |
| `retry_policy.can_retry`    | Is retrying allowed or useful?                  |
| `retry_policy.same_request` | Should the caller retry the exact same request? |

Examples:

| Scenario               | repairable |     can_retry | same_request |
| ---------------------- | ---------: | ------------: | -----------: |
| Missing required field |       true |          true |        false |
| Invalid enum           |       true |          true |        false |
| Resource not found     |       true |          true |        false |
| Rate limit             |      false |          true |         true |
| Dependency outage      |      false |          true |         true |
| Internal bug           |      false | false or true |         true |

This is especially important for LLM agents. If an upstream dependency fails, the agent should not invent alternative parameters.

## `repair_patch` vs `repair_plan`

REC supports two repair forms.

Use `repair_patch` only when the repair is deterministic and mechanically safe:

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

## Repository contents

* `spec/rec-v0.1.md` — pattern and candidate specification
* `schemas/repairable-problem.schema.json` — public REC response schema
* `schemas/diagnostic-capsule.schema.json` — private diagnostic capsule schema
* `examples/reddit-api/README.md` — Reddit API case study
* `examples/generic-invoice-api/README.md` — generic business API example
* `paper/repairable-error-contract.md` — draft paper
* `CITATION.cff` — citation metadata

## Maturity levels

```text
Level 0: Traditional vague errors
Level 1: Structured Problem Details
Level 2: Repairable Error Contract
Level 3: Analyzer route
Level 4: LLM-assisted REC
Level 5: Diagnostic feedback loop
```

Automatic issue creation, clustering, and repository remediation are useful later extensions, but they are not part of the core REC pattern.

## License

Specification, documentation, and diagrams are provided under **Creative Commons Attribution 4.0 International (CC BY 4.0)**.

Code examples and schema snippets may be used under the **MIT-style permission grant** described in `LICENSE.md`.

## Citation

If you reference this pattern, please cite:

```text
Martin Koschi. Repairable Error Contract Pattern. Version 0.1.0. 2026.
```

See `CITATION.cff`.
