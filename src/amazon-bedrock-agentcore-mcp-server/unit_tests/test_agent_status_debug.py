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

"""Debug Test: Agent Status and Invocation Issues.

This test will:
1. List all agents with detailed status info
2. Test strandsv2 specifically
3. Try invoking multiple agents to find working ones
4. Compare discovery vs invocation results
"""

import boto3
import json
import sys


def test_agent_discovery_and_status():
    """Test agent discovery with detailed status information."""
    print('🔍 AGENT DISCOVERY AND STATUS TEST')
    print('=' * 60)

    try:
        # Test 1: List all agents with full details
        print('\n📋 Step 1: Listing all agents with full status...')

        control_client = boto3.client('bedrock-agentcore-control', region_name='us-east-1')
        response = control_client.list_agent_runtimes(maxResults=50)

        agents = response.get('agentRuntimes', [])
        print(f'✅ Found {len(agents)} total agents')

        # Categorize agents by status
        ready_agents = []
        failed_agents = []
        other_agents = []

        print('\n📊 Detailed Agent Status:')
        print('-' * 60)

        for i, agent in enumerate(agents, 1):
            name = agent.get('agentRuntimeName', 'unknown')
            status = agent.get('status', 'UNKNOWN')
            arn = agent.get('agentRuntimeArn', '')
            agent_id = arn.split('/')[-1] if arn else 'unknown'
            last_updated = agent.get('lastUpdatedAt', 'unknown')

            print(f'{i:2d}. {name}')
            print(f'    Status: {status}')
            print(f'    ID: {agent_id}')
            print(f'    Updated: {last_updated}')
            print(f'    ARN: {arn}')

            if status == 'READY':
                ready_agents.append(name)
            elif 'FAIL' in status or 'ERROR' in status:
                failed_agents.append(name)
            else:
                other_agents.append(name)

            # Highlight strandsv2 specifically
            if 'strandsv2' in name.lower():
                print(f'    >>> 🎯 STRANDSV2 FOUND! Status: {status}')
            print()

        print('\n📊 Summary:')
        print(f'Ready agents: {len(ready_agents)}')
        print(f'Failed/Error agents: {len(failed_agents)}')
        print(f'Other status: {len(other_agents)}')

        return ready_agents, failed_agents, other_agents, agents

    except Exception as e:
        print(f'❌ Agent discovery failed: {str(e)}')
        return [], [], [], []


def test_agent_invocation(agent_name, agents_data):
    """Test individual agent invocation."""
    print(f'\n🚀 Testing invocation: {agent_name}')
    print('-' * 40)

    # First, get agent details
    agent_info = None
    for agent in agents_data:
        if agent.get('agentRuntimeName') == agent_name:
            agent_info = agent
            break

    if not agent_info:
        print(f'❌ Agent {agent_name} not found in agent list')
        return False

    print(f'✅ Agent found - Status: {agent_info.get("status")}')
    print(f'ARN: {agent_info.get("agentRuntimeArn")}')

    # Try to invoke using bedrock-agentcore client
    try:
        runtime_client = boto3.client('bedrock-agentcore', region_name='us-east-1')

        payload = {'message': 'Hello from debug test!'}
        payload_bytes = json.dumps(payload).encode('utf-8')

        print(f'📤 Sending payload: {payload}')

        response = runtime_client.invoke_agent_runtime(
            agentRuntimeArn=agent_info.get('agentRuntimeArn'),
            payload=payload_bytes,
            contentType='application/json',
            accept='application/json',
        )

        print('✅ Invocation successful!')
        print(f'Status Code: {response.get("statusCode", "unknown")}')

        # Handle response
        if 'response' in response:
            response_body = response['response']
            if hasattr(response_body, 'read'):
                result_text = response_body.read().decode('utf-8')
                print(f'📥 Response: {result_text}')
            else:
                print(f'📥 Response: {str(response_body)}')

        return True

    except Exception as e:
        print(f'❌ Invocation failed: {str(e)}')
        print(f'Error type: {type(e).__name__}')
        return False


def main():
    """Run comprehensive agent testing."""
    print('🎯 COMPREHENSIVE AGENT TESTING')
    print('Testing discovery, status, and invocation')
    print('=' * 60)

    # Step 1: Discover all agents
    ready_agents, failed_agents, other_agents, all_agents = test_agent_discovery_and_status()

    if not all_agents:
        print('❌ No agents found. Exiting.')
        return 1

    # Step 2: Test strandsv2 specifically
    print('\n🎯 STRANDSV2 SPECIFIC TEST')
    print('=' * 40)

    strandsv2_success = test_agent_invocation('strandsv2', all_agents)

    # Step 3: Test a few other ready agents for comparison
    print('\n🔄 TESTING OTHER AGENTS FOR COMPARISON')
    print('=' * 50)

    test_count = 0
    success_count = 0

    for agent_name in ready_agents[:3]:  # Test first 3 ready agents
        if agent_name != 'strandsv2':
            success = test_agent_invocation(agent_name, all_agents)
            test_count += 1
            if success:
                success_count += 1

    # Final summary
    print('\n🎯 FINAL SUMMARY')
    print('=' * 30)
    print(f'Total agents discovered: {len(all_agents)}')
    print(f'Ready status agents: {len(ready_agents)}')
    print(f'strandsv2 invocation: {"✅ SUCCESS" if strandsv2_success else "❌ FAILED"}')
    print(f'Other agents tested: {test_count}')
    print(f'Other agents working: {success_count}')

    # Recommendations
    print('\n💡 RECOMMENDATIONS:')
    if not strandsv2_success:
        print('❌ strandsv2 has runtime issues - check CloudWatch logs')
        if success_count > 0:
            print('✅ Other agents are working - strandsv2 specific issue')
        else:
            print('❌ Multiple agents failing - may be system-wide issue')
    else:
        print('✅ strandsv2 is working correctly!')

    return 0 if strandsv2_success else 1


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
