# Repairable Error Contract Pattern v0.1.0

**Author:** Martin Koschi
**Status:** Draft RFC 9457 extension profile and pattern proposal
**Version:** 0.1.0
**Short name:** REC

## Abstract

The Repairable Error Contract Pattern (REC) defines an RFC 9457 Problem Details profile for safe, structured, actionable API failures. A REC response classifies a failure, states retry semantics, identifies invalid fields or missing preconditions, distinguishes machine-applicable patches from judgment-required plans, and includes diagnostic correlation identifiers.

REC is designed for human developers, service-to-service callers, SDKs, CLIs, workflow engines, and LLM agents. The pattern is analyzer-independent: deterministic validation, rule engines, LLM-assisted analyzers, hybrid analyzers, and fallback analyzers may all produce REC responses, provided that public output is schema-validated and policy-gated.

## 1. Normative language

The key words **MUST**, **MUST NOT**, **REQUIRED**, **SHOULD**, **SHOULD NOT**, **MAY**, and **OPTIONAL** are to be interpreted as described in RFC 2119 and RFC 8174 when, and only when, they appear in all capitals.

REC v0.1.0 is a draft. The requirements below are intended to make implementations comparable and testable while the profile is still experimental.

## 2. Relationship to RFC 9457 Problem Details

REC is a profile of **RFC 9457 Problem Details for HTTP APIs**. It does not replace Problem Details.

A REC public response:

1. MUST be a valid Problem Details object.
2. SHOULD be served as `application/problem+json` for HTTP APIs.
3. MUST include the RFC 9457 members `type`, `title`, `status`, `detail`, and `instance`.
4. Adds REC extension members such as `classification`, `request_repairable`, `retry_policy`, `invalid_fields`, `repair_patch`, and `repair_plan`.
5. MUST allow unknown extension members. REC consumers MUST ignore unknown members they do not understand.

REC producers SHOULD use `type` URIs that dereference to human-readable documentation. When a `documentation_url` member is present, it SHOULD point to operation- or domain-specific remediation guidance.

## 3. Problem

APIs usually define how to call an operation successfully: request shape, response shape, authentication, status codes, and examples. Failure behavior is often much weaker.

A vague error such as:

```json
{
  "error": "Bad Request"
}
```

is insufficient for modern callers. A human developer may need to inspect logs. A service may retry incorrectly. A CLI user may not know which field is wrong. An SDK may not know whether retrying is safe. An LLM agent may guess alternate parameter names, modify unrelated values, or keep retrying a request that should be stopped.

The core problem:

> APIs usually define how to call them successfully, but not how callers should recover when calls fail.

## 4. Intent

When an operation fails, REC answers:

* what failed,
* where it failed,
* whether the caller, service, dependency, authorization context, rate limit, version, or business precondition is involved,
* whether re-invoking the operation may help,
* whether the caller should retry the exact same request unchanged,
* which fields are invalid,
* whether a safe JSON Patch can be applied,
* whether a prerequisite operation, user decision, authorization refresh, or diagnostic report is needed,
* how the public response correlates with private diagnostics,
* which information must not be exposed.

The most important agent-specific distinction is:

```text
Retrying may help  ≠  Retry this exact request unchanged
```

This distinction is represented by `retry_policy.can_retry` and `retry_policy.same_request`.

## 5. Applicability

Use REC when:

* APIs are called by LLM agents or tool-use frameworks.
* SDKs, CLIs, workflows, or services need structured failure guidance.
* Users repeatedly make similar request mistakes.
* Agents retry blindly after ambiguous errors.
* Logs contain useful failure information that should be surfaced safely.
* Operations need clear distinction between caller mistakes, dependency failures, rate limits, authorization context, missing business preconditions, and internal bugs.

Do not use REC as a substitute for:

* authentication and authorization,
* logging,
* distributed tracing,
* validation,
* secure exception handling,
* incident management,
* or human review for risky production changes.

REC is a failure contract layer.

## 6. Pattern structure

```text
Caller
  ↓
Operation boundary
  ↓
Failure
  ↓
Diagnostic boundary
  ↓
Sanitized Diagnostic Capsule
  ↓
Analyzer route
  ↓
Schema validation and policy gate
  ↓
RepairableProblem response
```

