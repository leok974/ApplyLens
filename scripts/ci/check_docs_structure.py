#!/usr/bin/env python3
"""
Documentation structure drift check.

This script validates that the docs/ folder structure remains consistent
with the Phase 5 reorganization and that key canonical documentation files exist.

Exit codes:
  0: All checks passed (warnings may be printed)
  1: Critical issues found (missing directories or key files)
"""

import sys
from pathlib import Path

# ANSI color codes
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
RESET = "\033[0m"


def check_docs_structure():
    """Validate docs folder structure and key files."""
    repo_root = Path(__file__).parent.parent.parent
    docs_dir = repo_root / "docs"

    errors = []
    warnings = []

    print(f"🔍 Checking documentation structure in: {docs_dir}\n")

    # 1. Check main documentation directories exist
    required_dirs = ["core", "agents", "future", "archive"]
    for dir_name in required_dirs:
        dir_path = docs_dir / dir_name
        if not dir_path.exists() or not dir_path.is_dir():
            errors.append(f"Missing required directory: docs/{dir_name}/")
        else:
            print(f"{GREEN}✓{RESET} docs/{dir_name}/ exists")

    # 2. Check core subdirectories
    expected_core_subdirs = ["api", "runbooks", "playbooks", "testing"]
    core_dir = docs_dir / "core"
    if core_dir.exists():
        for subdir in expected_core_subdirs:
            subdir_path = core_dir / subdir
            if not subdir_path.exists():
                warnings.append(
                    f"Expected core subdirectory missing: docs/core/{subdir}/"
                )

    # 3. Check canonical documentation files exist
    canonical_docs = {
        "docs/core/OVERVIEW.md": "System overview",
        "docs/core/ARCHITECTURE.md": "Architecture documentation",
        "docs/core/TESTING_OVERVIEW.md": "Testing overview",
        "docs/core/DEPLOYMENT.md": "Deployment guide",
        "docs/README.md": "Documentation index",
    }

    for doc_path, description in canonical_docs.items():
        full_path = repo_root / doc_path
        if not full_path.exists():
            errors.append(f"Missing canonical doc: {doc_path} ({description})")
        else:
            print(f"{GREEN}✓{RESET} {doc_path} exists")

    # 4. Check that docs/README.md mentions main folders
    readme_path = docs_dir / "README.md"
    if readme_path.exists():
        readme_content = readme_path.read_text(encoding="utf-8")
        for dir_name in required_dirs:
            if (
                f"docs/{dir_name}/" not in readme_content
                and f"{dir_name}/" not in readme_content
            ):
                warnings.append(
                    f"docs/README.md doesn't mention 'docs/{dir_name}/' or '{dir_name}/'"
                )
    else:
        errors.append("docs/README.md is missing")

    # 5. Check agent reading guide exists
    agent_guide = docs_dir / "agents" / "AGENT_READING_GUIDE.md"
    if not agent_guide.exists():
        warnings.append(
            "docs/agents/AGENT_READING_GUIDE.md is missing (agents may not know where to read)"
        )

    # Print summary
    print("\n" + "=" * 60)
    if errors:
        print(f"\n{RED}❌ ERRORS ({len(errors)}):{RESET}")
        for error in errors:
            print(f"  {RED}•{RESET} {error}")

    if warnings:
        print(f"\n{YELLOW}⚠️  WARNINGS ({len(warnings)}):{RESET}")
        for warning in warnings:
            print(f"  {YELLOW}•{RESET} {warning}")

    if not errors and not warnings:
        print(f"\n{GREEN}✅ All documentation structure checks passed!{RESET}")
    elif not errors:
        print(f"\n{YELLOW}⚠️  Warnings present, but no critical errors.{RESET}")

    print("=" * 60 + "\n")

    # Exit with appropriate code
    if errors:
        print(f"{RED}Exiting with code 1 due to critical errors.{RESET}")
        return 1
    else:
        print(f"{GREEN}Exiting with code 0.{RESET}")
        return 0


if __name__ == "__main__":
    sys.exit(check_docs_structure())
