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

## Scenario 1: wrong parameter name and missing required value

Caller sends:

```json
{
  "customer": {
    "name": "ACME GmbH"
  },
  "amount": 199.9,
  "currencyCode": "EUR"
}
```

REC response:

```json
{
  "type": "https://api.example.com/problems/caller-contract-violation",
  "title": "Request does not match the operation contract.",
  "status": 422,
  "detail": "The request is missing 'customerId' and used 'currencyCode' instead of 'currency'.",
  "instance": "urn:diagnostic:diag_invoice_001",
  "rec_version": "1.0",
  "operation_id": "createInvoice",
  "diagnostic_id": "diag_invoice_001",
  "classification": "caller_contract_violation",
  "repairable": true,
  "confidence": 0.91,
  "retry_policy": {
    "can_retry": true,
    "same_request": false,
    "idempotency_required": true
  },
  "invalid_fields": [
    {
      "path": "$.customerId",
      "problem": "missing_required_field",
      "expected": "string"
    },
    {
      "path": "$.currencyCode",
      "problem": "alias_field",
      "suggestion": "Use '$.currency' instead."
    }
  ],
  "repair_patch": [
    {
      "op": "move",
      "from": "/currencyCode",
      "path": "/currency"
    }
  ],
  "repair_plan": [
    {
      "action": "provide_missing_value",
      "path": "$.customerId",
      "value_hint": "Use the stable customer identifier.",
      "reason": "The invoice operation requires a customerId."
    }
  ],
  "correct_request_example": {
    "customerId": "cus_123",
    "amount": 199.9,
    "currency": "EUR",
    "idempotencyKey": "idem_abc123"
  },
  "caller_instruction": "Retry with customerId, amount, and currency. Do not send a customer object and do not use currencyCode.",
  "safe_debug_summary": "Request failed schema validation before invoice creation.",
  "analysis_mode": "hybrid"
}
```

## Scenario 2: semantic precondition missing

Caller sends:

```json
{
  "orderId": "ord_123",
  "carrier": "DHL"
}
```

The schema is valid, but the order is not paid.

REC response:

```json
{
  "type": "https://api.example.com/problems/semantic-precondition-missing",
  "title": "A required business precondition is missing.",
  "status": 409,
  "detail": "The order cannot be shipped because payment has not been captured.",
  "instance": "urn:diagnostic:diag_ship_001",
  "rec_version": "1.0",
  "operation_id": "shipOrder",
  "diagnostic_id": "diag_ship_001",
  "classification": "semantic_precondition_missing",
  "domain_code": "payment_not_captured",
  "repairable": true,
  "confidence": 0.88,
  "retry_policy": {
    "can_retry": true,
    "same_request": false,
    "idempotency_required": true
  },
  "repair_plan": [
    {
      "action": "call_prerequisite_operation",
      "operation_id": "capturePayment",
      "reason": "Payment must be captured before shipping can be created."
    }
  ],
  "caller_instruction": "Call capturePayment for this order before retrying shipOrder.",
  "safe_debug_summary": "Business precondition failed after request validation.",
  "analysis_mode": "deterministic"
}
```

## Scenario 3: dependency failure

The request is valid, but the inventory dependency is unavailable.

REC response:

```json
{
  "type": "https://api.example.com/problems/dependency-failure",
  "title": "A downstream dependency failed.",
  "status": 503,
  "detail": "The request format appears valid. The operation failed because a required dependency is unavailable.",
  "instance": "urn:diagnostic:diag_inventory_001",
  "rec_version": "1.0",
  "operation_id": "reserveInventory",
  "diagnostic_id": "diag_inventory_001",
  "classification": "dependency_failure",
  "repairable": false,
  "confidence": 0.86,
  "retry_policy": {
    "can_retry": true,
    "same_request": true,
    "retry_after_ms": 30000,
    "idempotency_required": true
  },
  "repair_plan": [
    {
      "action": "retry_later",
      "reason": "This failure is caused by a dependency outage, not by request parameters."
    }
  ],
  "caller_instruction": "Retry later with the same request and the same idempotency key. Do not invent alternative parameters.",
  "safe_debug_summary": "Dependency failure after request validation.",
  "analysis_mode": "fallback"
}
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
