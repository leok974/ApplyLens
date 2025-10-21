"""Unit tests for email risk advice API endpoints."""

from elasticsearch import BadRequestError, NotFoundError
from httpx import AsyncClient


class TestGetRiskAdvice:
    """Tests for GET /emails/{email_id}/risk-advice endpoint."""

    async def test_successful_get_from_alias(
        self, async_client: AsyncClient, monkeypatch
    ):
        """Test successful retrieval using gmail_emails alias."""
        mock_doc = {
            "_source": {
                "from": "security@paypal.com",
                "reply_to": None,
                "subject": "Your account was accessed",
                "suspicious": False,
                "suspicion_score": 25,
                "explanations": ["DMARC policy passed"],
                "suggested_actions": [],
                "verify_checks": [],
                "received_at": "2025-10-21T10:00:00Z",
            }
        }

        def mock_get(*args, **kwargs):
            return mock_doc

        # Mock ES in the routers.emails module where it's used
        from app.routers import emails as emails_module

        mock_es = type("ES", (), {"get": mock_get})()
        monkeypatch.setattr(emails_module, "es", mock_es)

        response = await async_client.get("/emails/test-email-001/risk-advice")

        assert response.status_code == 200
        data = response.json()
        assert data["suspicious"] is False
        assert data["suspicion_score"] == 25
        assert "DMARC policy passed" in data["explanations"]

    async def test_badrequest_fallback_to_search(
        self, async_client: AsyncClient, monkeypatch
    ):
        """
        Test that BadRequestError triggers fallback to search query.

        When alias points to multiple indices, ES.get raises BadRequestError.
        The endpoint should fall back to ES.search across gmail_emails-*.
        """
        mock_doc_source = {
            "from": "security@paypa1-verify.com",
            "reply_to": "phish@evil.com",
            "subject": "URGENT: Verify your account now!",
            "suspicious": True,
            "suspicion_score": 85,
            "explanations": [
                "From domain mismatch with PayPal",
                "Reply-to domain is suspicious",
            ],
            "suggested_actions": ["Mark as spam", "Report phishing"],
            "verify_checks": ["spf:fail", "dkim:fail"],
            "received_at": "2025-10-21T14:30:00Z",
        }

        # Track calls to verify fallback
        get_calls = []
        search_calls = []

        # Create a minimal mock meta object for the exception
        class MockMeta:
            status = 400

        def mock_get(*args, **kwargs):
            get_calls.append((args, kwargs))
            raise BadRequestError(
                "search_phase_execution_exception",
                MockMeta(),
                {"error": "Fielddata is disabled"},
            )

        def mock_search(*args, **kwargs):
            search_calls.append((args, kwargs))
            return {"hits": {"hits": [{"_source": mock_doc_source}]}}

        from app.routers import emails as emails_module

        mock_es = type("ES", (), {"get": mock_get, "search": mock_search})()
        monkeypatch.setattr(emails_module, "es", mock_es)

        response = await async_client.get("/emails/test-risk-v31-001/risk-advice")

        # Verify fallback behavior
        assert len(get_calls) == 1, "ES.get should be called first"
        assert (
            len(search_calls) == 1
        ), "ES.search should be called after BadRequestError"

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["suspicious"] is True
        assert data["suspicion_score"] == 85
        assert "From domain mismatch with PayPal" in data["explanations"]

    async def test_notfound_fallback_to_search(
        self, async_client: AsyncClient, monkeypatch
    ):
        """Test that NotFoundError also triggers fallback to search."""
        mock_doc_source = {
            "from": "newsletter@example.com",
            "reply_to": None,
            "subject": "Weekly updates",
            "suspicious": False,
            "suspicion_score": 10,
            "explanations": ["Recognized sender"],
            "suggested_actions": [],
            "verify_checks": [],
            "received_at": "2025-10-21T09:00:00Z",
        }

        class MockMeta:
            status = 404

        def mock_get(*args, **kwargs):
            raise NotFoundError(
                "index_not_found_exception",
                MockMeta(),
                {"error": "no such index [gmail_emails]"},
            )

        def mock_search(*args, **kwargs):
            return {"hits": {"hits": [{"_source": mock_doc_source}]}}

        from app.routers import emails as emails_module

        mock_es = type("ES", (), {"get": mock_get, "search": mock_search})()
        monkeypatch.setattr(emails_module, "es", mock_es)

        response = await async_client.get("/emails/weekly-newsletter-001/risk-advice")

        assert response.status_code == 200
        data = response.json()
        assert data["suspicious"] is False
        assert data["suspicion_score"] == 10

    async def test_search_fallback_not_found(
        self, async_client: AsyncClient, monkeypatch
    ):
        """Test 404 when email not found even after fallback search."""

        class MockMeta:
            status = 400

        def mock_get(*args, **kwargs):
            raise BadRequestError("error", MockMeta(), {"error": "Bad request"})

        def mock_search(*args, **kwargs):
            return {"hits": {"hits": []}}  # No results

        from app.routers import emails as emails_module

        mock_es = type("ES", (), {"get": mock_get, "search": mock_search})()
        monkeypatch.setattr(emails_module, "es", mock_es)

        response = await async_client.get("/emails/nonexistent-email/risk-advice")

        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()

    async def test_search_fallback_error(self, async_client: AsyncClient, monkeypatch):
        """Test 500 when search fallback raises an error."""

        class MockMeta:
            status = 400

        def mock_get(*args, **kwargs):
            raise BadRequestError("error", MockMeta(), {"error": "Bad request"})

        def mock_search(*args, **kwargs):
            raise Exception("Elasticsearch connection failed")

        from app.routers import emails as emails_module

        mock_es = type("ES", (), {"get": mock_get, "search": mock_search})()
        monkeypatch.setattr(emails_module, "es", mock_es)

        response = await async_client.get("/emails/error-case/risk-advice")

        assert response.status_code == 500

    async def test_custom_index_parameter(self, async_client: AsyncClient, monkeypatch):
        """Test custom index parameter works with direct get."""
        mock_doc = {
            "_source": {
                "from": "admin@company.com",
                "reply_to": None,
                "subject": "Internal notice",
                "suspicious": False,
                "suspicion_score": 5,
                "explanations": ["Internal sender"],
                "suggested_actions": [],
                "verify_checks": [],
                "received_at": "2025-10-21T08:00:00Z",
            }
        }

        get_index = None

        def mock_get(*args, **kwargs):
            nonlocal get_index
            get_index = kwargs.get("index")
            return mock_doc

        from app.routers import emails as emails_module

        mock_es = type("ES", (), {"get": mock_get})()
        monkeypatch.setattr(emails_module, "es", mock_es)

        response = await async_client.get(
            "/emails/internal-001/risk-advice?index=company_emails"
        )

        assert response.status_code == 200
        assert get_index == "company_emails"

    async def test_elasticsearch_unavailable(
        self, async_client: AsyncClient, monkeypatch
    ):
        """Test 503 when Elasticsearch is completely unavailable."""
        from app.routers import emails as emails_module

        # Set es to None to simulate unavailable ES
        monkeypatch.setattr(emails_module, "es", None)

        response = await async_client.get("/emails/unavailable-test/risk-advice")

        assert response.status_code == 503
        data = response.json()
        assert "not available" in data["detail"].lower()

    async def test_response_includes_all_fields(
        self, async_client: AsyncClient, monkeypatch
    ):
        """Test that response includes all expected RiskAdviceOut fields."""
        mock_doc = {
            "_source": {
                "from": "test@example.com",
                "reply_to": "reply@example.com",
                "subject": "Test Subject",
                "suspicious": True,
                "suspicion_score": 50,
                "explanations": ["Test explanation"],
                "suggested_actions": ["Test action"],
                "verify_checks": ["spf:pass"],
                "received_at": "2025-10-21T12:00:00Z",
            }
        }

        def mock_get(*args, **kwargs):
            return mock_doc

        from app.routers import emails as emails_module

        mock_es = type("ES", (), {"get": mock_get})()
        monkeypatch.setattr(emails_module, "es", mock_es)

        response = await async_client.get("/emails/field-test-001/risk-advice")

        assert response.status_code == 200
        data = response.json()

        # Verify all fields present
        assert "from" in data
        assert "reply_to" in data
        assert "subject" in data
        assert "suspicious" in data
        assert "suspicion_score" in data
        assert "explanations" in data
        assert "suggested_actions" in data
        assert "verify_checks" in data
        assert "received_at" in data

        # Verify values
        assert data["from"] == "test@example.com"
        assert data["reply_to"] == "reply@example.com"
        assert data["subject"] == "Test Subject"
        assert data["suspicious"] is True
        assert data["suspicion_score"] == 50