The pipeline has two explicit boundaries:

1. **Diagnostic boundary:** converts raw failure context into a private, sanitized, allowlisted Diagnostic Capsule.
2. **Policy gate:** converts a candidate analyzer output into either an accepted public RepairableProblem or a deterministic fallback.

Raw stack traces, logs, tokens, cookies, headers, upstream bodies, and caller-supplied secret values MUST NOT cross the public boundary.

## 7. Participants

### Caller

A human, LLM agent, SDK, CLI, workflow engine, or service that invokes an operation.

### Operation

The API or service operation that was invoked.

### Diagnostic boundary

Middleware or wrapper logic that catches failures, assigns diagnostic IDs, records private traces, and constructs a sanitized Diagnostic Capsule.

### Diagnostic Capsule

A private artifact containing safe evidence for analysis. The capsule is never returned directly to the caller.

### Analyzer route

A pluggable component that converts a Diagnostic Capsule into a candidate RepairableProblem. Analyzer implementations MAY be deterministic, LLM-assisted, hybrid, fallback-only, or human-assisted in later operational workflows.

### Policy gate

A validation and enforcement step. It treats analyzer output as untrusted until schema validation and policy checks succeed.

### RepairableProblem

The public `application/problem+json` response returned to the caller.

## 8. Conformance tiers

REC defines conformance tiers to avoid requiring every producer to emit every field.

### 8.1 REC-Core producer

A REC-Core producer MUST emit:

* RFC 9457 members: `type`, `title`, `status`, `detail`, `instance`,
* `rec_version`,
* `classification`,
* `request_repairable`,
* `retry_policy`.

A REC-Core producer SHOULD emit:

* `operation_id`,
* `diagnostic_id`,
* `agent_policy`,
* `caller_instruction`.

### 8.2 REC-Full producer

A REC-Full producer supports REC-Core and additionally emits relevant members such as:

* `invalid_fields`,
* `repair_patch`,
* `repair_patch_applicability`,
* `patch_verified`,
* `repair_plan`,
* `correct_request_example`,
* `safe_debug_summary`,
* `analysis_mode`,
* `confidence`,
* `documentation_url`.

### 8.3 REC consumer

A REC consumer MUST ignore unknown members. A REC consumer MUST NOT auto-apply `repair_patch` unless all of the following are true:

1. `repair_patch_applicability` is `machine_applicable`.
2. `patch_verified` is `true`.
3. The operation is idempotent, or an idempotency key / duplicate-suppression mechanism is in use when required.
4. Local policy allows auto-application.

## 9. Public response: RepairableProblem

A RepairableProblem is a Problem Details object with REC extension members.

Example:

```json
{
  "type": "https://api.example.com/problems/caller-contract-violation",
  "title": "Request does not match the operation contract.",
  "status": 400,
  "detail": "The request used 'url', but this operation expects 'post'.",
  "instance": "urn:diagnostic:diag_example",
  "rec_version": "0.1.0",
  "operation_id": "postRedditThread",
  "diagnostic_id": "diag_example",
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
    "post": "https://www.reddit.com/r/redditdev/comments/abc123/example/"
  },
  "caller_instruction": "Retry using field 'post'. Do not use 'url'.",
  "safe_debug_summary": "Request body shape error before upstream call.",
  "analysis_mode": "deterministic"
}
```

### 9.1 Field summary

| Field | Required in schema | Meaning |
|---|---:|---|
| `type`, `title`, `status`, `detail`, `instance` | yes | RFC 9457 Problem Details members. |
| `rec_version` | yes | REC profile version, for this draft `0.1.x`. |
| `classification` | yes | Stable top-level REC failure class. |
| `request_repairable` | yes | Whether caller-side repair can make progress. |
| `retry_policy` | yes | Retry permission and same-request semantics. |
| `agent_policy` | no | Closed machine-action hint. |
| `operation_id` | no | Operation identifier, preferably OpenAPI `operationId`. |
| `diagnostic_id` | no | Opaque correlation ID for private diagnostics. |
| `trace_id` | no | Trace or correlation ID, if safe. |
| `invalid_fields` | no | JSON Pointer field diagnostics. |
| `repair_patch` | no | RFC 6902 JSON Patch against the original request. |
| `repair_plan` | no | Enum-constrained non-mechanical repair steps. |
| `correct_request_example` | no | Synthetic safe valid request example. |
| `caller_instruction` | no | Short explanatory guidance. |
| `safe_debug_summary` | no | Safe high-level diagnostic summary. |
| `analysis_mode` | no | Analyzer route that produced the response. |
| `confidence` | no | Optional analyzer confidence, not assumed calibrated. |
| `documentation_url` | no | Link to remediation docs. |

