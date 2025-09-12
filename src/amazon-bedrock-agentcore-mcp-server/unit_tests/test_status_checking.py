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

"""Test: Deployment Status Checking System.

Test the new status checking and readiness verification system.
"""

import asyncio
import sys
from pathlib import Path


# Add our MCP server to the path
sys.path.insert(0, str(Path(__file__).parent / 'awslabs' / 'amazon_bedrock_agentcore_mcp_server'))


async def test_status_functions():
    """Test the new status checking functions."""
    print('Testing Status Checking System')
    print('=' * 50)

    try:
        from runtime import check_agent_ready_for_invocation

        # Test 1: Check readiness of strandsv3
        print('\nTest 1: Checking strandsv3 readiness...')
        ready, msg, arn = check_agent_ready_for_invocation('strandsv3', 'us-east-1')
        print(f'Ready: {ready}')
        print(f'Message: {msg}')
        print(f'ARN: {arn[:50]}...' if arn else 'ARN: None')

        # Test 2: Check readiness of strandsv2
        print('\nTest 2: Checking strandsv2 readiness...')
        ready, msg, arn = check_agent_ready_for_invocation('strandsv2', 'us-east-1')
        print(f'Ready: {ready}')
        print(f'Message: {msg}')
        print(f'ARN: {arn[:50]}...' if arn else 'ARN: None')

        # Test 3: Check non-existent agent
        print('\nTest 3: Checking non-existent agent...')
        ready, msg, arn = check_agent_ready_for_invocation('nonexistent', 'us-east-1')
        print(f'Ready: {ready}')
        print(f'Message: {msg}')
        print(f'ARN: {arn}')

        return True

    except Exception as e:
        print(f'Test failed: {str(e)}')
        return False


async def test_mcp_tools():
    """Test the MCP tools with status checking."""
    print('\n' + '=' * 50)
    print('Testing MCP Tools with Status Checking')
    print('=' * 50)

    try:
        from server import mcp

        # Test get_agent_status
        print('\nTest: get_agent_status for strandsv3...')
        result = await mcp.call_tool(
            'get_agent_status', {'agent_name': 'strandsv3', 'region': 'us-east-1'}
        )

        print('Result:')
        print(result[0][0].text)

        # Test invoke_agent with readiness check
        print('\n' + '-' * 40)
        print('Test: invoke_agent with readiness check...')
        result = await mcp.call_tool(
            'invoke_agent',
            {
                'agent_name': 'strandsv3',
                'message': 'Status test message',
                'region': 'us-east-1',
                'skip_readiness_check': False,
            },
        )

        print('Result:')
        print(
            result[0][0].text[:500] + '...' if len(result[0][0].text) > 500 else result[0][0].text
        )

        return True

    except Exception as e:
        print(f'MCP test failed: {str(e)}')
        return False


async def main():
    """Run all status checking tests."""
    print('Status Checking System Test Suite')
    print('Testing deployment status verification and readiness checks')

    # Test 1: Direct function tests
    success1 = await test_status_functions()

    # Test 2: MCP integration tests
    success2 = await test_mcp_tools()

    if success1 and success2:
        print('\n✅ All status checking tests passed!')
        return 0
    else:
        print('\n❌ Some tests failed')
        return 1


if __name__ == '__main__':
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
