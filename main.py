"""
Payments Mock API Service
A clean, production-style mock for payment processing workflows.
"""

from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn

from .routers import payments, refunds, webhooks
from .store import store
from .auth import verify_api_key


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Seed some initial data on startup."""
    store.seed()
    yield


app = FastAPI(
    title="Payments Mock API",
    description="A realistic mock payment processing service for development & testing.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(payments.router, prefix="/v1/payments", tags=["Payments"])
app.include_router(refunds.router, prefix="/v1/refunds", tags=["Refunds"])
app.include_router(webhooks.router, prefix="/v1/webhooks", tags=["Webhooks"])


@app.get("/health", tags=["Meta"])
def health():
    return {"status": "ok", "version": "1.0.0"}


@app.get("/v1/balance", tags=["Meta"])
def get_balance(api_key: str = Depends(verify_api_key)):
    """Return a mock account balance."""
    return {
        "available": [{"amount": 1_000_000, "currency": "usd"}],
        "pending":   [{"amount":    50_000, "currency": "usd"}],
    }


if __name__ == "__main__":
    uvicorn.run("payments_mock.main:app", host="0.0.0.0", port=8000, reload=True)
