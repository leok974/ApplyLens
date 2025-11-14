#!/usr/bin/env python
"""
Phase 5.0 Verification Script

Validates the complete feedback-aware style tuning implementation:
1. Database schema (feedback_status, edit_chars, style_hint)
2. Aggregator functions (StyleStats, selection logic)
3. API response structure

Note: Requires PostgreSQL for full validation.
SQLite will show schema validation skipped.
"""

import sys
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))


def check_database_schema():
    """Verify Phase 5.0 database columns exist"""
    print("\n" + "=" * 60)
    print("1. DATABASE SCHEMA VERIFICATION")
    print("=" * 60)

    try:
        from app.db import engine
        from sqlalchemy import inspect

        dialect = engine.dialect.name
        print(f"✓ Database dialect: {dialect}")

        if dialect != "postgresql":
            print("⚠ WARNING: Phase 5.0 requires PostgreSQL")
            print("  Current DB is SQLite - schema validation skipped")
            print("  Backend tests will be skipped")
            return False

        inspector = inspect(engine)

        # Check autofill_events table
        if inspector.has_table("autofill_events"):
            columns = {col["name"] for col in inspector.get_columns("autofill_events")}

            required = {"feedback_status", "edit_chars", "gen_style_id"}
            missing = required - columns

            if missing:
                print(f"✗ Missing columns in autofill_events: {missing}")
                return False

            print("✓ autofill_events has Phase 5.0 columns:")
            print("  - feedback_status")
            print("  - edit_chars")
            print("  - gen_style_id")
        else:
            print("✗ Table autofill_events not found")
            return False

        # Check form_profiles table
        if inspector.has_table("form_profiles"):
            columns = {col["name"] for col in inspector.get_columns("form_profiles")}

            if "style_hint" not in columns:
                print("✗ Missing style_hint column in form_profiles")
                return False

            print("✓ form_profiles has Phase 5.0 columns:")
            print("  - style_hint (JSONB)")
        else:
            print("✗ Table form_profiles not found")
            return False

        return True

    except Exception as e:
        print(f"✗ Database check failed: {e}")
        return False


