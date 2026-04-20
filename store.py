"""
In-memory store — thread-safe dict wrappers, easily swappable for a real DB.
"""

from __future__ import annotations

import threading
from typing import Optional

from .models import Payment, PaymentStatus, Refund, Currency, CardDetails


class Store:
    """Simple thread-safe in-memory store."""

    def __init__(self) -> None:
        self._lock     = threading.Lock()
        self._payments: dict[str, Payment] = {}
        self._refunds:  dict[str, Refund]  = {}

    # ── Payments ──────────────────────────────────────────────────────────────

    def save_payment(self, payment: Payment) -> Payment:
        with self._lock:
            self._payments[payment.id] = payment
        return payment

    def get_payment(self, payment_id: str) -> Optional[Payment]:
        return self._payments.get(payment_id)

    def list_payments(self, limit: int = 20, offset: int = 0) -> list[Payment]:
        all_payments = sorted(
            self._payments.values(),
            key=lambda p: p.created_at,
            reverse=True,
        )
        return all_payments[offset : offset + limit]

    # ── Refunds ───────────────────────────────────────────────────────────────

    def save_refund(self, refund: Refund) -> Refund:
        with self._lock:
            self._refunds[refund.id] = refund
        return refund

    def get_refund(self, refund_id: str) -> Optional[Refund]:
        return self._refunds.get(refund_id)

    def list_refunds_for_payment(self, payment_id: str) -> list[Refund]:
        return [r for r in self._refunds.values() if r.payment_id == payment_id]

    def total_refunded(self, payment_id: str) -> int:
        return sum(
            r.amount
            for r in self.list_refunds_for_payment(payment_id)
            if r.status.value == "succeeded"
        )

    # ── Seed ──────────────────────────────────────────────────────────────────

    def seed(self) -> None:
        """Pre-populate with a few realistic payments for demo purposes."""
        samples = [
            Payment(
                amount=4999, currency=Currency.USD, status=PaymentStatus.SUCCEEDED,
                description="Order #1001 — Acme Corp",
                card=CardDetails(brand="visa", last4="4242", exp_month=12, exp_year=2027),
            ),
            Payment(
                amount=12000, currency=Currency.EUR, status=PaymentStatus.SUCCEEDED,
                description="Subscription renewal",
                card=CardDetails(brand="mastercard", last4="5555", exp_month=8, exp_year=2026),
            ),
            Payment(
                amount=750, currency=Currency.GBP, status=PaymentStatus.FAILED,
                description="One-time top-up",
                card=CardDetails(brand="visa", last4="0002", exp_month=1, exp_year=2025),
                failure_code="card_declined",
                failure_message="Your card was declined.",
            ),
        ]
        for p in samples:
            self.save_payment(p)


# Singleton — import this everywhere
store = Store()
