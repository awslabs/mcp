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

"""Simple Test: Status Checking Functions.

Test the status checking functions directly without MCP framework.
"""

import sys
from pathlib import Path


# Add our MCP server to the path
sys.path.insert(0, str(Path(__file__).parent / 'awslabs' / 'amazon_bedrock_agentcore_mcp_server'))


def test_direct_functions():
    """Test the status functions directly."""
    print('Direct Status Function Testing')
    print('=' * 50)

    try:
        # Import the functions we need to test
        sys.path.insert(
            0, str(Path(__file__).parent / 'awslabs' / 'amazon_bedrock_agentcore_mcp_server')
        )

        # Import runtime functions
        from runtime import check_agent_ready_for_invocation

        print('✅ Successfully imported status functions')

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

        # Test 3: Test non-existent agent
        print('\nTest 3: Checking non-existent agent...')
        ready, msg, arn = check_agent_ready_for_invocation('nonexistent-agent', 'us-east-1')
        print(f'Ready: {ready}')
        print(f'Message: {msg}')
        print(f'ARN: {arn}')

        print('\n✅ Status function tests completed successfully!')
        return True

    except Exception as e:
        print(f'❌ Test failed: {str(e)}')
        import traceback

        traceback.print_exc()
        return False


def test_agent_listing():
    """Test listing agents to see what's available."""
    print('\n' + '=' * 50)
    print('Agent Listing Test')
    print('=' * 50)

    try:
        import boto3

        client = boto3.client('bedrock-agentcore-control', region_name='us-east-1')
        agents = client.list_agent_runtimes(maxResults=50)

        print(f'Found {len(agents.get("agentRuntimes", []))} agents:')

        for i, agent in enumerate(agents.get('agentRuntimes', []), 1):
            name = agent.get('agentRuntimeName', agent.get('name', 'unknown'))
            status = agent.get('status', 'Unknown')
            arn = agent.get('agentRuntimeArn', '')
            runtime_id = arn.split('/')[-1] if arn else 'unknown-id'

            print(f'{i}. {name}')
            print(f'   Status: {status}')
            print(f'   Runtime ID: {runtime_id}')
            print()

        print('✅ Agent listing completed successfully!')
        return True

    except Exception as e:
        print(f'❌ Agent listing failed: {str(e)}')
        return False


def main():
    """Run the direct tests."""
    print('🔍 Status Checking System - Direct Function Tests')

    # Test 1: Direct function testing
    success1 = test_direct_functions()

    # Test 2: Agent listing
    success2 = test_agent_listing()

    if success1 and success2:
        print('\n🎉 All direct tests passed!')
        return 0
    else:
        print('\n❌ Some tests failed')
        return 1


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
