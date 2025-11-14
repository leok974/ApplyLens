#!/usr/bin/env python3
"""
Manual test for Phase 5.1 without pytest dependency.
Tests core Phase 5.1 functions directly.
"""

import sys
from app.autofill_aggregator import (
    get_host_family,
    _pick_style_for_profile,
    StyleStats,
)

def test_get_host_family():
    """Test host-family mapping."""
    print("\n" + "="*60)
    print("TEST 1: get_host_family()")
    print("="*60)
    
    tests = [
        ("boards.greenhouse.io", "greenhouse"),
        ("greenhouse.io", "greenhouse"),
        ("jobs.lever.co", "lever"),
        ("myworkdayjobs.com", "workday"),
        ("jobs.ashbyhq.com", "ashby"),
        ("careers.bamboohr.com", "bamboohr"),
        ("unknown-ats.com", None),
        ("BOARDS.GREENHOUSE.IO", "greenhouse"),  # case insensitive
    ]
    
    passed = 0
    failed = 0
    
    for host, expected in tests:
        result = get_host_family(host)
        if result == expected:
            print(f"✅ {host:30} → {result}")
            passed += 1
        else:
            print(f"❌ {host:30} → {result} (expected: {expected})")
            failed += 1
    
    print(f"\nResults: {passed} passed, {failed} failed")
    return failed == 0


def test_pick_style_for_profile():
    """Test hierarchical style selection logic."""
    print("\n" + "="*60)
    print("TEST 2: _pick_style_for_profile()")
    print("="*60)
    
    # Scenario 1: Form stats with enough samples (should use form-level)
    print("\nScenario 1: Form has 10 runs (≥ MIN_FORM_RUNS=5)")
    form_stats = {
        ("boards.greenhouse.io", "test_hash"): {
            "style1": StyleStats(style_id="style1", helpful=8, unhelpful=2, total_runs=10, avg_edit_chars=10.0),
            "style2": StyleStats(style_id="style2", helpful=5, unhelpful=5, total_runs=10, avg_edit_chars=20.0),
        }
    }
    family_stats = {
        ("greenhouse", "style3"): StyleStats(style_id="style3", helpful=15, unhelpful=5, total_runs=20, avg_edit_chars=5.0),
    }
    
    result = _pick_style_for_profile(
        host="boards.greenhouse.io",
        schema_hash="test_hash",
        form_stats=form_stats,
        family_stats=family_stats,
    )
    
    if result and result.style_id == "style1":
        print("✅ Correctly chose form-level style (style1, 80% helpful)")
    else:
        print(f"❌ Expected style1, got {result.style_id if result else None}")
        return False
    
    # Scenario 2: Form stats low, family stats high (should use family-level)
    print("\nScenario 2: Form has 2 runs (< MIN_FORM_RUNS), Family has 20 runs (≥ MIN_FAMILY_RUNS=10)")
    form_stats = {
        ("boards.greenhouse.io", "test_hash"): {
            "style1": StyleStats(style_id="style1", helpful=2, unhelpful=0, total_runs=2, avg_edit_chars=10.0),
        }
    }
    family_stats = {
        ("greenhouse", "style3"): StyleStats(style_id="style3", helpful=15, unhelpful=5, total_runs=20, avg_edit_chars=5.0),
    }
    
    result = _pick_style_for_profile(
        host="boards.greenhouse.io",
        schema_hash="test_hash",
        form_stats=form_stats,
        family_stats=family_stats,
    )
    
    if result and result.style_id == "style3":
        print("✅ Correctly fell back to family-level style (style3, 75% helpful)")
    else:
        print(f"❌ Expected style3, got {result.style_id if result else None}")
        return False
    
    # Scenario 3: Both stats too sparse (should return None)
    print("\nScenario 3: Form has 2 runs, Family has 5 runs (both below thresholds)")
    form_stats = {
        ("boards.greenhouse.io", "test_hash"): {
            "style1": StyleStats(style_id="style1", helpful=2, unhelpful=0, total_runs=2, avg_edit_chars=10.0),
        }
    }
    family_stats = {
        ("greenhouse", "style3"): StyleStats(style_id="style3", helpful=4, unhelpful=1, total_runs=5, avg_edit_chars=5.0),
    }
    
    result = _pick_style_for_profile(
        host="boards.greenhouse.io",
        schema_hash="test_hash",
        form_stats=form_stats,
        family_stats=family_stats,
    )
    
    if result is None:
        print("✅ Correctly returned None (insufficient data)")
    else:
        print(f"❌ Expected None, got {result.style_id if result else None}")
        return False
    
    # Scenario 4: No family for unknown host (should use form if available)
    print("\nScenario 4: Unknown host (no family), form has 10 runs")
    form_stats = {
        ("unknown-ats.com", "test_hash"): {
            "style1": StyleStats(style_id="style1", helpful=8, unhelpful=2, total_runs=10, avg_edit_chars=10.0),
        }
    }
    family_stats = {}
    
    result = _pick_style_for_profile(
        host="unknown-ats.com",
        schema_hash="test_hash",
        form_stats=form_stats,
        family_stats=family_stats,
    )
    
    if result and result.style_id == "style1":
        print("✅ Correctly used form-level for unknown host (style1)")
    else:
        print(f"❌ Expected style1, got {result.style_id if result else None}")
        return False
    
    print("\n✅ All scenarios passed!")
    return True


def test_thresholds():
    """Test that thresholds are configured correctly."""
    print("\n" + "="*60)
    print("TEST 3: Threshold Configuration")
    print("="*60)
    
    from app.autofill_aggregator import MIN_FORM_RUNS, MIN_FAMILY_RUNS
    
    print(f"MIN_FORM_RUNS:   {MIN_FORM_RUNS} (expected: 5)")
    print(f"MIN_FAMILY_RUNS: {MIN_FAMILY_RUNS} (expected: 10)")
    
    if MIN_FORM_RUNS == 5 and MIN_FAMILY_RUNS == 10:
        print("✅ Thresholds configured correctly")
        return True
    else:
        print("❌ Thresholds incorrect")
        return False


def main():
    print("="*60)
    print("PHASE 5.1: MANUAL INTEGRATION TESTS")
    print("="*60)
    
    results = []
    
    # Run tests
    results.append(("get_host_family", test_get_host_family()))
    results.append(("_pick_style_for_profile", test_pick_style_for_profile()))
    results.append(("Thresholds", test_thresholds()))
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}   - {name}")
    
    print(f"\n{passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All Phase 5.1 manual tests passed!")
        print("Phase 5.1 is ready for production deployment.")
        return 0
    else:
        print("\n❌ Some tests failed.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
