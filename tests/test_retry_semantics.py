from __future__ import annotations

from jsonschema import Draft202012Validator

from rec.schema_loader import load_schema


def _base() -> dict:
    return {
        "type": "https://api.example.com/problems/internal-error",
        "title": "Internal service error.",
        "status": 500,
        "detail": "An internal error occurred.",
        "instance": "urn:diagnostic:diag_internal",
        "rec_version": "0.1.0",
        "classification": "service_bug_likely",
        "request_repairable": False,
    }


def test_same_request_absent_when_can_retry_false() -> None:
    schema = load_schema("repairable-problem")
    problem = _base() | {"retry_policy": {"can_retry": False}}
    Draft202012Validator(schema).validate(problem)


def test_same_request_rejected_when_can_retry_false() -> None:
    schema = load_schema("repairable-problem")
    problem = _base() | {"retry_policy": {"can_retry": False, "same_request": True}}
    errors = list(Draft202012Validator(schema).iter_errors(problem))
    assert errors


def test_same_request_required_when_can_retry_true() -> None:
    schema = load_schema("repairable-problem")
    problem = _base() | {
        "status": 503,
        "classification": "dependency_failure",
        "retry_policy": {"can_retry": True},
    }
    errors = list(Draft202012Validator(schema).iter_errors(problem))
    assert errors
