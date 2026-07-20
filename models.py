from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


# ── Enums ────────────────────────────────────────────────────────────────────

class PaymentStatus(str, Enum):
    PENDING    = "pending"
    PROCESSING = "processing"
    SUCCEEDED  = "succeeded"
    FAILED     = "failed"
    CANCELED   = "canceled"


class RefundStatus(str, Enum):
    PENDING   = "pending"
    SUCCEEDED = "succeeded"
    FAILED    = "failed"


class Currency(str, Enum):
    USD = "usd"
    EUR = "eur"
    GBP = "gbp"


class FailureCode(str, Enum):
    CARD_DECLINED          = "card_declined"
    INSUFFICIENT_FUNDS     = "insufficient_funds"
    EXPIRED_CARD           = "expired_card"
    INCORRECT_CVC          = "incorrect_cvc"
    DO_NOT_HONOR           = "do_not_honor"


# ── Card helpers ──────────────────────────────────────────────────────────────

class CardDetails(BaseModel):
    """Stripped-down card representation (never store raw PAN in real life)."""
    brand:       str = Field(..., examples=["visa", "mastercard"])
    last4:       str = Field(..., min_length=4, max_length=4)
    exp_month:   int = Field(..., ge=1, le=12)
    exp_year:    int = Field(..., ge=2024)
    fingerprint: str = Field(default_factory=lambda: uuid.uuid4().hex[:16])


# ── Payment ───────────────────────────────────────────────────────────────────

class PaymentCreate(BaseModel):
    """Fields required to initiate a payment."""
    amount:      int      = Field(..., gt=0, description="Amount in smallest currency unit (e.g. cents).")
    currency:    Currency = Field(default=Currency.USD)
    description: Optional[str] = Field(None, max_length=512)
    metadata:    dict[str, str] = Field(default_factory=dict)

    # Simulated card number triggers specific outcomes (Stripe-style)
    card_number: str = Field(..., min_length=13, max_length=19, examples=["4242424242424242"])

    @field_validator("card_number")
    @classmethod
    def strip_spaces(cls, v: str) -> str:
        return v.replace(" ", "")


class Payment(BaseModel):
    """Full payment object returned by the API."""
    id:          str           = Field(default_factory=lambda: f"pay_{uuid.uuid4().hex[:24]}")
    object:      str           = "payment"
    amount:      int
    currency:    Currency
    status:      PaymentStatus = PaymentStatus.PENDING
    description: Optional[str] = None
    metadata:    dict[str, str] = Field(default_factory=dict)
    card:        Optional[CardDetails] = None
    failure_code:    Optional[FailureCode] = None
    failure_message: Optional[str]        = None
    created_at:  datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at:  datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ── Refund ────────────────────────────────────────────────────────────────────

class RefundCreate(BaseModel):
    payment_id: str
    amount:     Optional[int] = Field(None, gt=0, description="Partial refund amount; omit for full refund.")
    reason:     Optional[str] = Field(None, examples=["duplicate", "fraudulent", "customer_request"])


class Refund(BaseModel):
    id:         str          = Field(default_factory=lambda: f"re_{uuid.uuid4().hex[:24]}")
    object:     str          = "refund"
    payment_id: str
    amount:     int
    currency:   Currency
    status:     RefundStatus = RefundStatus.PENDING
    reason:     Optional[str] = None
    created_at: datetime     = Field(default_factory=lambda: datetime.now(timezone.utc))


# ── List responses ────────────────────────────────────────────────────────────

class PaymentList(BaseModel):
    object: str = "list"
    data:   list[Payment]
    count:  int


class RefundList(BaseModel):
    object: str = "list"
    data:   list[Refund]
    count:  int
