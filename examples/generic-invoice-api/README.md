# Example: Generic invoice API

This example shows REC in a business API, independent of Reddit.

## Operation

```text
POST /invoices
```

Expected request:

```json
{
  "customerId": "cus_123",
  "amount": 199.9,
  "currency": "EUR",
  "idempotencyKey": "idem_abc123"
}
```

## Scenarios

### Scenario 1: wrong parameter name and missing required value

The caller sends:

```json
{
  "customer": {
    "name": "ACME GmbH"
  },
  "amount": 199.9,
  "currencyCode": "EUR"
}
```

The REC response is provided in:

```text
examples/generic-invoice-api/valid-missing-customer-id.rec.json
```

This example intentionally combines:

- one deterministic mechanical fix, represented by `repair_patch`;
- one missing business value, represented by `repair_plan`.

### Scenario 2: semantic precondition missing

The caller sends a structurally valid shipping request, but the order is not paid.

The REC response is provided in:

```text
examples/generic-invoice-api/valid-semantic-precondition.rec.json
```

### Scenario 3: dependency failure

The request is valid, but the inventory dependency is unavailable.

The REC response is provided in:

```text
examples/generic-invoice-api/valid-dependency-failure.rec.json
```

## Lessons

REC helps distinguish:

```text
Change your request.
Retry later unchanged.
Call a prerequisite operation.
Report the diagnostic ID.
Do not retry blindly.
```

This distinction is valuable for humans and essential for LLM agents.
