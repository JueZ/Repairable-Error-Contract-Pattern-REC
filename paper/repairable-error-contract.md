# Agent-Repairable Problem Details: A Repairable Error Contract Profile for Actionable API Failures

**Author:** Martin Koschi
**Version:** Draft 0.1.0
**Date:** 2026-06-09

## Abstract

Modern APIs are usually specified around successful interaction: request schemas, response schemas, status codes, authentication, and examples. Failure behavior is often described less rigorously. In human-driven systems, vague failures increase debugging cost. In agentic systems, vague failures can cause autonomous callers to retry blindly, mutate unrelated parameters, or abandon tasks.

This paper proposes **Repairable Error Contracts** (REC), a draft RFC 9457 Problem Details profile for actionable API failures. A REC response classifies the failure, describes retry semantics, identifies invalid fields or missing preconditions, provides safe repair guidance, and includes correlation identifiers for diagnostics. The profile emphasizes three agent-oriented contributions: `retry_policy.same_request` as an anti-mutation retry guard, a private Diagnostic Capsule plus policy-gated analyzer architecture for LLM-assisted error analysis, and a distinction between machine-applicable `repair_patch` and judgment-required `repair_plan`.

REC is not a replacement for Problem Details, JSON Schema, JSON Patch, OpenAPI, tracing, logging, SDK retry policies, or mature vendor error models. It is a recombination of those mechanisms with a narrower agent-recovery contract.

## 1. Introduction

APIs expose contracts. Most API contracts describe how to call an operation successfully. They do not always describe how a caller should recover when a call fails.

This was tolerable when the primary caller was a human developer with access to logs, documentation, source code, and operational context. It becomes more problematic when the caller is an SDK, CLI, workflow engine, microservice, or LLM agent.

A vague error such as:

```json
{
  "error": "Bad Request"
}
```

does not answer the questions a caller must answer:

* Should I retry?
* Should I retry the same request?
* Should I change a parameter?
* Which parameter?
* Is this a dependency problem?
* Is this a missing business precondition?
* Is this an authorization problem?
* Is this a service bug?
* Should I ask a user for more information?
* Should I stop?

LLM agents are especially sensitive to this gap. When a tool call fails, an LLM may attempt to infer the correct call from the error message. If the error is vague, the model may invent parameter names, change valid values, or repeat failing calls.

REC proposes that APIs expose not only success contracts, but also **repairable failure contracts**.

## 2. Problem statement

Traditional error handling creates several failure modes.

### 2.1 Trial-and-error retries

An autonomous caller may repeatedly retry with guessed parameter variants.

### 2.2 Wrong repair attempts

A dependency outage may be misinterpreted as a request problem, causing the caller to change parameters instead of retrying later.

### 2.3 Hidden debugging cost

A human developer may need to inspect logs or source code for a problem the API already understood internally.

### 2.4 Poor service-to-service diagnosability

In microservice systems, unclear failure responses can cause bad retry behavior, cascading failures, and slow root cause analysis.

### 2.5 Unsafe over-disclosure

Simply exposing raw stack traces or logs is not a safe solution. Failure responses must be useful without leaking secrets, authorization context, private resource existence, internal topology, or raw upstream messages.

### 2.6 Prompt-injection exposure in the error path

Tool errors may be shown to LLM agents. Any public field in an error response can become model-context input. A compromised upstream or malicious caller-supplied value can smuggle instructions into the error path unless public text is sanitized and treated as data, not authority.

## 3. Positioning and prior art

REC is a profile and safety architecture, not a new error-envelope invention.

### 3.1 Problem Details

RFC 9457 defines the Problem Details envelope: `type`, `title`, `status`, `detail`, and `instance`, plus extension members. REC uses that model directly and defines extension members for recovery semantics.

### 3.2 Field-level validation errors

JSON:API error objects, JSON Schema validation output, Google RPC `BadRequest.FieldViolation`, Stripe `param`, GitHub REST error arrays, and many framework validation errors already identify invalid fields. REC's `invalid_fields` is a curated version of this familiar mechanism, using JSON Pointer consistently.

### 3.3 Retry mechanisms

HTTP `Retry-After`, idempotency-key practice, Smithy `@retryable`, gRPC retry policies, AWS SDK retry modes, and Google RPC `RetryInfo` already express whether or when retrying may help. REC's addition is `same_request`, which states whether an autonomous caller should retry the exact same request unchanged.

### 3.4 JSON Patch and compiler fix-its

RFC 6902 JSON Patch already defines machine-readable document modifications. Compiler diagnostics such as rustc applicability levels and clang fix-its distinguish machine-applicable fixes from suggestions that require judgment. REC transfers that distinction to API request repair: `repair_patch` is for verified mechanical changes; `repair_plan` is for business, user, or prerequisite steps.