## 10. Retry and repair semantics

REC separates three concepts:

```text
request_repairable
retry_policy.can_retry
retry_policy.same_request
```

### 10.1 `request_repairable`

`request_repairable` is true when the caller can make progress by changing request data, credentials, a visible resource reference, or a prerequisite business state. It is false when the correct action is to retry unchanged, report a diagnostic ID, abort, or do nothing.

### 10.2 `retry_policy.can_retry`

`can_retry` is true when re-invoking the same operation may be useful after following the REC guidance. This may mean retrying with a modified request, retrying after a prerequisite operation, or retrying unchanged after a delay.

### 10.3 `retry_policy.same_request`

`same_request` is meaningful only when `can_retry` is true.

* `same_request: true` means the caller should retry the exact same request payload and parameters. The caller MUST NOT mutate request fields to work around the error.
* `same_request: false` means the exact same request is expected to fail again; the caller should follow `invalid_fields`, `repair_patch`, or `repair_plan` first.
* If `can_retry` is false, `same_request` MUST be absent.

Authentication headers MAY be refreshed without violating `same_request: true` only when `repair_plan.action` is `refresh_authorization` or `agent_policy` is `refresh_authorization`.

### 10.4 Default mapping table

The table below gives default semantics. Producers MAY deviate only when they have operation-specific evidence and SHOULD explain deviations in `safe_debug_summary`.

| Classification | Allowed HTTP statuses | Default `request_repairable` | Default `can_retry` | Default `same_request` | Default `agent_policy` |
|---|---|---:|---:|---:|---|
| `caller_contract_violation` | 400, 422 | true | true | false | `modify_request` |
| `semantic_precondition_missing` | 409, 422 | true | true | false | `call_prerequisite` |
| `resource_not_found` | 404 | true | true | false | `modify_request` or `ask_user` |
| `authorization_context_mismatch` | 401, 403, 404 when hiding existence | true for refreshable auth, otherwise false | true for refreshable auth, otherwise false | true only for credential refresh | `refresh_authorization` or `report_diagnostic_id` |
| `version_skew` | 400, 406, 412, 426 | true | true | false | `modify_request` |
| `dependency_failure` | 502, 503, 504 | false | true | true | `retry_unchanged` |
| `capacity_or_timeout` | 408, 429, 503, 504 | false | true | true | `retry_unchanged` |
| `service_bug_likely` | 500 | false | false | absent | `report_diagnostic_id` |
| `security_suspicious` | 400, 403, 429 | false | false | absent | `abort_task` |
| `diagnostic_uncertain` | any 4xx/5xx | false by default | false by default | absent | `report_diagnostic_id` |

### 10.5 Examples

Missing required field:

```json
{
  "request_repairable": true,
  "agent_policy": "modify_request",
  "retry_policy": {
    "can_retry": true,
    "same_request": false
  }
}
```

Rate limit:

```json
{
  "request_repairable": false,
  "agent_policy": "retry_unchanged",
  "retry_policy": {
    "can_retry": true,
    "same_request": true,
    "retry_after_ms": 30000,
    "backoff_hint": "server_directed"
  }
}
```

Internal bug:

```json
{
  "request_repairable": false,
  "agent_policy": "report_diagnostic_id",
  "retry_policy": {
    "can_retry": false
  }
}
```

## 11. Classification taxonomy

REC v0.1.0 defines these top-level classifications.

### `caller_contract_violation`

The caller request violates the operation contract. Examples: invalid JSON, missing field, wrong type, unknown parameter, invalid enum, unsupported media type.

### `semantic_precondition_missing`

The request is structurally valid but a business precondition is missing. Example: an order cannot be shipped before payment capture.

### `resource_not_found`

