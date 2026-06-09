from __future__ import annotations

from typing import Any, Iterable

from .deterministic import build_contract_violation_problem, fallback_problem
from .policy_gate import PolicyGate


def _loc_to_pointer(location: Iterable[Any]) -> str:
    parts = list(location)
    if parts and parts[0] in {"body", "query", "path", "header", "cookie"}:
        parts = parts[1:]
    if not parts:
        return ""
    escaped = [str(part).replace("~", "~0").replace("/", "~1") for part in parts]
    return "/" + "/".join(escaped)


def install_rec_exception_handlers(
    app: Any,
    *,
    operation_id: str,
    allowed_request_paths: set[str] | None = None,
    allowed_operation_ids: set[str] | None = None,
) -> None:
    """Install minimal FastAPI exception handlers that return REC responses.

    FastAPI is an optional dependency. This function imports it lazily so the
    core package can be used without a web framework.
    """

    try:
        from fastapi import Request
        from fastapi.exceptions import RequestValidationError
        from fastapi.responses import JSONResponse
    except Exception as exc:  # pragma: no cover - exercised only with optional dependency absent
        raise RuntimeError("Install with the 'fastapi' extra to use FastAPI handlers") from exc

    gate = PolicyGate(
        allowed_request_paths=allowed_request_paths or set(),
        allowed_operation_ids=allowed_operation_ids or {operation_id},
    )

    @app.exception_handler(RequestValidationError)
    async def rec_validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:  # type: ignore[misc]
        diagnostic_id = request.headers.get("x-diagnostic-id", "diag_validation")
        invalid_fields: list[dict[str, Any]] = []
        for error in exc.errors()[:20]:
            pointer = _loc_to_pointer(error.get("loc", []))
            invalid_fields.append(
                {
                    "path": pointer,
                    "problem": str(error.get("type", "validation_error")),
                    "expected": str(error.get("msg", "Request validation failed."))[:300],
                }
            )
        problem = build_contract_violation_problem(
            operation_id=operation_id,
            diagnostic_id=diagnostic_id,
            detail="The request failed validation.",
            invalid_fields=invalid_fields,
            status=422,
        )
        result = gate.evaluate(problem)
        return JSONResponse(
            status_code=result.problem["status"],
            content=result.problem,
            media_type="application/problem+json",
        )

    @app.exception_handler(Exception)
    async def rec_fallback_handler(request: Request, exc: Exception) -> JSONResponse:  # type: ignore[misc]
        capsule = {
            "diagnostic_id": request.headers.get("x-diagnostic-id", "diag_internal"),
            "operation_id": operation_id,
            "http_status": 500,
        }
        problem = fallback_problem(capsule, status=500, title="Internal service error.")
        problem["classification"] = "service_bug_likely"
        problem["type"] = "https://repairable-error-contract.dev/problems/internal-error"
        problem["title"] = "Internal service error."
        problem["detail"] = "An internal error occurred."
        problem["agent_policy"] = "report_diagnostic_id"
        result = gate.evaluate(problem)
        return JSONResponse(
            status_code=result.problem["status"],
            content=result.problem,
            media_type="application/problem+json",
        )