### 3.5 Mature API error design

Stripe, GitHub, Microsoft/Azure, AWS, and Google APIs demonstrate stable error codes, request IDs, field targets, documentation links, and sender/receiver fault distinctions. REC collects these into a portable profile and adds agent-oriented retry and repair semantics.

### 3.6 LLM tool-use systems

Tool-use protocols and function-calling systems often pass tool errors back into a model context so the model can recover. REC aims to standardize the content and safety boundary of those errors: structured fields over free text, sanitized capsule input for analyzers, and policy-gated output.

## 4. Contributions

The strongest REC contributions are narrow.

### 4.1 Same-request retry semantics

`retry_policy.can_retry` says whether re-invoking the operation may help. `retry_policy.same_request` says whether the caller should retry the exact same request payload and parameters.

This matters because an LLM agent may respond to a transient dependency failure by mutating a valid request. `same_request: true` is an explicit anti-mutation guard.

### 4.2 Capsule-to-analyzer-to-gate safety architecture

REC separates private diagnostic evidence from public guidance:

```text
Raw failure → sanitized Diagnostic Capsule → analyzer → schema validation + policy gate → public RepairableProblem
```

An LLM-assisted analyzer may see only the capsule. Its output is untrusted candidate data until schema validation and policy checks pass. Deterministic fallback remains mandatory.

### 4.3 Patch versus plan applicability

REC separates deterministic or verified `repair_patch` from `repair_plan`. This allows clients to auto-apply only machine-applicable, verified patches and to route judgment-required plans to a human, planner, or prerequisite operation.

## 5. Pattern overview

REC introduces a diagnostic boundary around an operation.

