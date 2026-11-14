"""ClearPay AI — FastAPI backend.

Phase 3: PayPal Sandbox order creation, buyer approval, payment capture,
database persistence with SQLAlchemy (clearpayai.db), and Gemini AI analysis.

Demo mode can be enabled by setting DEMO_MODE=1 in the environment.
This allows the application to demonstrate its workflow when
Sandbox checkout is blocked (e.g., currency mismatch error).
"""

import contextlib
import logging
import os
import time
from pathlib import Path
from typing import Optional

import httpx
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import text
from sqlalchemy.orm import Session

from database import DATABASE_URL, DEFAULT_DB_FILE, get_db, init_db
from models import AIAnalysis, PaymentTransaction, RecoveryCase

# Load environment variables from backend/.env
env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)

# PayPal configuration (read from environment — never logged or exposed)
PAYPAL_CLIENT_ID: str = os.getenv("PAYPAL_CLIENT_ID", "")
PAYPAL_CLIENT_SECRET: str = os.getenv("PAYPAL_CLIENT_SECRET", "")
PAYPAL_BASE_URL: str = os.getenv(
    "PAYPAL_BASE_URL", "https://api-m.sandbox.paypal.com"
)

# HTTP client timeout (seconds)
HTTP_TIMEOUT: float = 30.0

# In-memory access-token cache
_access_token: Optional[str] = None
_token_expires_at: float = 0.0

# In-memory set of captured order IDs (prevents duplicate capture attempts)
_captured_order_ids: set[str] = set()

# Diagnostics logger. Only order IDs, statuses and parameter names are logged —
# never credentials, access tokens or full PayPal URLs.
logger = logging.getLogger("clearpay.api")


# ---------------------------------------------------------------------------
# Gemini AI configuration
# ---------------------------------------------------------------------------
def _is_gemini_configured() -> bool:
    """Check whether the Gemini API key is set in the environment."""
    return bool(os.getenv("GEMINI_API_KEY"))


# ---------------------------------------------------------------------------
# Gemini AI client (lazy‑initialised)
# ---------------------------------------------------------------------------
_gemini_model = None


def _get_gemini_model():
    """Return a Gemini GenerativeModel instance, initialising on first call."""
    global _gemini_model
    if _gemini_model is None:
        import google.generativeai as genai
        key = os.getenv("GEMINI_API_KEY", "")
        if not key:
            raise RuntimeError("GEMINI_API_KEY not set")
        genai.configure(api_key=key)
        # Use configurable model; defaults to gemini-3.5-flash
        model_name = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
        _gemini_model = genai.GenerativeModel(model_name)
    return _gemini_model


# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------
_ANALYZE_PROMPT = """
You are an AI payment-failure analyst for ClearPay AI. Analyze the provided payment incident and produce a structured diagnosis.

Payment incident data:
- Provider: {provider}
- Status: {status}
- Error code: {error_code}
- Error message: {error_message}
- HTTP status: {http_status}
- Amount: {amount}
- Currency: {currency}
- Previous attempts: {previous_attempts}
- Incident description: {incident_description}
- Additional diagnostics: {additional_diagnostics}

You MUST respond with valid JSON matching this exact schema:
{{
  "issue_title": "string",
  "summary": "string (2-3 sentences)",
  "confirmed_facts": ["string"],
  "possible_causes": [{{"description": "string", "evidence": "string", "confidence": 0-100}}],
  "recommended_actions": ["string"],
  "retry_guidance": "string",
  "document_checklist": [{{"document": "string", "reason": "string", "condition": "string", "recommended_next_step": "string", "provider": "string", "where_to_obtain": "string", "official_source": "string"}}],
  "customer_facing_message": "string",
  "additional_info_needed": "string",
  "source_references": ["string (URL)"]
}}

Guidelines:
- Do NOT claim a cause is confirmed when evidence only supports a possibility.
- Do NOT claim every hold requires the same documents.
- Do NOT invent PayPal policies, error codes, document requirements, URLs, or guaranteed recovery probabilities.
- Prioritize actual provider error codes and responses over generic assumptions.
- If documentation does not establish a cause, say so explicitly and explain what additional information is needed.
- Source references must be real PayPal developer documentation URLs.
- Return ONLY the JSON object, no markdown, no code fences.
"""

_ANALYZE_FOLLOWUP_PROMPT = """
You are an AI payment-failure analyst continuing a conversation with a merchant.
Use the previous analysis and the new conversation history to answer the merchant's follow-up question.
Do NOT require the user to re-enter the original payment details.
Keep the conversation context temporary; do not persist case history.
Answer concisely and cite relevant PayPal documentation when it supports the answer.
If the available information is insufficient, say so explicitly and state what additional detail would help.

Previous analysis summary: {previous_summary}

Conversation history:
{history}

Current user question: {question}
"""


