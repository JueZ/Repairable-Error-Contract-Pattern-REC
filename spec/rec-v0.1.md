# Repairable Error Contract Pattern v0.1

**Author:** Martin Koschi  
**Status:** Draft pattern proposal  
**Version:** 0.1.0  
**Wire profile:** REC v0.1  
**Short name:** REC

## Abstract

The Repairable Error Contract Pattern defines a structured way for APIs and services to make failures actionable. Instead of returning vague errors, an operation returns a safe, machine-readable, human-readable response that identifies the failure class, retry semantics, invalid fields, repair guidance, examples, and diagnostic correlation identifiers.

The pattern is designed for human developers, service-to-service callers, CLIs, SDKs, workflow engines, and LLM agents.

REC is analyzer-independent. A Repairable Error Contract may be produced by deterministic validation, a rule engine, an LLM-assisted analyzer operating on a sanitized diagnostic capsule, a hybrid route, or a fallback route.

REC is intended to complement, not replace, existing mechanisms such as RFC 9457 Problem Details, OpenAPI, JSON Schema, JSON Patch, gRPC richer error details, Google-style API error models, logging, tracing, and observability.

## 1. Problem

APIs traditionally focus on success contracts:

- request shape,
- response shape,
- authentication,
- status codes,
- examples,
- and generated client support.

Failure behavior is often weaker.

Common responses include:

```json
{
  "error": "Bad Request"
}
```

or:

```json
{
  "message": "Validation failed"
}
```

These are insufficient for modern callers.

A human developer may need to inspect logs. A service may retry incorrectly. A CLI user may not know which field is wrong. An SDK may not know whether retrying is safe. An LLM agent may guess alternate parameter names, modify unrelated values, or give up.

The core problem:

> APIs usually define how to call them successfully, but not how callers should recover when calls fail.

## 2. Intent

When an operation fails, return an error contract that answers:

- What failed?
- Where did it fail?
- Is the caller at fault?
- Is the service at fault?
- Did a dependency fail?
- Is the failure caused by rate limiting or capacity?
- Is the request repairable?
- Can the caller retry?
- Should the caller retry the same request?
- Which fields are invalid?
- Which business precondition is missing?
- Which safe next action should the caller take?
- Which values or fields should the caller not change?
- How can the failure be correlated with logs and traces?

## 3. Applicability

Use REC when:

- APIs are called by LLM agents or GPT Actions.
- Microservices communicate across service boundaries.
- SDKs or CLIs need structured failure guidance.
- Users repeatedly make similar request mistakes.
- Agents retry blindly after ambiguous errors.
- Logs contain useful failure information that is not surfaced safely to callers.
- Operations need better distinction between caller mistakes, dependency failures, internal bugs, and retryable capacity problems.

Do not use REC as a substitute for:

- authentication,
- authorization,
- input validation,
- logging,
- distributed tracing,
- metrics,
- incident management,
- secure exception handling,
- or human review for high-risk production changes.

REC is a failure contract layer.

## 4. Pattern structure

```text
Caller
  ↓
Operation boundary
  ↓
Failure
  ↓
Diagnostic boundary
  ↓
Sanitized diagnostic capsule
  ↓
Analyzer route
  ↓
Schema validation and policy gate
  ↓
Public repairable error response
```

## 5. Participants

### Caller

The caller may be a human, LLM agent, SDK, CLI, workflow engine, or another service.

### Operation

The API or service operation that is invoked.

### Diagnostic boundary

A wrapper or middleware around the operation. It catches failures and creates a diagnostic capsule.

### Diagnostic capsule

A private, sanitized, allowlisted evidence package used for analysis.

### Analyzer route

A pluggable component that converts the diagnostic capsule into a candidate repairable error response.

Analyzer implementations may be:

- deterministic,
- LLM-assisted,
- hybrid,
- fallback,
- or human-assisted.

### Policy gate

A validation and sanitization step that treats analyzer output as untrusted until proven safe.

### Repairable error response

The public response returned to the caller.

## 6. Public response: RepairableProblem

A REC response should contain:

- `type`
- `title`
- `status`
- `detail`
- `instance`
- `rec_version`
- `operation_id`
- `diagnostic_id`
- `trace_id`, when available
- `classification`
- `repairable`
- `confidence`
- `retry_policy`
- `invalid_fields`, when applicable
- `repair_patch`, when deterministic and mechanically safe
- `repair_plan`, when a plan is needed
- `correct_request_example`, when useful and safe
- `caller_instruction`
- `safe_debug_summary`
- `analysis_mode`

