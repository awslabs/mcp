#!/usr/bin/env python3
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
Manual test script for ECS Security Analysis functionality
"""

import asyncio

from awslabs.ecs_mcp_server.api.security_analysis import ecs_security_analysis_tool


async def test_list_clusters():
    """Test the list_clusters action"""
    print("🔍 Testing list_clusters...")

    try:
        result = await ecs_security_analysis_tool(
            action="list_clusters", parameters={"region": "us-east-1"}
        )

        print("✅ list_clusters succeeded")
        print(f"Response type: {type(result)}")

        if isinstance(result, dict):
            print(f"Status: {result.get('status', 'unknown')}")
            if "clusters" in result:
                print(f"Found {len(result['clusters'])} clusters")

        return True

    except Exception as e:
        print(f"❌ list_clusters failed: {e}")
        return False


async def test_analyze_nonexistent_cluster():
    """Test analyze_cluster_security with a non-existent cluster"""
    print("\n🔍 Testing analyze_cluster_security with non-existent cluster...")

    try:
        result = await ecs_security_analysis_tool(
            action="analyze_cluster_security",
            parameters={"cluster_name": "non-existent-cluster-test", "region": "us-east-1"},
        )

        print("✅ analyze_cluster_security handled non-existent cluster gracefully")
        print(f"Response type: {type(result)}")

        if isinstance(result, dict):
            print(f"Status: {result.get('status', 'unknown')}")
            print(f"Assessment: {result.get('assessment', 'No assessment')[:100]}...")

        return True

    except Exception as e:
        print(f"❌ analyze_cluster_security failed: {e}")
        return False


async def main():
    """Run all manual tests"""
    print("🧪 Starting ECS Security Analysis Manual Tests")
    print("=" * 60)

    tests = [
        test_list_clusters,
        test_analyze_nonexistent_cluster,
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        if await test():
            passed += 1

    print("\n" + "=" * 60)
    print(f"📊 Test Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed!")
        return 0
    else:
        print("❌ Some tests failed")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
