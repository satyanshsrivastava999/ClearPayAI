"""ClearPay AI — FastAPI backend.

Phase 3: PayPal Sandbox order creation, buyer approval, and payment capture.

Demo mode can be enabled by setting DEMO_MODE=1 in the environment.
This allows the application to demonstrate its workflow when
Sandbox checkout is blocked (e.g., currency mismatch error).
"""

import logging
import os
import time
from pathlib import Path
from typing import Optional

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator

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
        # Use the latest available model; make configurable via env var
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
    # Allow demo order IDs (DEMO-ORDER-123 format) and real PayPal IDs
    if not order_id:
        raise HTTPException(status_code=400, detail="Invalid order ID format")
    # Check that the ID is alphanumeric with optional hyphens (PayPal order IDs)
    # Remove demo prefix for simpler check, then validate remaining part
    check_id = order_id.removeprefix("DEMO-") if order_id.startswith("DEMO-") else order_id
    # Allow alphanumeric and hyphens (PayPal order IDs contain hyphens)
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
        # Do NOT include response body — it may echo credentials
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
# PayPal order creation
# ---------------------------------------------------------------------------
async def create_paypal_order(amount: str, currency: str) -> dict:
    """Create a PayPal order and return the raw JSON response.

    If DEMO_MODE is enabled, returns a simulated order without calling PayPal.
    """
    if _is_demo_mode():
        return {
            "id": "DEMO-ORDER-123",
            "status": "CREATED",
            "links": [
                {
                    "href": "http://localhost:5173?demo=true",
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
            "return_url": "http://localhost:5173",
            "cancel_url": "http://localhost:5173?cancelled=1",
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
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(title="ClearPay AI API")

# CORS — allow local Vite dev origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
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


@app.get("/", tags=["root"])
async def get_root():
    """Welcome message."""
    return {"message": "Welcome to ClearPay AI API"}


@app.get("/health", tags=["health"])
async def get_health():
    """Health check."""
    return {"status": "healthy"}


@app.get("/api/settings/status", tags=["settings"])
async def get_settings_status():
    """Return non-sensitive configuration and service status."""
    return {
        "status": "healthy",
        "environment": "sandbox",
        "paypal_configured": _credentials_configured(),
        "gemini_configured": _is_gemini_configured(),
        "demo_mode": _is_demo_mode(),
        "model": os.getenv("GEMINI_MODEL", "gemini-3.5-flash"),
    }


@app.post("/api/orders", response_model=OrderResponse, tags=["orders"])
async def create_order(order_request: OrderRequest):
    """Create a PayPal Sandbox order and return the order ID + approval URL.

    If DEMO_MODE is enabled, returns a simulated order ID and approval URL
    without calling PayPal's API.
    """
    # Demo order: fixed amount and currency (10.00 USD Sandbox test payment)
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

    return OrderResponse(
        order_id=order_id,
        approval_url=approval_url,
        amount="10.00",
        currency="USD",
    )


@app.post("/api/orders/{order_id}/capture", response_model=CaptureResponse, tags=["orders"])
async def capture_order(order_id: str):
    """Capture a PayPal order after buyer approval.

    Verifies the actual PayPal response — never trusts frontend params alone.

    If DEMO_MODE is enabled and the order ID starts with 'DEMO-',
    simulates a completed capture without calling PayPal's capture API.
    """
    _validate_order_id(order_id)
    logger.info("capture_request_received order_id=%s", order_id)

    # Demo mode: simulate capture without calling PayPal's capture API
    if _is_demo_mode() and order_id.startswith("DEMO-"):
        # Mark as captured (in-memory guard against duplicates)
        _captured_order_ids.add(order_id)
        return CaptureResponse(
            order_id=order_id,
            status="SIMULATED_COMPLETED",
            capture_id="DEMO-CAPTURE-456",
            amount="10.00",
            currency="USD",
        )

    try:
        result = await capture_paypal_order(order_id)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=502, detail="An error occurred while capturing the order")

    status = result.get("status", "")
    logger.info("capture_outcome order_id=%s paypal_status=%s", order_id, status)

    # A payer decline is a final, distinct outcome (the frontend shows it as
    # "declined" rather than a technical failure).
    if status == "DECLINED":
        logger.warning("capture_declined order_id=%s", order_id)
        raise HTTPException(
            status_code=402,
            detail="Payment was declined by the payer.",
        )

    if status != "COMPLETED":
        raise HTTPException(
            status_code=409,
            detail=f"Payment not completed. PayPal status: {status}",
        )

    # Extract capture details from the verified response
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

    # Mark as captured (in-memory guard against duplicates)
    _captured_order_ids.add(order_id)
    logger.info("capture_succeeded order_id=%s capture_id=%s", order_id, capture_id)

    return CaptureResponse(
        order_id=order_id,
        status="COMPLETED",
        capture_id=capture_id,
        amount=amount,
        currency=currency,
    )


# ---------------------------------------------------------------------------
# AI analysis endpoint
# ---------------------------------------------------------------------------

def _sanitize_error_msg(error: Exception) -> str:
    """Sanitize error messages to prevent leaking API keys or credentials."""
    msg = str(error)
    key = os.getenv("GEMINI_API_KEY", "")
    if key and key in msg:
        msg = msg.replace(key, "[REDACTED]")
    return msg


@app.post("/api/ai/analyze-payment", response_model=AIAnalysisResponse, tags=["ai"])
async def analyze_payment(request: AIAnalysisRequest):
    """AI-powered payment failure/hold analysis.

    Accepts payment status and diagnostic information and returns a structured
    analysis including possible causes, recommended actions, document checklists,
    and customer‑facing messages. Uses Gemini AI when configured; otherwise
    returns a configuration error.
    """
    # Validate status field
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

    # Build the confirmed facts from the submitted data
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

    # Use Gemini to generate the analysis
    model = _get_gemini_model()
    # Build the prompt by embedding the request data into the template.
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
        # Request JSON output from Gemini
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

    # Parse and validate the Gemini response
    try:
        parsed = _json.loads(clean_text)
    except (ValueError, TypeError, _json.JSONDecodeError):
        raise HTTPException(
            status_code=502,
            detail="AI provider returned malformed output",
        )

    # Merge confirmed facts from our own data (always include them)
    if "confirmed_facts" not in parsed or not isinstance(parsed.get("confirmed_facts"), list):
        parsed["confirmed_facts"] = confirmed_facts
    else:
        # Ensure our confirmed facts are included
        for fact in confirmed_facts:
            if fact not in parsed["confirmed_facts"]:
                parsed["confirmed_facts"].append(fact)

    # Validate against the Pydantic model
    try:
        analysis = AIAnalysisResponse(**parsed)
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"AI provider returned invalid structure: {str(e)}",
        )

    return analysis


@app.post("/api/ai/follow-up", response_model=dict, tags=["ai"])
async def ai_followup(request: dict):
    """Follow‑up question about the same incident.

    Accepts the current analysis and a conversation history, returns an answer.
    Keeps context temporary; does not persist case history.
    """
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

    # Validate question length
    if len(question) > 2000:
        raise HTTPException(
            status_code=400,
            detail="Question too long (max 2000 characters)",
        )

    # Trim history to last 5 turns
    if isinstance(history, list):
        history = history[-5:]
    else:
        history = []

    # Check Gemini configuration
    if not _is_gemini_configured():
        raise HTTPException(
            status_code=503,
            detail="AI provider not configured. Set GEMINI_API_KEY in backend/.env.",
        )

    # Build a follow‑up prompt
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

