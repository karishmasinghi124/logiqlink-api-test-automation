"""Contract-based regression tests for the LogiQlink Order API."""
import json
import os
import urllib.error
import urllib.request
import uuid

import pytest

BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:8765")
TOKEN = os.getenv("API_TOKEN", "qa-assessment-token")


def request(method, path, payload=None, token=TOKEN):
    headers = {}
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(BASE_URL + path, data=data, headers=headers, method=method)
    try:
        response = urllib.request.urlopen(req, timeout=5)
    except urllib.error.HTTPError as exc:
        response = exc
    body = response.read()
    try:
        parsed = json.loads(body.decode("utf-8")) if body else None
    except json.JSONDecodeError:
        parsed = None
    return response.status, parsed, response.headers.get("Content-Type", "")


def new_order(**overrides):
    payload = {
        "sku": "NOTEBOOK",
        "quantity": 2,
        "customerEmail": "qa@example.com",
        "requestId": f"test-{uuid.uuid4()}",
    }
    payload.update(overrides)
    return payload


@pytest.fixture(autouse=True)
def isolate_api_state():
    status, body, _ = request("POST", "/test/reset")
    assert status == 200
    assert body == {"reset": True}
    yield


def create_order(**overrides):
    payload = new_order(**overrides)
    return payload, request("POST", "/orders", payload)


def test_health_is_public_and_returns_ok():
    status, body, content_type = request("GET", "/health", token=None)
    assert status == 200
    assert body == {"status": "ok"}
    assert "application/json" in content_type


def test_create_notebook_calculates_total():
    payload, (status, body, content_type) = create_order()
    assert status == 201
    assert "application/json" in content_type
    assert body["id"].startswith("ord-")
    assert body["sku"] == payload["sku"]
    assert body["quantity"] == payload["quantity"]
    assert body["customerEmail"] == payload["customerEmail"]
    assert body["requestId"] == payload["requestId"]
    assert body["total"] == 300
    assert body["status"] == "created"


def test_create_mouse_calculates_total():
    _, (status, body, _) = create_order(sku="MOUSE", quantity=3)
    assert status == 201
    assert body["total"] == 2400


@pytest.mark.parametrize("quantity", [1, 5])
def test_quantity_boundaries_are_accepted(quantity):
    _, (status, body, _) = create_order(quantity=quantity)
    assert status == 201
    assert body["quantity"] == quantity


@pytest.mark.parametrize("quantity", [0, 6, -1, 1.5, True])
def test_invalid_quantity_is_rejected(quantity):
    _, (status, body, _) = create_order(quantity=quantity)
    assert status == 400
    assert "error" in body


@pytest.mark.parametrize("sku", ["PENCIL", "", None])
def test_invalid_sku_is_rejected(sku):
    _, (status, body, _) = create_order(sku=sku)
    assert status == 400
    assert "error" in body


@pytest.mark.parametrize("email", ["", "not-an-email", "qa@", None])
def test_invalid_customer_email_is_rejected(email):
    _, (status, body, _) = create_order(customerEmail=email)
    assert status == 400
    assert "error" in body


def test_missing_request_id_is_rejected():
    payload = new_order()
    del payload["requestId"]
    status, body, _ = request("POST", "/orders", payload)
    assert status == 400
    assert "error" in body


def test_malformed_json_is_rejected():
    req = urllib.request.Request(
        BASE_URL + "/orders",
        data=b'{"sku":',
        headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        response = urllib.request.urlopen(req, timeout=5)
    except urllib.error.HTTPError as exc:
        response = exc
    body = json.loads(response.read().decode("utf-8"))
    assert response.status == 400
    assert "error" in body


@pytest.mark.parametrize("token", [None, "wrong-token", ""])
def test_missing_or_invalid_auth_is_rejected(token):
    status, body, _ = request("GET", "/orders", token=token)
    assert status == 401
    assert body == {"error": "unauthorized"}


def test_get_existing_order_returns_created_order():
    payload, (status, created, _) = create_order()
    assert status == 201
    get_status, fetched, _ = request("GET", f"/orders/{created['id']}")
    assert get_status == 200
    assert fetched == created
    assert fetched["requestId"] == payload["requestId"]


def test_get_missing_order_returns_404():
    status, body, _ = request("GET", "/orders/ord-9999")
    assert status == 404
    assert body == {"error": "not_found"}


def test_created_order_can_be_shipped_once():
    _, (_, created, _) = create_order()
    status, shipped, _ = request("POST", f"/orders/{created['id']}/ship")
    assert status == 200
    assert shipped["status"] == "shipped"
    second_status, body, _ = request("POST", f"/orders/{created['id']}/ship")
    assert second_status == 409
    assert body == {"error": "invalid_transition"}


def test_created_order_can_be_cancelled():
    _, (_, created, _) = create_order()
    status, cancelled, _ = request("POST", f"/orders/{created['id']}/cancel")
    assert status == 200
    assert cancelled["status"] == "cancelled"


def test_shipped_order_cannot_be_cancelled():
    _, (_, created, _) = create_order()
    ship_status, shipped, _ = request("POST", f"/orders/{created['id']}/ship")
    assert ship_status == 200 and shipped["status"] == "shipped"
    cancel_status, body, _ = request("POST", f"/orders/{created['id']}/cancel")
    assert cancel_status == 409
    assert body == {"error": "invalid_transition"}


def test_cannot_cancel_already_cancelled_order():
    _, (_, created, _) = create_order()
    request("POST", f"/orders/{created['id']}/cancel")
    status, body, _ = request("POST", f"/orders/{created['id']}/cancel")
    assert status == 409
    assert body == {"error": "invalid_transition"}


def test_transition_for_missing_order_returns_404():
    status, body, _ = request("POST", "/orders/ord-9999/ship")
    assert status == 404
    assert body == {"error": "not_found"}


def test_same_request_id_is_idempotent():
    payload = new_order()
    first_status, first, _ = request("POST", "/orders", payload)
    second_status, second, _ = request("POST", "/orders", payload)
    assert first_status == 201
    assert second_status == 200
    assert second == first


def test_list_without_filter_returns_all_orders_and_count():
    create_order()
    create_order(sku="MOUSE", quantity=1)
    status, body, _ = request("GET", "/orders")
    assert status == 200
    assert body["count"] == 2
    assert len(body["orders"]) == 2


def test_list_status_filter_returns_only_matching_orders():
    _, (_, created, _) = create_order()
    _, (_, another, _) = create_order()
    request("POST", f"/orders/{another['id']}/ship")
    status, body, _ = request("GET", "/orders?status=created")
    assert status == 200
    assert body["count"] == 1
    assert len(body["orders"]) == 1
    assert all(order["status"] == "created" for order in body["orders"])
    assert body["orders"][0]["id"] == created["id"]


def test_invalid_status_filter_is_rejected():
    status, body, _ = request("GET", "/orders?status=pending")
    assert status == 400
    assert "error" in body
