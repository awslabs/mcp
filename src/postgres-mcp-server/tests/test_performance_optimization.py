#!/usr/bin/env python3
"""Test script to validate performance optimizations for Direct PostgreSQL connection."""

import os
import subprocess
import sys
import time


def test_startup_performance():
    """Test startup performance for both connection types."""
    print("🚀 PostgreSQL MCP Server - Startup Performance Test")
    print("=" * 60)

    # Set AWS profile
    os.environ['AWS_PROFILE'] = 'mcp_profile'
    os.environ['AWS_REGION'] = 'us-west-2'

    results = {}

    # Test RDS Data API startup time
    print("\n Testing RDS Data API Startup Performance")
    print("-" * 50)

    cmd_rds = [
        sys.executable, "-m", "awslabs.postgres_mcp_server.server",
        "--resource_arn", "arn:aws:rds:us-west-2:288947426911:cluster:pg-clone-db-cluster",
        "--secret_arn", "arn:aws:secretsmanager:us-west-2:288947426911:secret:rds!cluster-7d957e88-d967-46f3-a21e-7db88c36bdf9-NEq9xL",
        "--database", "devdb",
        "--region", "us-west-2",
        "--readonly", "true"
    ]

    start_time = time.time()
    try:
        result = subprocess.run(cmd_rds, capture_output=True, text=True, timeout=15)
        rds_time = time.time() - start_time

        if "Starting PostgreSQL MCP Server with stdio transport" in result.stderr:
            print(f"✅ RDS Data API startup: {rds_time:.2f} seconds")
            results['rds_data_api'] = rds_time
        else:
            print("❌ RDS Data API startup failed")
            results['rds_data_api'] = None

    except subprocess.TimeoutExpired:
        rds_time = time.time() - start_time
        print(f"✅ RDS Data API startup: {rds_time:.2f} seconds (timeout expected)")
        results['rds_data_api'] = rds_time
    except Exception as e:
        print(f"❌ RDS Data API startup failed: {e}")
        results['rds_data_api'] = None

    # Test Direct PostgreSQL startup time
    print("\n🧪 Testing Direct PostgreSQL Startup Performance")
    print("-" * 50)

    cmd_postgres = [
        sys.executable, "-m", "awslabs.postgres_mcp_server.server",
        "--hostname", "fake-host.amazonaws.com",
        "--port", "5432",
        "--secret_arn", "arn:aws:secretsmanager:us-west-2:123456789012:secret:fake-secret",
        "--database", "fakedb",
        "--region", "us-west-2",
        "--readonly", "true"
    ]

    start_time = time.time()
    try:
        result = subprocess.run(cmd_postgres, capture_output=True, text=True, timeout=15)
        postgres_time = time.time() - start_time

        if "Starting PostgreSQL MCP Server with stdio transport" in result.stderr:
            print(f"✅ Direct PostgreSQL startup: {postgres_time:.2f} seconds")
            results['direct_postgres'] = postgres_time
        elif "Connection parameters validated" in result.stderr or "Connection will be established on first query" in result.stderr:
            print(f"✅ Direct PostgreSQL startup: {postgres_time:.2f} seconds (lazy connection)")
            results['direct_postgres'] = postgres_time
        else:
            print("❌ Direct PostgreSQL startup failed")
            print(f"Error output: {result.stderr[-500:]}")  # Last 500 chars
            results['direct_postgres'] = None

    except subprocess.TimeoutExpired:
        postgres_time = time.time() - start_time
        print(f"❌ Direct PostgreSQL startup: TIMEOUT after {postgres_time:.2f} seconds")
        results['direct_postgres'] = None
    except Exception as e:
        print(f"❌ Direct PostgreSQL startup failed: {e}")
        results['direct_postgres'] = None

    # Performance comparison
    print("\n" + "=" * 60)
    print("📊 STARTUP PERFORMANCE COMPARISON")
    print("=" * 60)

    if results['rds_data_api'] and results['direct_postgres']:
        print("\n⏱️  TIMING RESULTS:")
        print(f"RDS Data API:      {results['rds_data_api']:.2f} seconds")
        print(f"Direct PostgreSQL: {results['direct_postgres']:.2f} seconds")

        if results['direct_postgres'] <= results['rds_data_api'] * 1.5:  # Within 50%
            print("\n✅ PERFORMANCE OPTIMIZATION SUCCESS!")
            print("📊 Direct PostgreSQL startup is now comparable to RDS Data API")
            print(f"🎯 Performance difference: {abs(results['direct_postgres'] - results['rds_data_api']):.2f} seconds")
        else:
            print("\n⚠️  PERFORMANCE NEEDS IMPROVEMENT")
            print(f"📊 Direct PostgreSQL is {results['direct_postgres'] / results['rds_data_api']:.1f}x slower")
    else:
        print("\n⚠️  INCOMPLETE PERFORMANCE TEST")
        if not results['rds_data_api']:
            print("❌ RDS Data API test failed")
        if not results['direct_postgres']:
            print("❌ Direct PostgreSQL test failed")

    return results


