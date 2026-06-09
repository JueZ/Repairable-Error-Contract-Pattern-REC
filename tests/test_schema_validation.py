from __future__ import annotations

from jsonschema import Draft202012Validator

from rec.schema_loader import load_schema


def test_minimal_rec_core_valid() -> None:
    schema = load_schema("repairable-problem")
    problem = {
        "type": "https://api.example.com/problems/caller-contract-violation",
        "title": "Request does not match the operation contract.",
        "status": 400,
        "detail": "The request used 'url', but this operation expects 'post'.",
        "instance": "urn:diagnostic:diag_001",
        "rec_version": "0.1.0",
        "classification": "caller_contract_violation",
        "request_repairable": True,
        "retry_policy": {
            "can_retry": True,
            "same_request": False,
        },
    }
    Draft202012Validator(schema).validate(problem)


def test_unknown_public_extension_members_are_allowed() -> None:
    schema = load_schema("repairable-problem")
    problem = {
        "type": "https://api.example.com/problems/caller-contract-violation",
        "title": "Request does not match the operation contract.",
        "status": 400,
        "detail": "The request used 'url', but this operation expects 'post'.",
        "instance": "urn:diagnostic:diag_001",
        "rec_version": "0.1.0",
        "classification": "caller_contract_violation",
        "request_repairable": True,
        "retry_policy": {
            "can_retry": True,
            "same_request": False,
        },
        "x_vendor_field": "ignored by generic REC consumers",
    }
    Draft202012Validator(schema).validate(problem)


def test_diagnostic_capsule_requires_no_exposed_values() -> None:
    schema = load_schema("diagnostic-capsule")
    capsule = {
        "rec_version": "0.1.0",
        "diagnostic_id": "diag_001",
        "operation_id": "postRedditThread",
        "endpoint": "POST /api/reddit/thread",
        "method": "POST",
        "failure_stage": "input_validation",
        "http_status": 400,
        "safe_error": {"message": "Invalid request shape."},
        "request_shape": {
            "post": {"type": "string", "length_bucket": "medium", "value_exposed": False}
        },
        "contract_summary": {
            "required": ["post"],
            "properties": {"post": {"type": "string"}},
        },
        "safe_examples": [{"post": "https://www.reddit.com/r/redditdev/comments/abc123/example/"}],
        "security_policy": {
            "capsule_source": "allowlist",
            "raw_request_body_included": False,
            "authorization_headers_included": False,
            "tokens_included": False,
            "stack_trace_included": False,
            "raw_upstream_response_included": False,
            "return_only_schema_valid_problem": True,
        },
    }
    Draft202012Validator(schema).validate(capsule)