```text
Caller
  ↓
Operation
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

The public response is `application/problem+json`. REC members are Problem Details extension members.

## 6. Public response

A REC-Core response contains:

* Problem Details members: `type`, `title`, `status`, `detail`, `instance`,
* `rec_version`,
* `classification`,
* `request_repairable`,
* `retry_policy`.

REC-Full may additionally include:

* `operation_id`,
* `diagnostic_id`,
* `trace_id`,
* `agent_policy`,
* `invalid_fields`,
* `repair_patch`,
* `repair_patch_applicability`,
* `patch_verified`,
* `repair_plan`,
* `correct_request_example`,
* `caller_instruction`,
* `safe_debug_summary`,
* `analysis_mode`,
* `confidence`,
* `documentation_url`.

`confidence` is optional because deterministic analyzers do not necessarily produce calibrated confidence values.

## 7. Diagnostic Capsule

The Diagnostic Capsule is private. It is the safe input to an analyzer.

It may include:

* operation ID,
* endpoint and method,
* failure stage,
* status,
* safe error code and message,
* shape-only request information,
* bounded contract summary,
* safe examples,
* allowed request paths,
* allowed operation IDs,
* security policy flags.

It must not include raw secrets, stack traces, authorization headers, tokens, cookies, raw environment variables, raw upstream bodies, or raw caller-supplied values by default.

The capsule schema's const-false security fields are audit metadata, not proof. Safety depends on allowlisted construction and non-leakage tests.

## 8. Analyzer independence

REC is not tied to LLMs.

Analyzer routes may be:

### Deterministic

Rules and schema validation generate the REC response.

### LLM-assisted

An LLM analyzes a sanitized Diagnostic Capsule and proposes a REC response. The proposal is untrusted until schema validation and policy checks pass.

### Hybrid

Deterministic analysis handles common cases. LLM analysis handles ambiguous or high-value cases.

### Fallback

A generic safe response is returned when analysis fails or is disabled.

LLM-assisted REC should be default-off. It adds latency, cost, and safety risks that must be measured rather than assumed away.

## 9. Policy gate

The policy gate is the key safety mechanism. It should perform at least:

1. JSON Schema validation against `RepairableProblem`.
2. Classification/status consistency checks.
3. Retry-semantics consistency checks.
4. Request-path allowlist checks for `invalid_fields`, `repair_patch`, and `repair_plan`.
5. Operation-ID allowlist checks.
6. Secret-pattern and high-entropy checks in public text.
7. Prompt-injection and raw-upstream-message filtering.
8. Resource-existence disclosure policy checks.
9. Patch verification by applying the patch and re-validating the request.
10. Deterministic fallback on any failure.

The current repository includes a minimal Python policy gate that demonstrates these checks. It is not a complete production security product.

## 10. Classification taxonomy

REC v0.1.0 proposes a small taxonomy:

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

The taxonomy is intentionally small to improve adoption. Domain-specific systems may add `domain_code` without changing the top-level class.

## 11. Retry semantics

REC distinguishes:

* `request_repairable`,
* `retry_policy.can_retry`,
* `retry_policy.same_request`,
* `agent_policy`.

This prevents a common agent failure mode: changing request parameters when the failure is actually caused by rate limiting or an unavailable dependency.

Example transient failure:

```json
{
  "classification": "dependency_failure",
  "request_repairable": false,
  "agent_policy": "retry_unchanged",
  "retry_policy": {
    "can_retry": true,
    "same_request": true,
    "retry_after_ms": 30000
  },
  "caller_instruction": "Retry later with the same request. Do not invent alternative parameters."
}
```

Example internal bug:

```json
{
  "classification": "service_bug_likely",
  "request_repairable": false,
  "agent_policy": "report_diagnostic_id",
  "retry_policy": {
    "can_retry": false
  }
}
```

`same_request` is absent when `can_retry` is false.

## 12. Evaluation plan

The repository does not yet contain empirical results. A credible evaluation should compare:

* C0: vague errors (`{"error":"Bad Request"}`),
* C1: framework-default validation errors,
* C2: RFC 9457 Problem Details only,
* C3: deterministic REC,
* C4: LLM-assisted REC with policy gate.

### 12.1 LLM tool-call recovery

Tasks should cover mock APIs such as invoice, Reddit-thread, calendar, and payments. Failure injections should include missing fields, alias fields, invalid enum values, missing business preconditions, 404s, version skew, 429 with `Retry-After`, dependency 503, and deterministic 500.

Primary metrics:

* tool-call recovery rate,
* wrong-retry rate,
* retries until success,
* token cost,
* end-to-end latency,
* server-side analyzer latency,
* classification accuracy,
* unsafe suggestion pass-through rate.

The most important ablation is REC without `same_request`. If REC's key claim is right, wrong-retry rate should drop in transient-failure trap cases.

### 12.2 Human developer debugging

A human study should compare time-to-correct-request and number of log lookups across vague errors, Problem Details, and REC.

### 12.3 Safety evaluation

An adversarial set should inject canary secrets, fake stack traces, prompt-injection strings, and hostile upstream messages into capsules. Metrics should include secret-leakage rate and unsafe advice that survives the gate.

## 13. Limitations

REC does not automatically fix all errors.

REC does not eliminate the need for logs.

REC does not make LLM analysis automatically safe.

REC does not replace human review for production changes.

REC can be misused if public responses expose too much detail.

REC may be worse than vague errors if it confidently gives wrong repair guidance.

REC adds response size and implementation complexity.

LLM-assisted REC adds latency and cost.

## 14. Standardization strategy

The credible path is implementation before standardization:

1. Maintain the draft profile and schemas.
2. Ship reference middleware and safety tests.
3. Run the agent-recovery and safety benchmark.
4. Propose REC-Core as a tool-error convention for agent/tool ecosystems.
5. Consider an IETF HTTPAPI individual draft only after implementation and adoption evidence exists.

The profile should not lead with broad claims like “APIs should have failure contracts.” It should lead with the three specific contributions that are underserved by existing practice.

## 15. Conclusion

Modern APIs need failure contracts, not only success contracts. But REC's value is not a new envelope. The envelope already exists in Problem Details.

The useful contribution is an agent-oriented extension profile: explicit same-request retry semantics, safe public/private diagnostic separation, policy-gated analyzer output, and a machine-applicable versus judgment-required repair distinction.

The key principle is simple:

> APIs should not merely say that a call failed. They should safely explain how the caller can recover, whether recovery is possible, and what should not be changed.

## References

* RFC 9457 — Problem Details for HTTP APIs.
* RFC 7807 — Problem Details for HTTP APIs, obsoleted by RFC 9457.
* RFC 6901 — JavaScript Object Notation (JSON) Pointer.
* RFC 6902 — JavaScript Object Notation (JSON) Patch.
* RFC 9110 — HTTP Semantics, including `Retry-After`.
* RFC 2119 and RFC 8174 — normative keyword conventions.
* OpenAPI Specification 3.1.
* JSON Schema draft 2020-12.
* JSON:API Error Objects.
* Google RPC Status and error details, including `BadRequest`, `ErrorInfo`, `RetryInfo`, and `PreconditionFailure`.
* Google AIP-193 — Errors.
* Smithy specification `@retryable` trait.
* gRPC status codes and rich error model.
* Stripe API error and idempotency documentation.
* GitHub REST API error documentation.
* Microsoft REST API Guidelines for error responses.
* AWS API error-response and retry behavior documentation.
* W3C Trace Context.
* rustc diagnostics applicability and `rustfix`.
* clang Fix-It hints.
* Model Context Protocol tool-result error conventions.
* Shinn et al., Reflexion, 2023.
* Madaan et al., Self-Refine, 2023.
* Qin et al., ToolLLM, 2023.
