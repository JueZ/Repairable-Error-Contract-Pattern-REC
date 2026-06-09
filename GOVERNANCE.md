# Governance

REC is a draft profile. This file defines how classifications, repair actions, agent policies, and versioning should evolve while the project is small.

## Maintainer

Initial maintainer: Martin Koschi.

The project should move to a multi-maintainer model before any v1.0 claim or standards-track proposal.

## Design principles

1. **Reuse before invention.** Prefer RFC 9457, JSON Pointer, JSON Patch, OpenAPI, JSON Schema, HTTP headers, and existing vendor practice over new formats.
2. **Stable top-level taxonomy.** Keep `classification` small. Use `domain_code` for domain-specific detail.
3. **Safety over cleverness.** A safe fallback is better than a hallucinated or over-disclosing repair suggestion.
4. **Machine channels over prose.** Agents should rely on `agent_policy`, `retry_policy`, `invalid_fields`, `repair_patch`, and `repair_plan` before parsing `caller_instruction`.
5. **Implementations before standards.** Do not present REC as a mature standard until reference implementations, tests, and benchmark results exist.

## Registries

REC maintains four small registries in the JSON Schema and spec.

### Classification registry

Current values:

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

Adding a classification requires:

* a definition,
* allowed HTTP status mapping,
* retry defaults,
* security disclosure notes,
* at least two examples,
* policy-gate implications.

### Repair action registry

Current `repair_plan.action` values:

```text
provide_missing_value
replace_invalid_value
remove_unknown_field
call_prerequisite_operation
refresh_authorization
retry_with_modified_request
retry_later
do_not_change_request
ask_user
report_diagnostic_id
abort_task
```

Adding an action requires:

* a precise machine meaning,
* required/optional fields,
* auto-execution rules,
* at least one example.

### Agent policy registry

Current `agent_policy` values:

```text
modify_request
retry_unchanged
call_prerequisite
refresh_authorization
ask_user
report_diagnostic_id
abort_task
none
```

`agent_policy` should remain coarser than `repair_plan.action`. It is a switch target for SDKs and agent frameworks.

### Analysis mode registry

Current `analysis_mode` values:

```text
deterministic
llm_assisted
hybrid
fallback
```

New analyzer modes should not expose model/provider details publicly.

## Versioning

Current draft version: `0.1.0`.

During the `0.1.x` draft line:

* Patch releases may fix wording, examples, typos, schemas, and reference implementation bugs without changing field semantics.
* New optional fields may be proposed, but should normally wait for a minor draft line.
* New classifications, repair actions, or agent policies require a minor draft line.
* Removing a field or changing field semantics requires an incompatible draft line.

A future `1.0.0` release requires:

1. at least one production-quality reference implementation,
2. schema and policy-gate tests,
3. examples for 400, 401, 403, 404, hidden 404, 409, 422, 429, 500, 503,
4. a related-work section with primary sources,
5. benchmark evidence against a Problem Details baseline,
6. a multi-maintainer review process.

## Proposal process

Use issues or pull requests with this template:

```markdown
## Proposal

## Problem

## Existing mechanisms considered

## Schema/spec change

## Safety impact

## Retry/repair semantics impact

## Examples

## Tests
```

Changes that affect public schema semantics should include tests and example updates in the same pull request.

## Security process

Security-sensitive reports should not be disclosed publicly before triage. Until a private advisory channel exists, reports should avoid including live tokens, secrets, customer data, or exploit payloads from real systems.
