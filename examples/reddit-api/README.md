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

- raw Reddit article ID,
- raw Reddit comment ID if the service can resolve it to the parent post,
- `t3_` fullname,
- `redd.it` URL,
- canonical `reddit.com` comments URL,
- `old.reddit.com` comments URL,
- Reddit `/r/<subreddit>/s/<id>` share URL if it can be resolved safely.

## Scenarios

### Scenario 1: caller uses `url` instead of `post`

The caller sends:

```json
{
  "url": "https://www.reddit.com/r/redditdev/comments/abc123/example/"
}
```

A traditional vague response might be:

```json
{
  "error": "Bad Request"
}
```

The REC response is provided in:

```text
examples/reddit-api/valid-alias-field.rec.json
```

The important improvement:

```text
The caller knows exactly what to change.
```

### Scenario 2: unresolved Reddit share URL

The caller sends:

```json
{
  "post": "https://www.reddit.com/r/OpenAI/s/iuZlOIPdCI"
}
```

If the service cannot resolve the share URL to a canonical comments URL, it should not pretend that changing random parameters will help.

The REC response is provided in:

```text
examples/reddit-api/valid-share-url-repair-plan.rec.json
```

### Scenario 3: Reddit rate limit

If the upstream Reddit API rate-limits the request, the caller should retry later with the same request. It should not mutate `post`, `sort`, `maxComments`, or `maxMoreChildrenRequests`.

The REC response is provided in:

```text
examples/reddit-api/valid-rate-limit.rec.json
```

The important improvement:

```text
The caller knows not to mutate the request.
```

## LLM-assisted route

The LLM should not see raw headers, tokens, stack traces, or raw upstream bodies.

It should see only a sanitized diagnostic capsule.

An example diagnostic capsule is provided in:

```text
examples/reddit-api/diagnostic-capsule.example.json
```