Example:

```json
{
  "type": "https://api.example.com/problems/caller-contract-violation",
  "title": "Request does not match the operation contract.",
  "status": 400,
  "detail": "The request used 'url', but this operation expects 'post'.",
  "instance": "urn:diagnostic:diag_example",
  "rec_version": "0.1",
  "operation_id": "postRedditThread",
  "diagnostic_id": "diag_example",
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
    "post": "https://www.reddit.com/r/redditdev/comments/abc123/example/"
  },
  "caller_instruction": "Retry using field 'post'. Do not use 'url'.",
  "safe_debug_summary": "Request body shape error before upstream call.",
  "analysis_mode": "deterministic"
}
```

## 7. Diagnostic capsule

The diagnostic capsule is private. It is not returned to the caller.

It should include only allowlisted diagnostic information:

- operation ID,
- endpoint,
- method,
- failure stage,
- HTTP status,
- safe error code,
- safe error message,
- request shape,
- contract summary,
- safe examples,
- diagnostic ID,
- trace ID,
- security policy flags.

It must not include:

- raw authorization headers,
- bearer tokens,
- cookies,
- client secrets,
- access tokens,
- refresh tokens,
- raw stack traces,
- raw environment variables,
- raw upstream response bodies,
- sensitive customer data,
- full raw request bodies by default.

## 8. Analyzer route

The analyzer route is pluggable.

A standard interface can be described as:

```text
analyze(capsule, expected, policy) -> RepairableProblem | null
```

The analyzer may be deterministic or LLM-assisted.

If an LLM is used:

- the LLM must receive only the sanitized diagnostic capsule,
- it must not receive raw secrets or raw logs,
- its output must match the RepairableProblem schema,
- its output must pass a policy gate,
- invalid or unsafe output must be discarded,
- deterministic fallback must remain available.

The LLM is not the authority. It is a candidate analyzer.

## 9. Classification taxonomy

REC v0.1 defines these top-level classifications:

### `caller_contract_violation`

The caller request violates the operation contract.

Examples: missing field, wrong type, unknown parameter, invalid enum, invalid JSON.

### `semantic_precondition_missing`

The request is structurally valid but a business precondition is missing.

Example: order cannot be shipped before payment capture.

### `resource_not_found`

A referenced resource is not found or not visible.

### `authorization_context_mismatch`

The caller lacks required authorization or context.

Implementations must avoid leaking private resource existence.

### `version_skew`

Consumer and producer use incompatible contract versions.

### `dependency_failure`

A downstream or upstream dependency failed.

### `capacity_or_timeout`

The operation failed because of rate limiting, timeout, overload, or capacity constraints.

### `service_bug_likely`

The request passed contract validation but the service failed internally.

### `security_suspicious`

The request or failure context appears suspicious, abusive, or security-sensitive.

### `diagnostic_uncertain`

The system lacks enough safe evidence to classify confidently.

## 10. Retry and repair semantics

REC separates three concepts:

```text
repairable
retry_policy.can_retry
retry_policy.same_request
```

### Missing required field

```json
{
  "repairable": true,
  "retry_policy": {
    "can_retry": true,
    "same_request": false
  }
}
```

### Rate limit

```json
{
  "repairable": false,
  "retry_policy": {
    "can_retry": true,
    "same_request": true,
    "retry_after_ms": 30000
  }
}
```

### Internal bug

```json
{
  "repairable": false,
  "retry_policy": {
    "can_retry": false,
    "same_request": true
  }
}
```

## 11. Repair patch vs. repair plan

Use `repair_patch` only for deterministic mechanical changes.

`repair_patch` uses RFC 6902-style JSON Patch operations and JSON Pointer paths.

Example:

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

Use `repair_plan` when human, agent, or service judgment is required.

Example:

```json
{
  "repair_plan": [
    {
      "action": "provide_missing_value",
      "path": "$.customerId",
      "value_hint": "Use the stable customer identifier.",
      "reason": "The invoice operation requires a customerId."
    }
  ]
}
```

## 12. OpenAPI extension proposal

REC can be described with an OpenAPI extension:

