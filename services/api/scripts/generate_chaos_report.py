#!/usr/bin/env python3
"""
Chaos Testing Report Generator

Parses JUnit XML test results from chaos tests and generates a
human-readable markdown report with test summary, failures, and recommendations.

Usage:
    python generate_chaos_report.py --test-results chaos-test-results.xml --output chaos-report.md
    python generate_chaos_report.py --test-results chaos-test-results.xml
"""

import argparse
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional


@dataclass
class TestResult:
    """Individual test result."""

    name: str
    class_name: str
    time: float
    status: str  # "passed", "failed", "skipped"
    failure_message: Optional[str] = None
    failure_type: Optional[str] = None
    failure_traceback: Optional[str] = None


@dataclass
class TestSuite:
    """Test suite results."""

    name: str
    tests: int
    failures: int
    errors: int
    skipped: int
    time: float
    test_results: List[TestResult]


class ChaosReportGenerator:
    """Generate chaos testing reports from JUnit XML."""

    def __init__(self, junit_xml_path: str):
        """
        Initialize report generator.

        Args:
            junit_xml_path: Path to JUnit XML results file
        """
        self.junit_xml_path = junit_xml_path
        self.test_suites: List[TestSuite] = []

    def parse_junit_xml(self) -> bool:
        """
        Parse JUnit XML file.

        Returns:
            True if parsing succeeded, False otherwise
        """
        try:
            tree = ET.parse(self.junit_xml_path)
            root = tree.getroot()

            # Handle both <testsuites> and <testsuite> root elements
            if root.tag == "testsuites":
                testsuites = root.findall("testsuite")
            else:
                testsuites = [root]

            for testsuite_elem in testsuites:
                test_results = []

                for testcase_elem in testsuite_elem.findall("testcase"):
                    name = testcase_elem.get("name", "Unknown")
                    class_name = testcase_elem.get("classname", "Unknown")
                    time = float(testcase_elem.get("time", 0.0))

                    # Check for failure
                    failure_elem = testcase_elem.find("failure")
                    skipped_elem = testcase_elem.find("skipped")

                    if failure_elem is not None:
                        status = "failed"
                        failure_message = failure_elem.get("message", "No message")
                        failure_type = failure_elem.get("type", "Unknown")
                        failure_traceback = failure_elem.text
                    elif skipped_elem is not None:
                        status = "skipped"
                        failure_message = None
                        failure_type = None
                        failure_traceback = None
                    else:
                        status = "passed"
                        failure_message = None
                        failure_type = None
                        failure_traceback = None

                    test_results.append(
                        TestResult(
                            name=name,
                            class_name=class_name,
                            time=time,
                            status=status,
                            failure_message=failure_message,
                            failure_type=failure_type,
                            failure_traceback=failure_traceback,
                        )
                    )

                suite = TestSuite(
                    name=testsuite_elem.get("name", "Chaos Tests"),
                    tests=int(testsuite_elem.get("tests", 0)),
                    failures=int(testsuite_elem.get("failures", 0)),
                    errors=int(testsuite_elem.get("errors", 0)),
                    skipped=int(testsuite_elem.get("skipped", 0)),
                    time=float(testsuite_elem.get("time", 0.0)),
                    test_results=test_results,
                )
                self.test_suites.append(suite)

            return True

        except ET.ParseError as e:
            print(f"❌ Error parsing JUnit XML: {e}")
            return False
        except FileNotFoundError:
            print(f"❌ File not found: {self.junit_xml_path}")
            return False
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            return False

    def generate_report(self) -> str:
        """
        Generate markdown report from parsed test results.

        Returns:
            Markdown-formatted report
        """
        # Aggregate statistics
        total_tests = sum(suite.tests for suite in self.test_suites)
        total_failures = sum(suite.failures for suite in self.test_suites)
        total_errors = sum(suite.errors for suite in self.test_suites)
        total_skipped = sum(suite.skipped for suite in self.test_suites)
        total_passed = total_tests - total_failures - total_errors - total_skipped
        total_time = sum(suite.time for suite in self.test_suites)

        pass_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0

        timestamp = datetime.utcnow().isoformat()

        report = f"""# Chaos Engineering Test Report

**Timestamp:** {timestamp}  
**Duration:** {total_time:.2f}s  
**Status:** {'✅ PASSED' if total_failures == 0 and total_errors == 0 else '❌ FAILED'}

---

## Summary

| Metric | Value |
|--------|-------|
| Total Tests | {total_tests} |
| ✅ Passed | {total_passed} |
| ❌ Failed | {total_failures} |
| ⚠️ Errors | {total_errors} |
| ⏭️ Skipped | {total_skipped} |
| **Pass Rate** | **{pass_rate:.1f}%** |
| Execution Time | {total_time:.2f}s |

---

"""

        # Test suites breakdown
        if len(self.test_suites) > 1:
            report += "## Test Suites\n\n"
            for suite in self.test_suites:
                suite_pass_rate = (
                    ((suite.tests - suite.failures - suite.errors - suite.skipped) / suite.tests * 100)
                    if suite.tests > 0
                    else 0
                )
                status = "✅" if suite.failures == 0 and suite.errors == 0 else "❌"
                report += f"### {status} {suite.name}\n\n"
                report += f"- Tests: {suite.tests}\n"
                report += f"- Passed: {suite.tests - suite.failures - suite.errors - suite.skipped}\n"
                report += f"- Failed: {suite.failures}\n"
                report += f"- Pass Rate: {suite_pass_rate:.1f}%\n"
                report += f"- Duration: {suite.time:.2f}s\n\n"

        # Failures
        if total_failures > 0 or total_errors > 0:
            report += "## ❌ Failures\n\n"
            for suite in self.test_suites:
                failed_tests = [t for t in suite.test_results if t.status == "failed"]
                if failed_tests:
                    report += f"### {suite.name}\n\n"
                    for test in failed_tests:
                        report += f"#### `{test.name}`\n\n"
                        report += f"**Class:** {test.class_name}  \n"
                        report += f"**Time:** {test.time:.2f}s  \n"
                        report += f"**Type:** {test.failure_type}  \n\n"
                        if test.failure_message:
                            report += f"**Message:**\n```\n{test.failure_message}\n```\n\n"
                        if test.failure_traceback:
                            report += f"**Traceback:**\n```python\n{test.failure_traceback.strip()}\n```\n\n"
                    report += "---\n\n"

        # Recommendations
        if total_failures > 0 or total_errors > 0:
            report += self._generate_recommendations(total_failures, total_errors)
        else:
            report += "## ✅ All Tests Passed\n\n"
            report += "Chaos testing completed successfully. System demonstrated resilience under failure conditions.\n\n"
            report += "### Key Achievements\n\n"
            report += "- All chaos scenarios handled gracefully\n"
            report += "- SLO compliance maintained during failures\n"
            report += "- Automatic recovery mechanisms working as expected\n"
            report += "- No cascading failures detected\n\n"

        # Test categories breakdown
        report += "## Test Categories\n\n"
        categories = self._categorize_tests()
        for category, tests in categories.items():
            passed = sum(1 for t in tests if t.status == "passed")
            failed = sum(1 for t in tests if t.status == "failed")
            total = len(tests)
            pass_rate = (passed / total * 100) if total > 0 else 0
            status = "✅" if failed == 0 else "❌"

            report += f"### {status} {category}\n\n"
            report += f"- Total: {total} tests\n"
            report += f"- Passed: {passed}\n"
            report += f"- Failed: {failed}\n"
            report += f"- Pass Rate: {pass_rate:.1f}%\n\n"

        report += "---\n\n"
        report += "_Generated by Chaos Report Generator_\n"

        return report

    def _categorize_tests(self) -> dict:
        """
        Categorize tests by their class names.

        Returns:
            Dictionary mapping category names to test results
        """
        categories = {}
        for suite in self.test_suites:
            for test in suite.test_results:
                # Extract category from class name (e.g., TestAPIOutageChaos -> API Outage)
                class_name = test.class_name.split(".")[-1]
                if class_name.startswith("Test"):
                    class_name = class_name[4:]  # Remove "Test" prefix
                if class_name.endswith("Chaos"):
                    class_name = class_name[:-5]  # Remove "Chaos" suffix

                # Convert camel case to title case
                category = "".join(
                    " " + c if c.isupper() else c for c in class_name
                ).strip()

                if category not in categories:
                    categories[category] = []
                categories[category].append(test)

        return categories

    def _generate_recommendations(self, failures: int, errors: int) -> str:
        """
        Generate recommendations based on failures.

        Args:
            failures: Number of failed tests
            errors: Number of errored tests

        Returns:
            Markdown section with recommendations
        """
        report = "## 🔧 Recommendations\n\n"

        if failures > 0:
            report += "### Address Test Failures\n\n"
            report += "The following actions are recommended to improve resilience:\n\n"
            report += "1. **Review failure logs** - Examine the failure messages and tracebacks above\n"
            report += "2. **Identify root causes** - Determine why resilience mechanisms failed\n"
            report += "3. **Implement fixes** - Add or improve:\n"
            report += "   - Retry logic with exponential backoff\n"
            report += "   - Circuit breakers for cascading failure prevention\n"
            report += "   - Timeout handling and graceful degradation\n"
            report += "   - Fallback mechanisms (cache, default values)\n"
            report += "4. **Re-run chaos tests** - Verify fixes work under failure conditions\n"
            report += "5. **Update SLO targets** - If needed, adjust SLO targets based on findings\n\n"

        if errors > 0:
            report += "### Fix Test Errors\n\n"
            report += "Test errors indicate issues with the test infrastructure or setup:\n\n"
            report += "1. **Check test environment** - Ensure test dependencies are available\n"
            report += "2. **Review test code** - Fix any bugs in the test implementation\n"
            report += "3. **Validate chaos framework** - Ensure chaos injection is working correctly\n\n"

        report += "### General Best Practices\n\n"
        report += "- **Increase gradually** - Start with low chaos probability, increase over time\n"
        report += "- **Monitor SLOs** - Track error rate and latency during chaos testing\n"
        report += "- **Document learnings** - Record what broke and how it was fixed\n"
        report += "- **Automate testing** - Run chaos tests regularly (weekly/monthly)\n\n"

        report += "### Resources\n\n"
        report += "- [Chaos Testing Guide](../../docs/CHAOS_TESTING.md)\n"
        report += "- [Production Handbook](../../docs/PRODUCTION_HANDBOOK.md)\n"
        report += "- [Incident Playbooks](../../docs/playbooks/)\n\n"

        return report


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Generate chaos testing report from JUnit XML results"
    )
    parser.add_argument(
        "--test-results",
        type=str,
        required=True,
        help="Path to JUnit XML test results file",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output file for markdown report (default: print to stdout)",
    )

    args = parser.parse_args()

    # Create generator
    generator = ChaosReportGenerator(args.test_results)

    # Parse test results
    if not generator.parse_junit_xml():
        return 2

    # Generate report
    report = generator.generate_report()

    # Output report
    if args.output:
        try:
            with open(args.output, "w") as f:
                f.write(report)
            print(f"✅ Report generated: {args.output}")
        except IOError as e:
            print(f"❌ Error writing report: {e}")
            return 2
    else:
        print(report)

    return 0


if __name__ == "__main__":
    sys.exit(main())