# ---------------------------------------------------------------------------
# Demo mode helper
# ---------------------------------------------------------------------------
def _is_demo_mode() -> bool:
    """Return True when demo mode is explicitly enabled via DEMO_MODE=1 env var.

    Reads from os.getenv each time so it picks up environment changes.
    Defaults to disabled (returns False) when DEMO_MODE is not set.
    """
    return os.getenv("DEMO_MODE", "") == "1"


# ---------------------------------------------------------------------------
# Credentials check
# ---------------------------------------------------------------------------
def _credentials_configured() -> bool:
    """Return True only when both PayPal credentials are present."""
    return bool(PAYPAL_CLIENT_ID and PAYPAL_CLIENT_SECRET)


# ---------------------------------------------------------------------------
# Order ID validation
# ---------------------------------------------------------------------------
def _validate_order_id(order_id: str) -> None:
    """Validate that an order ID looks like a PayPal order ID."""
    if not order_id:
        raise HTTPException(status_code=400, detail="Invalid order ID format")
    check_id = order_id.removeprefix("DEMO-") if order_id.startswith("DEMO-") else order_id
    if not all(c.isalnum() or c == "-" for c in check_id) or len(order_id) < 5:
        raise HTTPException(status_code=400, detail="Invalid order ID format")


# ---------------------------------------------------------------------------
# PayPal OAuth token
# ---------------------------------------------------------------------------
async def get_access_token() -> str:
    """Retrieve (and cache) a PayPal OAuth access token.

    Raises HTTPException on failure. Never exposes the token or secret.
    """
    global _access_token, _token_expires_at

    if not _credentials_configured():
        raise HTTPException(
            status_code=500,
            detail="PayPal credentials are not configured. "
            "Set PAYPAL_CLIENT_ID and PAYPAL_CLIENT_SECRET in backend/.env.",
        )

    # Return cached token if still valid
    if _access_token and time.time() < _token_expires_at:
        return _access_token

    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            response = await client.post(
                f"{PAYPAL_BASE_URL}/v1/oauth2/token",
                auth=(PAYPAL_CLIENT_ID, PAYPAL_CLIENT_SECRET),
                data={"grant_type": "client_credentials"},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="PayPal authentication timed out")
    except httpx.HTTPError:
        raise HTTPException(status_code=502, detail="Network error contacting PayPal")

    if response.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail="PayPal authentication failed. Check your credentials.",
        )

    try:
        data = response.json()
        token = data["access_token"]
        expires_in = int(data.get("expires_in", 3600))
    except (KeyError, ValueError, TypeError):
        raise HTTPException(status_code=502, detail="Unexpected response from PayPal")

    # Cache with a 60-second safety buffer
    _access_token = token
    _token_expires_at = time.time() + expires_in - 60

    return _access_token


# ---------------------------------------------------------------------------
# Frontend URL helper
# ---------------------------------------------------------------------------
def _get_frontend_base_url() -> str:
    """Return the frontend base URL for redirect callbacks and CORS."""
    raw = os.getenv("FRONTEND_URL", "").strip()
    if raw:
        return raw.rstrip("/")
    return "http://localhost:5173"


# ---------------------------------------------------------------------------
# PayPal order creation
# ---------------------------------------------------------------------------
async def create_paypal_order(amount: str, currency: str) -> dict:
    """Create a PayPal order and return the raw JSON response.

    If DEMO_MODE is enabled, returns a simulated order without calling PayPal.
    """
    frontend_base = _get_frontend_base_url()
    if _is_demo_mode():
        return {
            "id": "DEMO-ORDER-123",
            "status": "CREATED",
            "links": [
                {
                    "href": f"{frontend_base}?demo=true",
                    "rel": "approve",
                    "method": "GET",
                }
            ],
        }

    token = await get_access_token()

    order_payload = {
        "intent": "CAPTURE",
        "purchase_units": [
            {
                "description": "ClearPay AI Sandbox Test Payment (USD 10.00)",
                "amount": {
                    "currency_code": currency,
                    "value": amount,
                },
            }
        ],
        "application_context": {
            "return_url": frontend_base,
            "cancel_url": f"{frontend_base}?cancelled=1",
            "brand_name": "ClearPay AI",
            "user_action": "PAY_NOW",
        },
    }

    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            response = await client.post(
                f"{PAYPAL_BASE_URL}/v2/checkout/orders",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                json=order_payload,
            )
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="PayPal order creation timed out")
    except httpx.HTTPError:
        raise HTTPException(status_code=502, detail="Network error contacting PayPal")

    if response.status_code not in (200, 201):
        raise HTTPException(
            status_code=502,
            detail="PayPal order creation failed. Please try again.",
        )

    try:
        return response.json()
    except ValueError:
        raise HTTPException(status_code=502, detail="Unexpected response from PayPal")


