# Test Execution Report — LogiQlink Order API

## Execution summary

- **Test framework:** pytest
- **Runtime:** Python 3.13.5
- **Command:** `python -m pytest -v`
- **Result:** 33 tests collected; **30 passed, 3 failed**
- **Interpretation:** The three failures are reproducible deviations from the supplied `API_CONTRACT.md`. They are retained as failing regression tests intentionally; the API fixture was not modified.

## Coverage

| Area | Coverage |
|---|---|
| Health | Public health endpoint and JSON response |
| Order creation | NOTEBOOK and MOUSE pricing, response fields and generated ID |
| Validation | SKU, email, request ID, malformed JSON, quantity boundaries and invalid values |
| Authentication | Missing, empty, and incorrect bearer token |
| Retrieval | Existing and missing order |
| State transitions | Ship, repeat ship, cancel, repeat cancel, cancel after shipment, missing order |
| Idempotency | Repeated request ID returns original order |
| Listing | Unfiltered list, valid status filter, invalid status filter |
| Test isolation | Reset endpoint before every test; unique request IDs |

## Defects found

### DEF-001 — Quantity zero is accepted

- **Endpoint:** `POST /orders`
- **Reproduction:** Submit a valid order body with `quantity: 0`.
- **Expected (contract):** HTTP 400 because quantity must be an integer from 1 through 5.
- **Actual:** HTTP 201; an order is created with quantity 0 and total 0.
- **Failing test:** `test_invalid_quantity_is_rejected[0]`
- **Risk:** Invalid zero-quantity orders can enter the order lifecycle and create misleading records.

### DEF-002 — Shipped orders can be cancelled

- **Endpoint:** `POST /orders/{id}/cancel`
- **Reproduction:** Create an order, ship it, then cancel it.
- **Expected (contract):** HTTP 409 with `{"error":"invalid_transition"}`.
- **Actual:** HTTP 200; the shipped order transitions to `cancelled`.
- **Failing test:** `test_shipped_order_cannot_be_cancelled`
- **Risk:** Order state can contradict fulfillment reality and downstream inventory/shipping records.

### DEF-003 — List status filter is ignored

- **Endpoint:** `GET /orders?status=created`
- **Reproduction:** Create two orders, ship one, then request the list with `status=created`.
- **Expected (contract):** Only created orders are returned and `count` equals the filtered list length (1 in this scenario).
- **Actual:** Both orders are returned and `count` is 2.
- **Failing test:** `test_list_status_filter_returns_only_matching_orders`
- **Risk:** Consumers relying on status-filtered results may process orders in the wrong state.

## CI behavior and team recommendation

The GitHub Actions workflow runs the same contract suite against the supplied local fixture. It is expected to report a failed job while these three defects remain. In a production team, I would link each failing test to a tracked defect, keep the contract regression tests enabled, and make the release gate policy explicit. If the team needs a green pipeline for unrelated changes, the defects can be tracked with a clearly visible quarantine/known-failure mechanism and an owner/expiry date; they should not be silently deleted or have their expected behavior weakened. Once the API fixes are merged, the tests should pass and the quarantine should be removed.

## Risks and areas not covered

- No concurrency/race testing for simultaneous order creation or duplicate request IDs.
- No load, stress, soak, or latency testing.
- No exhaustive malformed content-type, oversized body, or unusual Unicode input testing.
- No persistence/restart behavior test; the contract says state lasts only for the server process lifetime.
- No deployment, database, or external integration tests; the supplied service is an in-memory local fixture.
- The email validation cases cover representative invalid values, not the full email-address specification.

## Conclusion

The suite validates the principal documented workflows and identifies three intentional contract defects in the provided implementation. The failing assertions are evidence of product behavior that does not meet the assessment's source-of-truth contract.
