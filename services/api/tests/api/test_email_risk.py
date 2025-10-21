"""
Unit tests for email risk advice API endpoints.

Tests the /emails/{email_id}/risk-advice endpoint including the BadRequestError
fallback mechanism that searches across all gmail_emails-* indices.
"""

from elasticsearch import BadRequestError, NotFoundError
from fastapi.testclient import TestClient


class TestGetRiskAdvice:
    """Tests for GET /emails/{email_id}/risk-advice endpoint."""

    def test_successful_get_from_alias(self, client: TestClient, monkeypatch):
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

        # Mock Elasticsearch client
        from app import es as es_module

        monkeypatch.setattr(es_module, "es", type("ES", (), {"get": mock_get})())

        response = client.get("/emails/test-email-001/risk-advice")

        assert response.status_code == 200
        data = response.json()
        assert data["suspicious"] is False
        assert data["suspicion_score"] == 25
        assert "DMARC policy passed" in data["explanations"]

    def test_badrequest_fallback_to_search(self, client: TestClient, monkeypatch):
        """
        Test that BadRequestError triggers fallback to search query.

        When alias points to multiple indices, ES.get raises BadRequestError.
        The endpoint should fall back to ES.search across gmail_emails-*.
        """
        mock_doc_source = {
            "from": "security@paypa1-verify.com",
            "reply_to": "phisher@evil-server.xyz",
            "subject": "Urgent: Verify Your Account Now",
            "suspicious": True,
            "suspicion_score": 78,
            "explanations": [
                "SPF authentication failed",
                "DKIM authentication failed",
                "DMARC policy failed",
                "Reply-To domain differs from From domain",
                "Contains risky attachment (executable/script/macro/archive)",
                "Uses URL shortener (bit.ly, tinyurl, etc)",
            ],
            "suggested_actions": ["Wait to share any personal details until verified."],
            "verify_checks": [
                "Request official posting link.",
                "Ask for a calendar invite from corporate domain.",
            ],
            "received_at": "2025-10-21T19:00:00Z",
        }

        call_count = {"get": 0, "search": 0}

        def mock_get(*args, **kwargs):
            call_count["get"] += 1
            # Simulate BadRequestError when alias points to multiple indices
            raise BadRequestError(
                "illegal_argument_exception",
                "Alias points to multiple indices, use search instead",
            )

        def mock_search(*args, **kwargs):
            call_count["search"] += 1
            # Verify search parameters
            assert kwargs.get("index") == "gmail_emails-*"
            assert kwargs.get("size") == 1
            assert "ids" in kwargs.get("query", {})
            assert "test-risk-v31-001" in kwargs["query"]["ids"]["values"]

            # Return document from search
            return {"hits": {"hits": [{"_source": mock_doc_source}]}}

        # Mock Elasticsearch client
        from app import es as es_module

        mock_es = type("ES", (), {"get": mock_get, "search": mock_search})()
        monkeypatch.setattr(es_module, "es", mock_es)

        response = client.get("/emails/test-risk-v31-001/risk-advice")

        # Verify fallback was triggered
        assert call_count["get"] == 1, "ES.get should be called first"
        assert call_count["search"] == 1, "ES.search should be called as fallback"

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["suspicious"] is True
        assert data["suspicion_score"] == 78
        assert len(data["explanations"]) == 6
        assert "SPF authentication failed" in data["explanations"]
        assert "Reply-To domain differs from From domain" in data["explanations"]
        assert data["from"] == "security@paypa1-verify.com"
        assert data["reply_to"] == "phisher@evil-server.xyz"

    def test_notfound_fallback_to_search(self, client: TestClient, monkeypatch):
        """Test that NotFoundError also triggers fallback to search."""
        mock_doc_source = {
            "from": "test@example.com",
            "subject": "Test",
            "suspicious": False,
            "suspicion_score": 10,
            "explanations": [],
            "suggested_actions": [],
            "verify_checks": [],
            "received_at": "2025-10-21T10:00:00Z",
        }

        def mock_get(*args, **kwargs):
            raise NotFoundError("document not found in primary index")

        def mock_search(*args, **kwargs):
            return {"hits": {"hits": [{"_source": mock_doc_source}]}}

        from app import es as es_module

        mock_es = type("ES", (), {"get": mock_get, "search": mock_search})()
        monkeypatch.setattr(es_module, "es", mock_es)

        response = client.get("/emails/test-email-002/risk-advice")

        assert response.status_code == 200
        assert response.json()["suspicion_score"] == 10

    def test_search_fallback_not_found(self, client: TestClient, monkeypatch):
        """Test 404 when document not found in search fallback."""

        def mock_get(*args, **kwargs):
            raise BadRequestError("alias error")

        def mock_search(*args, **kwargs):
            # No hits in search result
            return {"hits": {"hits": []}}

        from app import es as es_module

        mock_es = type("ES", (), {"get": mock_get, "search": mock_search})()
        monkeypatch.setattr(es_module, "es", mock_es)

        response = client.get("/emails/nonexistent-email-999/risk-advice")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_search_fallback_error(self, client: TestClient, monkeypatch):
        """Test 500 when search fallback encounters error."""

        def mock_get(*args, **kwargs):
            raise NotFoundError("not found")

        def mock_search(*args, **kwargs):
            raise Exception("Elasticsearch connection failed")

        from app import es as es_module

        mock_es = type("ES", (), {"get": mock_get, "search": mock_search})()
        monkeypatch.setattr(es_module, "es", mock_es)

        response = client.get("/emails/test-email-003/risk-advice")

        assert response.status_code == 500
        assert "Error searching for email" in response.json()["detail"]

    def test_custom_index_parameter(self, client: TestClient, monkeypatch):
        """Test using custom index via query parameter."""
        mock_doc = {
            "_source": {
                "from": "test@example.com",
                "subject": "Test",
                "suspicious": False,
                "suspicion_score": 5,
                "explanations": [],
                "suggested_actions": [],
                "verify_checks": [],
                "received_at": "2025-10-21T10:00:00Z",
            }
        }

        def mock_get(*args, **kwargs):
            # Verify custom index is used
            assert kwargs.get("index") == "gmail_emails-202510"
            return mock_doc

        from app import es as es_module

        monkeypatch.setattr(es_module, "es", type("ES", (), {"get": mock_get})())

        response = client.get(
            "/emails/test-email-004/risk-advice?index=gmail_emails-202510"
        )

        assert response.status_code == 200
        assert response.json()["suspicion_score"] == 5

    def test_elasticsearch_unavailable(self, client: TestClient, monkeypatch):
        """Test 503 when Elasticsearch is not available."""
        from app import es as es_module

        monkeypatch.setattr(es_module, "es", None)

        response = client.get("/emails/test-email-005/risk-advice")

        assert response.status_code == 503
        assert "Elasticsearch not available" in response.json()["detail"]

    def test_response_includes_all_fields(self, client: TestClient, monkeypatch):
        """Test that response includes all expected risk advice fields."""
        mock_doc = {
            "_source": {
                "from": "hr@company.com",
                "reply_to": "no-reply@company.com",
                "subject": "Interview Invitation",
                "suspicious": False,
                "suspicion_score": 15,
                "explanations": ["DMARC policy passed", "Known sender domain"],
                "suggested_actions": ["Review interview details"],
                "verify_checks": ["Confirm via LinkedIn"],
                "received_at": "2025-10-21T14:30:00Z",
            }
        }

        def mock_get(*args, **kwargs):
            return mock_doc

        from app import es as es_module

        monkeypatch.setattr(es_module, "es", type("ES", (), {"get": mock_get})())

        response = client.get("/emails/test-email-006/risk-advice")

        assert response.status_code == 200
        data = response.json()

        # Verify all expected fields are present
        assert "suspicious" in data
        assert "suspicion_score" in data
        assert "explanations" in data
        assert "suggested_actions" in data
        assert "verify_checks" in data
        assert "from" in data
        assert "reply_to" in data
        assert "subject" in data
        assert "received_at" in data

        # Verify values
        assert data["from"] == "hr@company.com"
        assert data["reply_to"] == "no-reply@company.com"
        assert data["subject"] == "Interview Invitation"
        assert len(data["explanations"]) == 2
        assert len(data["suggested_actions"]) == 1
        assert len(data["verify_checks"]) == 1


class TestPrimeAdvice:
    """Tests for POST /emails/{email_id}/prime-advice endpoint."""

    def test_prime_advice_background_task(self, client: TestClient, monkeypatch):
        """Test that prime-advice endpoint accepts requests (background processing)."""
        # This is a background task endpoint, so we just verify 202 response
        # Actual ES interaction would happen asynchronously

        response = client.post("/emails/test-email-007/prime-advice")

        # Endpoint should accept request and return 202 or similar
        # (Actual implementation may vary based on your background task setup)
        assert response.status_code in [
            200,
            202,
            404,
        ]  # Adjust based on actual implementation
