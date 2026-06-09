from __future__ import annotations

import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_DIR = REPO_ROOT / "schemas"


def load_schema(name: str) -> dict[str, Any]:
    """Load a schema from the repository's schemas directory.

    Parameters
    ----------
    name:
        Either ``repairable-problem`` or ``diagnostic-capsule``; the
        ``.schema.json`` suffix is optional.
    """

    if name.endswith(".schema.json"):
        filename = name
    else:
        filename = f"{name}.schema.json"
    path = SCHEMA_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Schema not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))
