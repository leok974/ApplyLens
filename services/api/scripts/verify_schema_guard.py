#!/usr/bin/env python3
"""
Manual verification script for schema guard functionality.

Run this to verify that the schema guard correctly detects:
1. Current migration version
2. Column existence
3. Migration requirements

Usage:
    python scripts/verify_schema_guard.py
    
Or in Docker:
    docker-compose exec api python scripts/verify_schema_guard.py
"""
import sys
import os

# Add app to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.utils.schema_guard import (
    get_current_migration,
    check_column_exists,
    require_min_migration,
    require_columns,
    get_migration_info,
)


def print_section(title):
    """Print a formatted section header."""
    print(f"\n{'=' * 70}")
    print(f"{title:^70}")
    print('=' * 70)


def test_get_current_migration():
    """Test getting current migration version."""
    print_section("Test 1: Get Current Migration")
    
    try:
        version = get_current_migration()
        print(f"✓ Current migration: {version}")
        return True
    except Exception as e:
        print(f"✗ Failed: {e}")
        return False


def test_check_column_exists():
    """Test checking if columns exist."""
    print_section("Test 2: Check Column Existence")
    
    test_cases = [
        ("emails", "id", True),
        ("emails", "category", True),
        ("emails", "nonexistent_column", False),
    ]
    
    all_passed = True
    for table, column, expected in test_cases:
        try:
            result = check_column_exists(table, column)
            status = "✓" if result == expected else "✗"
            print(f"{status} {table}.{column}: {result} (expected {expected})")
            if result != expected:
                all_passed = False
        except Exception as e:
            print(f"✗ {table}.{column}: Error - {e}")
            all_passed = False
    
    return all_passed


def test_require_min_migration():
    """Test requiring minimum migration version."""
    print_section("Test 3: Require Minimum Migration")
    
    # Test with a version that should pass (older than current)
    try:
        require_min_migration("0008_approvals_proposed")
        print("✓ Passed: Required 0008_approvals_proposed")
        test1_passed = True
    except RuntimeError as e:
        print(f"✗ Failed: {e}")
        test1_passed = False
    
    # Test with current version (should pass)
    try:
        require_min_migration("0009_add_emails_category")
        print("✓ Passed: Required 0009_add_emails_category")
        test2_passed = True
    except RuntimeError as e:
        print(f"✗ Failed: {e}")
        test2_passed = False
    
    # Test with future version (should fail)
    try:
        require_min_migration("9999_future_migration")
        print("✗ Failed: Should have raised RuntimeError for future migration")
        test3_passed = False
    except RuntimeError as e:
        print(f"✓ Passed: Correctly raised error for future migration")
        print(f"   Error message: {str(e)[:100]}...")
        test3_passed = True
    
    return test1_passed and test2_passed and test3_passed


def test_require_columns():
    """Test requiring specific columns."""
    print_section("Test 4: Require Columns")
    
    # Test with existing columns (should pass)
    try:
        require_columns("emails", "id", "category", "subject")
        print("✓ Passed: All required columns exist (id, category, subject)")
        test1_passed = True
    except RuntimeError as e:
        print(f"✗ Failed: {e}")
        test1_passed = False
    
    # Test with non-existent column (should fail)
    try:
        require_columns("emails", "id", "nonexistent_column")
        print("✗ Failed: Should have raised RuntimeError for missing column")
        test2_passed = False
    except RuntimeError as e:
        print(f"✓ Passed: Correctly raised error for missing column")
        print(f"   Error message: {str(e)[:100]}...")
        test2_passed = True
    
    return test1_passed and test2_passed


def test_get_migration_info():
    """Test getting detailed migration info."""
    print_section("Test 5: Get Migration Info")
    
    try:
        info = get_migration_info()
        print(f"✓ Current migration: {info['current_migration']}")
        print(f"✓ Tables found: {len(info.get('tables', {}))}")
        
        # Check emails table
        if 'emails' in info.get('tables', {}):
            emails_info = info['tables']['emails']
            print(f"✓ emails table columns: {len(emails_info['columns'])}")
            print(f"✓ emails table indexes: {len(emails_info['indexes'])}")
            
            # Check for category column
            if 'category' in emails_info['columns']:
                print("✓ emails.category column exists")
            else:
                print("✗ emails.category column missing")
                return False
        else:
            print("✗ emails table not found")
            return False
        
        return True
    except Exception as e:
        print(f"✗ Failed: {e}")
        return False


def main():
    """Run all verification tests."""
    print("\n" + "=" * 70)
    print("Schema Guard Verification".center(70))
    print("=" * 70)
    
    results = []
    
    results.append(("Get Current Migration", test_get_current_migration()))
    results.append(("Check Column Existence", test_check_column_exists()))
    results.append(("Require Minimum Migration", test_require_min_migration()))
    results.append(("Require Columns", test_require_columns()))
    results.append(("Get Migration Info", test_get_migration_info()))
    
    # Summary
    print_section("Test Summary")
    
    all_passed = True
    for test_name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {test_name}")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 70)
    if all_passed:
        print("✓ ALL TESTS PASSED".center(70))
        print("=" * 70)
        return 0
    else:
        print("✗ SOME TESTS FAILED".center(70))
        print("=" * 70)
        return 1


if __name__ == "__main__":
    sys.exit(main())
