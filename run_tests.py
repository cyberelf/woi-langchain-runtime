#!/usr/bin/env python3
"""Test runner for the Pydantic-based configuration schema system."""

import subprocess
import sys
from pathlib import Path


def run_tests():
    """Run the comprehensive test suite."""
    print("🧪 Running Comprehensive Test Suite for Pydantic-based Configuration Schema System")
    print("=" * 80)

    # Test categories
    test_categories = [
        ("Pydantic Schema Generation", "TestPydanticSchemaGeneration"),
        ("Template Validation", "TestTemplateValidation"),
        ("Pydantic Model Integration", "TestPydanticModelIntegration"),
        ("Schema Response Structure", "TestSchemaResponseStructure"),
    ]

    total_passed = 0
    total_failed = 0

    for category_name, test_class in test_categories:
        print(f"\n📋 {category_name}")
        print("-" * 50)

        try:
            # Run tests for this category
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pytest",
                    f"tests/test_template_manager_schema.py::{test_class}",
                    "-v",
                    "--tb=short",
                    "-q",
                ],
                capture_output=True,
                text=True,
                cwd=Path(__file__).parent,
            )

            if result.returncode == 0:
                print("✅ All tests passed")
                # Count passed tests
                lines = result.stdout.split("\n")
                for line in lines:
                    if "passed" in line and "failed" not in line:
                        if "passed" in line:
                            try:
                                passed = int(line.split()[0])
                                total_passed += passed
                            except (ValueError, IndexError):
                                pass
            else:
                print("❌ Some tests failed")
                print(result.stdout)
                print(result.stderr)
                total_failed += 1

        except Exception as e:
            print(f"❌ Error running tests: {e}")
            total_failed += 1

    print("\n" + "=" * 80)
    print("📊 Test Summary")
    print("-" * 50)
    print(f"✅ Total passed: {total_passed}")
    print(f"❌ Total failed: {total_failed}")

    if total_failed == 0:
        print("\n🎉 All tests passed! The Pydantic-based configuration schema system is working correctly.")
        return True
    else:
        print(f"\n⚠️  {total_failed} test categories failed. Please check the output above.")
        return False


def run_specific_test(test_name):
    """Run a specific test."""
    print(f"🧪 Running specific test: {test_name}")
    print("=" * 50)

    try:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                f"tests/test_template_manager_schema.py::{test_name}",
                "-v",
                "-s",
            ],
            cwd=Path(__file__).parent,
        )

        return result.returncode == 0
    except Exception as e:
        print(f"❌ Error running test: {e}")
        return False


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Run specific test
        test_name = sys.argv[1]
        success = run_specific_test(test_name)
        sys.exit(0 if success else 1)
    else:
        # Run all tests
        success = run_tests()
        sys.exit(0 if success else 1)
