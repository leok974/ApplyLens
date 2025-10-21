#!/usr/bin/env python3
"""
CLI for managing encryption key rotation with envelope encryption.

This script provides commands to:
- Generate new AES data keys and wrap them with KMS
- List all key versions
- Activate/deactivate key versions
- Re-encrypt tokens with new keys (background job)

Requirements:
- google-cloud-kms (for GCP KMS)
- boto3 (for AWS KMS)

Usage:
    python scripts/keys.py rotate --kms-key <gcp-or-aws-kms-key-id>
    python scripts/keys.py list
    python scripts/keys.py activate --version <number>
    python scripts/keys.py re-encrypt --from-version <old> --to-version <new>

Examples:
    # Rotate with GCP KMS
    python scripts/keys.py rotate --kms-key projects/my-project/locations/global/keyRings/applylens/cryptoKeys/token-key
    
    # Rotate with AWS KMS
    python scripts/keys.py rotate --kms-key arn:aws:kms:us-west-2:123456789012:key/12345678-1234-1234-1234-123456789012
    
    # List all versions
    python scripts/keys.py list
    
    # Activate a specific version
    python scripts/keys.py activate --version 2
    
    # Re-encrypt all tokens from version 1 to version 2
    python scripts/keys.py re-encrypt --from-version 1 --to-version 2
"""

import argparse
import base64
import os
import sys
from datetime import datetime
from uuid import uuid4

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'services', 'api'))

from app.db import SessionLocal
from app.models import OAuthToken
from sqlalchemy import text


def generate_data_key() -> bytes:
    """Generate a random 256-bit AES key."""
    return os.urandom(32)


def wrap_with_gcp_kms(plaintext_key: bytes, kms_key_id: str) -> bytes:
    """Wrap AES key using GCP Cloud KMS.
    
    Args:
        plaintext_key: 32-byte AES key to wrap
        kms_key_id: GCP KMS key resource name
        
    Returns:
        KMS-encrypted wrapped key
    """
    try:
        from google.cloud import kms
    except ImportError:
        print("ERROR: google-cloud-kms not installed. Run: pip install google-cloud-kms")
        sys.exit(1)
    
    client = kms.KeyManagementServiceClient()
    
    # Encrypt the plaintext key
    response = client.encrypt(
        request={
            "name": kms_key_id,
            "plaintext": plaintext_key
        }
    )
    
    return response.ciphertext


def wrap_with_aws_kms(plaintext_key: bytes, kms_key_id: str) -> bytes:
    """Wrap AES key using AWS KMS.
    
    Args:
        plaintext_key: 32-byte AES key to wrap
        kms_key_id: AWS KMS key ARN or alias
        
    Returns:
        KMS-encrypted wrapped key
    """
    try:
        import boto3
    except ImportError:
        print("ERROR: boto3 not installed. Run: pip install boto3")
        sys.exit(1)
    
    client = boto3.client('kms')
    
    # Encrypt the plaintext key
    response = client.encrypt(
        KeyId=kms_key_id,
        Plaintext=plaintext_key
    )
    
    return response['CiphertextBlob']


