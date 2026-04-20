# Payments Mock API

A clean, production-style mock payment service for development and testing.  
Mirrors the Stripe API design so your integration code works against either.

---

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run the server
python -m payments_mock.main
# → http://localhost:8000
# → http://localhost:8000/docs   (Swagger UI)
```

---

## Authentication

All endpoints require a Bearer token that starts with `sk_test_`:

```
Authorization: Bearer sk_test_any_value_works
```

---

## Magic Card Numbers

| Card Number          | Outcome              | Failure Code         |
|----------------------|----------------------|----------------------|
| `4242424242424242`   | ✅ Succeeded         | —                    |
| `5555555555554444`   | ✅ Succeeded (MC)    | —                    |
| `4000000000000002`   | ❌ Failed            | `card_declined`      |
| `4000000000009995`   | ❌ Failed            | `insufficient_funds` |
| `4000000000000069`   | ❌ Failed            | `expired_card`       |
| `4000000000000127`   | ❌ Failed            | `incorrect_cvc`      |
| *any other number*   | ✅ Succeeded         | —                    |

---

## API Reference

### Payments

| Method | Path                           | Description              |
|--------|--------------------------------|--------------------------|
| POST   | `/v1/payments`                 | Create a payment         |
| GET    | `/v1/payments`                 | List payments            |
| GET    | `/v1/payments/{id}`            | Get a payment            |
| POST   | `/v1/payments/{id}/cancel`     | Cancel a payment         |

**Create a payment**
```bash
curl -X POST http://localhost:8000/v1/payments \
  -H "Authorization: Bearer sk_test_abc" \
  -H "Content-Type: application/json" \
  -d '{
    "amount": 4999,
    "currency": "usd",
    "card_number": "4242424242424242",
    "description": "Order #1042"
  }'
```

### Refunds

| Method | Path                                    | Description                    |
|--------|-----------------------------------------|--------------------------------|
| POST   | `/v1/refunds`                           | Create a refund                |
| GET    | `/v1/refunds/{id}`                      | Get a refund                   |
| GET    | `/v1/refunds/payment/{payment_id}`      | List refunds for a payment     |

**Full refund**
```bash
curl -X POST http://localhost:8000/v1/refunds \
  -H "Authorization: Bearer sk_test_abc" \
  -H "Content-Type: application/json" \
  -d '{"payment_id": "pay_abc123"}'
```

**Partial refund**
```bash
curl -X POST http://localhost:8000/v1/refunds \
  -H "Authorization: Bearer sk_test_abc" \
  -H "Content-Type: application/json" \
  -d '{"payment_id": "pay_abc123", "amount": 2000}'
```

### Webhooks

| Method | Path                      | Description                    |
|--------|---------------------------|--------------------------------|
| POST   | `/v1/webhooks`            | Register a webhook endpoint    |
| GET    | `/v1/webhooks`            | List registered webhooks       |
| DELETE | `/v1/webhooks/{id}`       | Delete a webhook               |
| POST   | `/v1/webhooks/simulate`   | Simulate event delivery        |
| GET    | `/v1/webhooks/deliveries` | View delivery log              |

### Other

| Method | Path           | Description         |
|--------|----------------|---------------------|
| GET    | `/health`      | Health check        |
| GET    | `/v1/balance`  | Mock account balance|

---

## Running Tests

```bash
pytest tests/ -v
```

---

## Project Structure

```
payments_mock/
├── main.py          # App factory, middleware, router registration
├── models.py        # Pydantic schemas (Payment, Refund, enums)
├── store.py         # In-memory store (swap for DB here)
├── auth.py          # API key dependency
├── simulation.py    # Magic card number → outcome mapping
└── routers/
    ├── payments.py  # POST/GET /v1/payments
    ├── refunds.py   # POST/GET /v1/refunds
    └── webhooks.py  # POST/GET /v1/webhooks + simulate

tests/
└── test_api.py      # Full test suite (auth, payments, refunds, webhooks)
```

---

## Extending

**Swap in a real database** — `store.py` is the only file that touches persistence.  
Replace `_payments` / `_refunds` dicts with SQLAlchemy calls and nothing else changes.

**Add 3D Secure simulation** — Add a `requires_action` status and a `/v1/payments/{id}/confirm` endpoint.

**Real webhook delivery** — In `routers/webhooks.py`, replace the mock delivery log with `httpx.AsyncClient.post()` calls and an HMAC-SHA256 signature header.
