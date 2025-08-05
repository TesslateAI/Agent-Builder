#!/usr/bin/env python3
"""
Authentication Test Runner for Agent-Builder
Runs comprehensive authentication and authorization tests
"""

import os
import sys
import time
import subprocess
import argparse
from datetime import datetime

def print_banner():
    """Print test banner"""
    print("=" * 70)
    print("Agent-Builder Authentication Test Suite")
    print("=" * 70)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

def check_test_environment():
    """Check if test environment is ready"""
    print("🔍 Checking test environment...")
    
    # Check if backend is running
    try:
        import requests
        response = requests.get("http://localhost:5000/health", timeout=5)
        if response.status_code != 200:
            print("❌ Backend service not responding at http://localhost:5000")
            return False
        print("✅ Backend service running")
    except Exception as e:
        print(f"❌ Backend service not available: {e}")
        return False
    
    # Check if Keycloak is running (optional)
    try:
        import requests
        response = requests.get("http://localhost:8081/realms/agent-builder", timeout=5)
        if response.status_code == 200:
            print("✅ Keycloak service running")
        else:
            print("⚠️  Keycloak service not available (some tests may be skipped)")
    except Exception:
        print("⚠️  Keycloak service not available (some tests may be skipped)")
    
    print()
    return True

def run_unit_tests():
    """Run unit tests"""
    print("🧪 Running Unit Tests...")
    print("-" * 50)
    
    unit_test_files = [
        "tests/unit/test_keycloak_client.py"
    ]
    
    results = []
    
    for test_file in unit_test_files:
        if os.path.exists(test_file):
            print(f"\nRunning {test_file}...")
            try:
                result = subprocess.run([
                    sys.executable, test_file
                ], capture_output=True, text=True, timeout=60)
                
                if result.returncode == 0:
                    print("✅ PASSED")
                    results.append((test_file, True, result.stdout))
                else:
                    print("❌ FAILED")
                    results.append((test_file, False, result.stderr))
                    
            except subprocess.TimeoutExpired:
                print("⏰ TIMEOUT")
                results.append((test_file, False, "Test timed out"))
            except Exception as e:
                print(f"❌ ERROR: {e}")
                results.append((test_file, False, str(e)))
        else:
            print(f"⚠️  Test file not found: {test_file}")
    
    return results

def run_integration_tests():
    """Run integration tests"""
    print("\n🔗 Running Integration Tests...")
    print("-" * 50)
    
    integration_test_files = [
        "tests/integration/authentication_integration_tests.py",
        "tests/integration/api_integration_tests.py"
    ]
    
    results = []
    
    for test_file in integration_test_files:
        if os.path.exists(test_file):
            print(f"\nRunning {test_file}...")
            try:
                result = subprocess.run([
                    sys.executable, test_file
                ], capture_output=True, text=True, timeout=120)
                
                if result.returncode == 0:
                    print("✅ PASSED")
                    results.append((test_file, True, result.stdout))
                else:
                    print("❌ FAILED")
                    results.append((test_file, False, result.stderr))
                    
            except subprocess.TimeoutExpired:
                print("⏰ TIMEOUT")
                results.append((test_file, False, "Test timed out"))
            except Exception as e:
                print(f"❌ ERROR: {e}")
                results.append((test_file, False, str(e)))
        else:
            print(f"⚠️  Test file not found: {test_file}")
    
    return results

def print_detailed_results(results, test_type):
    """Print detailed test results"""
    print(f"\n📊 {test_type} Test Results:")
    print("-" * 50)
    
    passed = 0
    failed = 0
    
    for test_file, success, output in results:
        status = "PASSED ✅" if success else "FAILED ❌"
        print(f"{os.path.basename(test_file)}: {status}")
        
        if success:
            passed += 1
        else:
            failed += 1
            # Print error details for failed tests
            if output and len(output.strip()) > 0:
                print(f"  Error details:")
                # Print first few lines of error
                error_lines = output.strip().split('\n')[:5]
                for line in error_lines:
                    print(f"    {line}")
                if len(output.strip().split('\n')) > 5:
                    print("    ... (truncated)")
        print()
    
    return passed, failed

def run_specific_test_category(category):
    """Run tests for a specific category"""
    if category == "unit":
        return run_unit_tests()
    elif category == "integration":
        return run_integration_tests()
    elif category == "auth":
        # Run only authentication-specific tests
        return run_integration_tests()  # For now, auth tests are in integration
    else:
        print(f"Unknown test category: {category}")
        return []

def main():
    """Main test runner"""
    parser = argparse.ArgumentParser(description="Run Agent-Builder authentication tests")
    parser.add_argument(
        "--category",
        choices=["unit", "integration", "auth", "all"],
        default="all",
        help="Test category to run (default: all)"
    )
    parser.add_argument(
        "--skip-env-check",
        action="store_true",
        help="Skip environment readiness check"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed output"
    )
    
    args = parser.parse_args()
    
    print_banner()
    
    # Check environment unless skipped
    if not args.skip_env_check:
        if not check_test_environment():
            print("❌ Environment check failed. Use --skip-env-check to bypass.")
            return 1
    
    # Run tests based on category
    unit_results = []
    integration_results = []
    
    if args.category in ["unit", "all"]:
        unit_results = run_unit_tests()
    
    if args.category in ["integration", "auth", "all"]:
        integration_results = run_integration_tests()
    
    # Print results summary
    print("\n" + "=" * 70)
    print("📋 TEST SUMMARY")
    print("=" * 70)
    
    total_passed = 0
    total_failed = 0
    
    if unit_results:
        passed, failed = print_detailed_results(unit_results, "Unit")
        total_passed += passed
        total_failed += failed
    
    if integration_results:
        passed, failed = print_detailed_results(integration_results, "Integration")
        total_passed += passed
        total_failed += failed
    
    # Overall summary
    total_tests = total_passed + total_failed
    success_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0
    
    print(f"📈 OVERALL RESULTS:")
    print(f"   Total Tests: {total_tests}")
    print(f"   Passed: {total_passed} ✅")
    print(f"   Failed: {total_failed} ❌")
    print(f"   Success Rate: {success_rate:.1f}%")
    print()
    print(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Return exit code
    return 0 if total_failed == 0 else 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)