# ---------------------------------------------------------------------------
# PayPal order capture
# ---------------------------------------------------------------------------
async def capture_paypal_order(order_id: str) -> dict:
    """Capture a PayPal order and return the raw JSON response.

    If DEMO_MODE is enabled and the order ID starts with 'DEMO-',
    returns a simulated capture without calling PayPal's capture API.
    """
    # Demo mode: simulate a completed payment without calling PayPal
    if _is_demo_mode() and order_id.startswith("DEMO-"):
        return {
            "id": order_id,
            "status": "COMPLETED",
            "purchase_units": [
                {
                    "payments": {
                        "captures": [
                            {
                                "id": "DEMO-CAPTURE-456",
                                "amount": {
                                    "currency_code": "USD",
                                    "value": "10.00",
                                },
                                "status": "COMPLETED",
                            }
                        ]
                    }
                }
            ],
        }

    # Prevent duplicate capture attempts (in-memory guard)
    if order_id in _captured_order_ids:
        raise HTTPException(
            status_code=409,
            detail="Order has already been captured.",
        )

    token = await get_access_token()

    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            response = await client.post(
                f"{PAYPAL_BASE_URL}/v2/checkout/orders/{order_id}/capture",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
            )
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="PayPal capture timed out")
    except httpx.HTTPError:
        raise HTTPException(status_code=502, detail="Network error contacting PayPal")

    # Handle specific PayPal error responses
    if response.status_code == 404:
        raise HTTPException(
            status_code=404, detail="Order not found. Verify the order ID."
        )

    if response.status_code == 422:
        try:
            error_data = response.json()
            details = error_data.get("details", [])
            for detail in details:
                issue = detail.get("issue", "")
                if issue == "ORDER_NOT_APPROVED":
                    raise HTTPException(
                        status_code=409,
                        detail="Order has not been approved by the buyer yet.",
                    )
                if issue in ("ORDER_ALREADY_CAPTURED", "CAPTURE_ALREADY_COMPLETED"):
                    _captured_order_ids.add(order_id)
                    raise HTTPException(
                        status_code=409,
                        detail="Order has already been captured.",
                    )
        except HTTPException:
            raise
        except Exception:
            pass
        raise HTTPException(
            status_code=422, detail="Unable to capture order. Check order status."
        )

    if response.status_code not in (200, 201):
        raise HTTPException(
            status_code=502, detail="PayPal capture failed. Please try again."
        )

    try:
        return response.json()
    except ValueError:
        raise HTTPException(status_code=502, detail="Unexpected response from PayPal")


# ---------------------------------------------------------------------------
# FastAPI app setup with Lifespan Database Initialization
# ---------------------------------------------------------------------------
@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    """Ensure database tables exist on server startup without destroying data."""
    init_db()
    yield


app = FastAPI(title="ClearPay AI API", lifespan=lifespan)

# Auto-initialize on import so tables exist even if lifespan context isn't used
init_db()

def _get_cors_origins() -> list[str]:
    """Build list of allowed CORS origins, supporting local dev and deployed frontend."""
    origins = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]
    frontend_url = os.getenv("FRONTEND_URL", "").strip()
    if frontend_url:
        cleaned = frontend_url.rstrip("/")
        if cleaned not in origins:
            origins.append(cleaned)
    custom_origins = os.getenv("CORS_ORIGINS", "").strip()
    if custom_origins:
        for orig in custom_origins.split(","):
            cleaned = orig.strip().rstrip("/")
            if cleaned and cleaned not in origins:
                origins.append(cleaned)
    return origins


# CORS — allow local Vite dev origin, deployed Vercel frontend, and Vercel preview deploys
app.add_middleware(
    CORSMiddleware,
    allow_origins=_get_cors_origins(),
    allow_origin_regex=r"^https://.*\.vercel\.app$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------
class OrderRequest(BaseModel):
    """Request body for creating a PayPal order."""

    amount: str = Field(default="10.00", description="Order amount (e.g. '10.00')")
    currency: str = Field(default="USD", description="3-letter ISO currency code")

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, value: str) -> str:
        try:
            numeric = float(value)
        except (ValueError, TypeError):
            raise ValueError("Amount must be a valid number")
        if numeric <= 0:
            raise ValueError("Amount must be greater than zero")
        if "." in value:
            decimals = len(value.split(".")[1])
            if decimals > 2:
                raise ValueError("Amount must have at most 2 decimal places")
        return value

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, value: str) -> str:
        if not value or len(value) != 3 or not value.isalpha():
            raise ValueError("Currency must be a 3-letter ISO code (e.g. USD)")
        return value.upper()


class OrderResponse(BaseModel):
    """Response returned to the frontend after order creation."""

    order_id: str
    approval_url: str
    amount: str = "10.00"
    currency: str = "USD"


class CaptureResponse(BaseModel):
    """Response returned after a capture attempt."""

    order_id: str
    status: str
    capture_id: Optional[str] = None
    amount: Optional[str] = None
    currency: Optional[str] = None


class RecoveryCaseCreate(BaseModel):
    """Payload to create a new recovery case in the database."""

    title: str = Field(description="Case title")
    problem_description: str = Field(default="", description="Description of the incident")
    order_id: Optional[str] = Field(default=None, description="Optional associated PayPal order ID")
    payment_reference: Optional[str] = Field(default=None, description="Error code or reference")
    status: Optional[str] = Field(default="Action Required", description="Initial case status")


