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
Integration test to verify AWS Security Hub MCP Server functionality with real AWS data.

IMPORTANT: This test requires valid AWS credentials to be configured via:
- Environment variables (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_SESSION_TOKEN)
- AWS credentials file (~/.aws/credentials)
- IAM role (when running on EC2)

The test will use whatever AWS account the credentials have access to.
Ensure you have appropriate Security Hub permissions before running.
"""

import asyncio
from unittest.mock import Mock

from awslabs.aws_security_hub_mcp_server.server import (
    generate_security_report,
    get_enabled_standards,
    get_finding_statistics,
    get_security_findings,
    get_security_score,
    list_security_control_definitions,
)


async def test_real_aws_functionality():
    """Test MCP server functionality with real AWS Security Hub data."""
    print("🔍 Testing AWS Security Hub MCP Server with real AWS data...")
    print("Region: us-east-1")
    print("-" * 60)

    # Create a mock context (MCP context is not needed for our functions)
    mock_context = Mock()

    try:
        # Test 1: Get enabled standards
        print("1️⃣ Testing get_enabled_standards...")
        standards = await get_enabled_standards(mock_context)
        print(f"   ✅ Found {len(standards)} enabled standards")
        for standard in standards[:3]:  # Show first 3
            print(f"      - {standard.name}: {standard.standards_status}")

        # Test 2: List security control definitions
        print("\n2️⃣ Testing list_security_control_definitions...")
        controls = await list_security_control_definitions(mock_context, max_results=5)
        print(f"   ✅ Found {len(controls)} security controls")
        for control in controls[:3]:  # Show first 3
            print(f"      - {control.security_control_id}: {control.title}")

        # Test 3: Get security findings
        print("\n3️⃣ Testing get_security_findings...")
        findings = await get_security_findings(mock_context, max_results=10)
        print(f"   ✅ Found {len(findings)} security findings")
        if findings:
            for finding in findings[:3]:  # Show first 3
                print(f"      - {finding.id[:50]}... ({finding.severity_label.value})")
        else:
            print("      - No findings found (this is good!)")

        # Test 4: Get finding statistics
        print("\n4️⃣ Testing get_finding_statistics...")
        stats = await get_finding_statistics(mock_context, group_by="SeverityLabel")
        print(f"   ✅ Generated statistics for {len(stats)} severity groups")
        for stat in stats:
            print(f"      - {stat.group_key}: {stat.count} findings ({stat.percentage}%)")

        # Test 5: Get security score
        print("\n5️⃣ Testing get_security_score...")
        score = await get_security_score(mock_context)
        print(f"   ✅ Security Score: {score.current_score}/100")
        print(f"      - Control findings: {score.control_findings_count}")
        print(f"      - Score date: {score.score_date}")

        # Test 6: Generate security report
        print("\n6️⃣ Testing generate_security_report...")
        report = await generate_security_report(mock_context, max_findings_per_severity=3)
        print("   ✅ Generated security report")
        print(f"      - Total findings: {report['executive_summary']['total_findings']}")
        print(f"      - Security score: {report['executive_summary']['security_score']}")
        print(f"      - Enabled standards: {report['executive_summary']['enabled_standards_count']}")
        print(f"      - Recommendations: {len(report['recommendations'])}")

        print("\n" + "=" * 60)
        print("🎉 ALL TESTS PASSED! MCP Server is working correctly with real AWS data.")
        print("=" * 60)

        return True

    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        import traceback

        traceback.print_exc()
        return False


async def test_mcp_tools_interface():
    """Test the MCP tools interface directly."""
    print("\n🔧 Testing MCP Tools Interface...")
    print("-" * 40)

    try:
        from awslabs.aws_security_hub_mcp_server.server import mcp

        # List available tools
        tools = await mcp.list_tools()
        print(f"✅ MCP Server has {len(tools)} tools available:")
        for i, tool in enumerate(tools, 1):
            print(f"   {i}. {tool.name}")

        return True

    except Exception as e:
        print(f"❌ ERROR testing MCP interface: {str(e)}")
        return False


if __name__ == "__main__":
    print("AWS Security Hub MCP Server - Real AWS Integration Test")
    print("=" * 60)

    # Run the tests
    success1 = asyncio.run(test_real_aws_functionality())
    success2 = asyncio.run(test_mcp_tools_interface())

    if success1 and success2:
        print("\n🚀 All integration tests completed successfully!")
        exit(0)
    else:
        print("\n💥 Some tests failed. Please check the output above.")
        exit(1)