```yaml
x-repairable-error:
  recVersion: "0.1"
  analyzer:
    supportedModes:
      - deterministic
      - llm_assisted
      - hybrid
      - fallback
    defaultMode: hybrid
    llm:
      input: sanitized_diagnostic_capsule
      output: RepairableProblem
      requiresSchemaValidation: true
      requiresPolicyGate: true
  retry:
    idempotencyRequired: false
  security:
    diagnosticCapsulePolicy: sanitized-only
    exposeRawRequestBody: false
    exposeHeaders: false
    exposeTokens: false
    exposeStackTrace: false
    exposeRawUpstreamBody: false
```

## 13. Safety rules

Implementations MUST NOT expose:

- authorization headers,
- bearer tokens,
- access tokens,
- refresh tokens,
- cookies,
- client secrets,
- raw stack traces,
- raw environment variables,
- raw upstream bodies,
- raw logs by default.

Implementations SHOULD:

- use allowlists rather than blacklists,
- validate analyzer output,
- limit text field lengths,
- restrict repair paths to known fields,
- restrict suggested operation IDs to known operations,
- use fallback responses when analysis fails,
- keep public and private diagnostics separate.

## 14. Prior art and related mechanisms

REC is not a replacement for existing standards and mechanisms. It is intended as a pattern that composes with them.

### RFC 9457 Problem Details

Problem Details defines a standard error envelope for HTTP APIs. REC should be expressible as a set of problem-specific extension members on top of that envelope.

### JSON Schema

JSON Schema can validate the public REC response and the private diagnostic capsule.

### JSON Patch and JSON Pointer

`repair_patch` uses JSON Patch-style operations and JSON Pointer paths for deterministic repairs.

### OpenAPI Specification Extensions

REC can be documented using an `x-repairable-error` extension.

### gRPC richer error model

gRPC systems may express similar ideas through structured error details.

### Google API error model

Google-style APIs already emphasize canonical error codes, structured details, and actionable messages. REC is aligned with that direction but focuses specifically on explicit repair and retry semantics.

### Observability systems

REC should carry diagnostic and trace identifiers, but it does not replace logs, traces, metrics, or incident management.

## 15. Maturity model

### Level 0: Traditional errors

```json
{
  "error": "Bad Request"
}
```

### Level 1: Structured problem details

Stable envelope with `type`, `title`, `status`, `detail`, and `instance`.

### Level 2: Repairable Error Contract

Adds classification, retry policy, invalid fields, repair plan, and caller instruction.

### Level 3: Analyzer route

Analyzer is pluggable and may be deterministic or hybrid.

### Level 4: LLM-assisted REC

An LLM analyzes sanitized diagnostic capsules and emits schema-validated repairable errors.

### Level 5: Diagnostic feedback loop

Repeated diagnostic patterns may be aggregated into issues, documentation improvements, tests, or remediation workflows.

Level 5 is intentionally outside the core pattern.

## 16. Known risks

- overexposing diagnostic details,
- hallucinated repair suggestions from LLM analyzers,
- wrong retry guidance,
- leaking private resource existence,
- excessive latency,
- excessive cost,
- inconsistent taxonomy usage,
- treating probabilistic analysis as fact,
- using REC as a substitute for proper validation or observability.

## 17. Reference implementation principles

A reference implementation should:

- keep analyzer code isolated,
- default LLM diagnostics off unless configured,
- use short timeouts,
- fallback safely,
- test unsafe-output rejection,
- test secret and stack-trace non-leakage,
- test retry semantics,
- test both human and agent-readable instructions,
- validate all examples against schemas in CI.

## 18. Non-goals

REC does not:

- replace RFC 9457 Problem Details;
- replace OpenAPI, JSON Schema, JSON Patch, gRPC, or Google-style API error models;
- expose internal logs or stack traces;
- guarantee that an LLM-generated repair is correct;
- require LLMs;
- perform automatic remediation by itself;
- define a universal error taxonomy for all domains;
- replace observability, tracing, incident management, validation, authentication, or authorization logic.

## 19. Concise pattern statement

> Put a diagnostic boundary around an operation. When it fails, build a sanitized diagnostic capsule, analyze it through a deterministic, LLM-assisted, hybrid, or fallback route, validate the candidate response, and return a safe Repairable Error Contract that tells the caller what failed, whether to retry, what to change, and what not to change.
