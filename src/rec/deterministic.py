from __future__ import annotations

from typing import Any

REC_VERSION = "0.1.0"


def _diagnostic_id(capsule: dict[str, Any] | None) -> str:
    if capsule:
        return str(capsule.get("diagnostic_id") or "diag_unavailable")
    return "diag_unavailable"


def fallback_problem(
    capsule: dict[str, Any] | None = None,
    *,
    status: int | None = None,
    title: str = "Failure could not be safely classified.",
) -> dict[str, Any]:
    """Build a conservative safe fallback RepairableProblem.

    Fallback deliberately avoids request-field guidance and retry mutation advice.
    """

    diagnostic_id = _diagnostic_id(capsule)
    http_status = status or int(capsule.get("http_status", 500) if capsule else 500)
    operation_id = capsule.get("operation_id") if capsule else None
    problem: dict[str, Any] = {
        "type": "https://repairable-error-contract.dev/problems/diagnostic-uncertain",
        "title": title,
        "status": http_status,
        "detail": "The failure could not be safely analyzed. Use the diagnostic ID for investigation.",
        "instance": f"urn:diagnostic:{diagnostic_id}",
        "rec_version": REC_VERSION,
        "diagnostic_id": diagnostic_id,
        "classification": "diagnostic_uncertain",
        "request_repairable": False,
        "agent_policy": "report_diagnostic_id",
        "retry_policy": {
            "can_retry": False
        },
        "repair_plan": [
            {
                "action": "report_diagnostic_id",
                "reason": "A safe repair instruction could not be produced."
            }
        ],
        "caller_instruction": "Do not change request parameters based on this response. Report the diagnostic ID.",
        "safe_debug_summary": "Policy-gated fallback response.",
        "analysis_mode": "fallback",
    }
    if operation_id:
        problem["operation_id"] = operation_id
    return problem


def build_contract_violation_problem(
    *,
    operation_id: str,
    diagnostic_id: str,
    detail: str,
    invalid_fields: list[dict[str, Any]],
    repair_patch: list[dict[str, Any]] | None = None,
    repair_plan: list[dict[str, Any]] | None = None,
    correct_request_example: dict[str, Any] | None = None,
    status: int = 400,
) -> dict[str, Any]:
    """Build a deterministic caller-contract violation response."""

    problem: dict[str, Any] = {
        "type": "https://repairable-error-contract.dev/problems/caller-contract-violation",
        "title": "Request does not match the operation contract.",
        "status": status,
        "detail": detail,
        "instance": f"urn:diagnostic:{diagnostic_id}",
        "rec_version": REC_VERSION,
        "operation_id": operation_id,
        "diagnostic_id": diagnostic_id,
        "classification": "caller_contract_violation",
        "request_repairable": True,
        "agent_policy": "modify_request",
        "retry_policy": {
            "can_retry": True,
            "same_request": False
        },
        "invalid_fields": invalid_fields,
        "caller_instruction": "Repair the indicated request fields before retrying. Retrying the same request is expected to fail.",
        "safe_debug_summary": "Request failed contract validation before business processing.",
        "analysis_mode": "deterministic",
    }
    if repair_patch:
        problem["repair_patch"] = repair_patch
        problem["repair_patch_applicability"] = "machine_applicable"
        problem["patch_verified"] = True
    if repair_plan:
        problem["repair_plan"] = repair_plan
    if correct_request_example:
        problem["correct_request_example"] = correct_request_example
    return problem
