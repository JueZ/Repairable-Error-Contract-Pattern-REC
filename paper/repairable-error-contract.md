# Repairable Error Contracts: A Draft Pattern for Actionable API Failures in Agentic and Service-Oriented Systems

**Author:** Martin Koschi  
**Version:** Draft 0.1  
**Date:** 2026-05-25  
**Status:** Position paper / design note

## Abstract

Modern APIs are usually specified around successful interaction: request schemas, response schemas, status codes, authentication, and examples. Failure behavior is often described less rigorously. In human-driven systems, vague failures increase debugging cost. In agentic systems, vague failures can cause autonomous callers to retry blindly, mutate unrelated parameters, or abandon tasks.

This paper proposes the **Repairable Error Contract Pattern** (REC), a draft architecture pattern that treats failures as first-class contracts. A REC response classifies the failure, describes retry semantics, identifies invalid fields or missing preconditions, provides safe repair guidance, and includes correlation identifiers for diagnostics.

The pattern is analyzer-independent: deterministic, LLM-assisted, hybrid, or fallback analyzers may produce REC responses, provided their output is schema-validated and policy-gated. This makes the pattern applicable to traditional service-to-service systems and emerging LLM-agent tool-use systems.

REC is not intended to replace RFC 9457 Problem Details, OpenAPI, JSON Schema, JSON Patch, gRPC error details, Google-style API error models, logging, tracing, or observability. It is intended as a complementary pattern focused on explicit repair and retry semantics.

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

- Should I retry?
- Should I retry the same request?
- Should I change a parameter?
- Which parameter?
- Is this a dependency problem?
- Is this a business precondition?
- Is this a bug?
- Should I ask a user for more information?
- Should I stop?

LLM agents are especially sensitive to this gap. When a tool call fails, an LLM may attempt to infer the correct call from the error message. If the error is vague, the model may invent parameter names, change valid values, or repeat failing calls.

The Repairable Error Contract Pattern proposes that APIs should expose not only success contracts, but also **repairable failure contracts**.

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

Simply exposing raw stack traces or logs is not a safe solution. Failure responses must be useful without leaking secrets or internals.

## 3. Pattern overview

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
Sanitized diagnostic capsule
  ↓
Analyzer route
  ↓
Schema validation and policy gate
  ↓
