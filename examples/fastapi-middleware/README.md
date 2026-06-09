# Example: FastAPI exception handlers

This is a minimal framework adapter for the reference core. It demonstrates one way to return REC Problem Details from FastAPI validation and fallback exception handlers.

Install optional dependencies:

```bash
python -m pip install -e '.[fastapi]'
```

Sketch:

```python
from fastapi import FastAPI
from pydantic import BaseModel

from rec.fastapi import install_rec_exception_handlers

app = FastAPI()

install_rec_exception_handlers(
    app,
    operation_id="postRedditThread",
    allowed_request_paths={"/post", "/sort", "/maxComments", "/maxMoreChildrenRequests"},
)

class ThreadRequest(BaseModel):
    post: str
    sort: str = "confidence"
    maxComments: int = 10000

@app.post("/api/reddit/thread")
def post_reddit_thread(request: ThreadRequest) -> dict:
    return {"ok": True}
```

This adapter is intentionally small. Production middleware should attach real diagnostic IDs, trace IDs, OpenAPI operation metadata, operation-specific allowed paths, existence-hiding policy, and non-leakage tests.