class RecoveryCaseUpdate(BaseModel):
    """Payload to update an existing recovery case."""

    status: Optional[str] = None
    title: Optional[str] = None
    problem_description: Optional[str] = None


# ---------------------------------------------------------------------------
# AI analysis models
# ---------------------------------------------------------------------------
class AIAnalysisRequest(BaseModel):
    """Request body for AI-powered payment failure/hold analysis."""

    provider: str = Field(
        default="gemini",
        description="AI provider (currently only 'gemini' is supported)",
    )
    status: str = Field(
        default="FAILED",
        description="Payment status: FAILED, DECLINED, PENDING, or ON_HOLD",
    )
    error_code: Optional[str] = Field(
        default=None,
        description="Provider error code, if available (e.g. PayPal error code)",
    )
    error_message: Optional[str] = Field(
        default=None,
        description="Provider error message, if available",
    )
    http_status: Optional[int] = Field(
        default=None,
        description="HTTP/API error status, if relevant",
    )
    amount: Optional[str] = Field(
        default=None,
        description="Amount as string (e.g. '10.00'), if relevant",
    )
    currency: Optional[str] = Field(
        default=None,
        description="3-letter ISO currency code, if relevant",
    )
    previous_attempts: int = Field(
        default=0,
        ge=0,
        description="Number of previous attempts made",
    )
    incident_description: str = Field(
        default="",
        description="Sanitized incident description from the merchant",
    )
    additional_diagnostics: Optional[str] = Field(
        default=None,
        description="Additional non-sensitive diagnostic information",
    )
    order_id: Optional[str] = Field(
        default=None,
        description="Optional associated PayPal order ID",
    )
    case_id: Optional[int] = Field(
        default=None,
        description="Optional associated recovery case ID",
    )


class AICause(BaseModel):
    """A possible root cause for the payment issue."""

    description: str = Field(description="What the cause is")
    evidence: str = Field(description="How the submitted data supports (or contradicts) it")
    confidence: int = Field(
        ge=0,
        le=100,
        description="Percentage confidence (0–100)",
    )


class AIAnalysisResponse(BaseModel):
    """Structured response from the AI analysis endpoint."""

    issue_title: str = Field(description="Concise title for the problem")
    summary: str = Field(description="Plain‑English summary (2‑3 sentences)")
    confirmed_facts: list[str] = Field(
        default_factory=list,
        description="Facts directly from the submitted data",
    )
    possible_causes: list[AICause] = Field(
        default_factory=list,
        description="Possible root causes with evidence and confidence",
    )
    recommended_actions: list[str] = Field(
        default_factory=list,
        description="Prioritized recommended actions",
    )
    retry_guidance: str = Field(
        description="Whether retrying is appropriate/inappropriate/conditional and what condition must be met"
    )
    document_checklist: list[dict] = Field(
        default_factory=list,
        description="Conditional document checklist",
    )
    customer_facing_message: str = Field(
        description="Message the merchant can reuse with the customer"
    )
    additional_info_needed: str = Field(
        description="What extra information would improve the diagnosis"
    )
    source_references: list[str] = Field(
        default_factory=list,
        description="Verified official documentation URLs",
    )


# ---------------------------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------------------------
@app.get("/", tags=["root"])
async def get_root():
    """Welcome message."""
    return {"message": "Welcome to ClearPay AI API"}


@app.get("/health", tags=["health"])
async def get_health():
    """Health check."""
    return {"status": "healthy"}


@app.get("/api/settings/status", tags=["settings"])
async def get_settings_status(db: Session = Depends(get_db)):
    """Return non-sensitive configuration and service status."""
    db_ok = True
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        db_ok = False

    return {
        "status": "healthy",
        "environment": "sandbox",
        "paypal_configured": _credentials_configured(),
        "gemini_configured": _is_gemini_configured(),
        "demo_mode": _is_demo_mode(),
        "model": os.getenv("GEMINI_MODEL", "gemini-3.5-flash"),
        "database_configured": db_ok,
        "database_type": "sqlite" if "sqlite" in DATABASE_URL else "postgresql",
        "database_file": DEFAULT_DB_FILE.name if "sqlite" in DATABASE_URL else "",
    }


