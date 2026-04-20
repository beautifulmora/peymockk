"""
/v1/refunds — create and retrieve refunds against existing payments.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from ..auth import verify_api_key
from ..models import PaymentStatus, Refund, RefundCreate, RefundList, RefundStatus
from ..store import store

router = APIRouter()


@router.post("", response_model=Refund, status_code=status.HTTP_201_CREATED)
def create_refund(
    body: RefundCreate,
    api_key: str = Depends(verify_api_key),
) -> Refund:
    """
    Refund a succeeded payment — fully or partially.

    Rules:
    - The payment must be in `succeeded` status.
    - Total refunded amount cannot exceed the original charge.
    - Omit `amount` to refund the full remaining balance.
    """
    payment = store.get_payment(body.payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail=f"Payment '{body.payment_id}' not found.")

    if payment.status != PaymentStatus.SUCCEEDED:
        raise HTTPException(
            status_code=400,
            detail=f"Only succeeded payments can be refunded (status: '{payment.status}').",
        )

    already_refunded = store.total_refunded(payment.id)
    remaining        = payment.amount - already_refunded

    if remaining <= 0:
        raise HTTPException(status_code=400, detail="Payment has already been fully refunded.")

    refund_amount = body.amount if body.amount is not None else remaining

    if refund_amount > remaining:
        raise HTTPException(
            status_code=400,
            detail=f"Refund amount {refund_amount} exceeds remaining refundable balance {remaining}.",
        )

    refund = Refund(
        payment_id=payment.id,
        amount=refund_amount,
        currency=payment.currency,
        status=RefundStatus.SUCCEEDED,
        reason=body.reason,
    )

    store.save_refund(refund)
    return refund


@router.get("/{refund_id}", response_model=Refund)
def get_refund(
    refund_id: str,
    api_key: str = Depends(verify_api_key),
) -> Refund:
    """Retrieve a single refund by ID."""
    refund = store.get_refund(refund_id)
    if not refund:
        raise HTTPException(status_code=404, detail=f"Refund '{refund_id}' not found.")
    return refund


@router.get("/payment/{payment_id}", response_model=RefundList)
def list_refunds_for_payment(
    payment_id: str,
    api_key: str = Depends(verify_api_key),
) -> RefundList:
    """List all refunds associated with a payment."""
    if not store.get_payment(payment_id):
        raise HTTPException(status_code=404, detail=f"Payment '{payment_id}' not found.")

    refunds = store.list_refunds_for_payment(payment_id)
    return RefundList(data=refunds, count=len(refunds))
