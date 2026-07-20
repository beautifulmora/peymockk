"""
API key authentication - dead-simple for a mock, easy to harden for real use.

Pass any key that starts with "sk_test_" in the Authorization header:
    Authorization: Bearer sk_test_your_key_here
"""

from fastapi import HTTPException, status, Header
from typing import Optional


VALID_TEST_PREFIX = "sk_test_"


def verify_api_key(authorization: Optional[str] = Header(None)) -> str:
    """
    Dependency that validates the Bearer token.
    Returns the raw API key on success.
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header. Use: Authorization: Bearer sk_test_<key>",
        )

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.startswith(VALID_TEST_PREFIX):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key. Test keys must start with 'sk_test_'.",
        )

    return token
