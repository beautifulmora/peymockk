"""
Test suite — covers happy paths, edge cases, and error handling.
Run with:  pytest tests/ -v
"""

import pytest
from fastapi.testclient import TestClient

from payments_mock.main import app
from payments_mock.store import store

client = TestClient(app)
HEADERS = {"Authorization": "Bearer sk_test_abc123"}


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def reset_store():
    """Wipe and re-seed the store before each test."""
    store._payments.clear()
    store._refunds.clear()
    store.seed()
    yield


# ── Auth ──────────────────────────────────────────────────────────────────────

class TestAuth:
    def test_missing_header(self):
        r = client.get("/v1/payments")
        assert r.status_code == 401

    def test_invalid_prefix(self):
        r = client.get("/v1/payments", headers={"Authorization": "Bearer live_key_123"})
        assert r.status_code == 401

    def test_valid_key(self):
        r = client.get("/v1/payments", headers=HEADERS)
        assert r.status_code == 200


# ── Payments ──────────────────────────────────────────────────────────────────

class TestPayments:
    def _create(self, card="4242424242424242", amount=1000):
        return client.post(
            "/v1/payments",
            json={"amount": amount, "currency": "usd", "card_number": card},
            headers=HEADERS,
        )

    def test_create_success(self):
        r = self._create()
        assert r.status_code == 201
        body = r.json()
        assert body["status"] == "succeeded"
        assert body["card"]["last4"] == "4242"
        assert body["id"].startswith("pay_")

    def test_create_declined(self):
        r = self._create(card="4000000000000002")
        assert r.status_code == 201
        body = r.json()
        assert body["status"] == "failed"
        assert body["failure_code"] == "card_declined"

    def test_create_insufficient_funds(self):
        r = self._create(card="4000000000009995")
        body = r.json()
        assert body["failure_code"] == "insufficient_funds"

    def test_create_expired_card(self):
        r = self._create(card="4000000000000069")
        body = r.json()
        assert body["failure_code"] == "expired_card"

    def test_get_payment(self):
        pay_id = self._create().json()["id"]
        r = client.get(f"/v1/payments/{pay_id}", headers=HEADERS)
        assert r.status_code == 200
        assert r.json()["id"] == pay_id

    def test_get_not_found(self):
        r = client.get("/v1/payments/pay_doesnotexist", headers=HEADERS)
        assert r.status_code == 404

    def test_list_payments(self):
        r = client.get("/v1/payments", headers=HEADERS)
        assert r.status_code == 200
        body = r.json()
        assert "data" in body
        assert body["count"] == len(body["data"])

    def test_list_pagination(self):
        r = client.get("/v1/payments?limit=2&offset=0", headers=HEADERS)
        assert len(r.json()["data"]) <= 2

    def test_cancel_succeeded_fails(self):
        pay_id = self._create().json()["id"]
        r = client.post(f"/v1/payments/{pay_id}/cancel", headers=HEADERS)
        assert r.status_code == 400  # already succeeded


# ── Refunds ───────────────────────────────────────────────────────────────────

class TestRefunds:
    def _succeeded_payment_id(self):
        r = client.post(
            "/v1/payments",
            json={"amount": 5000, "currency": "usd", "card_number": "4242424242424242"},
            headers=HEADERS,
        )
        return r.json()["id"]

    def test_full_refund(self):
        pay_id = self._succeeded_payment_id()
        r = client.post("/v1/refunds", json={"payment_id": pay_id}, headers=HEADERS)
        assert r.status_code == 201
        body = r.json()
        assert body["amount"] == 5000
        assert body["status"] == "succeeded"

    def test_partial_refund(self):
        pay_id = self._succeeded_payment_id()
        r = client.post("/v1/refunds", json={"payment_id": pay_id, "amount": 2000}, headers=HEADERS)
        assert r.status_code == 201
        assert r.json()["amount"] == 2000

    def test_over_refund_rejected(self):
        pay_id = self._succeeded_payment_id()
        r = client.post("/v1/refunds", json={"payment_id": pay_id, "amount": 9999}, headers=HEADERS)
        assert r.status_code == 400

    def test_double_full_refund_rejected(self):
        pay_id = self._succeeded_payment_id()
        client.post("/v1/refunds", json={"payment_id": pay_id}, headers=HEADERS)
        r = client.post("/v1/refunds", json={"payment_id": pay_id}, headers=HEADERS)
        assert r.status_code == 400

    def test_refund_failed_payment_rejected(self):
        r = client.post(
            "/v1/payments",
            json={"amount": 1000, "currency": "usd", "card_number": "4000000000000002"},
            headers=HEADERS,
        )
        pay_id = r.json()["id"]
        r2 = client.post("/v1/refunds", json={"payment_id": pay_id}, headers=HEADERS)
        assert r2.status_code == 400

    def test_get_refund(self):
        pay_id    = self._succeeded_payment_id()
        refund_id = client.post("/v1/refunds", json={"payment_id": pay_id}, headers=HEADERS).json()["id"]
        r = client.get(f"/v1/refunds/{refund_id}", headers=HEADERS)
        assert r.status_code == 200

    def test_list_refunds_for_payment(self):
        pay_id = self._succeeded_payment_id()
        client.post("/v1/refunds", json={"payment_id": pay_id, "amount": 1000}, headers=HEADERS)
        r = client.get(f"/v1/refunds/payment/{pay_id}", headers=HEADERS)
        assert r.status_code == 200
        assert r.json()["count"] == 1


# ── Webhooks ──────────────────────────────────────────────────────────────────

class TestWebhooks:
    def test_register_and_list(self):
        r = client.post(
            "/v1/webhooks",
            json={"url": "https://example.com/hook"},
            headers=HEADERS,
        )
        assert r.status_code == 201
        assert r.json()["id"].startswith("wh_")

        r2 = client.get("/v1/webhooks", headers=HEADERS)
        assert any(w["url"] == "https://example.com/hook" for w in r2.json())

    def test_simulate_event(self):
        pay_id = client.post(
            "/v1/payments",
            json={"amount": 100, "currency": "usd", "card_number": "4242424242424242"},
            headers=HEADERS,
        ).json()["id"]

        client.post("/v1/webhooks", json={"url": "https://example.com/hook"}, headers=HEADERS)

        r = client.post(
            "/v1/webhooks/simulate",
            json={"payment_id": pay_id, "event_type": "payment.succeeded"},
            headers=HEADERS,
        )
        assert r.status_code == 200
        body = r.json()
        assert body["event"]["type"] == "payment.succeeded"
        assert "signature" in body
