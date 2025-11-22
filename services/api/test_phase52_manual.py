#!/usr/bin/env python3
"""
Phase 5.2 Manual Validation Script

Tests segment-aware style tuning without pytest dependency.
Run: python test_phase52_manual.py
"""

import sys

# Import Phase 5.2 functions
from app.autofill_aggregator import (
    derive_segment_key,
    _pick_style_for_profile,
    StyleStats,
    MIN_SEGMENT_RUNS,
)


def test_derive_segment_key():
    """Unit test for segment derivation from job titles"""
    print("\n=== Test 1: derive_segment_key() ===")

    test_cases = [
        # Intern cases
        ({"title": "Summer Intern"}, "intern"),
        ({"title": "Software Engineering Intern"}, "intern"),
        ({"title": "Co-op Developer"}, "intern"),
        ({"normalized_title": "intern software engineer"}, "intern"),
        # Junior cases
        ({"title": "Junior Developer"}, "junior"),
        ({"title": "Jr. Software Engineer"}, "junior"),
        ({"title": "Entry Level Engineer"}, "junior"),
        ({"normalized_title": "junior backend engineer"}, "junior"),
        # Senior cases
        ({"title": "Senior Engineer"}, "senior"),
        ({"title": "Sr. Developer"}, "senior"),
        ({"title": "Lead Engineer"}, "senior"),
        ({"title": "Principal Software Engineer"}, "senior"),
        ({"normalized_title": "senior full stack engineer"}, "senior"),
        # Default cases
        ({"title": "Software Engineer"}, "default"),
        ({"title": "Backend Developer"}, "default"),
        ({"title": "Full Stack Engineer"}, "default"),
        # Edge cases
        ({}, None),
        (None, None),
        ({"other_field": "value"}, None),
    ]

    passed = 0
    failed = 0

    for job, expected in test_cases:
        result = derive_segment_key(job)
        status = "✓" if result == expected else "✗"

        if result == expected:
            passed += 1
        else:
            failed += 1
            print(f"  {status} FAIL: {job} → {result} (expected {expected})")

    print(f"\n  Passed: {passed}/{len(test_cases)}")
    print(f"  Failed: {failed}/{len(test_cases)}")

    return failed == 0


def test_segment_stats_structure():
    """Test segment stats dictionary structure (no DB required)"""
    print("\n=== Test 2: Segment Stats Structure ===")

    # Mock segment stats (as would be returned by _compute_segment_style_stats)
    segment_stats = {
        ("greenhouse", "senior", "professional_v1"): StyleStats(
            style_id="professional_v1",
            helpful=12,
            unhelpful=2,
            total_runs=15,
            avg_edit_chars=50,
        ),
        ("greenhouse", "junior", "friendly_bullets_v1"): StyleStats(
            style_id="friendly_bullets_v1",
            helpful=6,
            unhelpful=1,
            total_runs=8,
            avg_edit_chars=80,
        ),
        ("lever", "senior", "professional_v1"): StyleStats(
            style_id="professional_v1",
            helpful=5,
            unhelpful=0,
            total_runs=6,
            avg_edit_chars=30,
        ),
    }

    print(f"  ✓ Created mock segment_stats with {len(segment_stats)} entries")

    # Verify structure
    for (family, segment, style_id), stats in segment_stats.items():
        assert isinstance(family, str), f"Family should be str: {family}"
        assert isinstance(segment, str), f"Segment should be str: {segment}"
        assert isinstance(style_id, str), f"Style ID should be str: {style_id}"
        assert isinstance(stats, StyleStats), f"Stats should be StyleStats: {stats}"
        assert (
            stats.style_id == style_id
        ), f"Style ID mismatch: {stats.style_id} != {style_id}"

    print("  ✓ All segment_stats entries have correct structure")
    return True