@app.post("/api/orders", response_model=OrderResponse, tags=["orders"])
async def create_order(
    order_request: OrderRequest,
    db: Session = Depends(get_db),
):
    """Create a PayPal Sandbox order and return the order ID + approval URL.

    Persists the created order into the database.
    If DEMO_MODE is enabled, returns a simulated order ID and approval URL.
    """
    DEMO_AMOUNT = "10.00"
    DEMO_CURRENCY = "USD"
    try:
        result = await create_paypal_order(DEMO_AMOUNT, DEMO_CURRENCY)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=502, detail="An error occurred while creating the order")

    order_id = result.get("id")
    if not order_id:
        raise HTTPException(status_code=502, detail="Invalid response from PayPal")

    approval_url: Optional[str] = None
    for link in result.get("links", []):
        if link.get("rel") == "approve":
            approval_url = link.get("href")
            break

    if not approval_url:
        raise HTTPException(status_code=502, detail="No approval URL returned by PayPal")

    # Demo mode: use a simulated order ID and show demo labeling
    if _is_demo_mode():
        order_id = "DEMO-ORDER-123"
        approval_url = "http://localhost:5173?demo=true"

    # Persist in database (handle duplicate gracefully)
    existing_tx = db.query(PaymentTransaction).filter_by(order_id=order_id).first()
    if existing_tx:
        if existing_tx.status not in ("COMPLETED", "SIMULATED_COMPLETED"):
            existing_tx.status = "AWAITING_APPROVAL"
            existing_tx.amount = "10.00"
            existing_tx.currency = "USD"
            db.commit()
    else:
        new_tx = PaymentTransaction(
            order_id=order_id,
            amount="10.00",
            currency="USD",
            status="AWAITING_APPROVAL",
        )
        db.add(new_tx)
        db.commit()

    return OrderResponse(
        order_id=order_id,
        approval_url=approval_url,
        amount="10.00",
        currency="USD",
    )


@app.post("/api/orders/{order_id}/capture", response_model=CaptureResponse, tags=["orders"])
async def capture_order(
    order_id: str,
    db: Session = Depends(get_db),
):
    """Capture a PayPal order after buyer approval.

    Verifies the actual PayPal response — never trusts frontend params alone.
    Updates the database with confirmed capture status and capture ID.
    """
    _validate_order_id(order_id)
    logger.info("capture_request_received order_id=%s", order_id)

    # Check database and in-memory guard to prevent duplicate capture
    existing_tx = db.query(PaymentTransaction).filter_by(order_id=order_id).first()
    if (order_id in _captured_order_ids) or (
        existing_tx and existing_tx.status in ("COMPLETED", "SIMULATED_COMPLETED")
    ):
        _captured_order_ids.add(order_id)
        raise HTTPException(
            status_code=409,
            detail="Order has already been captured.",
        )

    # Demo mode: simulate capture without calling PayPal's capture API
    if _is_demo_mode() and order_id.startswith("DEMO-"):
        _captured_order_ids.add(order_id)
        if existing_tx:
            existing_tx.status = "SIMULATED_COMPLETED"
            existing_tx.capture_id = "DEMO-CAPTURE-456"
            existing_tx.amount = "10.00"
            existing_tx.currency = "USD"
        else:
            new_tx = PaymentTransaction(
                order_id=order_id,
                capture_id="DEMO-CAPTURE-456",
                amount="10.00",
                currency="USD",
                status="SIMULATED_COMPLETED",
            )
            db.add(new_tx)
        db.commit()

        return CaptureResponse(
            order_id=order_id,
            status="SIMULATED_COMPLETED",
            capture_id="DEMO-CAPTURE-456",
            amount="10.00",
            currency="USD",
        )

    try:
        result = await capture_paypal_order(order_id)
    except HTTPException as exc:
        if existing_tx and exc.status_code != 409:
            existing_tx.status = "FAILED"
            existing_tx.failure_reason = exc.detail
            try:
                db.commit()
            except Exception:
                db.rollback()
        raise
    except Exception as exc:
        if existing_tx:
            existing_tx.status = "FAILED"
            existing_tx.failure_reason = str(exc)
            try:
                db.commit()
            except Exception:
                db.rollback()
        raise HTTPException(status_code=502, detail="An error occurred while capturing the order")

    status = result.get("status", "")
    logger.info("capture_outcome order_id=%s paypal_status=%s", order_id, status)

    if status == "DECLINED":
        logger.warning("capture_declined order_id=%s", order_id)
        if existing_tx:
            existing_tx.status = "DECLINED"
            existing_tx.failure_reason = "Payment was declined by the payer."
            db.commit()
        raise HTTPException(
            status_code=402,
            detail="Payment was declined by the payer.",
        )

    if status != "COMPLETED":
        if existing_tx:
            existing_tx.status = "FAILED"
            existing_tx.failure_reason = f"Payment not completed. PayPal status: {status}"
            db.commit()
        raise HTTPException(
            status_code=409,
            detail=f"Payment not completed. PayPal status: {status}",
        )

    # Extract capture details from verified PayPal response
    capture_id: Optional[str] = None
    amount: Optional[str] = None
    currency: Optional[str] = None

    purchase_units = result.get("purchase_units", [])
    if purchase_units:
        payments = purchase_units[0].get("payments", {})
        captures = payments.get("captures", [])
        if captures:
            capture = captures[0]
            capture_id = capture.get("id")
            capture_amount = capture.get("amount", {})
            amount = capture_amount.get("value")
            currency = capture_amount.get("currency_code")

    # Mark as captured (both in memory and database)
    _captured_order_ids.add(order_id)
    logger.info("capture_succeeded order_id=%s capture_id=%s", order_id, capture_id)

    if existing_tx:
        existing_tx.status = "COMPLETED"
        existing_tx.capture_id = capture_id
        if amount:
            existing_tx.amount = amount
        if currency:
            existing_tx.currency = currency
        existing_tx.failure_reason = None
    else:
        new_tx = PaymentTransaction(
            order_id=order_id,
            capture_id=capture_id,
            status="COMPLETED",
            amount=amount or "10.00",
            currency=currency or "USD",
        )
        db.add(new_tx)
    db.commit()

    return CaptureResponse(
        order_id=order_id,
        status="COMPLETED",
        capture_id=capture_id,
        amount=amount,
        currency=currency,
    )


