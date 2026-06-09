# Example: Required status coverage

This catalog covers status examples that are easy to mishandle in repairable-error systems: 401, 403, 404, hidden-existence 404, and 500. The examples are deliberately conservative about information disclosure.

## 401: refreshable authorization context

The request body is valid, but the access token is expired. The request payload should not be changed; credentials should be refreshed.

```json
{
  "type": "https://api.example.com/problems/authorization-context-mismatch",
  "title": "Authentication context is no longer valid.",
  "status": 401,
  "detail": "Authentication must be refreshed before this operation can continue.",
  "instance": "urn:diagnostic:diag_auth_001",
  "rec_version": "0.1.0",
  "operation_id": "createInvoice",
  "diagnostic_id": "diag_auth_001",
  "classification": "authorization_context_mismatch",
  "domain_code": "token_expired",
  "request_repairable": true,
  "agent_policy": "refresh_authorization",
  "retry_policy": {
    "can_retry": true,
    "same_request": true,
    "idempotency_required": true
  },
  "repair_plan": [
    {
      "action": "refresh_authorization",
      "operation_id": "refreshToken",
      "reason": "Refresh the authentication context, then retry the same request payload."
    }
  ],
  "caller_instruction": "Refresh authentication and retry the same request payload. Do not change invoice fields.",
  "safe_debug_summary": "Authorization failed before business processing.",
  "analysis_mode": "deterministic"
}
```

## 403: authorization denied, existence not disclosed

The caller is authenticated but lacks permission. The public response does not reveal whether the target resource exists.

```json
{
  "type": "https://api.example.com/problems/authorization-context-mismatch",
  "title": "The caller is not authorized for this operation.",
  "status": 403,
  "detail": "The current authorization context does not permit this operation.",
  "instance": "urn:diagnostic:diag_authz_001",
  "rec_version": "0.1.0",
  "operation_id": "deleteInvoice",
  "diagnostic_id": "diag_authz_001",
  "classification": "authorization_context_mismatch",
  "request_repairable": false,
  "agent_policy": "report_diagnostic_id",
  "retry_policy": {
    "can_retry": false
  },
  "repair_plan": [
    {
      "action": "report_diagnostic_id",
      "reason": "A privileged user or operator can investigate using the diagnostic ID."
    }
  ],
  "caller_instruction": "Do not retry or change request parameters. Report the diagnostic ID if access is expected.",
  "safe_debug_summary": "Authorization denied. Resource-existence details were not exposed.",
  "analysis_mode": "deterministic"
}
```

## 404: visible resource not found

The caller is authorized to know that the resource space exists, and the referenced customer ID is not found or was mistyped.

```json
{
  "type": "https://api.example.com/problems/resource-not-found",
  "title": "Referenced resource was not found.",
  "status": 404,
  "detail": "The customer reference does not identify a visible customer resource.",
  "instance": "urn:diagnostic:diag_customer_404",
  "rec_version": "0.1.0",
  "operation_id": "createInvoice",
  "diagnostic_id": "diag_customer_404",
  "classification": "resource_not_found",
  "domain_code": "customer_not_found",
  "request_repairable": true,
  "agent_policy": "ask_user",
  "retry_policy": {
    "can_retry": true,
    "same_request": false,
    "idempotency_required": true
  },
  "invalid_fields": [
    {
      "path": "/customerId",
      "problem": "resource_not_found",
      "expected": "visible customer identifier"
    }
  ],
  "repair_plan": [
    {
      "action": "ask_user",
      "path": "/customerId",
      "reason": "A different visible customer identifier is required."
    }
  ],
  "caller_instruction": "Ask for or select a visible customerId before retrying. Retrying the same customerId is expected to fail.",
  "safe_debug_summary": "Visible resource reference was not found.",
  "analysis_mode": "deterministic"
}
```

## 404: authorization hidden as not found

Local policy may choose a 404-shaped response instead of 403 when confirming resource existence would disclose private information.

```json
{
  "type": "https://api.example.com/problems/not-found",
  "title": "Resource was not found.",
  "status": 404,
  "detail": "No resource is available for this request.",
  "instance": "urn:diagnostic:diag_hidden_404",
  "rec_version": "0.1.0",
  "operation_id": "getPrivateInvoice",
  "diagnostic_id": "diag_hidden_404",
  "classification": "authorization_context_mismatch",
  "request_repairable": false,
  "agent_policy": "report_diagnostic_id",
  "retry_policy": {
    "can_retry": false
  },
  "repair_plan": [
    {
      "action": "report_diagnostic_id",
      "reason": "Resource-existence details are not exposed publicly."
    }
  ],
  "caller_instruction": "Do not infer whether the resource exists. Report the diagnostic ID if access is expected.",
  "safe_debug_summary": "Existence-hiding policy applied.",
  "analysis_mode": "deterministic"
}
```

## 500: likely service bug

A safe REC response for internal failures should degrade to useful correlation without exposing internals.

```json
{
  "type": "https://api.example.com/problems/internal-error",
  "title": "Internal service error.",
  "status": 500,
  "detail": "An internal error occurred.",
  "instance": "urn:diagnostic:diag_internal_001",
  "rec_version": "0.1.0",
  "operation_id": "createInvoice",
  "diagnostic_id": "diag_internal_001",
  "classification": "service_bug_likely",
  "request_repairable": false,
  "agent_policy": "report_diagnostic_id",
  "retry_policy": {
    "can_retry": false
  },
  "repair_plan": [
    {
      "action": "report_diagnostic_id",
      "reason": "The service owner can investigate this internal failure using the diagnostic ID."
    }
  ],
  "caller_instruction": "Do not change request parameters to work around this error. Report the diagnostic ID.",
  "safe_debug_summary": "Internal failure after request validation. Stack trace omitted.",
  "analysis_mode": "fallback"
}
```
