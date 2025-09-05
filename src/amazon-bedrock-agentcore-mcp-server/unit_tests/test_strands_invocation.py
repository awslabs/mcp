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
"""Independent Test: List, Select and Invoke strandsv2 Agent.

This test validates our AWS API fixes by:
1. Listing all available agents
2. Finding the strandsv2 agent specifically
3. Invoking the strandsv2 agent with a test message
"""

import asyncio
import sys
from pathlib import Path


# Add our MCP server to the path
sys.path.insert(0, str(Path(__file__).parent / 'awslabs' / 'amazon_bedrock_agentcore_mcp_server'))


async def test_strandsv2_workflow():
    """Test the complete workflow: list -> find -> invoke strands agent."""
    try:
        # Import our MCP server
        from server import create_server

        print('🔍 Step 1: Creating MCP Server...')
        server = create_server()
        print('✅ MCP Server created successfully')

        # Step 1: List all AWS agents using project_discover
        print('\n🔍 Step 2: Discovering AWS agents...')

        try:
            result = await server.call_tool(
                'project_discover', {'action': 'aws', 'region': 'us-east-1'}
            )

            # Extract result from MCP response format
            aws_discovery_result = result[0][0].text
            print('✅ AWS Discovery Result:')
            print(aws_discovery_result)

            # Check if strandsv2 is found
            if 'strandsv2' in aws_discovery_result.lower():
                print('✅ strandsv2 agent found in discovery!')
            else:
                print('❌ strandsv2 agent NOT found in discovery')
                print('Available agents are listed above')

        except Exception as e:
            print(f'❌ AWS Discovery Failed: {str(e)}')
            return False

        # Step 2: Get specific agent status
        print('\n🔍 Step 3: Checking strandsv2 agent status...')

        try:
            result = await server.call_tool(
                'get_agent_status', {'agent_name': 'strandsv2', 'region': 'us-east-1'}
            )

            status_result = result[0][0].text
            print('✅ Agent Status Result:')
            print(status_result)

            if 'READY' in status_result:
                print('✅ strandsv2 is READY for invocation!')
                agent_ready = True
            else:
                print('⚠️ strandsv2 may not be ready yet')
                agent_ready = False

        except Exception as e:
            agent_ready = False
            print(f'❌ Status Check Failed: {str(e)}', agent_ready)

        # Step 3: Invoke the agent (try both methods)
        print('\n🔍 Step 4: Invoking strandsv2 agent...')

        test_message = 'Hello from independent test! Please respond.'

        # Try method 1: Regular invocation with starter toolkit
        print('\n🔍 Step 4a: Trying starter toolkit invocation...')
        try:
            result = await server.call_tool(
                'invoke_agent',
                {
                    'agent_name': 'strandsv2',
                    'message': test_message,
                    'region': 'us-east-1',
                    'use_starter_toolkit': True,
                },
            )

            invoke_result = result[0][0].text
            print('✅ Starter Toolkit Invocation Result:')
            print(invoke_result)

            if 'Success' in invoke_result or 'Agent Invocation Complete' in invoke_result:
                print('✅ Starter toolkit invocation SUCCESS!')
                return True
            else:
                print('⚠️ Starter toolkit invocation had issues')

        except Exception as e:
            print(f'❌ Starter Toolkit Invocation Failed: {str(e)}')

        # Try method 2: Direct boto3 invocation
        print('\n🔍 Step 4b: Trying direct boto3 invocation...')
        try:
            result = await server.call_tool(
                'invoke_agent',
                {
                    'agent_name': 'strandsv2',
                    'message': test_message,
                    'region': 'us-east-1',
                    'use_starter_toolkit': False,
                },
            )

            invoke_result = result[0][0].text
            print('✅ Direct boto3 Invocation Result:')
            print(invoke_result)

            if 'Success' in invoke_result or 'Agent Invocation Complete' in invoke_result:
                print('✅ Direct boto3 invocation SUCCESS!')
                return True
            else:
                print('⚠️ Direct boto3 invocation had issues')

        except Exception as e:
            print(f'❌ Direct boto3 Invocation Failed: {str(e)}')

        print('\n❌ Both invocation methods failed')
        return False

    except Exception as e:
        print(f'❌ Test Setup Error: {str(e)}')
        return False


async def test_raw_aws_api():
    """Test raw AWS API calls to debug the response structure."""
    print('\n🔍 Raw AWS API Test: Checking actual response structure...')

    try:
        import boto3

        # Test the control client directly
        client = boto3.client('bedrock-agentcore-control', region_name='us-east-1')

        print('✅ Created bedrock-agentcore-control client')

        # Test list_agent_runtimes
        print('🔍 Calling list_agent_runtimes()...')
        response = client.list_agent_runtimes()

        print('✅ Raw API Response Structure:')
        print(f'Response keys: {list(response.keys())}')

        # Check both possible keys
        items = response.get('items', [])
        agent_runtimes = response.get('agentRuntimes', [])

        print(f'Items found: {len(items)}')
        print(f'AgentRuntimes found: {len(agent_runtimes)}')

        # Use whichever is populated
        agents = items if items else agent_runtimes

        print(f'\n📋 Found {len(agents)} total agents:')
        strandsv2_found = False

        for i, agent in enumerate(agents):
            # Get the correct name field
            agent_name = agent.get('agentRuntimeName', agent.get('name', 'Unknown'))
            agent_status = agent.get('status', 'Unknown')
            agent_arn = agent.get('agentRuntimeArn', 'Not found')

            print(f'  {i + 1}. {agent_name} (Status: {agent_status})')
            print(f'      ARN: {agent_arn}')

            # Check for strandsv2, strands_starter, or similar patterns
            search_terms = ['strandsv2', 'strands_starter', 'strands-starter']
            found_match = False

            for term in search_terms:
                if term in str(agent_name).lower() or term in str(agent_arn).lower():
                    found_match = True
                    strandsv2_found = True
                    print(f"    ✅ Found potential match for '{term}'!")
                    break

            if found_match:
                print(f'    Full agent data: {agent}')
            print()

        if strandsv2_found:
            print('\n✅ strandsv2 confirmed in raw AWS API response!')
            return True
        else:
            print('\n❌ strandsv2 NOT found in raw AWS API response')
            return False

    except Exception as e:
        print(f'❌ Raw AWS API Test Failed: {str(e)}')
        return False


async def main():
    """Run the complete test suite."""
    print('🚀 Starting Independent strandsv2 Test')
    print('=' * 50)

    # Test 1: Raw AWS API
    print('\n📋 TEST 1: Raw AWS API Response Structure')
    raw_success = await test_raw_aws_api()

    # Test 2: MCP Server workflow
    print('\n📋 TEST 2: MCP Server Workflow (List -> Find -> Invoke)')
    mcp_success = await test_strandsv2_workflow()

    # Summary
    print('\n' + '=' * 50)
    print('🎯 TEST SUMMARY:')
    print(f'Raw AWS API Test: {"✅ PASS" if raw_success else "❌ FAIL"}')
    print(f'MCP Server Test: {"✅ PASS" if mcp_success else "❌ FAIL"}')

    if raw_success and mcp_success:
        print('\n🎉 ALL TESTS PASSED! strandsv2 is working correctly!')
        return 0
    elif raw_success:
        print('\n⚠️ AWS API works but MCP server has issues')
        return 1
    else:
        print('\n❌ AWS API issues - agent may not be deployed or accessible')
        return 2


if __name__ == '__main__':
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