# ---------------------------------------------------------------------------
# AI Analysis endpoint
# ---------------------------------------------------------------------------
def _sanitize_error_msg(error: Exception) -> str:
    """Sanitize error messages to prevent leaking API keys or credentials."""
    msg = str(error)
    key = os.getenv("GEMINI_API_KEY", "")
    if key and key in msg:
        msg = msg.replace(key, "[REDACTED]")
    return msg


@app.post("/api/ai/analyze-payment", response_model=AIAnalysisResponse, tags=["ai"])
async def analyze_payment(
    request: AIAnalysisRequest,
    db: Session = Depends(get_db),
):
    """AI-powered payment failure/hold analysis.

    Accepts payment status and diagnostic information, invokes Gemini AI,
    persists the analysis and associated recovery case to the database,
    and returns a structured report.
    """
    valid_statuses = {"FAILED", "DECLINED", "PENDING", "ON_HOLD"}
    status_upper = request.status.upper()
    if status_upper not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status '{request.status}'. Must be one of: {', '.join(valid_statuses)}",
        )

    # Check Gemini configuration
    if not _is_gemini_configured():
        raise HTTPException(
            status_code=503,
            detail="AI provider not configured. Set GEMINI_API_KEY in backend/.env.",
        )

    # Build confirmed facts
    confirmed_facts: list[str] = []
    if request.error_code:
        confirmed_facts.append(f"Error code: {request.error_code}")
    if request.error_message:
        confirmed_facts.append(f"Error message: {request.error_message}")
    if request.http_status is not None:
        confirmed_facts.append(f"HTTP status: {request.http_status}")
    if request.amount:
        confirmed_facts.append(f"Amount: {request.amount} {request.currency or 'unspecified'}")
    if request.incident_description:
        confirmed_facts.append(f"Incident: {request.incident_description}")
    if request.additional_diagnostics:
        confirmed_facts.append(f"Additional diagnostics: {request.additional_diagnostics}")
    confirmed_facts.append(f"Status: {request.status}")
    confirmed_facts.append(f"Provider: {request.provider}")
    confirmed_facts.append(f"Previous attempts: {request.previous_attempts}")

    # Use Gemini to generate analysis
    model = _get_gemini_model()
    prompt = _ANALYZE_PROMPT.format(
        provider=request.provider,
        status=request.status,
        error_code=request.error_code or "",
        error_message=request.error_message or "",
        http_status=request.http_status if request.http_status is not None else "",
        amount=request.amount or "",
        currency=request.currency or "",
        previous_attempts=request.previous_attempts,
        incident_description=request.incident_description or "",
        additional_diagnostics=request.additional_diagnostics or "",
    )

    try:
        import json as _json

        response = await model.generate_content_async(
            prompt,
            generation_config={"response_mime_type": "application/json"},
        )
        analysis_text = response.text
    except Exception as e:
        safe_msg = _sanitize_error_msg(e)
        error_str = safe_msg.lower()
        if "timeout" in error_str or "timed out" in error_str or "deadline" in error_str:
            raise HTTPException(
                status_code=504,
                detail="AI provider request timed out",
            )
        raise HTTPException(
            status_code=502,
            detail=f"AI provider error: {safe_msg}",
        )

    # Clean markdown fences if present
    clean_text = analysis_text.strip()
    if clean_text.startswith("```"):
        lines = clean_text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        clean_text = "\n".join(lines).strip()

    try:
        parsed = _json.loads(clean_text)
    except (ValueError, TypeError, _json.JSONDecodeError):
        raise HTTPException(
            status_code=502,
            detail="AI provider returned malformed output",
        )

    # Ensure confirmed facts are included
    if "confirmed_facts" not in parsed or not isinstance(parsed.get("confirmed_facts"), list):
        parsed["confirmed_facts"] = confirmed_facts
    else:
        for fact in confirmed_facts:
            if fact not in parsed["confirmed_facts"]:
                parsed["confirmed_facts"].append(fact)

    try:
        analysis = AIAnalysisResponse(**parsed)
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"AI provider returned invalid structure: {str(e)}",
        )

    # Persist in database
    try:
        tx = None
        if request.order_id:
            tx = db.query(PaymentTransaction).filter_by(order_id=request.order_id).first()

        rec_case = None
        if request.case_id:
            rec_case = db.query(RecoveryCase).filter_by(id=request.case_id).first()
        elif request.order_id:
            rec_case = db.query(RecoveryCase).filter_by(order_id=request.order_id).first()

        if not rec_case:
            case_num = f"CASE-{int(time.time() * 1000) % 1000000:06d}"
            case_title = analysis.issue_title or f"{request.status} Payment Incident"
            case_desc = request.incident_description or analysis.summary
            rec_case = RecoveryCase(
                case_number=case_num,
                title=case_title,
                order_id=request.order_id or (f"INC-{request.error_code}" if request.error_code else None),
                transaction_id=tx.id if tx else None,
                payment_reference=request.error_code,
                problem_description=case_desc,
                status="Action Required",
            )
            db.add(rec_case)
            db.flush()

        ai_record = AIAnalysis(
            case_id=rec_case.id if rec_case else None,
            transaction_id=tx.id if tx else None,
            order_id=request.order_id,
            problem_summary=request.incident_description or "",
            issue_title=analysis.issue_title,
            summary=analysis.summary,
            confirmed_facts=analysis.confirmed_facts,
            possible_causes=[c.model_dump() for c in analysis.possible_causes],
            recommended_actions=analysis.recommended_actions,
            retry_guidance=analysis.retry_guidance,
            document_checklist=analysis.document_checklist,
            customer_facing_message=analysis.customer_facing_message,
            additional_info_needed=analysis.additional_info_needed,
            source_references=analysis.source_references,
        )
        db.add(ai_record)
        db.commit()
    except Exception as db_err:
        db.rollback()
        logger.warning("database_persistence_failed: %s", db_err)

    return analysis