def check_aggregator_code():
    """Verify Phase 5.0 aggregator functions exist"""
    print("\n" + "=" * 60)
    print("2. AGGREGATOR CODE VERIFICATION")
    print("=" * 60)

    try:
        from app import autofill_aggregator

        # Check StyleStats dataclass
        if not hasattr(autofill_aggregator, "StyleStats"):
            print("✗ StyleStats dataclass not found")
            return False

        print("✓ StyleStats dataclass exists")

        # Check aggregator functions
        required_functions = [
            "_compute_style_stats",
            "_pick_best_style",
            "_update_style_hints",
            "aggregate_autofill_profiles",
        ]

        for func_name in required_functions:
            if not hasattr(autofill_aggregator, func_name):
                print(f"✗ Function {func_name} not found")
                return False
            print(f"✓ Function {func_name} exists")

        # Check StyleStats has helpful_ratio property
        StyleStats = autofill_aggregator.StyleStats

        # Create a test instance
        test_stats = StyleStats(
            style_id="test_style",
            helpful=8,
            unhelpful=2,
            total_runs=10,
            avg_edit_chars=120.0,
        )

        if not hasattr(test_stats, "helpful_ratio"):
            print("✗ StyleStats.helpful_ratio property not found")
            return False

        expected_ratio = 0.8
        actual_ratio = test_stats.helpful_ratio

        if abs(actual_ratio - expected_ratio) > 0.001:
            print(
                f"✗ StyleStats.helpful_ratio calculation wrong: {actual_ratio} != {expected_ratio}"
            )
            return False

        print(f"✓ StyleStats.helpful_ratio property works correctly ({actual_ratio})")

        return True

    except Exception as e:
        print(f"✗ Aggregator check failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def check_api_models():
    """Verify Phase 5.0 API models"""
    print("\n" + "=" * 60)
    print("3. API MODEL VERIFICATION")
    print("=" * 60)

    try:
        from app.models_learning import StyleHint

        # Check StyleHint has preferred_style_id field
        hint = StyleHint(
            gen_style_id="test_style",
            confidence=0.9,
            preferred_style_id="friendly_bullets_v1",
        )

        if not hasattr(hint, "preferred_style_id"):
            print("✗ StyleHint.preferred_style_id field not found")
            return False

        print("✓ StyleHint model has Phase 5.0 fields:")
        print("  - preferred_style_id")

        # Verify it serializes correctly
        data = hint.model_dump()

        if "preferred_style_id" not in data:
            print("✗ preferred_style_id not in serialized data")
            return False

        if data["preferred_style_id"] != "friendly_bullets_v1":
            print(f"✗ Wrong value: {data['preferred_style_id']}")
            return False

        print("✓ StyleHint serializes correctly")

        return True

    except Exception as e:
        print(f"✗ API model check failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def check_migration():
    """Verify Phase 5.0 migration exists"""
    print("\n" + "=" * 60)
    print("4. MIGRATION VERIFICATION")
    print("=" * 60)

    try:
        from pathlib import Path

        # Check migration file exists
        migrations_dir = Path(__file__).parent / "alembic" / "versions"
        phase5_migration = list(migrations_dir.glob("*phase_5*"))

        if not phase5_migration:
            # Try alternative naming
            phase5_migration = list(migrations_dir.glob("*75310f8e88d7*"))

        if not phase5_migration:
            print("✗ Phase 5.0 migration file not found")
            print(f"  Searched in: {migrations_dir}")
            return False

        migration_file = phase5_migration[0]
        print(f"✓ Phase 5.0 migration found: {migration_file.name}")

        # Read migration content
        content = migration_file.read_text()

        # Check for key Phase 5.0 additions
        required_strings = ["feedback_status", "edit_chars", "style_hint"]

        for s in required_strings:
            if s not in content:
                print(f"✗ Migration missing '{s}'")
                return False

        print("✓ Migration contains all Phase 5.0 columns")

        return True

    except Exception as e:
        print(f"✗ Migration check failed: {e}")
        return False


def check_tests():
    """Verify Phase 5.0 tests exist"""
    print("\n" + "=" * 60)
    print("5. TEST SUITE VERIFICATION")
    print("=" * 60)

    try:
        from pathlib import Path

        # Check backend tests
        test_file = Path(__file__).parent / "tests" / "test_learning_style_tuning.py"

        if not test_file.exists():
            print("✗ Backend test file not found")
            return False

        print(f"✓ Backend test file exists: {test_file.name}")

        # Read test content
        content = test_file.read_text()

        # Check for key tests
        required_tests = [
            "test_style_stats_dataclass",
            "test_compute_style_stats_basic",
            "test_pick_best_style_by_helpful_ratio",
            "test_update_style_hints_integration",
        ]

        for test_name in required_tests:
            if test_name not in content:
                print(f"✗ Test missing: {test_name}")
                return False
            print(f"✓ Test found: {test_name}")

        # Check test is marked for PostgreSQL
        if "@pytest.mark.postgresql" not in content:
            print("⚠ WARNING: Tests not marked with @pytest.mark.postgresql")
        else:
            print("✓ Tests properly marked for PostgreSQL")

        return True

    except Exception as e:
        print(f"✗ Test check failed: {e}")
        return False


def main():
    """Run all Phase 5.0 verifications"""
    print("\n" + "#" * 60)
    print("# PHASE 5.0 VERIFICATION")
    print("# Feedback-Aware Style Tuning")
    print("#" * 60)

    results = {
        "Schema": check_database_schema(),
        "Aggregator": check_aggregator_code(),
        "API Models": check_api_models(),
        "Migration": check_migration(),
        "Tests": check_tests(),
    }

    print("\n" + "=" * 60)
    print("VERIFICATION SUMMARY")
    print("=" * 60)

    for check, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status:10} {check}")

    all_passed = all(results.values())

    print("\n" + "=" * 60)
    if all_passed:
        print("✅ ALL CHECKS PASSED - PHASE 5.0 COMPLETE!")
    else:
        print("⚠️  SOME CHECKS FAILED - SEE DETAILS ABOVE")
        if not results["Schema"]:
            print("\n💡 Tip: Phase 5.0 requires PostgreSQL")
            print("   Backend tests will be skipped on SQLite")
            print("   Extension tests will still work!")
    print("=" * 60 + "\n")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