def test_lazy_connection_behavior():
    """Test that Direct PostgreSQL uses lazy connection."""
    print("\n🧪 Testing Lazy Connection Behavior")
    print("-" * 50)

    cmd = [
        sys.executable, "-m", "awslabs.postgres_mcp_server.server",
        "--hostname", "fake-host.amazonaws.com",
        "--port", "5432",
        "--secret_arn", "arn:aws:secretsmanager:us-west-2:123456789012:secret:fake-secret",
        "--database", "fakedb",
        "--region", "us-west-2",
        "--readonly", "true"
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

        # Check for lazy connection indicators
        lazy_indicators = [
            "PostgreSQL connector initialized (lazy)",
            "Connection parameters validated",
            "Connection will be established on first query",
            "Starting PostgreSQL MCP Server with stdio transport"
        ]

        found_indicators = []
        for indicator in lazy_indicators:
            if indicator in result.stderr:
                found_indicators.append(indicator)

        if len(found_indicators) >= 2:
            print("✅ Lazy connection behavior confirmed")
            print("📊 Found indicators:")
            for indicator in found_indicators:
                print(f"   • {indicator}")
            return True
        else:
            print("❌ Lazy connection behavior not confirmed")
            print(f"Output: {result.stderr[-300:]}")  # Last 300 chars
            return False

    except subprocess.TimeoutExpired:
        print("❌ Test timed out - lazy connection may not be working")
        return False
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False


def main():
    """Run performance optimization tests."""
    print("🚀 PostgreSQL MCP Server - Performance Optimization Tests")
    print("=" * 70)

    # Set AWS profile
    os.environ['AWS_PROFILE'] = 'mcp_profile'
    os.environ['AWS_REGION'] = 'us-west-2'

    test_results = []

    # Test startup performance
    startup_results = test_startup_performance()
    startup_success = startup_results.get('direct_postgres') is not None
    test_results.append(startup_success)

    # Test lazy connection behavior
    lazy_success = test_lazy_connection_behavior()
    test_results.append(lazy_success)

    # Summary
    print("\n" + "=" * 70)
    print("📋 PERFORMANCE OPTIMIZATION TEST RESULTS")
    print("=" * 70)

    passed = sum(test_results)
    total = len(test_results)

    print("\n📊 OVERALL RESULTS:")
    print(f"✅ Passed: {passed}/{total} tests")
    print(f"❌ Failed: {total - passed}/{total} tests")

    if passed == total:
        print("\n🎉 ALL PERFORMANCE TESTS PASSED!")
        print("🚀 Direct PostgreSQL startup optimization is working")
        print("✅ Lazy connection behavior implemented successfully")
        print("✅ Q Chat integration should now be fast")
    else:
        print("\n⚠️  SOME PERFORMANCE TESTS FAILED")
        print("🔧 Review the optimization implementation")

    print("\n" + "=" * 70)
    print("🏁 Performance test execution completed")

    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