def rotate_key(kms_key_id: str):
    """Generate new AES key, wrap with KMS, and store in database.
    
    Args:
        kms_key_id: GCP or AWS KMS key identifier
    """
    print("=" * 80)
    print("KEY ROTATION")
    print("=" * 80)
    
    # Generate new AES-256 data key
    print("\n[1/5] Generating new AES-256 data key...")
    data_key = generate_data_key()
    print(f"      Generated {len(data_key)*8}-bit key")
    
    # Determine KMS provider and wrap key
    print(f"\n[2/5] Wrapping key with KMS...")
    print(f"      KMS Key: {kms_key_id}")
    
    if kms_key_id.startswith("projects/"):
        # GCP KMS
        print("      Provider: GCP Cloud KMS")
        wrapped_key = wrap_with_gcp_kms(data_key, kms_key_id)
    elif kms_key_id.startswith("arn:aws:kms:"):
        # AWS KMS
        print("      Provider: AWS KMS")
        wrapped_key = wrap_with_aws_kms(data_key, kms_key_id)
    else:
        print(f"ERROR: Unknown KMS key format: {kms_key_id}")
        print("Expected GCP format: projects/.../keyRings/.../cryptoKeys/...")
        print("Or AWS format: arn:aws:kms:region:account:key/...")
        sys.exit(1)
    
    print(f"      Wrapped key size: {len(wrapped_key)} bytes")
    
    # Connect to database
    print("\n[3/5] Connecting to database...")
    db = SessionLocal()
    
    try:
        # Get next version number
        result = db.execute(text("SELECT COALESCE(MAX(version), 0) + 1 FROM encryption_keys"))
        next_version = result.scalar()
        print(f"      Next version: {next_version}")
        
        # Deactivate current active key(s)
        print("\n[4/5] Deactivating old keys...")
        result = db.execute(
            text("UPDATE encryption_keys SET active = false, rotated_at = now() WHERE active = true RETURNING version")
        )
        old_versions = [row[0] for row in result]
        if old_versions:
            print(f"      Deactivated versions: {old_versions}")
        else:
            print("      No active keys to deactivate")
        
        # Insert new key
        print(f"\n[5/5] Storing new key version {next_version}...")
        db.execute(
            text("""
                INSERT INTO encryption_keys (id, version, kms_wrapped_key, algorithm, kms_key_id, active, created_at)
                VALUES (:id, :version, :wrapped_key, 'AES-GCM-256', :kms_key_id, true, now())
            """),
            {
                "id": str(uuid4()),
                "version": next_version,
                "wrapped_key": wrapped_key,
                "kms_key_id": kms_key_id
            }
        )
        db.commit()
        
        print("      ✅ Key stored successfully")
        print("\n" + "=" * 80)
        print("ROTATION COMPLETE")
        print("=" * 80)
        print(f"\n✅ New encryption key version {next_version} is now active")
        print("\nNext steps:")
        print("1. Restart API containers to load new key")
        print("2. New tokens will use version {next_version}")
        print("3. Old tokens (version {}) still decryptable".format(old_versions[0] if old_versions else "N/A"))
        print("4. Optional: Re-encrypt old tokens with:")
        print(f"   python scripts/keys.py re-encrypt --from-version {old_versions[0] if old_versions else 1} --to-version {next_version}")
        
    except Exception as e:
        db.rollback()
        print(f"\nERROR: {e}")
        sys.exit(1)
    finally:
        db.close()


def list_keys():
    """List all encryption key versions."""
    print("=" * 80)
    print("ENCRYPTION KEYS")
    print("=" * 80)
    
    db = SessionLocal()
    try:
        result = db.execute(
            text("""
                SELECT version, active, algorithm, created_at, rotated_at,
                       LEFT(kms_key_id, 50) || '...' as kms_key_short
                FROM encryption_keys
                ORDER BY version DESC
            """)
        )
        
        rows = result.fetchall()
        if not rows:
            print("\nNo encryption keys found.")
            print("\nTo create the first key, run:")
            print("  python scripts/keys.py rotate --kms-key <your-kms-key-id>")
            return
        
        print(f"\nFound {len(rows)} key version(s):\n")
        print(f"{'Version':<10} {'Status':<10} {'Algorithm':<15} {'Created':<20} {'Rotated':<20}")
        print("-" * 80)
        
        for row in rows:
            status = "🟢 ACTIVE" if row[1] else "🔴 inactive"
            created = row[3].strftime("%Y-%m-%d %H:%M:%S") if row[3] else "N/A"
            rotated = row[4].strftime("%Y-%m-%d %H:%M:%S") if row[4] else "-"
            print(f"{row[0]:<10} {status:<10} {row[2]:<15} {created:<20} {rotated:<20}")
        
        # Count tokens per version
        print("\n" + "=" * 80)
        print("TOKEN DISTRIBUTION")
        print("=" * 80)
        
        result = db.execute(
            text("""
                SELECT key_version, COUNT(*) as count
                FROM oauth_tokens
                GROUP BY key_version
                ORDER BY key_version
            """)
        )
        
        token_rows = result.fetchall()
        if token_rows:
            print(f"\n{'Version':<10} {'Token Count':<15}")
            print("-" * 80)
            for row in token_rows:
                print(f"{row[0] or 'NULL':<10} {row[1]:<15}")
        else:
            print("\nNo tokens found.")
            
    finally:
        db.close()


