"""
/v1/webhooks — register endpoints and simulate event delivery.

In a real system you would sign payloads (HMAC-SHA256) and retry on failure.
This mock logs delivery attempts and returns a simulated result.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, HttpUrl

from ..auth import verify_api_key
from ..models import Payment
from ..store import store

router = APIRouter()

# ── In-memory webhook registry ────────────────────────────────────────────────

_webhooks:  dict[str, dict] = {}
_deliveries: list[dict]     = []

WEBHOOK_SECRET = "whsec_mock_secret_key"


# ── Schemas ───────────────────────────────────────────────────────────────────

class WebhookCreate(BaseModel):
    url:    str
    events: list[str] = ["payment.succeeded", "payment.failed", "refund.created"]
    description: Optional[str] = None


class WebhookOut(BaseModel):
    id:          str
    url:         str
    events:      list[str]
    description: Optional[str]
    created_at:  datetime


class SimulateEvent(BaseModel):
    payment_id: str
    event_type: str = "payment.succeeded"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _build_event(event_type: str, payment: Payment) -> dict:
    return {
        "id":         f"evt_{uuid.uuid4().hex[:24]}",
        "object":     "event",
        "type":       event_type,
        "created":    datetime.now(timezone.utc).isoformat(),
        "data":       {"object": payment.model_dump(mode="json")},
    }


def _sign_payload(payload: str) -> str:
    timestamp = int(datetime.now(timezone.utc).timestamp())
    signed    = f"{timestamp}.{payload}"
    sig       = hmac.new(WEBHOOK_SECRET.encode(), signed.encode(), hashlib.sha256).hexdigest()
    return f"t={timestamp},v1={sig}"


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("", status_code=status.HTTP_201_CREATED, response_model=WebhookOut)
def register_webhook(
    body: WebhookCreate,
    api_key: str = Depends(verify_api_key),
) -> WebhookOut:
    """Register a URL to receive webhook events."""
    wh_id = f"wh_{uuid.uuid4().hex[:16]}"
    record = {
        "id":          wh_id,
        "url":         body.url,
        "events":      body.events,
        "description": body.description,
        "created_at":  datetime.now(timezone.utc),
    }
    _webhooks[wh_id] = record
    return WebhookOut(**record)


@router.get("", response_model=list[WebhookOut])
def list_webhooks(api_key: str = Depends(verify_api_key)):
    """List all registered webhook endpoints."""
    return [WebhookOut(**w) for w in _webhooks.values()]


@router.delete("/{webhook_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_webhook(webhook_id: str, api_key: str = Depends(verify_api_key)):
    if webhook_id not in _webhooks:
        raise HTTPException(status_code=404, detail=f"Webhook '{webhook_id}' not found.")
    del _webhooks[webhook_id]


@router.post("/simulate", status_code=status.HTTP_200_OK)
def simulate_event(
    body: SimulateEvent,
    api_key: str = Depends(verify_api_key),
) -> dict:
    """
    Simulate dispatching a webhook event for a given payment.
    Returns the event payload and a mock delivery log — no real HTTP calls are made.
    """
    payment = store.get_payment(body.payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail=f"Payment '{body.payment_id}' not found.")

    event   = _build_event(body.event_type, payment)
    payload = json.dumps(event, default=str)
    signature = _sign_payload(payload)

    deliveries = []
    for wh in _webhooks.values():
        if body.event_type in wh["events"]:
            delivery = {
                "webhook_id":  wh["id"],
                "url":         wh["url"],
                "status":      "delivered",
                "http_status": 200,
                "duration_ms": 42,
                "timestamp":   datetime.now(timezone.utc).isoformat(),
            }
            _deliveries.append(delivery)
            deliveries.append(delivery)

    return {
        "event":      event,
        "signature":  signature,
        "deliveries": deliveries,
        "note": "No real HTTP requests were made. This is a simulation.",
    }


@router.get("/deliveries", response_model=list[dict])
def list_deliveries(api_key: str = Depends(verify_api_key)):
    """Return the log of all simulated webhook deliveries."""
    return _deliveries