@app.post("/api/ai/follow-up", response_model=dict, tags=["ai"])
async def ai_followup(request: dict):
    """Follow‑up question about the same incident."""
    analysis = request.get("analysis")
    history = request.get("history", [])
    question = request.get("question", "")

    if not analysis or not isinstance(analysis, dict):
        raise HTTPException(
            status_code=400,
            detail="Missing or invalid 'analysis' in request body",
        )

    if not question or not isinstance(question, str):
        raise HTTPException(
            status_code=400,
            detail="Missing or invalid 'question' in request body",
        )

    if len(question) > 2000:
        raise HTTPException(
            status_code=400,
            detail="Question too long (max 2000 characters)",
        )

    if isinstance(history, list):
        history = history[-5:]
    else:
        history = []

    if not _is_gemini_configured():
        raise HTTPException(
            status_code=503,
            detail="AI provider not configured. Set GEMINI_API_KEY in backend/.env.",
        )

    model = _get_gemini_model()
    history_text = ""
    for turn in history:
        if isinstance(turn, dict):
            history_text += f"User: {turn.get('question', '')}\nAssistant: {turn.get('answer', '')}\n"

    previous_summary = analysis.get("summary", "") if isinstance(analysis, dict) else str(analysis)

    prompt = _ANALYZE_FOLLOWUP_PROMPT.format(
        previous_summary=previous_summary,
        history=history_text,
        question=question,
    )

    try:
        response = await model.generate_content_async(prompt)
        return {"answer": response.text}
    except Exception as e:
        safe_msg = _sanitize_error_msg(e)
        error_str = safe_msg.lower()
        if "timeout" in error_str or "timed out" in error_str or "deadline" in error_str:
            raise HTTPException(
                status_code=504,
                detail="AI provider request timed out",
            )
        raise HTTPException(
            status_code=502,
            detail=f"AI provider error: {safe_msg}",
        )


# ---------------------------------------------------------------------------
# Dashboard and Data Endpoints
# ---------------------------------------------------------------------------
@app.get("/api/dashboard/stats", tags=["dashboard"])
async def get_dashboard_stats(db: Session = Depends(get_db)):
    """Calculate aggregated payment and recovery KPI metrics directly from database."""
    total_tx = db.query(PaymentTransaction).count()
    successful = db.query(PaymentTransaction).filter(
        PaymentTransaction.status.in_(["COMPLETED", "SIMULATED_COMPLETED", "completed", "simulated_completed"])
    ).count()
    failed = db.query(PaymentTransaction).filter(
        PaymentTransaction.status.in_(["FAILED", "DECLINED", "CANCELLED", "failed", "declined", "cancelled"])
    ).count()
    pending = db.query(PaymentTransaction).filter(
        PaymentTransaction.status.in_(["CREATED", "AWAITING_APPROVAL", "PROCESSING", "created", "awaiting_approval", "processing"])
    ).count()

    total_cases = db.query(RecoveryCase).count()
    open_cases = db.query(RecoveryCase).filter(
        RecoveryCase.status.in_(["OPEN", "Action Required", "IN_PROGRESS", "Active Analysis"])
    ).count()
    resolved_cases = db.query(RecoveryCase).filter(
        RecoveryCase.status.in_(["RESOLVED", "Resolved"])
    ).count()

    return {
        "total_transactions": total_tx,
        "successful_payments": successful,
        "failed_payments": failed,
        "pending_payments": pending,
        "recovery_cases": total_cases,
        "open_recovery_cases": open_cases,
        "resolved_recovery_cases": resolved_cases,
    }