Repairable error response
```

The pattern separates private evidence from public guidance.

The private diagnostic capsule contains safe, allowlisted context. The public repairable error response contains actionable guidance.

## 4. Public response

A REC response contains:

- stable failure type,
- title,
- HTTP status,
- human-readable detail,
- concrete diagnostic instance,
- REC version,
- operation ID,
- diagnostic ID,
- classification,
- repairability,
- confidence,
- retry policy,
- invalid fields,
- optional repair patch,
- optional repair plan,
- optional correct request example,
- caller instruction,
- safe debug summary,
- analyzer mode.

The response is useful to humans and machines.

## 5. Diagnostic capsule

The diagnostic capsule is private. It is the safe input to an analyzer.

It may include:

- operation ID,
- endpoint,
- method,
- failure stage,
- status,
- safe error code,
- safe error message,
- request shape,
- contract summary,
- safe examples,
- security policy flags.

It must not include raw secrets, stack traces, authorization headers, tokens, raw environment variables, or raw upstream bodies.

## 6. Analyzer independence

The pattern is not tied to LLMs.

Analyzer routes may be:

### Deterministic

Rules and schema validation generate the REC response.

### LLM-assisted

An LLM analyzes a sanitized diagnostic capsule and proposes a REC response.

### Hybrid

Deterministic analysis handles common cases. LLM analysis handles ambiguous or high-value cases.

### Fallback

A generic safe response is returned when analysis fails or is disabled.

The analyzer output must be treated as untrusted until schema-validated and policy-gated.

## 7. Safety model

The safety model is part of the pattern.

A REC implementation should enforce:

- allowlisted diagnostic capsule construction,
- no raw authorization headers,
- no access tokens,
- no secrets,
- no raw stack traces,
- no raw upstream bodies by default,
- bounded text fields,
- allowed classification taxonomy,
- allowed request field paths,
- allowed operation IDs,
- schema validation,
- deterministic fallback.

For LLM-assisted analyzers, the LLM must not receive unrestricted logs or source context. It should receive only the sanitized capsule.

## 8. Classification taxonomy

REC v0.1 proposes a small taxonomy:

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

The taxonomy is intentionally small to improve adoption. Domain-specific systems may add subcodes.

## 9. Retry semantics

REC distinguishes:

- `repairable`,
- `retry_policy.can_retry`,
- `retry_policy.same_request`.

This distinction prevents a common agent failure mode: changing request parameters when the failure is actually caused by rate limiting or an unavailable dependency.

## 10. Repair semantics

REC distinguishes `repair_patch` from `repair_plan`.

`repair_patch` is used only for deterministic, mechanical repairs. It uses JSON Patch-style operations and JSON Pointer paths.

`repair_plan` is used when a value, user decision, prerequisite operation, or business decision is required.

This distinction is important because not every recoverable error is mechanically patchable.

## 11. Case study: Reddit thread API

A Reddit thread endpoint receives a `post` field. The caller may accidentally send `url` instead.

A vague API returns “Bad Request.”

A REC response can state:

- `url` is an alias-like unknown field,
- `post` is required,
- the caller should move the value to `post`,
- retrying with the same request will not help,
- a valid example is provided.

For unresolved Reddit share URLs, the response can state that the caller should not retry the same `/s/` URL and should provide a canonical comments URL, `redd.it` URL, `t3` fullname, or raw article ID.

For rate limits, the response can state that the caller should retry later with the same request and not mutate parameters.

## 12. Evaluation plan

A REC implementation can be evaluated with three experiments.

### 12.1 LLM tool-call recovery

Compare LLM agent success rates with:

- vague errors,
- normal validation errors,
- REC responses.

Measure:

- successful task completion,
- number of failed retries,
- wrong-parameter retry rate,
- token cost,
- time to successful recovery.

### 12.2 Human developer debugging

Compare developer diagnosis time with:

- vague error plus logs,
- REC response plus diagnostic ID.

Measure:

- time to identify cause,
- time to corrected request,
- number of log lookups,
- subjective clarity.

### 12.3 Microservice retry behavior

Inject failures:

- missing field,
- invalid enum,
- resource not found,
- version skew,
- dependency outage,
- rate limit,
- internal bug.

Measure:

- bad retries avoided,
- correct retry behavior,
- trace correlation,
- classification accuracy.

## 13. Related concepts

REC complements:

- RFC 9457 Problem Details,
- OpenAPI,
- JSON Schema,
- JSON Patch,
- JSON Pointer,
- gRPC richer error details,
- Google-style API errors,
- distributed tracing,
- structured logging,
- observability,
- SDK generation,
- CLI diagnostics,
- LLM tool-use frameworks.

REC does not replace these mechanisms. It combines them into a failure contract pattern focused on recovery semantics.

## 14. Limitations

REC does not automatically fix all errors.

REC does not eliminate the need for logs.

REC does not make LLM analysis automatically safe.

REC does not replace human review for production changes.

REC can be misused if public responses expose too much detail.

REC requires careful schema and policy design.

REC v0.1 is a draft. It needs implementation experience and evaluation before it can be treated as a stable specification.

## 15. Conclusion

Modern APIs need failure contracts, not only success contracts.

The Repairable Error Contract Pattern proposes a structured, safe, analyzer-independent way to make failures actionable for humans, services, workflows, and LLM agents.

It enables immediate caller recovery while preserving security boundaries and supporting future diagnostic feedback loops.

The key principle is simple:

> APIs should not merely say that a call failed. They should safely explain how the caller can recover, whether recovery is possible, and what should not be changed.