def test_hierarchical_selection():
    """Test form → segment → family → none fallback logic"""
    print("\n=== Test 3: Hierarchical Selection Logic ===")

    # Mock stats
    # form_stats: Dict[Tuple[host, schema], Dict[style_id, StyleStats]]
    form_stats = {
        ("ats.com", "schema1"): {
            "style_a": StyleStats(
                style_id="style_a",
                helpful=2,
                unhelpful=1,
                total_runs=3,
                avg_edit_chars=50,
            ),
        }
    }

    # segment_stats: Dict[Tuple[family, segment, style_id], StyleStats]
    segment_stats = {
        ("greenhouse", "senior", "style_b"): StyleStats(
            style_id="style_b",
            helpful=12,
            unhelpful=2,
            total_runs=15,
            avg_edit_chars=40,
        ),
    }

    # family_stats: Dict[Tuple[family, style_id], StyleStats]
    family_stats = {
        ("greenhouse", "style_c"): StyleStats(
            style_id="style_c",
            helpful=15,
            unhelpful=3,
            total_runs=20,
            avg_edit_chars=60,
        ),
    }

    # Test Case 1: Segment preferred over family (form insufficient)
    print("\n  Test Case 1: Segment preferred over family")
    best, meta = _pick_style_for_profile(
        host="boards.greenhouse.io",  # Valid Greenhouse host
        schema_hash="new-schema",
        form_stats=form_stats,  # 3 runs < MIN_FORM_RUNS
        family_stats=family_stats,  # 20 runs >= MIN_FAMILY_RUNS
        segment_stats=segment_stats,  # 15 runs >= MIN_SEGMENT_RUNS
        segment_key="senior",
    )

    assert best is not None, "Should return segment-level recommendation"
    assert best.style_id == "style_b", f"Should use segment style, got {best.style_id}"
    assert (
        meta["source"] == "segment"
    ), f"Source should be 'segment', got {meta['source']}"
    assert meta.get("segment_key") == "senior", "Should include segment_key in metadata"
    print(f"    ✓ Chose segment-level: {best.style_id} (source={meta['source']})")

    # Test Case 2: Family fallback when segment too sparse
    print("\n  Test Case 2: Family fallback when segment too sparse")
    sparse_segment_stats = {
        ("greenhouse", "senior", "style_b"): StyleStats(
            style_id="style_b", helpful=2, unhelpful=1, total_runs=3, avg_edit_chars=40
        ),
    }

    best, meta = _pick_style_for_profile(
        host="boards.greenhouse.io",  # Valid Greenhouse host
        schema_hash="new-schema",
        form_stats={},  # No form-level data
        family_stats=family_stats,  # 20 runs >= MIN_FAMILY_RUNS
        segment_stats=sparse_segment_stats,  # 3 runs < MIN_SEGMENT_RUNS
        segment_key="senior",
    )

    assert best is not None, "Should return family-level recommendation"
    assert best.style_id == "style_c", f"Should use family style, got {best.style_id}"
    assert (
        meta["source"] == "family"
    ), f"Source should be 'family', got {meta['source']}"
    print(f"    ✓ Fell back to family-level: {best.style_id} (source={meta['source']})")

    # Test Case 3: None when all levels too sparse
    print("\n  Test Case 3: None when all levels too sparse")
    best, meta = _pick_style_for_profile(
        host="boards.greenhouse.io",  # Valid Greenhouse host
        schema_hash="new-schema",
        form_stats={},
        family_stats={},
        segment_stats=sparse_segment_stats,  # 3 runs < MIN_SEGMENT_RUNS
        segment_key="senior",
    )

    assert best is None, "Should return None when all levels sparse"
    assert meta["source"] is None, f"Source should be None, got {meta['source']}"
    print(f"    ✓ Returned None (source={meta['source']})")

    # Test Case 4: Form-level still highest priority
    print("\n  Test Case 4: Form-level has highest priority")
    sufficient_form_stats = {
        ("ats.com", "schema1"): {
            "style_a": StyleStats(
                style_id="style_a",
                helpful=8,
                unhelpful=1,
                total_runs=10,
                avg_edit_chars=30,
            ),
        }
    }

    best, meta = _pick_style_for_profile(
        host="ats.com",
        schema_hash="schema1",
        form_stats=sufficient_form_stats,  # 10 runs >= MIN_FORM_RUNS
        family_stats=family_stats,  # 20 runs >= MIN_FAMILY_RUNS
        segment_stats=segment_stats,  # 15 runs >= MIN_SEGMENT_RUNS
        segment_key="senior",
    )

    assert best is not None, "Should return form-level recommendation"
    assert best.style_id == "style_a", f"Should use form style, got {best.style_id}"
    assert meta["source"] == "form", f"Source should be 'form', got {meta['source']}"
    print(
        f"    ✓ Chose form-level (highest priority): {best.style_id} (source={meta['source']})"
    )

    print("\n  ✓ All hierarchical selection tests passed")
    return True


def test_segment_constants():
    """Verify Phase 5.2 constants are defined"""
    print("\n=== Test 4: Phase 5.2 Constants ===")

    assert (
        MIN_SEGMENT_RUNS == 5
    ), f"MIN_SEGMENT_RUNS should be 5, got {MIN_SEGMENT_RUNS}"
    print(f"  ✓ MIN_SEGMENT_RUNS = {MIN_SEGMENT_RUNS}")

    return True


def main():
    print("=" * 60)
    print("Phase 5.2: Segment-Aware Style Tuning - Manual Validation")
    print("=" * 60)

    all_passed = True

    try:
        if not test_derive_segment_key():
            all_passed = False
    except Exception as e:
        print(f"\n  ✗ Test 1 FAILED with exception: {e}")
        import traceback

        traceback.print_exc()
        all_passed = False

    try:
        if not test_segment_stats_structure():
            all_passed = False
    except Exception as e:
        print(f"\n  ✗ Test 2 FAILED with exception: {e}")
        import traceback

        traceback.print_exc()
        all_passed = False

    try:
        if not test_hierarchical_selection():
            all_passed = False
    except Exception as e:
        print(f"\n  ✗ Test 3 FAILED with exception: {e}")
        import traceback

        traceback.print_exc()
        all_passed = False

    try:
        if not test_segment_constants():
            all_passed = False
    except Exception as e:
        print(f"\n  ✗ Test 4 FAILED with exception: {e}")
        import traceback

        traceback.print_exc()
        all_passed = False

    print("\n" + "=" * 60)
    if all_passed:
        print("✅ ALL PHASE 5.2 TESTS PASSED")
        print("=" * 60)
        return 0
    else:
        print("❌ SOME TESTS FAILED")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
