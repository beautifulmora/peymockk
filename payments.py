"""
/v1/payments -create, retrieve, list, cancel.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status

from ..auth import verify_api_key
from ..models import Payment, PaymentCreate, PaymentList, PaymentStatus
from ..simulation import simulate
from ..store import store

router = APIRouter()


@router.post("", response_model=Payment, status_code=status.HTTP_201_CREATED)
def create_payment(
    body: PaymentCreate,
    api_key: str = Depends(verify_api_key),
) -> Payment:
    """
    Initiate a new payment.

    Use one of the magic card numbers to trigger specific outcomes:
    - `4242424242424242` → succeeded
    - `4000000000000002` → card_declined
    - `4000000000009995` → insufficient_funds
    - `4000000000000069` → expired_card
    - `4000000000000127` → incorrect_cvc
    - `5555555555554444` → mastercard succeeded
    """
    outcome = simulate(body.card_number)

    payment = Payment(
        amount=body.amount,
        currency=body.currency,
        description=body.description,
        metadata=body.metadata,
        status=outcome["status"],
        card=outcome.get("card"),
        failure_code=outcome.get("failure_code"),
        failure_message=outcome.get("failure_message"),
    )

    store.save_payment(payment)
    return payment


@router.get("", response_model=PaymentList)
def list_payments(
    limit:  int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    api_key: str = Depends(verify_api_key),
) -> PaymentList:
    """Return a paginated list of payments, newest first."""
    payments = store.list_payments(limit=limit, offset=offset)
    return PaymentList(data=payments, count=len(payments))


@router.get("/{payment_id}", response_model=Payment)
def get_payment(
    payment_id: str,
    api_key: str = Depends(verify_api_key),
) -> Payment:
    """Retrieve a single payment by ID."""
    payment = store.get_payment(payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail=f"Payment '{payment_id}' not found.")
    return payment


@router.post("/{payment_id}/cancel", response_model=Payment)
def cancel_payment(
    payment_id: str,
    api_key: str = Depends(verify_api_key),
) -> Payment:
    """
    Cancel a payment that is still in `pending` or `processing` state.
    Succeeded or already-canceled payments cannot be canceled (use refunds instead).
    """
    payment = store.get_payment(payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail=f"Payment '{payment_id}' not found.")

    if payment.status not in (PaymentStatus.PENDING, PaymentStatus.PROCESSING):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel a payment with status '{payment.status}'. "
                   "Use /v1/refunds for succeeded payments.",
        )

    payment.status     = PaymentStatus.CANCELED
    payment.updated_at = datetime.now(timezone.utc)
    store.save_payment(payment)
    return payment