A referenced resource is not found or not visible. Producers MUST consider the existence-disclosure policy before exposing details.

### `authorization_context_mismatch`

The caller lacks required authentication, authorization, tenant context, scope, role, or credentials. Producers MUST avoid leaking private resource existence.

### `version_skew`

Consumer and producer use incompatible contract versions, feature versions, content types, or precondition headers.

### `dependency_failure`

A downstream or upstream dependency failed after the caller request was accepted as valid.

### `capacity_or_timeout`

The operation failed because of rate limiting, timeout, overload, queue saturation, or capacity constraints.

### `service_bug_likely`

The request passed contract validation, but the service failed internally. Public detail SHOULD be intentionally vague and SHOULD include a diagnostic ID.

### `security_suspicious`

The request or failure context appears abusive or security-sensitive. Producers SHOULD avoid revealing detection logic. Public responses MAY collapse this to `diagnostic_uncertain` or a generic class if exposing `security_suspicious` creates risk.

### `diagnostic_uncertain`

The system lacks enough safe evidence to classify confidently. Producers SHOULD use conservative retry defaults.

## 12. Decision tree

A producer SHOULD classify using this order:

1. If public detail would leak secrets, private resource existence, security detections, or raw internals, first apply the security policy and select the safest public class.
2. If the request cannot be parsed or violates the operation schema, use `caller_contract_violation`.
3. If authentication or authorization context is invalid, use `authorization_context_mismatch`, or return a 404-shaped response when existence hiding is required.
4. If a referenced visible resource is absent or invalid, use `resource_not_found`.
5. If the request is structurally valid but business state is missing, use `semantic_precondition_missing`.
6. If a version, media type, feature flag, or precondition header mismatch caused the failure, use `version_skew`.
7. If a downstream/upstream dependency failed, use `dependency_failure`.
8. If capacity, rate limiting, timeout, or overload caused the failure, use `capacity_or_timeout`.
9. If internal service code failed after validation, use `service_bug_likely`.
10. If evidence is insufficient, use `diagnostic_uncertain`.

## 13. Field diagnostics and path syntax

REC v0.1.0 uses **RFC 6901 JSON Pointer** for all request field paths.

Examples:

```text
/customerId
/currency
/items/0/sku
```

Producers MUST NOT use JSONPath notation such as `$.customerId` in REC paths. This avoids confusing agents and clients that also process RFC 6902 JSON Patch.

`invalid_fields[].received` MUST be shape-only or redacted. It MUST NOT contain raw secrets, tokens, credentials, payment data, or high-risk user content.

When `invalid_fields` is truncated because of response size or safety limits, producers SHOULD set `errors_truncated: true`.

## 14. Repair patch vs repair plan

### 14.1 `repair_patch`

`repair_patch` is an RFC 6902 JSON Patch array against the original request document.

A producer MUST emit `repair_patch` only when one of the following is true:

1. The patch was produced by deterministic validation logic, or
2. the patch was proposed by a non-deterministic analyzer and then server-side verified by applying it to the original request and re-validating the patched request against the operation contract.

When `repair_patch` is present, producers MUST include:

* `repair_patch_applicability`,
* `patch_verified`.

Consumers MUST NOT auto-apply patches unless `repair_patch_applicability` is `machine_applicable` and `patch_verified` is `true`.

### 14.2 `repair_plan`

`repair_plan` contains enum-constrained actions for non-mechanical recovery. It is appropriate when a missing value, business decision, prerequisite operation, authorization refresh, user question, or diagnostic report is required.

Allowed `repair_plan.action` values are defined in `schemas/repairable-problem.schema.json`. Additions to this action registry require a minor version update during the v0.1.x draft line.

## 15. Diagnostic Capsule

The Diagnostic Capsule is private analyzer input. It is not returned to the caller.

It SHOULD include only allowlisted information such as:

* `operation_id`,
* endpoint and method,
* failure stage,
* HTTP status,
* safe error code and message,
* shape-only request information,
* a bounded contract summary,
* synthetic safe examples,
* allowed request paths,
* allowed operation IDs,
* diagnostic and trace IDs,
* security policy audit metadata.

It MUST NOT include:

