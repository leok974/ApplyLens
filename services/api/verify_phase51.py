#!/usr/bin/env python3
"""
Phase 5.1 Verification Script

Tests Phase 5.1 host-family bundle functionality without database.
Run with: python verify_phase51.py
"""

from app.autofill_aggregator import (
    get_host_family,
    ATS_FAMILIES,
    MIN_FORM_RUNS,
    MIN_FAMILY_RUNS,
)


def test_host_family_mapping():
    """Verify host-to-family mapping works correctly."""
    print("=" * 60)
    print("TEST 1: Host-Family Mapping")
    print("=" * 60)

    test_cases = [
        # (host, expected_family)
        ("boards.greenhouse.io", "greenhouse"),
        ("greenhouse.io", "greenhouse"),
        ("jobs.lever.co", "lever"),
        ("myworkdayjobs.com", "workday"),
        ("jobs.ashbyhq.com", "ashby"),
        ("careers.bamboohr.com", "bamboohr"),
        ("unknown-ats.com", None),
        ("example.com", None),
    ]

    passed = 0
    failed = 0

    for host, expected in test_cases:
        result = get_host_family(host)
        status = "✅" if result == expected else "❌"
        print(f"{status} {host:30} → {result or 'None':15} (expected: {expected or 'None'})")

        if result == expected:
            passed += 1
        else:
            failed += 1

    print(f"\nResults: {passed} passed, {failed} failed\n")
    return failed == 0


def test_thresholds():
    """Verify MIN_FORM_RUNS and MIN_FAMILY_RUNS are set correctly."""
    print("=" * 60)
    print("TEST 2: Thresholds")
    print("=" * 60)

    print(f"MIN_FORM_RUNS:   {MIN_FORM_RUNS} (should be 5)")
    print(f"MIN_FAMILY_RUNS: {MIN_FAMILY_RUNS} (should be 10)")

    form_ok = MIN_FORM_RUNS == 5
    family_ok = MIN_FAMILY_RUNS == 10

    status = "✅" if (form_ok and family_ok) else "❌"
    print(f"\n{status} Thresholds configured correctly\n")

    return form_ok and family_ok


def test_ats_families_coverage():
    """Verify ATS_FAMILIES has expected entries."""
    print("=" * 60)
    print("TEST 3: ATS Family Coverage")
    print("=" * 60)

    expected_families = ["greenhouse", "lever", "workday", "ashby", "bamboohr"]
    actual_families = list(ATS_FAMILIES.keys())

    print(f"Expected families: {expected_families}")
    print(f"Actual families:   {actual_families}")

    for family in expected_families:
        status = "✅" if family in ATS_FAMILIES else "❌"
        suffixes = ATS_FAMILIES.get(family, ())
        print(f"{status} {family:15} - {len(suffixes)} suffix(es): {', '.join(suffixes)}")

    all_present = all(f in ATS_FAMILIES for f in expected_families)
    print(f"\n{'✅' if all_present else '❌'} All expected families present\n")

    return all_present


def test_case_insensitivity():
    """Verify host matching is case-insensitive."""
    print("=" * 60)
    print("TEST 4: Case Insensitivity")
    print("=" * 60)

    test_cases = [
        "BOARDS.GREENHOUSE.IO",
        "Boards.Greenhouse.Io",
        "boards.greenhouse.io",
        "BoArDs.GrEeNhOuSe.Io",
    ]

    passed = 0
    for host in test_cases:
        result = get_host_family(host)
        status = "✅" if result == "greenhouse" else "❌"
        print(f"{status} {host:30} → {result or 'None'}")
        if result == "greenhouse":
            passed += 1

    all_passed = passed == len(test_cases)
    print(f"\n{'✅' if all_passed else '❌'} All case variations handled correctly\n")

    return all_passed


def main():
    """Run all verification tests."""
    print("\n" + "=" * 60)
    print("  PHASE 5.1: HOST-FAMILY BUNDLE VERIFICATION")
    print("=" * 60 + "\n")

    results = []
    results.append(("Host-Family Mapping", test_host_family_mapping()))
    results.append(("Thresholds", test_thresholds()))
    results.append(("ATS Family Coverage", test_ats_families_coverage()))
    results.append(("Case Insensitivity", test_case_insensitivity()))

    # Summary
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status:8} - {test_name}")

    print(f"\n{passed}/{total} tests passed\n")

    if passed == total:
        print("🎉 All verification tests passed!")
        print("Phase 5.1 is ready to deploy.\n")
        return 0
    else:
        print("⚠️  Some tests failed. Review implementation before deploying.\n")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
