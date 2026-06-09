# Review remediation summary

This file maps the major review findings to repository changes in draft v0.1.0.

## Positioning

* Reframed REC as an RFC 9457 Problem Details profile, not a replacement envelope.
* Added `application/problem+json` guidance.
* Added prior-art positioning in the spec and paper.
* Added “What REC is not” to the README.

## Schema and semantics

* Replaced ambiguous `repairable` with `request_repairable`.
* Added `agent_policy` for closed machine-action routing.
* Made `confidence`, `caller_instruction`, `safe_debug_summary`, and `analysis_mode` optional.
* Standardized all paths on RFC 6901 JSON Pointer.
* Allowed public extension members by permitting additional properties in the public schema.
* Made `retry_policy.same_request` valid only when `can_retry` is true.
* Added `repair_patch_applicability` and `patch_verified`.
* Removed `llm_instruction`.
* Added `documentation_url`, `errors_truncated`, `max_retries`, and `backoff_hint`.
* Aligned all versions on `0.1.0`.

## Safety

* Added concrete policy-gate requirements.
* Added prompt-injection and no-echo rules.
* Added resource-existence disclosure guidance for 403/404.
* Tightened Diagnostic Capsule schema holes around `contract_summary` and `safe_examples`.
* Reframed capsule security flags as audit metadata, not proof of safety.
* Added non-leakage and policy-gate rejection tests.

## Examples

* Updated Reddit and invoice examples.
* Added 401, 403, visible 404, hidden-existence 404, and 500 examples.
* Added OpenAPI 3.1 example.
* Added optional FastAPI middleware sketch.

## Implementation and tests

* Added a minimal Python reference core under `src/rec/`.
* Added JSON Patch helper for verification tests.
* Added deterministic fallback and contract-violation builders.
* Added policy gate with schema, path, operation, retry, text, and patch checks.
* Added pytest tests and a GitHub Actions workflow.

## Remaining limitations

* No empirical benchmark results are included.
* The benchmark directory is a design scaffold, not a completed experiment.
* The FastAPI adapter is intentionally minimal and not production middleware.
* LLM-assisted analysis is specified as an architecture but not implemented as a default route.