@app.get("/api/transactions", tags=["transactions"])
async def list_transactions(
    search: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """Retrieve persisted payment transactions from the database."""
    query = db.query(PaymentTransaction)
    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            (PaymentTransaction.order_id.ilike(search_filter))
            | (PaymentTransaction.capture_id.ilike(search_filter))
        )
    if status and status.lower() != "all":
        query = query.filter(PaymentTransaction.status.ilike(status))

    txs = query.order_by(PaymentTransaction.created_at.desc()).limit(limit).all()
    return [tx.to_dict() for tx in txs]


@app.get("/api/recovery-cases", tags=["recovery-cases"])
async def list_recovery_cases(
    status: Optional[str] = None,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """Retrieve persisted recovery cases from the database."""
    query = db.query(RecoveryCase)
    if status and status.lower() != "all":
        query = query.filter(RecoveryCase.status.ilike(status))
    cases = query.order_by(RecoveryCase.created_at.desc()).limit(limit).all()
    return [c.to_dict() for c in cases]


@app.post("/api/recovery-cases", tags=["recovery-cases"])
async def create_recovery_case(
    case_in: RecoveryCaseCreate,
    db: Session = Depends(get_db),
):
    """Create a new payment recovery case in the database."""
    tx = None
    if case_in.order_id:
        tx = db.query(PaymentTransaction).filter_by(order_id=case_in.order_id).first()

    case_num = f"CASE-{int(time.time() * 1000) % 1000000:06d}"
    new_case = RecoveryCase(
        case_number=case_num,
        title=case_in.title,
        order_id=case_in.order_id,
        transaction_id=tx.id if tx else None,
        payment_reference=case_in.payment_reference,
        problem_description=case_in.problem_description,
        status=case_in.status or "Action Required",
    )
    db.add(new_case)
    db.commit()
    db.refresh(new_case)
    return new_case.to_dict()


@app.get("/api/recovery-cases/{case_id}", tags=["recovery-cases"])
async def get_recovery_case(
    case_id: int,
    db: Session = Depends(get_db),
):
    """Retrieve a single recovery case by internal ID."""
    case = db.query(RecoveryCase).filter_by(id=case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Recovery case not found")
    return case.to_dict()


@app.patch("/api/recovery-cases/{case_id}", tags=["recovery-cases"])
async def update_recovery_case(
    case_id: int,
    case_update: RecoveryCaseUpdate,
    db: Session = Depends(get_db),
):
    """Update status, title, or problem description of a recovery case."""
    case = db.query(RecoveryCase).filter_by(id=case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Recovery case not found")
    if case_update.status is not None:
        case.status = case_update.status
    if case_update.title is not None:
        case.title = case_update.title
    if case_update.problem_description is not None:
        case.problem_description = case_update.problem_description
    db.commit()
    db.refresh(case)
    return case.to_dict()


@app.get("/api/activity", tags=["activity"])
async def get_recent_activity(
    limit: int = 20,
    db: Session = Depends(get_db),
):
    """Generate activity feed from database records."""
    activities = []

    txs = db.query(PaymentTransaction).order_by(PaymentTransaction.created_at.desc()).limit(limit).all()
    for tx in txs:
        t_time = tx.updated_at or tx.created_at
        status_upper = tx.status.upper()
        if status_upper in ("COMPLETED", "SIMULATED_COMPLETED"):
            desc = f"Payment captured: {tx.capture_id or tx.order_id} ({tx.amount} {tx.currency})"
            badge = "COMPLETED"
        elif status_upper in ("FAILED", "DECLINED"):
            desc = f"Payment failed for order {tx.order_id}: {tx.failure_reason or 'Declined'}"
            badge = status_upper
        elif status_upper == "CANCELLED":
            desc = f"Payment cancelled for order {tx.order_id}"
            badge = "CANCELLED"
        else:
            desc = f"Created PayPal order: {tx.order_id} ({tx.amount} {tx.currency})"
            badge = "AWAITING"
        activities.append({
            "id": f"act-tx-{tx.id}",
            "timestamp": t_time.strftime("%H:%M:%S") if t_time else "",
            "sort_key": t_time.timestamp() if t_time else 0,
            "type": "payment",
            "description": desc,
            "badge": badge,
        })

    analyses = db.query(AIAnalysis).order_by(AIAnalysis.created_at.desc()).limit(limit).all()
    for a in analyses:
        a_time = a.created_at
        activities.append({
            "id": f"act-ai-{a.id}",
            "timestamp": a_time.strftime("%H:%M:%S") if a_time else "",
            "sort_key": a_time.timestamp() if a_time else 0,
            "type": "copilot",
            "description": f"AI Diagnosis complete: {a.issue_title or 'Payment Failure'}",
            "badge": "DIAGNOSED",
        })

    activities.sort(key=lambda x: x["sort_key"], reverse=True)
    return [
        {
            "id": x["id"],
            "timestamp": x["timestamp"],
            "type": x["type"],
            "description": x["description"],
            "badge": x["badge"],
        }
        for x in activities[:limit]
    ]


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