* raw authorization headers,
* bearer tokens,
* cookies,
* client secrets,
* access or refresh tokens,
* raw stack traces,
* raw environment variables,
* raw upstream response bodies,
* raw logs by default,
* sensitive customer data,
* full raw request bodies by default.

The capsule schema contains const-false audit fields. These fields alone do not prove safety. Implementations MUST build capsules from allowlists and MUST test non-leakage separately.

## 16. Analyzer route

A standard analyzer interface is:

```text
analyze(capsule, operation_contract, policy) -> RepairableProblem | null
```

Analyzer routes MAY be:

* deterministic,
* LLM-assisted,
* hybrid,
* fallback.

An LLM-assisted analyzer MUST satisfy all of the following:

1. The LLM receives only the sanitized Diagnostic Capsule, not raw logs, raw request bodies, stack traces, secrets, credentials, or raw upstream payloads.
2. The LLM output is treated as untrusted candidate data.
3. The candidate output validates against the RepairableProblem schema.
4. The candidate output passes the policy gate.
5. Invalid or unsafe output is discarded.
6. Deterministic fallback remains available.
7. The route has a hard timeout and should be disabled by default in latency-sensitive synchronous paths.

The LLM is not the authority. It is a candidate analyzer.

## 17. Policy gate requirements

A REC policy gate MUST perform at least these checks before returning analyzer output publicly:

1. Validate the candidate against `schemas/repairable-problem.schema.json`.
2. Ensure `classification` is consistent with `status`, `failure_stage`, and operation policy.
3. Ensure retry semantics are consistent with the mapping table unless an explicit operation policy permits deviation.
4. Ensure every `invalid_fields[].path`, `repair_plan[].path`, `repair_patch[].path`, and `repair_patch[].from` is an allowed request path for the operation.
5. Ensure every `repair_plan[].operation_id` is in the allowed operation set.
6. Reject `repair_patch` unless `patch_verified` is true and `repair_patch_applicability` is present.
7. For LLM-originated patches, apply the patch to the original request and re-validate the patched request before setting `patch_verified: true`.
8. Reject text fields that contain secret patterns, raw tokens, stack traces, high-entropy likely secrets, or upstream prompt-injection content.
9. Ensure `correct_request_example` contains only synthetic safe values.
10. Enforce the public resource-existence policy for 403/404 cases.
11. On any policy failure, discard the candidate and emit a deterministic fallback response.

A gate SHOULD log rejection reasons privately for analyzer evaluation.

## 18. Prompt-injection and agent-safety rules

Because REC responses may be shown to LLM agents, public free-text fields are part of the tool-result attack surface.

Producers MUST NOT echo raw caller-supplied values or raw upstream messages into:

* `detail`,
* `caller_instruction`,
* `safe_debug_summary`,
* `invalid_fields[].suggestion`,
* `repair_plan[].reason`,
* `repair_plan[].value_hint`.

Producers SHOULD:

* keep `caller_instruction` imperative, short, and factual,
* reference only fields and operations present in structured REC members,
* include an explicit negative instruction when `same_request: true`, for example “Do not change request parameters,”
* strip markdown code fences and instruction-like upstream text from public fields,
* render REC as structured data in agent frameworks instead of concatenating it into untrusted prose.

`dependency_failure` and `capacity_or_timeout` messages from upstream systems MUST be treated as hostile by default and MUST NOT be passed through verbatim.

## 19. Authorization and resource-existence policy

Implementations MUST define a public resource-existence policy.

When revealing that a resource exists would disclose private information, producers SHOULD return a generic 404-shaped response. In that case:

* `status` MAY be 404,
* `classification` MAY be `authorization_context_mismatch` or `resource_not_found` depending on local policy,
* `detail` MUST NOT confirm whether the resource exists,
* `invalid_fields` SHOULD be omitted,
* `correct_request_example` SHOULD be omitted,
* `agent_policy` SHOULD be `report_diagnostic_id` or `abort_task`.

## 20. OpenAPI extension

OpenAPI 3.1 can describe REC using normal response schemas plus an `x-repairable-error` extension. The repository includes `openapi.yaml` as a complete example.

Minimal form:

