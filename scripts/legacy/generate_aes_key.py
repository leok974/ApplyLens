#!/usr/bin/env python3
# STATUS: unclear. Mentioned in REPO_AUDIT_PHASE1.md.
# If not used by 2025-12-31, move to scripts/legacy/.
"""
Generate a secure AES-256 key for token encryption.

Usage:
    python scripts/generate_aes_key.py

Output:
    A 256-bit (32 byte) random key, base64url-encoded.
    Safe to use as APPLYLENS_AES_KEY_BASE64 environment variable.
"""

import os
import base64


def generate_aes_key() -> str:
    """Generate a secure 256-bit AES key and return it base64url-encoded."""
    key_bytes = os.urandom(32)  # 256 bits = 32 bytes
    key_b64 = base64.urlsafe_b64encode(key_bytes).decode("ascii")
    return key_b64


if __name__ == "__main__":
    key = generate_aes_key()
    print("=" * 80)
    print("AES-256 Key Generated (Base64URL)")
    print("=" * 80)
    print()
    print(key)
    print()
    print("=" * 80)
    print("Usage:")
    print("=" * 80)
    print()
    print("1. Copy the key above")
    print("2. Store in GCP Secret Manager or AWS Secrets Manager:")
    print()
    print("   # GCP")
    print(
        f"   echo '{key}' | gcloud secrets versions add APPLYLENS_AES_KEY_BASE64 --data-file=-"
    )
    print()
    print("   # AWS")
    print(
        f"   aws secretsmanager create-secret --name APPLYLENS_AES_KEY_BASE64 --secret-string '{key}'"
    )
    print()
    print("3. Set as environment variable:")
    print()
    print(f"   export APPLYLENS_AES_KEY_BASE64='{key}'")
    print()
    print("=" * 80)
    print("⚠️  SECURITY WARNING")
    print("=" * 80)
    print()
    print("- NEVER commit this key to version control")
    print("- Store only in secure secret managers (GCP/AWS)")
    print("- Rotate keys periodically (every 90 days recommended)")
    print("- Use envelope encryption for production key rotation")
    print()
