# Phase 5.5 PR5: Policy Bundle Signing Utility
# Reusable HMAC signing for policy bundles (import/export)

import hashlib
import hmac
import json
from datetime import datetime, timedelta
from typing import Any


def sign_bundle(
    bundle: dict[str, Any],
    secret_key: str,
    expiry_hours: int = 24
) -> dict[str, Any]:
    """
    Sign a policy bundle for export.
    
    Args:
        bundle: Policy bundle to sign
        secret_key: HMAC secret key
        expiry_hours: Signature expiry in hours
    
    Returns:
        Signed bundle with signature and metadata
    """
    # Add export metadata
    export_data = {
        "bundle": bundle,
        "exported_at": datetime.utcnow().isoformat(),
        "expires_at": (datetime.utcnow() + timedelta(hours=expiry_hours)).isoformat(),
        "format_version": "1.0"
    }
    
    # Generate signature
    message = json.dumps(export_data["bundle"], sort_keys=True).encode("utf-8")
    signature = hmac.new(
        secret_key.encode("utf-8"),
        message,
        hashlib.sha256
    ).hexdigest()
    
    export_data["signature"] = signature
    
    return export_data


def verify_bundle(
    signed_bundle: dict[str, Any],
    secret_key: str
) -> tuple[bool, str | None]:
    """
    Verify a signed policy bundle.
    
    Args:
        signed_bundle: Signed bundle with signature
        secret_key: HMAC secret key
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check required fields
    if "bundle" not in signed_bundle:
        return False, "Missing 'bundle' field"
    if "signature" not in signed_bundle:
        return False, "Missing 'signature' field"
    if "expires_at" not in signed_bundle:
        return False, "Missing 'expires_at' field"
    
    # Check expiry
    try:
        expires_at = datetime.fromisoformat(signed_bundle["expires_at"])
        if datetime.utcnow() > expires_at:
            return False, "Signature expired"
    except (ValueError, TypeError):
        return False, "Invalid expiry date format"
    
    # Verify signature
    message = json.dumps(signed_bundle["bundle"], sort_keys=True).encode("utf-8")
    expected_signature = hmac.new(
        secret_key.encode("utf-8"),
        message,
        hashlib.sha256
    ).hexdigest()
    
    provided_signature = signed_bundle["signature"]
    
    if not hmac.compare_digest(expected_signature, provided_signature):
        return False, "Invalid signature"
    
    return True, None


def sign_payload(payload: dict[str, Any], secret_key: str) -> str:
    """
    Generate HMAC-SHA256 signature for a payload.
    
    Args:
        payload: Data to sign
        secret_key: HMAC secret key
    
    Returns:
        Hex-encoded signature
    """
    message = json.dumps(payload, sort_keys=True).encode("utf-8")
    signature = hmac.new(
        secret_key.encode("utf-8"),
        message,
        hashlib.sha256
    ).hexdigest()
    return signature


def verify_payload(
    payload: dict[str, Any],
    signature: str,
    secret_key: str
) -> bool:
    """
    Verify HMAC-SHA256 signature for a payload.
    
    Args:
        payload: Data to verify
        signature: Signature to check
        secret_key: HMAC secret key
    
    Returns:
        True if signature is valid
    """
    expected = sign_payload(payload, secret_key)
    return hmac.compare_digest(signature, expected)
