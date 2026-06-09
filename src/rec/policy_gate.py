from __future__ import annotations

from dataclasses import dataclass, field
import math
import re
from typing import Any, Iterable

from jsonschema import Draft202012Validator

from .deterministic import fallback_problem
from .json_patch import JsonPatchError, apply_patch
from .schema_loader import load_schema

_TEXT_FIELDS = (
    "detail",
    "caller_instruction",
    "safe_debug_summary",
)

_SECRET_PATTERNS = [
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"(?i)bearer\s+[a-z0-9._~+\-/]+=*"),
    re.compile(r"(?i)(api[_-]?key|access[_-]?token|refresh[_-]?token|client[_-]?secret)\s*[:=]\s*\S+"),
    re.compile(r"-----BEGIN [A-Z ]+PRIVATE KEY-----"),
    re.compile(r"(?i)stack trace"),
    re.compile(r"Traceback \(most recent call last\)"),
]

_PROMPT_INJECTION_PATTERNS = [
    re.compile(r"(?i)ignore (all )?(previous|prior) instructions"),
    re.compile(r"(?i)system prompt"),
    re.compile(r"(?i)developer message"),
    re.compile(r"(?i)you are now"),
]

_CLASS_STATUS_DEFAULTS: dict[str, set[int]] = {
    "caller_contract_violation": {400, 422},
    "semantic_precondition_missing": {409, 422},
    "resource_not_found": {404},
    "authorization_context_mismatch": {401, 403, 404},
    "version_skew": {400, 406, 412, 426},
    "dependency_failure": {502, 503, 504},
    "capacity_or_timeout": {408, 429, 503, 504},
    "service_bug_likely": {500},
    "security_suspicious": {400, 403, 429},
}


@dataclass(slots=True)
class PolicyViolation:
    code: str
    message: str


@dataclass(slots=True)
class GateResult:
    accepted: bool
    problem: dict[str, Any]
    violations: list[PolicyViolation] = field(default_factory=list)


