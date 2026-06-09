# Agent recovery benchmark design

This directory is a benchmark scaffold, not empirical evidence. The purpose is to test whether REC improves agent and human recovery compared with strong baselines.

## Conditions

* **C0: Vague errors** — `{"error":"Bad Request"}`.
* **C1: Framework validation errors** — normal framework output such as JSON Schema or FastAPI-style validation errors.
* **C2: RFC 9457 Problem Details** — `type`, `title`, `status`, `detail`, `instance` only.
* **C3: Deterministic REC** — REC produced by deterministic validators and rule tables.
* **C4: LLM-assisted REC** — REC produced through sanitized capsule, LLM proposal, schema validation, and policy gate.

## Task families

Use mock APIs where the ground truth is known:

* invoice creation,
* Reddit thread fetch,
* calendar event creation,
* payment authorization/capture,
* shipping/order workflow.

## Failure injections

Cover the REC taxonomy:

* missing field,
* alias field,
* wrong type,
* invalid enum,
* semantic precondition missing,
* visible 404,
* hidden-existence 404,
* authorization refresh,
* version skew,
* rate limit with `Retry-After`,
* dependency 503,
* deterministic internal 500,
* suspicious request.

Include trap cases where the correct action is retry unchanged and any request-parameter mutation is scored as failure.

## Metrics

| Metric | Definition |
|---|---|
| Task recovery rate | Failed first calls followed by eventual task success. |
| Wrong-retry rate | Transient failures where the agent mutated request parameters. |
| Retries until success | Attempts after first failure. |
| Token cost | Total model tokens consumed during recovery. |
| Latency | End-to-end recovery time and server-side analyzer latency. |
| Human debugging time | Time to identify cause and corrected request. |
| Classification accuracy | Analyzer class versus injected ground truth. |
| Secret-leakage rate | Canary secrets appearing in public REC fields. |
| Unsafe suggestion rate | Unsafe candidate responses accepted by the policy gate. |

## Ablations

At minimum, run:

* REC without `same_request`,
* REC without `caller_instruction`,
* `caller_instruction` prose without structured REC fields,
* deterministic REC versus LLM-assisted REC.

## Reporting requirements

Report null results honestly. If a strong Problem Details baseline performs as well as REC, the extra schema complexity is not justified for that task class. Also report latency and response-size overhead.
