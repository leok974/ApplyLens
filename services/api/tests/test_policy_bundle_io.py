# Phase 5.5 PR5: Policy Bundle Import/Export Tests
# Tests for signed bundle import/export with provenance

import json
from datetime import datetime, timedelta

import pytest
from httpx import AsyncClient

from app.utils.signing import sign_bundle, verify_bundle, sign_payload, verify_payload


class TestSigning:
    """Test signing utility functions."""
    
    def test_sign_bundle(self):
        """Test bundle signing."""
        bundle = {
            "version": "1.0.0",
            "rules": {"rules": []},
            "notes": "Test bundle"
        }
        
        signed = sign_bundle(bundle, secret_key="test-secret", expiry_hours=24)
        
        assert "signature" in signed
        assert "exported_at" in signed
        assert "expires_at" in signed
        assert signed["bundle"] == bundle
        assert signed["format_version"] == "1.0"
    
    def test_verify_bundle_valid(self):
        """Test verifying a valid signed bundle."""
        bundle = {
            "version": "1.0.0",
            "rules": {"rules": []},
            "notes": "Test bundle"
        }
        
        signed = sign_bundle(bundle, secret_key="test-secret", expiry_hours=24)
        is_valid, error = verify_bundle(signed, secret_key="test-secret")
        
        assert is_valid is True
        assert error is None
    
    def test_verify_bundle_invalid_signature(self):
        """Test verifying bundle with tampered signature."""
        bundle = {
            "version": "1.0.0",
            "rules": {"rules": []},
            "notes": "Test bundle"
        }
        
        signed = sign_bundle(bundle, secret_key="test-secret", expiry_hours=24)
        
        # Tamper with signature
        signed["signature"] = "invalid_signature"
        
        is_valid, error = verify_bundle(signed, secret_key="test-secret")
        
        assert is_valid is False
        assert "Invalid signature" in error
    
    def test_verify_bundle_expired(self):
        """Test verifying an expired bundle."""
        bundle = {
            "version": "1.0.0",
            "rules": {"rules": []},
            "notes": "Test bundle"
        }
        
        signed = sign_bundle(bundle, secret_key="test-secret", expiry_hours=24)
        
        # Set expiry to past
        signed["expires_at"] = (datetime.utcnow() - timedelta(hours=1)).isoformat()
        
        is_valid, error = verify_bundle(signed, secret_key="test-secret")
        
        assert is_valid is False
        assert "expired" in error.lower()
    
    def test_verify_bundle_tampered_data(self):
        """Test verifying bundle with tampered data."""
        bundle = {
            "version": "1.0.0",
            "rules": {"rules": []},
            "notes": "Test bundle"
        }
        
        signed = sign_bundle(bundle, secret_key="test-secret", expiry_hours=24)
        
        # Tamper with bundle data
        signed["bundle"]["version"] = "2.0.0"
        
        is_valid, error = verify_bundle(signed, secret_key="test-secret")
        
        assert is_valid is False
        assert "Invalid signature" in error
    
    def test_sign_payload(self):
        """Test payload signing."""
        payload = {"key": "value", "number": 123}
        
        signature = sign_payload(payload, secret_key="test-secret")
        
        assert isinstance(signature, str)
        assert len(signature) == 64  # SHA256 hex is 64 chars
    
    def test_verify_payload(self):
        """Test payload verification."""
        payload = {"key": "value", "number": 123}
        
        signature = sign_payload(payload, secret_key="test-secret")
        is_valid = verify_payload(payload, signature, secret_key="test-secret")
        
        assert is_valid is True
    
    def test_verify_payload_invalid(self):
        """Test payload verification with wrong signature."""
        payload = {"key": "value"}
        
        is_valid = verify_payload(payload, "wrong_signature", secret_key="test-secret")
        
        assert is_valid is False


