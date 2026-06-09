# Example: Reddit thread endpoint

This example illustrates REC with a Reddit thread API endpoint. The examples use `application/problem+json`, RFC 9457 Problem Details members, REC extension members, RFC 6901 JSON Pointer paths, and RFC 6902 JSON Patch.

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
  "rec_version": "0.1.0",
  "operation_id": "postRedditThread",
  "diagnostic_id": "diag_example_alias",
  "classification": "caller_contract_violation",
  "request_repairable": true,
  "agent_policy": "modify_request",
  "retry_policy": {
    "can_retry": true,
    "same_request": false,
    "idempotency_required": false
  },
  "invalid_fields": [
    {
      "path": "/url",
      "problem": "alias_field",
      "suggestion": "Use /post instead."
    }
  ],
  "repair_patch": [
    {
      "op": "move",
      "from": "/url",
      "path": "/post"
    }
  ],
  "repair_patch_applicability": "machine_applicable",
  "patch_verified": true,
  "correct_request_example": {
    "post": "https://www.reddit.com/r/redditdev/comments/abc123/example/",
    "sort": "confidence",
    "maxComments": 10000
  },
  "caller_instruction": "Retry using field 'post'. Do not use 'url', 'redditUrl', or 'threadUrl'.",
  "safe_debug_summary": "Request body shape error before Reddit upstream call.",
  "analysis_mode": "deterministic"
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
  "rec_version": "0.1.0",
  "operation_id": "postRedditThread",
  "diagnostic_id": "diag_example_share",
  "classification": "caller_contract_violation",
  "request_repairable": true,
  "agent_policy": "modify_request",
  "confidence": 0.82,
  "retry_policy": {
    "can_retry": true,
    "same_request": false,
    "idempotency_required": false
  },
  "invalid_fields": [
    {
      "path": "/post",
      "problem": "unresolvable_share_url",
      "expected": "canonical Reddit comments URL, redd.it URL, t3 fullname, or raw article ID"
    }
  ],
  "repair_plan": [
    {
      "action": "replace_invalid_value",
      "path": "/post",
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

Upstream Reddit responds with rate limiting. The HTTP response should include a `Retry-After` header when the delay is known, and `retry_after_ms` should mirror it after conversion to milliseconds.

REC response:

```json
{
  "type": "https://api.example.com/problems/reddit-thread/capacity-or-timeout",
  "title": "Reddit rate limit reached",
  "status": 429,
  "detail": "The upstream request was rate-limited.",
  "instance": "urn:diagnostic:diag_example_rate_limit",
  "rec_version": "0.1.0",
  "operation_id": "postRedditThread",
  "diagnostic_id": "diag_example_rate_limit",
  "classification": "capacity_or_timeout",
  "request_repairable": false,
  "agent_policy": "retry_unchanged",
  "retry_policy": {
    "can_retry": true,
    "same_request": true,
    "retry_after_ms": 30000,
    "idempotency_required": false,
    "backoff_hint": "server_directed"
  },
  "repair_plan": [
    {
      "action": "retry_later",
      "reason": "This is a capacity or rate-limit failure, not a request-parameter failure."
    },
    {
      "action": "do_not_change_request",
      "reason": "Changing post, sort, maxComments, or maxMoreChildrenRequests is not expected to fix this failure."
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

The LLM must not see raw headers, tokens, stack traces, raw request bodies, or raw upstream bodies. It should see only a sanitized Diagnostic Capsule.

Example capsule:

```json
{
  "rec_version": "0.1.0",
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
        "accepted_formats": [
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
  "allowed_request_paths": [
    "/post",
    "/sort",
    "/maxComments",
    "/maxMoreChildrenRequests"
  ],
  "allowed_operation_ids": [
    "postRedditThread"
  ],
  "security_policy": {
    "capsule_source": "allowlist",
    "raw_request_body_included": false,
    "authorization_headers_included": false,
    "tokens_included": false,
    "stack_trace_included": false,
    "raw_upstream_response_included": false,
    "return_only_schema_valid_problem": true
  }
}
```

The capsule is still only an input artifact. Any analyzer output, including LLM output, must pass the public schema and the policy gate before it is returned.