```yaml
responses:
  '400':
    description: Repairable request error
    headers:
      Retry-After:
        schema:
          type: string
    content:
      application/problem+json:
        schema:
          $ref: './schemas/repairable-problem.schema.json'
    x-repairable-error:
      recVersion: 0.1.0
      modes: [deterministic, fallback]
      defaultClassification: caller_contract_violation
      allowedRequestPaths: [/post, /sort, /maxComments]
      policyGateRequired: true
```

## 21. Versioning and registries

During the v0.1.x draft line:

* Patch versions fix wording, examples, schema bugs, and reference implementation defects without changing field semantics.
* Minor draft lines may add optional fields, classifications, or repair actions.
* Removing fields or changing field semantics requires a new incompatible draft line.

REC maintains registries for:

* top-level `classification` values,
* `repair_plan.action` values,
* `agent_policy` values,
* analyzer `analysis_mode` values.

Governance details are in `GOVERNANCE.md`.

## 22. Safety risks

Known risks include:

* overexposing diagnostic details,
* hallucinated repair suggestions from LLM analyzers,
* wrong retry guidance,
* leaking private resource existence,
* prompt injection through public error fields,
* excessive latency and cost for LLM-assisted synchronous analysis,
* inconsistent taxonomy usage,
* treating probabilistic analysis as fact,
* auto-applying a bad repair patch.

Mitigations are not optional for LLM-assisted REC. The capsule boundary, schema validation, policy gate, fallback, and tests are part of the pattern.

## 23. Reference implementation principles

A reference implementation SHOULD:

* keep analyzer code isolated,
* default LLM diagnostics off,
* use deterministic analysis first,
* cache repeated deterministic failure signatures,
* use short timeouts for non-deterministic analyzers,
* fallback safely,
* validate schemas,
* test unsafe-output rejection,
* test secret and stack-trace non-leakage,
* test retry semantics,
* test 403/404 existence-hiding behavior,
* test both human-readable and agent-readable fields.

This repository includes a minimal Python reference core under `src/rec/`.

## 24. Relationship to prior art

REC intentionally composes existing mechanisms:

* **RFC 9457 / RFC 7807 Problem Details**: REC uses the standard problem envelope and extension-member model.
* **JSON Schema and validation-output practice**: `invalid_fields` is a curated field-diagnostic projection.
* **JSON:API, Google RPC error details, Stripe, GitHub, Azure, and AWS error models**: REC borrows stable codes, field targets, request IDs, and documentation-link ideas from mature API practice.
* **RFC 6902 JSON Patch and RFC 6901 JSON Pointer**: `repair_patch` is a standard patch format against request documents.
* **HTTP `Retry-After`, idempotency-key practice, Smithy `@retryable`, gRPC retry policies, and SDK retry modes**: REC reuses retry concepts but adds `same_request` as a per-response anti-mutation guard.
* **Compiler fix-it systems such as rustc applicability and clang fix-its**: REC transfers the distinction between machine-applicable and judgment-required repairs to API failures.
* **LLM tool-use systems such as MCP-style tool errors**: REC provides structured content for errors that may enter a model context, rather than free-text-only tool failures.

The novel claim is not “structured errors.” The REC-specific claim is the combination of agent-oriented retry semantics, a public/private diagnostic split, a policy-gated analyzer route, and machine-applicable versus judgment-required repair guidance.

## 25. Evaluation plan

A credible REC evaluation SHOULD compare at least:

* vague errors,
* ordinary framework validation errors,
* RFC 9457 Problem Details without REC fields,
* deterministic REC,
* LLM-assisted REC with policy gate.

Important metrics:

* task recovery rate,
* wrong-retry rate when the correct action is retry unchanged,
* retries until success,
* token cost,
* latency,
* human debugging time,
* classification accuracy,
* secret-leakage rate,
* unsafe suggestion pass-through rate.

The repository includes a benchmark design under `benchmarks/agent-recovery/README.md`; it is a design scaffold, not empirical evidence.

## 26. Concise pattern statement

> Put a diagnostic boundary around an operation. When it fails, build a sanitized diagnostic capsule, analyze it through a deterministic, LLM-assisted, hybrid, or fallback route, validate and policy-gate the candidate response, and return an RFC 9457 RepairableProblem that tells the caller what failed, whether to retry, what to change, and what not to change.
