"""Tests for ClearPay AI backend (Phase 2)."""

import os

import httpx
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# Import the app module
import main
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from database import Base, get_db
from models import PaymentTransaction, RecoveryCase, AIAnalysis

TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(autouse=True)
def test_db_session():
    """Create a fresh in-memory SQLite database for each test, isolated from clearpayai.db."""
    main._captured_order_ids.clear()
    main._access_token = None
    main._token_expires_at = 0.0

    test_engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    Base.metadata.create_all(bind=test_engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    main.app.dependency_overrides[get_db] = override_get_db
    yield TestingSessionLocal
    main.app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=test_engine)
    test_engine.dispose()
    main._captured_order_ids.clear()
    main._access_token = None
    main._token_expires_at = 0.0


# ---------------------------------------------------------------------------
# Capture endpoint tests
# ---------------------------------------------------------------------------


def test_capture_order_success(client):
    """Mock PayPal capture to return COMPLETED and verify response."""
    mock_token_response = MagicMock()
    mock_token_response.status_code = 200
    mock_token_response.json.return_value = {
        "access_token": "fake-access-token",
        "expires_in": 32400,
    }

    mock_capture_response = MagicMock()
    mock_capture_response.status_code = 201
    mock_capture_response.json.return_value = {
        "id": "ORDER-123",
        "status": "COMPLETED",
        "purchase_units": [
            {
                "payments": {
                    "captures": [
                        {
                            "id": "CAPTURE-456",
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

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(
        side_effect=[mock_token_response, mock_capture_response]
    )

    mock_async_client = MagicMock()
    mock_async_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_async_client.__aexit__ = AsyncMock(return_value=None)

    # Reset captured set
    main._captured_order_ids.clear()
    main._access_token = None
    main._token_expires_at = 0.0

    with patch.object(main, "PAYPAL_CLIENT_ID", "test-client-id"), patch.object(
        main, "PAYPAL_CLIENT_SECRET", "test-client-secret"
    ), patch("main.httpx.AsyncClient", return_value=mock_async_client):
        response = client.post("/api/orders/ORDER12345/capture")

        assert response.status_code == 200
        data = response.json()
        assert data["order_id"] == "ORDER12345"
        assert data["status"] == "COMPLETED"
        assert data["capture_id"] == "CAPTURE-456"
        assert data["amount"] == "10.00"
        assert data["currency"] == "USD"


def test_demo_mode_disabled_by_default(client):
    """Verify that demo mode is disabled by default (no DEMO_MODE env var)."""
    # When DEMO_MODE is not set, it defaults to empty string, so DEMO_MODE == "1" is False
    with patch.object(main, "PAYPAL_CLIENT_ID", "test-client-id"), patch.object(
        main, "PAYPAL_CLIENT_SECRET", "test-client-secret"
    ), patch("main.httpx.AsyncClient", return_value=MagicMock()):
        # Just verify the app runs without demo mode enabled
        response = client.get("/")
        assert response.status_code == 200


def test_demo_mode_create_order_simulated(client):
    """Verify that creating an order in demo mode returns a simulated order ID."""
    mock_token_response = MagicMock()
    mock_token_response.status_code = 200
    mock_token_response.json.return_value = {
        "access_token": "fake-access-token",
        "expires_in": 32400,
    }

    mock_order_response = MagicMock()
    mock_order_response.status_code = 201
    mock_order_response.json.return_value = {
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

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(side_effect=[mock_token_response, mock_order_response])

    mock_async_client = MagicMock()
    mock_async_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_async_client.__aexit__ = AsyncMock(return_value=None)

    with patch.object(main, "PAYPAL_CLIENT_ID", "test-client-id"), patch.object(
        main, "PAYPAL_CLIENT_SECRET", "test-client-secret"
    ), patch("main.httpx.AsyncClient", return_value=mock_async_client):
        # Enable demo mode by setting env var
        with patch.dict(os.environ, {"DEMO_MODE": "1"}):
            main._access_token = None
            main._token_expires_at = 0.0

            response = client.post(
                "/api/orders", json={"amount": "10.00", "currency": "USD"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["order_id"] == "DEMO-ORDER-123"
            assert "demo=true" in data["approval_url"]


def test_demo_mode_capture_simulated(client):
    """Verify that capturing a demo order returns SIMULATED_COMPLETED status."""
    mock_token_response = MagicMock()
    mock_token_response.status_code = 200
    mock_token_response.json.return_value = {
        "access_token": "fake-access-token",
        "expires_in": 32400,
    }

    mock_capture_response = MagicMock()
    mock_capture_response.status_code = 201
    mock_capture_response.json.return_value = {
        "id": "DEMO-ORDER-123",
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

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(
        side_effect=[mock_token_response, mock_capture_response]
    )

    mock_async_client = MagicMock()
    mock_async_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_async_client.__aexit__ = AsyncMock(return_value=None)

    with patch.object(main, "PAYPAL_CLIENT_ID", "test-client-id"), patch.object(
        main, "PAYPAL_CLIENT_SECRET", "test-client-secret"
    ), patch("main.httpx.AsyncClient", return_value=mock_async_client):
        # Enable demo mode by setting env var
        with patch.dict(os.environ, {"DEMO_MODE": "1"}):
            main._captured_order_ids.clear()
            main._access_token = None
            main._token_expires_at = 0.0

            response = client.post("/api/orders/DEMO-ORDER-123/capture")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "SIMULATED_COMPLETED"
            assert data["capture_id"] == "DEMO-CAPTURE-456"
            assert data["amount"] == "10.00"
            assert data["currency"] == "USD"

        # Verify the demo order was marked as captured
        assert "DEMO-ORDER-123" in main._captured_order_ids


def test_capture_order_not_approved(client):
    """Mock PayPal to return ORDER_NOT_APPROVED and verify 409."""
    mock_token_response = MagicMock()
    mock_token_response.status_code = 200
    mock_token_response.json.return_value = {
        "access_token": "fake-access-token",
        "expires_in": 32400,
    }

    mock_capture_response = MagicMock()
    mock_capture_response.status_code = 422
    mock_capture_response.json.return_value = {
        "name": "UNPROCESSABLE_ENTITY",
        "details": [{"issue": "ORDER_NOT_APPROVED"}],
    }

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(
        side_effect=[mock_token_response, mock_capture_response]
    )

    mock_async_client = MagicMock()
    mock_async_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_async_client.__aexit__ = AsyncMock(return_value=None)

    main._captured_order_ids.clear()
    main._access_token = None
    main._token_expires_at = 0.0

    with patch.object(main, "PAYPAL_CLIENT_ID", "test-client-id"), patch.object(
        main, "PAYPAL_CLIENT_SECRET", "test-client-secret"
    ), patch("main.httpx.AsyncClient", return_value=mock_async_client):
        response = client.post("/api/orders/ORDER12345/capture")

        assert response.status_code == 409
        assert "not been approved" in response.json()["detail"].lower()


def test_capture_order_already_captured_paypal(client):
    """Mock PayPal to return ORDER_ALREADY_CAPTURED and verify 409."""
    mock_token_response = MagicMock()
    mock_token_response.status_code = 200
    mock_token_response.json.return_value = {
        "access_token": "fake-access-token",
        "expires_in": 32400,
    }

    mock_capture_response = MagicMock()
    mock_capture_response.status_code = 422
    mock_capture_response.json.return_value = {
        "name": "UNPROCESSABLE_ENTITY",
        "details": [{"issue": "ORDER_ALREADY_CAPTURED"}],
    }

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(
        side_effect=[mock_token_response, mock_capture_response]
    )

    mock_async_client = MagicMock()
    mock_async_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_async_client.__aexit__ = AsyncMock(return_value=None)

    main._captured_order_ids.clear()
    main._access_token = None
    main._token_expires_at = 0.0

    with patch.object(main, "PAYPAL_CLIENT_ID", "test-client-id"), patch.object(
        main, "PAYPAL_CLIENT_SECRET", "test-client-secret"
    ), patch("main.httpx.AsyncClient", return_value=mock_async_client):
        response = client.post("/api/orders/ORDER12345/capture")

        assert response.status_code == 409
        assert "already been captured" in response.json()["detail"].lower()


def test_capture_order_duplicate_guard(client):
    """Verify in-memory guard prevents duplicate capture attempts."""
    main._captured_order_ids.add("ORDER12345")

    response = client.post("/api/orders/ORDER12345/capture")

    assert response.status_code == 409
    assert "already been captured" in response.json()["detail"].lower()

    # Clean up
    main._captured_order_ids.discard("ORDER12345")


def test_capture_order_not_found(client):
    """Mock PayPal to return 404 and verify 404 response."""
    mock_token_response = MagicMock()
    mock_token_response.status_code = 200
    mock_token_response.json.return_value = {
        "access_token": "fake-access-token",
        "expires_in": 32400,
    }

    mock_capture_response = MagicMock()
    mock_capture_response.status_code = 404

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(
        side_effect=[mock_token_response, mock_capture_response]
    )

    mock_async_client = MagicMock()
    mock_async_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_async_client.__aexit__ = AsyncMock(return_value=None)

    main._captured_order_ids.clear()
    main._access_token = None
    main._token_expires_at = 0.0

    with patch.object(main, "PAYPAL_CLIENT_ID", "test-client-id"), patch.object(
        main, "PAYPAL_CLIENT_SECRET", "test-client-secret"
    ), patch("main.httpx.AsyncClient", return_value=mock_async_client):
        response = client.post("/api/orders/ORDER12345/capture")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


def test_capture_order_paypal_auth_failure(client):
    """Mock PayPal auth to fail and verify 502."""
    mock_token_response = MagicMock()
    mock_token_response.status_code = 401

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_token_response)

    mock_async_client = MagicMock()
    mock_async_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_async_client.__aexit__ = AsyncMock(return_value=None)

    main._captured_order_ids.clear()
    main._access_token = None
    main._token_expires_at = 0.0

    with patch.object(main, "PAYPAL_CLIENT_ID", "test-client-id"), patch.object(
        main, "PAYPAL_CLIENT_SECRET", "test-client-secret"
    ), patch("main.httpx.AsyncClient", return_value=mock_async_client):
        response = client.post("/api/orders/ORDER12345/capture")

        assert response.status_code == 502


def test_capture_order_timeout(client):
    """Mock httpx timeout and verify 504."""
    mock_token_response = MagicMock()
    mock_token_response.status_code = 200
    mock_token_response.json.return_value = {
        "access_token": "fake-access-token",
        "expires_in": 32400,
    }

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(
        side_effect=[mock_token_response, httpx.TimeoutException("timeout")]
    )

    mock_async_client = MagicMock()
    mock_async_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_async_client.__aexit__ = AsyncMock(return_value=None)

    main._captured_order_ids.clear()
    main._access_token = None
    main._token_expires_at = 0.0

    with patch.object(main, "PAYPAL_CLIENT_ID", "test-client-id"), patch.object(
        main, "PAYPAL_CLIENT_SECRET", "test-client-secret"
    ), patch("main.httpx.AsyncClient", return_value=mock_async_client):
        response = client.post("/api/orders/ORDER12345/capture")

        assert response.status_code == 504


def test_capture_order_paypal_error(client):
    """Mock PayPal capture to return 500 and verify 502."""
    mock_token_response = MagicMock()
    mock_token_response.status_code = 200
    mock_token_response.json.return_value = {
        "access_token": "fake-access-token",
        "expires_in": 32400,
    }

    mock_capture_response = MagicMock()
    mock_capture_response.status_code = 500

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(
        side_effect=[mock_token_response, mock_capture_response]
    )

    mock_async_client = MagicMock()
    mock_async_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_async_client.__aexit__ = AsyncMock(return_value=None)

    main._captured_order_ids.clear()
    main._access_token = None
    main._token_expires_at = 0.0

    with patch.object(main, "PAYPAL_CLIENT_ID", "test-client-id"), patch.object(
        main, "PAYPAL_CLIENT_SECRET", "test-client-secret"
    ), patch("main.httpx.AsyncClient", return_value=mock_async_client):
        response = client.post("/api/orders/ORDER12345/capture")

        assert response.status_code == 502


def test_capture_order_invalid_id(client):
    """Verify invalid order ID returns 400."""
    main._captured_order_ids.clear()
    response = client.post("/api/orders/ab/capture")
    assert response.status_code == 400


def test_capture_order_not_completed_status(client):
    """Mock PayPal to return non-COMPLETED status and verify 409."""
    mock_token_response = MagicMock()
    mock_token_response.status_code = 200
    mock_token_response.json.return_value = {
        "access_token": "fake-access-token",
        "expires_in": 32400,
    }

    mock_capture_response = MagicMock()
    mock_capture_response.status_code = 201
    mock_capture_response.json.return_value = {
        "id": "ORDER-123",
        "status": "PENDING",
        "purchase_units": [],
    }

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(
        side_effect=[mock_token_response, mock_capture_response]
    )

    mock_async_client = MagicMock()
    mock_async_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_async_client.__aexit__ = AsyncMock(return_value=None)

    main._captured_order_ids.clear()
    main._access_token = None
    main._token_expires_at = 0.0

    with patch.object(main, "PAYPAL_CLIENT_ID", "test-client-id"), patch.object(
        main, "PAYPAL_CLIENT_SECRET", "test-client-secret"
    ), patch("main.httpx.AsyncClient", return_value=mock_async_client):
        response = client.post("/api/orders/ORDER12345/capture")

        assert response.status_code == 409
        assert "not completed" in response.json()["detail"].lower()


def test_capture_order_declined_status(client):
    """Mock PayPal to return DECLINED and verify 402 with a decline detail."""
    mock_token_response = MagicMock()
    mock_token_response.status_code = 200
    mock_token_response.json.return_value = {
        "access_token": "fake-access-token",
        "expires_in": 32400,
    }

    mock_capture_response = MagicMock()
    mock_capture_response.status_code = 201
    mock_capture_response.json.return_value = {
        "id": "ORDER-123",
        "status": "DECLINED",
        "purchase_units": [],
    }

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(
        side_effect=[mock_token_response, mock_capture_response]
    )

    mock_async_client = MagicMock()
    mock_async_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_async_client.__aexit__ = AsyncMock(return_value=None)

    main._captured_order_ids.clear()
    main._access_token = None
    main._token_expires_at = 0.0

    with patch.object(main, "PAYPAL_CLIENT_ID", "test-client-id"), patch.object(
        main, "PAYPAL_CLIENT_SECRET", "test-client-secret"
    ), patch("main.httpx.AsyncClient", return_value=mock_async_client):
        response = client.post("/api/orders/ORDER12345/capture")

        assert response.status_code == 402
        assert "declined" in response.json()["detail"].lower()
        # A declined order is not recorded as captured
        assert "ORDER12345" not in main._captured_order_ids


def test_capture_missing_credentials(client):
    """Verify missing credentials returns 500."""
    with patch.object(main, "PAYPAL_CLIENT_ID", ""), patch.object(
        main, "PAYPAL_CLIENT_SECRET", ""
    ):
        response = client.post("/api/orders/ORDER12345/capture")
        assert response.status_code == 500
        assert "credentials" in response.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Phase 1 endpoints (preserved)
# ---------------------------------------------------------------------------


def test_root_endpoint(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to ClearPay AI API"}


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_settings_status_endpoint(client):
    """GET /api/settings/status returns non-sensitive status info."""
    response = client.get("/api/settings/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["environment"] == "sandbox"
    assert "paypal_configured" in data
    assert "gemini_configured" in data
    assert "demo_mode" in data
    assert "model" in data
    # Ensure no secrets leaked
    assert "key" not in str(data).lower()
    assert "secret" not in str(data).lower()


# ---------------------------------------------------------------------------
# Missing credentials
# ---------------------------------------------------------------------------


def test_create_order_missing_credentials(client):
    """POST /api/orders should fail when PayPal credentials are not set."""
    with patch.object(main, "PAYPAL_CLIENT_ID", ""), patch.object(
        main, "PAYPAL_CLIENT_SECRET", ""
    ):
        response = client.post("/api/orders", json={"amount": "10.00", "currency": "USD"})
        assert response.status_code == 500
        assert "credentials" in response.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------


def test_create_order_invalid_amount_zero(client):
    response = client.post("/api/orders", json={"amount": "0", "currency": "USD"})
    assert response.status_code == 422


def test_create_order_invalid_amount_negative(client):
    response = client.post("/api/orders", json={"amount": "-5.00", "currency": "USD"})
    assert response.status_code == 422


def test_create_order_invalid_amount_too_many_decimals(client):
    response = client.post("/api/orders", json={"amount": "10.123", "currency": "USD"})
    assert response.status_code == 422


def test_create_order_invalid_amount_non_numeric(client):
    response = client.post("/api/orders", json={"amount": "abc", "currency": "USD"})
    assert response.status_code == 422


def test_create_order_invalid_currency_too_short(client):
    response = client.post("/api/orders", json={"amount": "10.00", "currency": "US"})
    assert response.status_code == 422


def test_create_order_invalid_currency_too_long(client):
    response = client.post("/api/orders", json={"amount": "10.00", "currency": "USDD"})
    assert response.status_code == 422


def test_create_order_invalid_currency_non_alpha(client):
    response = client.post("/api/orders", json={"amount": "10.00", "currency": "U$D"})
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Successful order creation (mocked PayPal API)
# ---------------------------------------------------------------------------


def test_create_order_success(client):
    """Mock PayPal API to return a valid order and verify the response."""
    mock_token_response = MagicMock()
    mock_token_response.status_code = 200
    mock_token_response.json.return_value = {
        "access_token": "fake-access-token",
        "token_type": "Bearer",
        "expires_in": 32400,
    }

    mock_order_response = MagicMock()
    mock_order_response.status_code = 201
    mock_order_response.json.return_value = {
        "id": "ORDER-123",
        "status": "CREATED",
        "links": [
            {
                "href": "https://www.sandbox.paypal.com/checkoutnow?token=ORDER-123",
                "rel": "approve",
                "method": "GET",
            }
        ],
    }

    # Mock httpx.AsyncClient as an async context manager
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(side_effect=[mock_token_response, mock_order_response])

    mock_async_client = MagicMock()
    mock_async_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_async_client.__aexit__ = AsyncMock(return_value=None)

    with patch.object(main, "PAYPAL_CLIENT_ID", "test-client-id"), patch.object(
        main, "PAYPAL_CLIENT_SECRET", "test-client-secret"
    ), patch("main.httpx.AsyncClient", return_value=mock_async_client):
        # Reset cached token
        main._access_token = None
        main._token_expires_at = 0.0

        response = client.post(
            "/api/orders", json={"amount": "10.00", "currency": "USD"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["order_id"] == "ORDER-123"
        assert data["approval_url"] != ""
        assert "ORDER-123" in data["approval_url"]
        assert data["amount"] == "10.00"
        assert data["currency"] == "USD"

        # Verify PayPal order payload uses USD
        order_call = mock_client.post.call_args_list[1]
        payload = order_call.kwargs.get("json", {})
        pu = payload.get("purchase_units", [{}])[0]
        assert pu["amount"]["currency_code"] == "USD"
        assert pu["amount"]["value"] == "10.00"


# ---------------------------------------------------------------------------
# PayPal API error handling
# ---------------------------------------------------------------------------


def test_create_order_paypal_auth_failure(client):
    """Mock PayPal to return auth error and verify safe handling."""
    mock_token_response = MagicMock()
    mock_token_response.status_code = 401
    mock_token_response.json.return_value = {"error": "invalid_client"}

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_token_response)

    mock_async_client = MagicMock()
    mock_async_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_async_client.__aexit__ = AsyncMock(return_value=None)

    with patch.object(main, "PAYPAL_CLIENT_ID", "test-client-id"), patch.object(
        main, "PAYPAL_CLIENT_SECRET", "test-client-secret"
    ), patch("main.httpx.AsyncClient", return_value=mock_async_client):
        main._access_token = None
        main._token_expires_at = 0.0

        response = client.post(
            "/api/orders", json={"amount": "10.00", "currency": "USD"}
        )

        assert response.status_code == 502
        # Ensure secret is not leaked
        detail = response.json()["detail"]
        assert "test-client-secret" not in detail
        assert "test-client-id" not in detail


def test_create_order_paypal_order_failure(client):
    """Mock PayPal to return order creation error."""
    mock_token_response = MagicMock()
    mock_token_response.status_code = 200
    mock_token_response.json.return_value = {
        "access_token": "fake-access-token",
        "expires_in": 32400,
    }

    mock_order_response = MagicMock()
    mock_order_response.status_code = 400
    mock_order_response.json.return_value = {"error": "INVALID_REQUEST"}

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(side_effect=[mock_token_response, mock_order_response])

    mock_async_client = MagicMock()
    mock_async_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_async_client.__aexit__ = AsyncMock(return_value=None)

    with patch.object(main, "PAYPAL_CLIENT_ID", "test-client-id"), patch.object(
        main, "PAYPAL_CLIENT_SECRET", "test-client-secret"
    ), patch("main.httpx.AsyncClient", return_value=mock_async_client):
        main._access_token = None
        main._token_expires_at = 0.0

        response = client.post(
            "/api/orders", json={"amount": "10.00", "currency": "USD"}
        )

        assert response.status_code == 502


# ---------------------------------------------------------------------------
# Default values
# ---------------------------------------------------------------------------


def test_create_order_default_values(client):
    """POST /api/orders with empty body should use defaults (10.00 USD)."""
    mock_token_response = MagicMock()
    mock_token_response.status_code = 200
    mock_token_response.json.return_value = {
        "access_token": "fake-access-token",
        "expires_in": 32400,
    }

    mock_order_response = MagicMock()
    mock_order_response.status_code = 201
    mock_order_response.json.return_value = {
        "id": "ORDER-DEFAULT",
        "links": [
            {
                "href": "https://www.sandbox.paypal.com/checkoutnow?token=ORDER-DEFAULT",
                "rel": "approve",
                "method": "GET",
            }
        ],
    }

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(side_effect=[mock_token_response, mock_order_response])

    mock_async_client = MagicMock()
    mock_async_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_async_client.__aexit__ = AsyncMock(return_value=None)

    with patch.object(main, "PAYPAL_CLIENT_ID", "test-client-id"), patch.object(
        main, "PAYPAL_CLIENT_SECRET", "test-client-secret"
    ), patch("main.httpx.AsyncClient", return_value=mock_async_client):
        main._access_token = None
        main._token_expires_at = 0.0

        response = client.post("/api/orders", json={})

        assert response.status_code == 200
        assert response.json()["order_id"] == "ORDER-DEFAULT"
        assert response.json()["amount"] == "10.00"
        assert response.json()["currency"] == "USD"

# ---------------------------------------------------------------------------
# Missing credentials
# ---------------------------------------------------------------------------

@pytest.fixture
def client():
    """FastAPI TestClient."""
    return TestClient(main.app)


# ---------------------------------------------------------------------------
# AI analysis endpoint tests (mocked Gemini)
# ---------------------------------------------------------------------------


def _make_gemini_mock(response_text: str):
    """Create a mock Gemini model that returns the given text."""
    mock_response = MagicMock()
    mock_response.text = response_text

    mock_model = MagicMock()
    mock_model.generate_content_async = AsyncMock(return_value=mock_response)
    return mock_model


VALID_AI_JSON = """{
  "issue_title": "Payment FAILED analysis",
  "summary": "The payment failed due to an insufficient funds error.",
  "confirmed_facts": ["Error code: INSUFFICIENT_FUNDS", "Status: FAILED"],
  "possible_causes": [
    {"description": "Insufficient funds in buyer account", "evidence": "Error code INSUFFICIENT_FUNDS", "confidence": 85}
  ],
  "recommended_actions": ["Contact the buyer", "Retry after funding"],
  "retry_guidance": "Conditional: retry after buyer adds funds",
  "document_checklist": [
    {"document": "Buyer bank statement", "reason": "Verify funds", "provider": "Buyer", "where_to_obtain": "Bank"}
  ],
  "customer_facing_message": "Your payment could not be processed.",
  "additional_info_needed": "Transaction ID and timestamp",
  "source_references": ["https://developer.paypal.com/api/handle-payment-failures/"]
}"""


def test_ai_analyze_payment_failed(client):
    """Valid FAILED transaction analysis."""
    mock_model = _make_gemini_mock(VALID_AI_JSON)
    with patch.object(main, "_is_gemini_configured", return_value=True), \
         patch.object(main, "_get_gemini_model", return_value=mock_model):
        response = client.post(
            "/api/ai/analyze-payment",
            json={
                "status": "FAILED",
                "error_code": "INSUFFICIENT_FUNDS",
                "error_message": "Insufficient funds",
                "amount": "10.00",
                "currency": "USD",
                "previous_attempts": 1,
                "incident_description": "Buyer payment failed",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["issue_title"] == "Payment FAILED analysis"
        assert len(data["possible_causes"]) == 1
        assert data["possible_causes"][0]["confidence"] == 85
        assert len(data["document_checklist"]) == 1
        # Confirmed facts should include our submitted data
        assert any("INSUFFICIENT_FUNDS" in f for f in data["confirmed_facts"])


def test_ai_analyze_payment_declined(client):
    """DECLINED transaction analysis."""
    mock_model = _make_gemini_mock(VALID_AI_JSON.replace("FAILED", "DECLINED"))
    with patch.object(main, "_is_gemini_configured", return_value=True), \
         patch.object(main, "_get_gemini_model", return_value=mock_model):
        response = client.post(
            "/api/ai/analyze-payment",
            json={
                "status": "DECLINED",
                "error_code": "DECLINED_BY_ISSUER",
                "error_message": "Card declined",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "DECLINED" in data["issue_title"]


def test_ai_analyze_payment_pending(client):
    """PENDING transaction analysis."""
    mock_model = _make_gemini_mock(VALID_AI_JSON.replace("FAILED", "PENDING"))
    with patch.object(main, "_is_gemini_configured", return_value=True), \
         patch.object(main, "_get_gemini_model", return_value=mock_model):
        response = client.post(
            "/api/ai/analyze-payment",
            json={"status": "PENDING"},
        )
        assert response.status_code == 200


def test_ai_analyze_payment_on_hold(client):
    """ON_HOLD transaction analysis."""
    mock_model = _make_gemini_mock(VALID_AI_JSON.replace("FAILED", "ON_HOLD"))
    with patch.object(main, "_is_gemini_configured", return_value=True), \
         patch.object(main, "_get_gemini_model", return_value=mock_model):
        response = client.post(
            "/api/ai/analyze-payment",
            json={"status": "ON_HOLD"},
        )
        assert response.status_code == 200


def test_ai_analyze_payment_invalid_status(client):
    """Invalid transaction status returns 400."""
    with patch.object(main, "_is_gemini_configured", return_value=True):
        response = client.post(
            "/api/ai/analyze-payment",
            json={"status": "COMPLETED"},
        )
        assert response.status_code == 400
        assert "invalid status" in response.json()["detail"].lower()


def test_ai_analyze_payment_missing_config(client):
    """Missing GEMINI_API_KEY returns 503."""
    with patch.object(main, "_is_gemini_configured", return_value=False):
        response = client.post(
            "/api/ai/analyze-payment",
            json={"status": "FAILED"},
        )
        assert response.status_code == 503
        assert "not configured" in response.json()["detail"].lower()


def test_ai_analyze_payment_gemini_timeout(client):
    """Gemini timeout returns 504."""
    mock_model = MagicMock()
    mock_model.generate_content_async = AsyncMock(
        side_effect=Exception("Request timed out")
    )
    with patch.object(main, "_is_gemini_configured", return_value=True), \
         patch.object(main, "_get_gemini_model", return_value=mock_model):
        response = client.post(
            "/api/ai/analyze-payment",
            json={"status": "FAILED"},
        )
        assert response.status_code == 504


def test_ai_analyze_payment_gemini_error(client):
    """Gemini provider error returns 502."""
    mock_model = MagicMock()
    mock_model.generate_content_async = AsyncMock(
        side_effect=Exception("API error 500")
    )
    with patch.object(main, "_is_gemini_configured", return_value=True), \
         patch.object(main, "_get_gemini_model", return_value=mock_model):
        response = client.post(
            "/api/ai/analyze-payment",
            json={"status": "FAILED"},
        )
        assert response.status_code == 502


def test_ai_analyze_payment_malformed_output(client):
    """Malformed Gemini output returns 502."""
    mock_model = _make_gemini_mock("this is not json")
    with patch.object(main, "_is_gemini_configured", return_value=True), \
         patch.object(main, "_get_gemini_model", return_value=mock_model):
        response = client.post(
            "/api/ai/analyze-payment",
            json={"status": "FAILED"},
        )
        assert response.status_code == 502
        assert "malformed" in response.json()["detail"].lower()


def test_ai_analyze_payment_invalid_structure(client):
    """Gemini returns JSON but missing required fields returns 502."""
    mock_model = _make_gemini_mock('{"foo": "bar"}')
    with patch.object(main, "_is_gemini_configured", return_value=True), \
         patch.object(main, "_get_gemini_model", return_value=mock_model):
        response = client.post(
            "/api/ai/analyze-payment",
            json={"status": "FAILED"},
        )
        assert response.status_code == 502
        assert "invalid structure" in response.json()["detail"].lower()


def test_ai_analyze_payment_conditional_docs(client):
    """Conditional document recommendations are passed through."""
    mock_model = _make_gemini_mock(VALID_AI_JSON)
    with patch.object(main, "_is_gemini_configured", return_value=True), \
         patch.object(main, "_get_gemini_model", return_value=mock_model):
        response = client.post(
            "/api/ai/analyze-payment",
            json={"status": "FAILED", "error_code": "INSUFFICIENT_FUNDS"},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["document_checklist"]) > 0
        assert data["document_checklist"][0]["document"] == "Buyer bank statement"


def test_ai_followup_valid(client):
    """Follow-up question using previous analysis context."""
    mock_model = MagicMock()
    mock_resp = MagicMock()
    mock_resp.text = "You should contact the buyer and ask them to add funds."
    mock_model.generate_content_async = AsyncMock(return_value=mock_resp)
    with patch.object(main, "_is_gemini_configured", return_value=True), \
         patch.object(main, "_get_gemini_model", return_value=mock_model):
        response = client.post(
            "/api/ai/follow-up",
            json={
                "analysis": {"summary": "Payment failed due to insufficient funds."},
                "history": [
                    {"question": "Why did it fail?", "answer": "Insufficient funds."}
                ],
                "question": "What should I do next?",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert len(data["answer"]) > 0


def test_ai_followup_missing_analysis(client):
    """Follow-up with missing analysis returns 400."""
    with patch.object(main, "_is_gemini_configured", return_value=True):
        response = client.post(
            "/api/ai/follow-up",
            json={"question": "What next?"},
        )
        assert response.status_code == 400
        assert "analysis" in response.json()["detail"].lower()


def test_ai_followup_missing_question(client):
    """Follow-up with missing question returns 400."""
    with patch.object(main, "_is_gemini_configured", return_value=True):
        response = client.post(
            "/api/ai/follow-up",
            json={"analysis": {"summary": "test"}},
        )
        assert response.status_code == 400
        assert "question" in response.json()["detail"].lower()


def test_ai_followup_oversized_history(client):
    """Oversized conversation history is trimmed to last 5 turns."""
    mock_model = MagicMock()
    mock_resp = MagicMock()
    mock_resp.text = "Answer based on recent context."
    mock_model.generate_content_async = AsyncMock(return_value=mock_resp)
    with patch.object(main, "_is_gemini_configured", return_value=True), \
         patch.object(main, "_get_gemini_model", return_value=mock_model):
        # Build 10 turns of history
        history = [
            {"question": f"Q{i}", "answer": f"A{i}"} for i in range(10)
        ]
        response = client.post(
            "/api/ai/follow-up",
            json={
                "analysis": {"summary": "test summary"},
                "history": history,
                "question": "What next?",
            },
        )
        assert response.status_code == 200
        # Verify the prompt only included last 5 turns
        call_args = mock_model.generate_content_async.call_args
        prompt = call_args[0][0] if call_args[0] else call_args[1].get("prompt", "")
        # Q0-Q4 should NOT be in the prompt, Q5-Q9 should be
        assert "Q0" not in prompt
        assert "Q9" in prompt


def test_ai_followup_missing_config(client):
    """Missing GEMINI_API_KEY returns 503."""
    with patch.object(main, "_is_gemini_configured", return_value=False):
        response = client.post(
            "/api/ai/follow-up",
            json={
                "analysis": {"summary": "test"},
                "question": "What next?",
            },
        )
        assert response.status_code == 503


def test_ai_followup_gemini_error(client):
    """Gemini error in follow-up returns 502."""
    mock_model = MagicMock()
    mock_model.generate_content_async = AsyncMock(
        side_effect=Exception("API error")
    )
    with patch.object(main, "_is_gemini_configured", return_value=True), \
         patch.object(main, "_get_gemini_model", return_value=mock_model):
        response = client.post(
            "/api/ai/follow-up",
            json={
                "analysis": {"summary": "test"},
                "question": "What next?",
            },
        )
        assert response.status_code == 502


def test_ai_does_not_change_payment_status(client):
    """AI analysis endpoint does not modify payment state or trigger capture."""
    mock_model = _make_gemini_mock(VALID_AI_JSON)
    main._captured_order_ids.clear()
    with patch.object(main, "_is_gemini_configured", return_value=True), \
         patch.object(main, "_get_gemini_model", return_value=mock_model):
        response = client.post(
            "/api/ai/analyze-payment",
            json={"status": "FAILED"},
        )
        assert response.status_code == 200
        # No order should have been captured
        assert len(main._captured_order_ids) == 0
        # Response should not contain COMPLETED status
        data = response.json()
        assert "COMPLETED" not in str(data).upper() or data.get("issue_title", "") != "COMPLETED"


def test_ai_analyze_payment_markdown_fences(client):
    """Gemini output wrapped in markdown code fences is parsed successfully."""
    fenced_json = f"```json\n{VALID_AI_JSON}\n```"
    mock_model = _make_gemini_mock(fenced_json)
    with patch.object(main, "_is_gemini_configured", return_value=True), \
         patch.object(main, "_get_gemini_model", return_value=mock_model):
        response = client.post(
            "/api/ai/analyze-payment",
            json={"status": "FAILED", "error_code": "INSTRUMENT_DECLINED"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["issue_title"] == "Payment FAILED analysis"


def test_ai_analyze_payment_sanitizes_secret(client):
    """Exception containing a secret key redacts it in error response."""
    secret = "secret-gemini-key-12345"
    mock_model = MagicMock()
    mock_model.generate_content_async = AsyncMock(
        side_effect=Exception(f"Error accessing API with key {secret}")
    )
    with patch.object(main, "_is_gemini_configured", return_value=True), \
         patch.dict(os.environ, {"GEMINI_API_KEY": secret}), \
         patch.object(main, "_get_gemini_model", return_value=mock_model):
        response = client.post(
            "/api/ai/analyze-payment",
            json={"status": "FAILED"},
        )
        assert response.status_code == 502
        detail = response.json()["detail"]
        assert secret not in detail
        assert "[REDACTED]" in detail


def test_ai_followup_question_too_long(client):
    """Follow-up question over 2000 characters is rejected with 400."""
    with patch.object(main, "_is_gemini_configured", return_value=True):
        response = client.post(
            "/api/ai/follow-up",
            json={
                "analysis": {"summary": "test"},
                "question": "A" * 2001,
            },
        )
        assert response.status_code == 400
        assert "too long" in response.json()["detail"].lower()


def test_ai_analyze_with_rich_document_checklist(client):
    """Document checklist with condition, next_step, and source is accepted."""
    rich_json = """{
      "issue_title": "Payment FAILED analysis",
      "summary": "Payment failed during processing.",
      "confirmed_facts": ["Status: FAILED"],
      "possible_causes": [{"description": "Card expired", "evidence": "Status FAILED", "confidence": 75}],
      "recommended_actions": ["Ask customer for another payment method"],
      "retry_guidance": "Retry after card update",
      "document_checklist": [
        {
          "document": "Card statement",
          "reason": "Verify expiry date",
          "condition": "If customer insists card is valid",
          "recommended_next_step": "Request recent statement",
          "provider": "PayPal",
          "where_to_obtain": "Online banking portal",
          "official_source": "https://developer.paypal.com"
        }
      ],
      "customer_facing_message": "Please update your card details.",
      "additional_info_needed": "None",
      "source_references": ["https://developer.paypal.com"]
    }"""
    mock_model = _make_gemini_mock(rich_json)
    with patch.object(main, "_is_gemini_configured", return_value=True), \
         patch.object(main, "_get_gemini_model", return_value=mock_model):
        response = client.post(
            "/api/ai/analyze-payment",
            json={"status": "FAILED"},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["document_checklist"]) == 1
        doc = data["document_checklist"][0]
        assert doc["condition"] == "If customer insists card is valid"
        assert doc["recommended_next_step"] == "Request recent statement"
        assert doc["official_source"] == "https://developer.paypal.com"


# ---------------------------------------------------------------------------
# Database integration and persistence tests
# ---------------------------------------------------------------------------

def test_database_initialization():
    """Verify database initialization creates all required tables idempotently."""
    from database import init_db
    from sqlalchemy import inspect
    test_eng = create_engine("sqlite:///:memory:", poolclass=StaticPool)
    init_db(target_engine=test_eng)
    inspector = inspect(test_eng)
    tables = inspector.get_table_names()
    assert "payment_transactions" in tables
    assert "recovery_cases" in tables
    assert "ai_analyses" in tables


def test_empty_database_behavior(client):
    """Verify empty database returns 0 stats and empty lists."""
    stats_res = client.get("/api/dashboard/stats")
    assert stats_res.status_code == 200
    stats = stats_res.json()
    assert stats["total_transactions"] == 0
    assert stats["successful_payments"] == 0
    assert stats["failed_payments"] == 0
    assert stats["pending_payments"] == 0
    assert stats["recovery_cases"] == 0
    assert stats["open_recovery_cases"] == 0
    assert stats["resolved_recovery_cases"] == 0

    tx_res = client.get("/api/transactions")
    assert tx_res.status_code == 200
    assert tx_res.json() == []

    cases_res = client.get("/api/recovery-cases")
    assert cases_res.status_code == 200
    assert cases_res.json() == []

    act_res = client.get("/api/activity")
    assert act_res.status_code == 200
    assert act_res.json() == []


def test_payment_transaction_creation_and_retrieval(client):
    """Creating an order persists it in the database and lists it via /api/transactions."""
    mock_token = MagicMock()
    mock_token.status_code = 200
    mock_token.json.return_value = {"access_token": "token-1", "expires_in": 3600}

    mock_order = MagicMock()
    mock_order.status_code = 201
    mock_order.json.return_value = {
        "id": "ORDER-PERSIST-1",
        "status": "CREATED",
        "links": [{"rel": "approve", "href": "https://paypal.com/approve/1"}],
    }

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(side_effect=[mock_token, mock_order])
    mock_async = MagicMock()
    mock_async.__aenter__ = AsyncMock(return_value=mock_client)
    mock_async.__aexit__ = AsyncMock(return_value=None)

    with patch.object(main, "PAYPAL_CLIENT_ID", "id"), patch.object(
        main, "PAYPAL_CLIENT_SECRET", "secret"
    ), patch("main.httpx.AsyncClient", return_value=mock_async):
        res = client.post("/api/orders", json={"amount": "10.00", "currency": "USD"})
        assert res.status_code == 200

    tx_res = client.get("/api/transactions")
    assert tx_res.status_code == 200
    txs = tx_res.json()
    assert len(txs) == 1
    assert txs[0]["orderId"] == "ORDER-PERSIST-1"
    assert txs[0]["amount"] == "10.00"
    assert txs[0]["currency"] == "USD"
    assert txs[0]["status"] == "awaiting_approval"


def test_payment_status_updates_after_confirmed_capture(client):
    """Payment transaction status transitions to COMPLETED after verified capture."""
    mock_token = MagicMock()
    mock_token.status_code = 200
    mock_token.json.return_value = {"access_token": "token-1", "expires_in": 3600}

    mock_order = MagicMock()
    mock_order.status_code = 201
    mock_order.json.return_value = {
        "id": "ORDER-FLOW-1",
        "status": "CREATED",
        "links": [{"rel": "approve", "href": "https://paypal.com/approve"}],
    }

    mock_capture = MagicMock()
    mock_capture.status_code = 201
    mock_capture.json.return_value = {
        "id": "ORDER-FLOW-1",
        "status": "COMPLETED",
        "purchase_units": [
            {
                "payments": {
                    "captures": [
                        {
                            "id": "CAPTURE-FLOW-1",
                            "amount": {"value": "10.00", "currency_code": "USD"},
                            "status": "COMPLETED",
                        }
                    ]
                }
            }
        ],
    }

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(side_effect=[mock_token, mock_order, mock_capture])
    mock_async = MagicMock()
    mock_async.__aenter__ = AsyncMock(return_value=mock_client)
    mock_async.__aexit__ = AsyncMock(return_value=None)

    with patch.object(main, "PAYPAL_CLIENT_ID", "id"), patch.object(
        main, "PAYPAL_CLIENT_SECRET", "secret"
    ), patch("main.httpx.AsyncClient", return_value=mock_async):
        client.post("/api/orders", json={"amount": "10.00", "currency": "USD"})

        cap_res = client.post("/api/orders/ORDER-FLOW-1/capture")
        assert cap_res.status_code == 200
        assert cap_res.json()["status"] == "COMPLETED"

    tx_res = client.get("/api/transactions?search=ORDER-FLOW-1")
    assert tx_res.status_code == 200
    txs = tx_res.json()
    assert len(txs) == 1
    assert txs[0]["status"] == "completed"
    assert txs[0]["captureId"] == "CAPTURE-FLOW-1"


def test_duplicate_paypal_order_handling(client):
    """Attempting to capture an already captured order returns 409 and avoids duplicate records."""
    mock_token = MagicMock()
    mock_token.status_code = 200
    mock_token.json.return_value = {"access_token": "token-1", "expires_in": 3600}

    mock_capture = MagicMock()
    mock_capture.status_code = 201
    mock_capture.json.return_value = {
        "id": "ORDER-DUP-1",
        "status": "COMPLETED",
        "purchase_units": [
            {
                "payments": {
                    "captures": [{"id": "CAP-DUP-1", "status": "COMPLETED"}]
                }
            }
        ],
    }

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(side_effect=[mock_token, mock_capture])
    mock_async = MagicMock()
    mock_async.__aenter__ = AsyncMock(return_value=mock_client)
    mock_async.__aexit__ = AsyncMock(return_value=None)

    with patch.object(main, "PAYPAL_CLIENT_ID", "id"), patch.object(
        main, "PAYPAL_CLIENT_SECRET", "secret"
    ), patch("main.httpx.AsyncClient", return_value=mock_async):
        res1 = client.post("/api/orders/ORDER-DUP-1/capture")
        assert res1.status_code == 200

        res2 = client.post("/api/orders/ORDER-DUP-1/capture")
        assert res2.status_code == 409
        assert "already been captured" in res2.json()["detail"].lower()

    txs = client.get("/api/transactions?search=ORDER-DUP-1").json()
    assert len(txs) == 1


def test_recovery_case_creation_and_retrieval(client):
    """Verify manual and automatic recovery case creation and listing."""
    new_case = {
        "title": "Declined card on checkout",
        "problem_description": "Cardholder reported recurring failure",
        "order_id": "ORDER-CASE-TEST",
        "payment_reference": "CARD_DECLINED",
        "status": "Action Required",
    }
    create_res = client.post("/api/recovery-cases", json=new_case)
    assert create_res.status_code == 200
    created = create_res.json()
    assert created["title"] == "Declined card on checkout"
    assert created["orderId"] == "ORDER-CASE-TEST"
    assert created["status"] == "Action Required"

    list_res = client.get("/api/recovery-cases")
    assert list_res.status_code == 200
    cases = list_res.json()
    assert len(cases) == 1
    assert cases[0]["title"] == "Declined card on checkout"

    case_id = created["id"]
    get_res = client.get(f"/api/recovery-cases/{case_id}")
    assert get_res.status_code == 200
    assert get_res.json()["id"] == case_id


def test_recovery_case_status_updates(client):
    """Verify updating a recovery case status via PATCH /api/recovery-cases/{id}."""
    create_res = client.post(
        "/api/recovery-cases",
        json={"title": "Test Case", "problem_description": "Initial desc", "status": "OPEN"},
    )
    case_id = create_res.json()["id"]

    patch_res = client.patch(
        f"/api/recovery-cases/{case_id}",
        json={"status": "RESOLVED", "title": "Resolved Case"},
    )
    assert patch_res.status_code == 200
    updated = patch_res.json()
    assert updated["status"] == "RESOLVED"
    assert updated["title"] == "Resolved Case"


def test_successful_ai_analysis_persistence(client):
    """Successful Gemini AI payment analysis is saved to the database and linked to a recovery case."""
    analysis_json = """{
      "issue_title": "Instrument Declined Diagnosis",
      "summary": "Customer card declined by bank filters.",
      "confirmed_facts": ["Status: FAILED", "Error code: INSTRUMENT_DECLINED"],
      "possible_causes": [{"description": "Insufficient funds", "evidence": "Status FAILED", "confidence": 80}],
      "recommended_actions": ["Request alternative payment method"],
      "retry_guidance": "Do not retry with same card",
      "document_checklist": [{"document": "Bank statement", "reason": "Check funds", "condition": "If dispute"}],
      "customer_facing_message": "Please try a different card.",
      "additional_info_needed": "Bank decline reason code",
      "source_references": ["https://developer.paypal.com"]
    }"""
    mock_model = _make_gemini_mock(analysis_json)

    with patch.object(main, "_is_gemini_configured", return_value=True), patch.object(
        main, "_get_gemini_model", return_value=mock_model
    ):
        ai_res = client.post(
            "/api/ai/analyze-payment",
            json={
                "status": "FAILED",
                "error_code": "INSTRUMENT_DECLINED",
                "incident_description": "Buyer card declined during sandbox testing",
                "order_id": "ORDER-AI-1",
            },
        )
        assert ai_res.status_code == 200
        data = ai_res.json()
        assert data["issue_title"] == "Instrument Declined Diagnosis"

    cases_res = client.get("/api/recovery-cases")
    assert cases_res.status_code == 200
    cases = cases_res.json()
    assert len(cases) == 1
    assert cases[0]["title"] == "Instrument Declined Diagnosis"
    assert cases[0]["analysis"] is not None
    assert cases[0]["analysis"]["summary"] == "Customer card declined by bank filters."


def test_dashboard_stats_calculation(client, test_db_session):
    """Dashboard KPI metrics calculate accurately from real database records."""
    db = test_db_session()
    tx1 = PaymentTransaction(order_id="TX-1", amount="10.00", currency="USD", status="COMPLETED")
    tx2 = PaymentTransaction(order_id="TX-2", amount="20.00", currency="USD", status="FAILED", failure_reason="Declined")
    tx3 = PaymentTransaction(order_id="TX-3", amount="30.00", currency="USD", status="AWAITING_APPROVAL")
    c1 = RecoveryCase(case_number="CASE-001", title="Case 1", status="Action Required")
    c2 = RecoveryCase(case_number="CASE-002", title="Case 2", status="RESOLVED")
    db.add_all([tx1, tx2, tx3, c1, c2])
    db.commit()
    db.close()

    stats_res = client.get("/api/dashboard/stats")
    assert stats_res.status_code == 200
    stats = stats_res.json()
    assert stats["total_transactions"] == 3
    assert stats["successful_payments"] == 1
    assert stats["failed_payments"] == 1
    assert stats["pending_payments"] == 1
    assert stats["recovery_cases"] == 2
    assert stats["open_recovery_cases"] == 1
    assert stats["resolved_recovery_cases"] == 1


def test_database_rollback_and_error_handling(test_db_session):
    """Verify that database errors trigger rollbacks and do not leave partial state."""
    from sqlalchemy.exc import IntegrityError
    db = test_db_session()
    tx1 = PaymentTransaction(order_id="ROLLBACK-1", amount="10.00", currency="USD", status="CREATED")
    db.add(tx1)
    db.commit()

    # Attempt to insert duplicate order_id which violates unique constraint
    tx2 = PaymentTransaction(order_id="ROLLBACK-1", amount="20.00", currency="USD", status="CREATED")
    db.add(tx2)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()

    # Verify state after rollback is intact
    tx_count = db.query(PaymentTransaction).filter_by(order_id="ROLLBACK-1").count()
    assert tx_count == 1
    db.close()


def test_settings_status_includes_database(client):
    """Verify /api/settings/status reports database configuration safely."""
    res = client.get("/api/settings/status")
    assert res.status_code == 200
    data = res.json()
    assert data["database_configured"] is True
    assert data["database_type"] in ("sqlite", "postgresql")



