# Order API — Expected Contract (source of truth)

Base: `http://127.0.0.1:8765`  
All requests below, except `GET /health`, require `Authorization: Bearer qa-assessment-token`.

All bodies are JSON. Successful responses have `Content-Type: application/json`.

## Endpoints

### `GET /health`
- **200**: `{"status":"ok"}`

### `POST /test/reset`
- **200**: `{"reset":true}`; clears all orders and request IDs. For test isolation only.

### `POST /orders`
Example body:
```json
{"sku":"NOTEBOOK","quantity":2,"customerEmail":"qa@example.com","requestId":"req-unique-001"}
```
Validation:
- `sku`: exactly `NOTEBOOK` (₹150 each) or `MOUSE` (₹800 each).
- `quantity`: **integer between 1 and 5 inclusive**.
- `customerEmail`: non-empty, syntactically plausible email.
- `requestId`: non-empty string; use a unique value for a fresh order.
- Malformed JSON or invalid fields: **400**, with an `error` key.

New order: **201** and:
```json
{"id":"ord-0001","sku":"NOTEBOOK","quantity":2,"customerEmail":"qa@example.com","requestId":"req-unique-001","total":300,"status":"created"}
```
The `id` is server-generated. `total` is integer INR amount.

**Idempotency:** repeating the same `requestId` returns **200** with the *original* order, without creating a new one. Do not assume ID values across resets or test cases.

### `GET /orders/{id}`
- Existing: **200** and the order object.
- Missing: **404** with `{"error":"not_found"}`.

### `POST /orders/{id}/ship`
- `created → shipped`: **200** and updated order object.
- Any other status: **409** with `{"error":"invalid_transition"}`.
- Missing order: **404**.

### `POST /orders/{id}/cancel`
- `created → cancelled`: **200** and updated order object.
- **Shipped or already cancelled:** **409** (`invalid_transition`).
- Missing order: **404**.

### `GET /orders?status={status}`
- Without a status parameter: **200**, `{"orders":[...],"count":N}` for all orders.
- With `status=created`, `shipped`, or `cancelled`: **200** with only matching orders, and `count` matching the returned list length.
- Invalid status: **400** with an `error` key.

## General behavior
- Missing or invalid auth token: **401** with `{"error":"unauthorized"}`.
- State persists only while the local server process is running, unless explicitly reset.
- The API is a deliberately simplified assessment service, not production software. **Implementation may violate this contract.** Your assertions should reflect the contract.
