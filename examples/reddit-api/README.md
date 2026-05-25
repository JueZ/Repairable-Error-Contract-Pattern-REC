# Example: Reddit thread endpoint

This example illustrates the Repairable Error Contract Pattern with a Reddit thread API endpoint.

## Operation

```text
POST /api/reddit/thread
```

Expected request:

```json
{
  "post": "https://www.reddit.com/r/redditdev/comments/abc123/example/",
  "sort": "confidence",
  "maxComments": 10000,
  "maxMoreChildrenRequests": 1000
}
```

Accepted `post` formats:

* raw Reddit article ID,
* raw Reddit comment ID if the service can resolve it to the parent post,
* `t3_` fullname,
* `redd.it` URL,
* canonical `reddit.com` comments URL,
* `old.reddit.com` comments URL,
* Reddit `/r/<subreddit>/s/<token>` share URL if it can be resolved safely.

## Scenario 1: caller uses `url` instead of `post`

Caller sends:

```json
{
  "url": "https://www.reddit.com/r/redditdev/comments/abc123/example/"
}
```

Traditional response:

```json
{
  "error": "Bad Request"
}
```

REC response:

```json
{
  "type": "https://api.example.com/problems/reddit-thread/caller-contract-violation",
  "title": "Request contract violation",
  "status": 400,
  "detail": "The request used 'url', but this operation expects 'post'.",
  "instance": "urn:diagnostic:diag_example_alias",
  "rec_version": "1.0",
  "operation_id": "postRedditThread",
  "diagnostic_id": "diag_example_alias",
  "classification": "caller_contract_violation",
  "repairable": true,
  "confidence": 0.93,
  "retry_policy": {
    "can_retry": true,
    "same_request": false,
    "idempotency_required": false
  },
  "invalid_fields": [
    {
      "path": "$.url",
      "problem": "alias_field",
      "suggestion": "Use '$.post' instead."
    }
  ],
  "repair_patch": [
    {
      "op": "move",
      "from": "/url",
      "path": "/post"
    }
  ],
  "correct_request_example": {
    "post": "https://www.reddit.com/r/redditdev/comments/abc123/example/",
    "sort": "confidence",
    "maxComments": 10000
  },
  "caller_instruction": "Retry using field 'post'. Do not use 'url', 'redditUrl', or 'threadUrl'.",
  "safe_debug_summary": "Request body shape error before Reddit upstream call.",
  "analysis_mode": "llm_assisted"
}
```

The important improvement:

```text
The caller knows exactly what to change.
```

## Scenario 2: unresolved Reddit share URL

Caller sends:

```json
{
  "post": "https://www.reddit.com/r/OpenAI/s/iuZlOIPdCI"
}
```

If the service cannot resolve the share URL to a canonical comments URL, it should not pretend that changing random parameters will help.

REC response:

```json
{
  "type": "https://api.example.com/problems/reddit-thread/caller-contract-violation",
  "title": "Request contract violation",
  "status": 400,
  "detail": "The Reddit share URL could not be resolved to a canonical comments URL.",
  "instance": "urn:diagnostic:diag_example_share",
  "rec_version": "1.0",
  "operation_id": "postRedditThread",
  "diagnostic_id": "diag_example_share",
  "classification": "caller_contract_violation",
  "repairable": true,
  "confidence": 0.82,
  "retry_policy": {
    "can_retry": true,
    "same_request": false,
    "idempotency_required": false
  },
  "repair_plan": [
    {
      "action": "replace_invalid_value",
      "path": "$.post",
      "value_hint": "Use a canonical /comments/<id> URL, redd.it URL, t3 fullname, or raw article ID.",
      "reason": "The share URL could not be resolved deterministically."
    }
  ],
  "caller_instruction": "Do not retry the same /s/ share URL. Use a canonical Reddit comments URL, redd.it URL, t3 fullname, or raw article ID instead.",
  "safe_debug_summary": "Unresolved Reddit share URL before thread fetch.",
  "analysis_mode": "fallback"
}
```

## Scenario 3: Reddit rate limit

Upstream Reddit responds with rate limiting.

REC response:

```json
{
  "type": "https://api.example.com/problems/reddit-thread/capacity-or-timeout",
  "title": "Reddit rate limit reached",
  "status": 429,
  "detail": "Reddit rate-limited the upstream request.",
  "instance": "urn:diagnostic:diag_example_rate_limit",
  "rec_version": "1.0",
  "operation_id": "postRedditThread",
  "diagnostic_id": "diag_example_rate_limit",
  "classification": "capacity_or_timeout",
  "repairable": false,
  "confidence": 0.9,
  "retry_policy": {
    "can_retry": true,
    "same_request": true,
    "retry_after_ms": 30000,
    "idempotency_required": false
  },
  "repair_plan": [
    {
      "action": "retry_later",
      "reason": "The upstream service asked callers to slow down."
    }
  ],
  "caller_instruction": "Retry later with the same request. Do not change post, sort, maxComments, or maxMoreChildrenRequests to work around this error.",
  "safe_debug_summary": "Upstream rate-limit response.",
  "analysis_mode": "fallback"
}
```

The important improvement:

```text
The caller knows not to mutate the request.
```

## LLM-assisted route

The LLM should not see raw headers, tokens, stack traces, or raw upstream bodies.

It should see only a sanitized diagnostic capsule, for example:

```json
{
  "rec_version": "1.0",
  "diagnostic_id": "diag_example",
  "operation_id": "postRedditThread",
  "endpoint": "POST /api/reddit/thread",
  "method": "POST",
  "failure_stage": "input_validation",
  "http_status": 400,
  "safe_error": {
    "code": "UNRESOLVED_REDDIT_SHARE_URL",
    "message": "Could not resolve Reddit /s/ share URL to canonical /comments/<id>/ URL."
  },
  "request_shape": {
    "post": {
      "type": "string",
      "length_bucket": "medium",
      "value_exposed": false
    }
  },
  "contract_summary": {
    "required": [
      "post"
    ],
    "properties": {
      "post": {
        "type": "string",
        "acceptedFormats": [
          "raw Reddit article ID",
          "t3 fullname",
          "redd.it URL",
          "reddit.com comments URL"
        ]
      }
    }
  },
  "safe_examples": [
    {
      "post": "https://www.reddit.com/r/redditdev/comments/abc123/example/"
    }
  ],
  "security_policy": {
    "raw_request_body_included": false,
    "authorization_headers_included": false,
    "tokens_included": false,
    "stack_trace_included": false,
    "raw_upstream_response_included": false,
    "return_only_schema_valid_problem": true
  }
}
```
