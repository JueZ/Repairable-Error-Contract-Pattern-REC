# Changelog

## 0.1.0 — draft rewrite

This draft incorporates a broad review of the initial repository and narrows REC into an RFC 9457 extension profile plus analyzer-safety architecture.

### Changed

* Reframed REC as an RFC 9457 Problem Details profile using extension members.
* Aligned all examples and schemas on `rec_version: "0.1.0"`.
* Replaced ambiguous `repairable` with `request_repairable`.
* Made `confidence`, `analysis_mode`, `safe_debug_summary`, and `caller_instruction` optional rather than mandatory.
* Allowed unknown public extension members by removing `additionalProperties: false` from the public schema.
* Standardized all request paths on RFC 6901 JSON Pointer.
* Made `retry_policy.same_request` valid only when `retry_policy.can_retry` is true.
* Defined default classification/status/retry mappings.
* Added `agent_policy` as a closed machine-action hint.
* Added `repair_patch_applicability` and `patch_verified` to govern auto-application.
* Removed `llm_instruction` to avoid duplicate free-text machine channels.
* Added `documentation_url`, `errors_truncated`, `max_retries`, and `backoff_hint`.

### Added

* Normative relationship to RFC 9457 and `application/problem+json`.
* REC-Core and REC-Full conformance tiers.
* Prompt-injection and resource-existence disclosure guidance.
* Concrete policy-gate checklist.
* 401, 403, 404, hidden-existence 404, and 500 examples.
* `openapi.yaml` example.
* Minimal Python reference core under `src/rec/`.
* Tests for schema validation, retry semantics, non-leakage, and policy-gate behavior.
* Benchmark design scaffold under `benchmarks/agent-recovery/`.
* Governance and registry process.

### Not yet done

* No empirical benchmark results are included.
* No production middleware package is published.
* LLM-assisted analyzer implementation is intentionally not enabled by default.
