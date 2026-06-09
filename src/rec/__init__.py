"""Minimal reference core for Repairable Error Contracts.

This package is intentionally small. It demonstrates schema validation,
retry-semantics checks, safe fallback generation, JSON Patch verification,
and policy-gate rejection. It is not a production security product.
"""

from .deterministic import build_contract_violation_problem, fallback_problem
from .json_patch import JsonPatchError, apply_patch
from .policy_gate import GateResult, PolicyGate, PolicyViolation
from .schema_loader import load_schema

__all__ = [
    "GateResult",
    "JsonPatchError",
    "PolicyGate",
    "PolicyViolation",
    "apply_patch",
    "build_contract_violation_problem",
    "fallback_problem",
    "load_schema",
]