def activate_version(version: int):
    """Activate a specific key version."""
    print(f"Activating version {version}...")
    
    db = SessionLocal()
    try:
        # Check if version exists
        result = db.execute(
            text("SELECT version FROM encryption_keys WHERE version = :version"),
            {"version": version}
        )
        if not result.fetchone():
            print(f"ERROR: Version {version} not found")
            sys.exit(1)
        
        # Deactivate all keys
        db.execute(text("UPDATE encryption_keys SET active = false, rotated_at = now() WHERE active = true"))
        
        # Activate target version
        db.execute(
            text("UPDATE encryption_keys SET active = true, rotated_at = NULL WHERE version = :version"),
            {"version": version}
        )
        db.commit()
        
        print(f"✅ Version {version} is now active")
        print("\n⚠️  Restart API containers to load this key version")
        
    except Exception as e:
        db.rollback()
        print(f"ERROR: {e}")
        sys.exit(1)
    finally:
        db.close()


def re_encrypt_tokens(from_version: int, to_version: int, batch_size: int = 100):
    """Re-encrypt tokens from one key version to another.
    
    This is a STUB - actual implementation requires:
    1. Loading both key versions from KMS
    2. Decrypting with old key
    3. Encrypting with new key
    4. Updating database
    
    This is complex and should be implemented carefully!
    """
    print("=" * 80)
    print("TOKEN RE-ENCRYPTION (STUB)")
    print("=" * 80)
    print("\n⚠️  This feature is not fully implemented yet!")
    print("\nTo implement this, you need to:")
    print("1. Load wrapped keys for both versions from encryption_keys table")
    print("2. Unwrap both keys using KMS decrypt")
    print("3. For each token:")
    print("   - Decrypt access_token and refresh_token with old key")
    print("   - Encrypt with new key")
    print("   - Update oauth_tokens row with new ciphertext and key_version")
    print("4. Process in batches to avoid long transactions")
    print("\nThis is typically run as a background job, not a CLI command.")
    print("\nExample pseudocode:")
    print("""
    db = SessionLocal()
    old_key = unwrap_kms(get_key_version(from_version))
    new_key = unwrap_kms(get_key_version(to_version))
    
    tokens = db.query(OAuthToken).filter_by(key_version=from_version).limit(batch_size)
    for token in tokens:
        old_access = decrypt(token.access_token, old_key)
        old_refresh = decrypt(token.refresh_token, old_key)
        
        token.access_token = encrypt(old_access, new_key)
        token.refresh_token = encrypt(old_refresh, new_key)
        token.key_version = to_version
        db.add(token)
    
    db.commit()
    """)


def main():
    parser = argparse.ArgumentParser(
        description="Manage encryption key rotation with envelope encryption",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    subparsers = parser.add_subparsers(dest='command', required=True)
    
    # Rotate command
    rotate_parser = subparsers.add_parser('rotate', help='Generate new key and wrap with KMS')
    rotate_parser.add_argument('--kms-key', required=True, help='GCP or AWS KMS key identifier')
    
    # List command
    subparsers.add_parser('list', help='List all key versions')
    
    # Activate command
    activate_parser = subparsers.add_parser('activate', help='Activate a specific key version')
    activate_parser.add_argument('--version', type=int, required=True, help='Key version to activate')
    
    # Re-encrypt command (stub)
    reencrypt_parser = subparsers.add_parser('re-encrypt', help='Re-encrypt tokens (stub)')
    reencrypt_parser.add_argument('--from-version', type=int, required=True)
    reencrypt_parser.add_argument('--to-version', type=int, required=True)
    reencrypt_parser.add_argument('--batch-size', type=int, default=100)
    
    args = parser.parse_args()
    
    if args.command == 'rotate':
        rotate_key(args.kms_key)
    elif args.command == 'list':
        list_keys()
    elif args.command == 'activate':
        activate_version(args.version)
    elif args.command == 're-encrypt':
        re_encrypt_tokens(args.from_version, args.to_version, args.batch_size)


if __name__ == "__main__":
    main()
