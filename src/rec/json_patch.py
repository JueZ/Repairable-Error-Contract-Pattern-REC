from __future__ import annotations

from copy import deepcopy
from typing import Any


class JsonPatchError(ValueError):
    """Raised when a JSON Patch cannot be applied safely."""


def _unescape(segment: str) -> str:
    return segment.replace("~1", "/").replace("~0", "~")


def _parts(pointer: str) -> list[str]:
    if pointer == "":
        return []
    if not pointer.startswith("/"):
        raise JsonPatchError(f"Invalid JSON Pointer: {pointer!r}")
    return [_unescape(part) for part in pointer.split("/")[1:]]


def _resolve_parent(document: Any, pointer: str) -> tuple[Any, str]:
    parts = _parts(pointer)
    if not parts:
        raise JsonPatchError("Operation requires a non-root path")
    current = document
    for part in parts[:-1]:
        if isinstance(current, list):
            try:
                index = int(part)
            except ValueError as exc:
                raise JsonPatchError(f"Array index expected at {part!r}") from exc
            try:
                current = current[index]
            except IndexError as exc:
                raise JsonPatchError(f"Array index out of range: {part!r}") from exc
        elif isinstance(current, dict):
            if part not in current:
                raise JsonPatchError(f"Path does not exist: {pointer!r}")
            current = current[part]
        else:
            raise JsonPatchError(f"Cannot traverse non-container at {part!r}")
    return current, parts[-1]


def _get(document: Any, pointer: str) -> Any:
    current = document
    for part in _parts(pointer):
        if isinstance(current, list):
            try:
                current = current[int(part)]
            except (ValueError, IndexError) as exc:
                raise JsonPatchError(f"Path does not exist: {pointer!r}") from exc
        elif isinstance(current, dict):
            if part not in current:
                raise JsonPatchError(f"Path does not exist: {pointer!r}")
            current = current[part]
        else:
            raise JsonPatchError(f"Cannot traverse non-container for {pointer!r}")
    return current


def _add(document: Any, pointer: str, value: Any) -> None:
    if pointer == "":
        raise JsonPatchError("Replacing the root with add is not supported by this minimal helper")
    parent, key = _resolve_parent(document, pointer)
    if isinstance(parent, list):
        if key == "-":
            parent.append(value)
            return
        try:
            index = int(key)
        except ValueError as exc:
            raise JsonPatchError(f"Array index expected at {key!r}") from exc
        if index < 0 or index > len(parent):
            raise JsonPatchError(f"Array index out of range: {key!r}")
        parent.insert(index, value)
    elif isinstance(parent, dict):
        parent[key] = value
    else:
        raise JsonPatchError("Cannot add to non-container")


def _remove(document: Any, pointer: str) -> Any:
    parent, key = _resolve_parent(document, pointer)
    if isinstance(parent, list):
        try:
            return parent.pop(int(key))
        except (ValueError, IndexError) as exc:
            raise JsonPatchError(f"Array index out of range: {key!r}") from exc
    if isinstance(parent, dict):
        if key not in parent:
            raise JsonPatchError(f"Path does not exist: {pointer!r}")
        return parent.pop(key)
    raise JsonPatchError("Cannot remove from non-container")


def _replace(document: Any, pointer: str, value: Any) -> None:
    parent, key = _resolve_parent(document, pointer)
    if isinstance(parent, list):
        try:
            parent[int(key)] = value
            return
        except (ValueError, IndexError) as exc:
            raise JsonPatchError(f"Array index out of range: {key!r}") from exc
    if isinstance(parent, dict):
        if key not in parent:
            raise JsonPatchError(f"Path does not exist: {pointer!r}")
        parent[key] = value
        return
    raise JsonPatchError("Cannot replace in non-container")


def apply_patch(document: Any, patch: list[dict[str, Any]]) -> Any:
    """Apply a small RFC 6902 JSON Patch subset to a deep copy of document.

    The helper implements add, remove, replace, move, copy, and test well enough
    for reference-policy tests. Production code should use a mature JSON Patch
    implementation with comprehensive edge-case coverage.
    """

    result = deepcopy(document)
    for operation in patch:
        op = operation.get("op")
        path = operation.get("path")
        if not isinstance(path, str):
            raise JsonPatchError("Patch operation requires string path")
        if op == "add":
            if "value" not in operation:
                raise JsonPatchError("add requires value")
            _add(result, path, deepcopy(operation["value"]))
        elif op == "remove":
            _remove(result, path)
        elif op == "replace":
            if "value" not in operation:
                raise JsonPatchError("replace requires value")
            _replace(result, path, deepcopy(operation["value"]))
        elif op == "move":
            from_path = operation.get("from")
            if not isinstance(from_path, str):
                raise JsonPatchError("move requires from")
            value = _remove(result, from_path)
            _add(result, path, value)
        elif op == "copy":
            from_path = operation.get("from")
            if not isinstance(from_path, str):
                raise JsonPatchError("copy requires from")
            _add(result, path, deepcopy(_get(result, from_path)))
        elif op == "test":
            if "value" not in operation:
                raise JsonPatchError("test requires value")
            if _get(result, path) != operation["value"]:
                raise JsonPatchError(f"test failed at {path!r}")
        else:
            raise JsonPatchError(f"Unsupported patch op: {op!r}")
    return result