class PolicyGate:
    """Validate and policy-gate candidate RepairableProblem objects."""

    def __init__(
        self,
        *,
        allowed_request_paths: Iterable[str] | None = None,
        allowed_operation_ids: Iterable[str] | None = None,
        strict_status_mapping: bool = False,
    ) -> None:
        self.problem_schema = load_schema("repairable-problem")
        self.validator = Draft202012Validator(self.problem_schema)
        self.allowed_request_paths = set(allowed_request_paths or [])
        self.allowed_operation_ids = set(allowed_operation_ids or [])
        self.strict_status_mapping = strict_status_mapping

    def evaluate(
        self,
        candidate: dict[str, Any],
        *,
        capsule: dict[str, Any] | None = None,
        original_request: dict[str, Any] | list[Any] | None = None,
        request_schema: dict[str, Any] | None = None,
    ) -> GateResult:
        """Return accepted candidate or safe fallback with violations."""

        violations = self._violations(
            candidate,
            capsule=capsule,
            original_request=original_request,
            request_schema=request_schema,
        )
        if violations:
            return GateResult(
                accepted=False,
                problem=fallback_problem(capsule, status=int(candidate.get("status", 500))),
                violations=violations,
            )
        return GateResult(accepted=True, problem=candidate, violations=[])

    def assert_valid(self, candidate: dict[str, Any], **kwargs: Any) -> None:
        result = self.evaluate(candidate, **kwargs)
        if not result.accepted:
            joined = "; ".join(f"{v.code}: {v.message}" for v in result.violations)
            raise ValueError(joined)

    def _violations(
        self,
        candidate: dict[str, Any],
        *,
        capsule: dict[str, Any] | None,
        original_request: dict[str, Any] | list[Any] | None,
        request_schema: dict[str, Any] | None,
    ) -> list[PolicyViolation]:
        violations: list[PolicyViolation] = []
        for error in sorted(self.validator.iter_errors(candidate), key=lambda err: list(err.path)):
            path = "/" + "/".join(str(part) for part in error.path)
            violations.append(PolicyViolation("schema_invalid", f"{path}: {error.message}"))

        if violations:
            return violations

        allowed_paths = set(self.allowed_request_paths)
        allowed_ops = set(self.allowed_operation_ids)
        if capsule:
            allowed_paths.update(capsule.get("allowed_request_paths", []))
            allowed_ops.update(capsule.get("allowed_operation_ids", []))

        operation_id = candidate.get("operation_id")
        if operation_id and allowed_ops and operation_id not in allowed_ops:
            violations.append(PolicyViolation("operation_not_allowed", f"operation_id {operation_id!r} is not allowed"))

        self._check_status_mapping(candidate, violations)
        self._check_retry_semantics(candidate, violations)
        self._check_paths(candidate, allowed_paths, violations)
        self._check_operation_ids(candidate, allowed_ops, violations)
        self._check_text(candidate, violations)
        self._check_patch(candidate, original_request, request_schema, violations)
        return violations

    def _check_status_mapping(self, candidate: dict[str, Any], violations: list[PolicyViolation]) -> None:
        classification = candidate.get("classification")
        status = candidate.get("status")
        if classification == "diagnostic_uncertain":
            return
        allowed = _CLASS_STATUS_DEFAULTS.get(str(classification), set())
        if allowed and status not in allowed:
            code = "status_mapping_strict" if self.strict_status_mapping else "status_mapping_deviation"
            message = f"classification {classification!r} normally uses statuses {sorted(allowed)}, got {status!r}"
            if self.strict_status_mapping:
                violations.append(PolicyViolation(code, message))
            elif "safe_debug_summary" not in candidate:
                violations.append(PolicyViolation(code, message + " and no safe_debug_summary explains deviation"))

    def _check_retry_semantics(self, candidate: dict[str, Any], violations: list[PolicyViolation]) -> None:
        retry = candidate.get("retry_policy", {})
        can_retry = retry.get("can_retry")
        if can_retry is False:
            for forbidden in ("same_request", "retry_after_ms", "max_retries"):
                if forbidden in retry:
                    violations.append(PolicyViolation("retry_semantics", f"{forbidden} is invalid when can_retry is false"))
        if can_retry is True and "same_request" not in retry:
            violations.append(PolicyViolation("retry_semantics", "same_request is required when can_retry is true"))
        if candidate.get("classification") in {"dependency_failure", "capacity_or_timeout"}:
            if retry.get("can_retry") is True and retry.get("same_request") is not True:
                violations.append(PolicyViolation("same_request_expected", "transient failures should normally retry unchanged"))

    def _check_paths(
        self,
        candidate: dict[str, Any],
        allowed_paths: set[str],
        violations: list[PolicyViolation],
    ) -> None:
        if not allowed_paths:
            return
        for item in candidate.get("invalid_fields", []) or []:
            self._path_allowed(item.get("path"), allowed_paths, violations, "invalid_fields.path")
        for item in candidate.get("repair_plan", []) or []:
            if "path" in item:
                self._path_allowed(item.get("path"), allowed_paths, violations, "repair_plan.path")
        for item in candidate.get("repair_patch", []) or []:
            self._path_allowed(item.get("path"), allowed_paths, violations, "repair_patch.path")
            if "from" in item:
                self._path_allowed(item.get("from"), allowed_paths, violations, "repair_patch.from")

    def _path_allowed(
        self,
        path: Any,
        allowed_paths: set[str],
        violations: list[PolicyViolation],
        field: str,
    ) -> None:
        if not isinstance(path, str):
            violations.append(PolicyViolation("path_invalid", f"{field} must be a string"))
            return
        if path not in allowed_paths:
            violations.append(PolicyViolation("path_not_allowed", f"{field} {path!r} is not in allowed request paths"))

    def _check_operation_ids(
        self,
        candidate: dict[str, Any],
        allowed_ops: set[str],
        violations: list[PolicyViolation],
    ) -> None:
        if not allowed_ops:
            return
        for item in candidate.get("repair_plan", []) or []:
            operation_id = item.get("operation_id")
            if operation_id and operation_id not in allowed_ops:
                violations.append(PolicyViolation("operation_not_allowed", f"repair operation {operation_id!r} is not allowed"))

    def _check_text(self, candidate: dict[str, Any], violations: list[PolicyViolation]) -> None:
        texts: list[tuple[str, str]] = []
        for field in _TEXT_FIELDS:
            value = candidate.get(field)
            if isinstance(value, str):
                texts.append((field, value))
        for index, item in enumerate(candidate.get("invalid_fields", []) or []):
            for field in ("expected", "received", "suggestion"):
                value = item.get(field)
                if isinstance(value, str):
                    texts.append((f"invalid_fields[{index}].{field}", value))
        for index, item in enumerate(candidate.get("repair_plan", []) or []):
            for field in ("value_hint", "reason"):
                value = item.get(field)
                if isinstance(value, str):
                    texts.append((f"repair_plan[{index}].{field}", value))

        for field, value in texts:
            if _looks_high_entropy_secret(value):
                violations.append(PolicyViolation("secret_like_text", f"{field} looks like a high-entropy secret"))
            for pattern in _SECRET_PATTERNS:
                if pattern.search(value):
                    violations.append(PolicyViolation("secret_pattern", f"{field} matched {pattern.pattern!r}"))
                    break
            for pattern in _PROMPT_INJECTION_PATTERNS:
                if pattern.search(value):
                    violations.append(PolicyViolation("prompt_injection_text", f"{field} matched {pattern.pattern!r}"))
                    break

    def _check_patch(
        self,
        candidate: dict[str, Any],
        original_request: dict[str, Any] | list[Any] | None,
        request_schema: dict[str, Any] | None,
        violations: list[PolicyViolation],
    ) -> None:
        patch = candidate.get("repair_patch")
        if not patch:
            return
        if candidate.get("patch_verified") is not True:
            violations.append(PolicyViolation("patch_not_verified", "repair_patch requires patch_verified true"))
        if candidate.get("repair_patch_applicability") != "machine_applicable":
            violations.append(PolicyViolation("patch_not_machine_applicable", "auto-applicable patches must be machine_applicable"))
        if candidate.get("analysis_mode") == "llm_assisted" and candidate.get("patch_verified") is not True:
            violations.append(PolicyViolation("llm_patch_unverified", "LLM-assisted patch must be verified"))
        if original_request is not None and request_schema is not None:
            try:
                patched = apply_patch(original_request, patch)
                Draft202012Validator(request_schema).validate(patched)
            except (JsonPatchError, Exception) as exc:  # jsonschema raises ValidationError, covered here intentionally
                violations.append(PolicyViolation("patch_revalidation_failed", str(exc)))


def _looks_high_entropy_secret(text: str) -> bool:
    compact = re.sub(r"[^A-Za-z0-9+/=_-]", "", text)
    if len(compact) < 32:
        return False
    alphabet = set(compact)
    if len(alphabet) < 16:
        return False
    counts = {char: compact.count(char) for char in alphabet}
    entropy = -sum((count / len(compact)) * math.log2(count / len(compact)) for count in counts.values())
    return entropy >= 4.2
