from __future__ import annotations

from rec.json_patch import apply_patch


def test_move_field() -> None:
    result = apply_patch({"url": "x"}, [{"op": "move", "from": "/url", "path": "/post"}])
    assert result == {"post": "x"}
