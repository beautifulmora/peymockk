"""
Simulation engine — maps magic card numbers to deterministic outcomes.

Card numbers mirror the Stripe testing convention so teams can reuse
their existing test suites with minimal changes.
"""

from __future__ import annotations

from .models import CardDetails, FailureCode, PaymentStatus

# ── Magic card number → outcome ───────────────────────────────────────────────

CARD_OUTCOMES: dict[str, dict] = {
    # Always succeeds
    "4242424242424242": {
        "status": PaymentStatus.SUCCEEDED,
        "card": CardDetails(brand="visa", last4="4242", exp_month=12, exp_year=2028),
    },
    # Always declined
    "4000000000000002": {
        "status":          PaymentStatus.FAILED,
        "failure_code":    FailureCode.CARD_DECLINED,
        "failure_message": "Your card was declined.",
        "card": CardDetails(brand="visa", last4="0002", exp_month=12, exp_year=2028),
    },
    # Insufficient funds
    "4000000000009995": {
        "status":          PaymentStatus.FAILED,
        "failure_code":    FailureCode.INSUFFICIENT_FUNDS,
        "failure_message": "Your card has insufficient funds.",
        "card": CardDetails(brand="visa", last4="9995", exp_month=12, exp_year=2028),
    },
    # Expired card
    "4000000000000069": {
        "status":          PaymentStatus.FAILED,
        "failure_code":    FailureCode.EXPIRED_CARD,
        "failure_message": "Your card has expired.",
        "card": CardDetails(brand="visa", last4="0069", exp_month=1, exp_year=2020),
    },
    # Incorrect CVC
    "4000000000000127": {
        "status":          PaymentStatus.FAILED,
        "failure_code":    FailureCode.INCORRECT_CVC,
        "failure_message": "Your card's security code is incorrect.",
        "card": CardDetails(brand="visa", last4="0127", exp_month=12, exp_year=2028),
    },
    # Mastercard — succeeds
    "5555555555554444": {
        "status": PaymentStatus.SUCCEEDED,
        "card": CardDetails(brand="mastercard", last4="4444", exp_month=8, exp_year=2027),
    },
}

_DEFAULT_OUTCOME = {
    "status": PaymentStatus.SUCCEEDED,
    "card": CardDetails(brand="visa", last4="0000", exp_month=12, exp_year=2028),
}


def simulate(card_number: str) -> dict:
    """
    Return an outcome dict for the given card number.
    Unknown numbers default to a successful charge.
    """
    return CARD_OUTCOMES.get(card_number, _DEFAULT_OUTCOME)