@pytest.mark.asyncio
class TestBundleExport:
    """Test bundle export endpoints."""
    
    async def test_export_bundle(self, client: AsyncClient, db):
        """Test exporting a bundle."""
        # Create bundle
        create_response = await client.post(
            "/api/policy/bundles",
            json={
                "version": "1.0.0",
                "rules": [
                    {
                        "id": "test-rule",
                        "agent": "inbox.triage",
                        "action": "quarantine",
                        "effect": "allow",
                        "reason": "Test rule for export"
                    }
                ],
                "notes": "Test bundle",
                "created_by": "test@example.com"
            }
        )
        bundle_id = create_response.json()["id"]
        
        # Export bundle
        response = await client.get(f"/api/policy/bundles/{bundle_id}/export")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "signature" in data
        assert "exported_at" in data
        assert "expires_at" in data
        assert "bundle" in data
        assert data["format_version"] == "1.0"
        assert data["bundle"]["version"] == "1.0.0"
    
    async def test_export_bundle_not_found(self, client: AsyncClient):
        """Test exporting non-existent bundle."""
        response = await client.get("/api/policy/bundles/99999/export")
        
        assert response.status_code == 404
    
    async def test_export_bundle_custom_expiry(self, client: AsyncClient, db):
        """Test exporting with custom expiry."""
        # Create bundle
        create_response = await client.post(
            "/api/policy/bundles",
            json={
                "version": "1.0.0",
                "rules": [
                    {
                        "id": "test-rule",
                        "agent": "inbox.triage",
                        "action": "quarantine",
                        "effect": "allow",
                        "reason": "Test rule"
                    }
                ],
                "created_by": "test@example.com"
            }
        )
        bundle_id = create_response.json()["id"]
        
        # Export with 48h expiry
        response = await client.get(
            f"/api/policy/bundles/{bundle_id}/export?expiry_hours=48"
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check expiry is ~48 hours from now
        exported_at = datetime.fromisoformat(data["exported_at"])
        expires_at = datetime.fromisoformat(data["expires_at"])
        delta = (expires_at - exported_at).total_seconds() / 3600
        
        assert 47 <= delta <= 49  # Allow some variance
    
    async def test_download_bundle(self, client: AsyncClient, db):
        """Test downloading bundle as file."""
        # Create bundle
        create_response = await client.post(
            "/api/policy/bundles",
            json={
                "version": "1.2.3",
                "rules": [
                    {
                        "id": "test-rule",
                        "agent": "inbox.triage",
                        "action": "quarantine",
                        "effect": "allow",
                        "reason": "Test rule"
                    }
                ],
                "created_by": "test@example.com"
            }
        )
        bundle_id = create_response.json()["id"]
        
        # Download
        response = await client.get(
            f"/api/policy/bundles/{bundle_id}/export/download"
        )
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"
        assert "attachment" in response.headers["content-disposition"]
        assert "policy-bundle-1.2.3.json" in response.headers["content-disposition"]
        
        # Verify JSON content
        data = response.json()
        assert "signature" in data
        assert "bundle" in data


@pytest.mark.asyncio
class TestBundleImport:
    """Test bundle import endpoints."""
    
    async def test_import_valid_bundle(self, client: AsyncClient, db):
        """Test importing a valid signed bundle."""
        # Create and export a bundle
        create_response = await client.post(
            "/api/policy/bundles",
            json={
                "version": "1.0.0",
                "rules": [
                    {
                        "id": "export-test",
                        "agent": "inbox.triage",
                        "action": "quarantine",
                        "effect": "allow",
                        "reason": "Test rule for import"
                    }
                ],
                "notes": "Original bundle",
                "created_by": "exporter@example.com"
            }
        )
        bundle_id = create_response.json()["id"]
        
        export_response = await client.get(f"/api/policy/bundles/{bundle_id}/export")
        exported_data = export_response.json()
        
        # Import as new version
        import_response = await client.post(
            "/api/policy/bundles/import",
            json={
                **exported_data,
                "import_as_version": "1.1.0"  # New version
            }
        )
        
        assert import_response.status_code == 201
        data = import_response.json()
        
        assert data["version"] == "1.1.0"
        assert data["verified"] is True
        assert data["imported_from"] == "1.0.0"
        assert "Successfully imported" in data["message"]
    
    async def test_import_invalid_signature(self, client: AsyncClient):
        """Test importing bundle with invalid signature."""
        import_data = {
            "bundle": {
                "version": "1.0.0",
                "rules": {"rules": []},
                "notes": "Test"
            },
            "signature": "invalid_signature",
            "exported_at": datetime.utcnow().isoformat(),
            "expires_at": (datetime.utcnow() + timedelta(hours=24)).isoformat(),
            "format_version": "1.0",
            "import_as_version": "2.0.0"
        }
        
        response = await client.post("/api/policy/bundles/import", json=import_data)
        
        assert response.status_code == 400
        assert "verification failed" in response.json()["detail"].lower()
    
    async def test_import_expired_bundle(self, client: AsyncClient):
        """Test importing an expired bundle."""
        # Create expired bundle
        bundle = {
            "version": "1.0.0",
            "rules": {"rules": []},
            "notes": "Test"
        }
        
        signed = sign_bundle(bundle, secret_key="test-secret", expiry_hours=24)
        
        # Set expiry to past
        signed["expires_at"] = (datetime.utcnow() - timedelta(hours=1)).isoformat()
        
        response = await client.post(
            "/api/policy/bundles/import",
            json={
                **signed,
                "import_as_version": "2.0.0"
            }
        )
        
        assert response.status_code == 400
        assert "expired" in response.json()["detail"].lower()
    
    async def test_import_duplicate_version(self, client: AsyncClient, db):
        """Test importing with existing version fails."""
        # Create original bundle
        await client.post(
            "/api/policy/bundles",
            json={
                "version": "1.0.0",
                "rules": [
                    {
                        "id": "test",
                        "agent": "inbox.triage",
                        "action": "quarantine",
                        "effect": "allow",
                        "reason": "Test"
                    }
                ],
                "created_by": "test@example.com"
            }
        )
        
        # Try to import with same version
        bundle = {
            "version": "1.0.0",
            "rules": {"rules": []},
            "notes": "Test"
        }
        
        signed = sign_bundle(bundle, secret_key="test-secret", expiry_hours=24)
        
        response = await client.post(
            "/api/policy/bundles/import",
            json={
                **signed,
                "import_as_version": "1.0.0"
            }
        )
        
        assert response.status_code == 409
        assert "already exists" in response.json()["detail"]
    
    async def test_import_preserves_provenance(self, client: AsyncClient, db):
        """Test that import preserves provenance information."""
        # Export bundle
        create_response = await client.post(
            "/api/policy/bundles",
            json={
                "version": "1.0.0",
                "rules": [
                    {
                        "id": "test",
                        "agent": "inbox.triage",
                        "action": "quarantine",
                        "effect": "allow",
                        "reason": "Test"
                    }
                ],
                "created_by": "original@example.com",
                "metadata": {"env": "production"}
            }
        )
        bundle_id = create_response.json()["id"]
        
        export_response = await client.get(f"/api/policy/bundles/{bundle_id}/export")
        exported = export_response.json()
        
        # Import
        import_response = await client.post(
            "/api/policy/bundles/import",
            json={
                **exported,
                "import_as_version": "2.0.0"
            }
        )
        
        imported_id = import_response.json()["id"]
        
        # Verify provenance
        get_response = await client.get(f"/api/policy/bundles/{imported_id}")
        imported_bundle = get_response.json()
        
        assert imported_bundle["source"] == "imported"
        assert imported_bundle["metadata"]["env"] == "production"
        assert "imported_at" in imported_bundle["metadata"]
