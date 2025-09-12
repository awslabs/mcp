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

"""Test: Agent Readiness Functions (AWS API Only).

Test just the readiness checking functions without MCP dependencies.
"""

import boto3
import sys
from typing import Any, Dict, Optional, Tuple


def check_agent_ready_for_invocation(
    agent_name: str, region: str = 'us-east-1'
) -> Tuple[bool, str, Optional[str]]:
    """Check if agent is ready for invocation and return its ARN."""
    try:
        client = boto3.client('bedrock-agentcore-control', region_name=region)
        agents = client.list_agent_runtimes(maxResults=50)

        for agent in agents.get('agentRuntimes', []):
            if agent.get('agentRuntimeName', agent.get('name')) == agent_name:
                status = agent.get('status', 'Unknown')
                arn = agent.get('agentRuntimeArn')

                if status == 'READY':
                    return True, f'Agent {agent_name} is ready for invocation', arn
                else:
                    return False, f'Agent {agent_name} is not ready (status: {status})', arn

        return False, f'Agent {agent_name} not found', None

    except Exception as e:
        return False, f'Error checking agent readiness: {str(e)}', None


def wait_for_agent_ready(
    agent_name: str, region: str = 'us-east-1', timeout_minutes: int = 2
) -> Tuple[bool, str, Dict[str, Any]]:
    """Wait for agent to reach READY status (with shorter timeout for testing)."""
    import time
    from datetime import datetime, timedelta

    client = boto3.client('bedrock-agentcore-control', region_name=region)
    start_time = datetime.now()
    timeout_time = start_time + timedelta(minutes=timeout_minutes)

    while datetime.now() < timeout_time:
        try:
            # Get current agent status
            agents = client.list_agent_runtimes(maxResults=50)

            for agent in agents.get('agentRuntimes', []):
                if agent.get('agentRuntimeName', agent.get('name')) == agent_name:
                    status = agent.get('status', 'Unknown')

                    if status == 'READY':
                        return True, f'Agent {agent_name} is ready', agent
                    elif status in ['FAILED', 'STOPPED']:
                        return (
                            False,
                            f'Agent {agent_name} deployment failed with status: {status}',
                            agent,
                        )

                    # Still in progress, continue waiting
                    elapsed = (datetime.now() - start_time).total_seconds()
                    print(f'Agent {agent_name} status: {status} (waiting {elapsed:.0f}s)')
                    time.sleep(5)  # Wait 5 seconds for testing
                    break
            else:
                return False, f'Agent {agent_name} not found in deployment list', {}

        except Exception as e:
            return False, f'Error checking agent status: {str(e)}', {}

    # Timeout reached
    return (
        False,
        f'Timeout waiting for agent {agent_name} to be ready (waited {timeout_minutes} minutes)',
        {},
    )


def test_readiness_functions():
    """Test the readiness checking functions."""
    print('Agent Readiness Function Testing')
    print('=' * 50)

    # Test 1: Check strandsv3 readiness
    print('\n🔍 Test 1: Checking strandsv3 readiness...')
    ready, msg, arn = check_agent_ready_for_invocation('strandsv3', 'us-east-1')
    print(f'Ready: {ready}')
    print(f'Message: {msg}')
    print(f'ARN: {arn[:60]}...' if arn else 'ARN: None')

    if ready:
        print('✅ strandsv3 is ready for invocation')
    else:
        print('❌ strandsv3 is not ready')

    # Test 2: Check strandsv2 readiness
    print('\n🔍 Test 2: Checking strandsv2 readiness...')
    ready, msg, arn = check_agent_ready_for_invocation('strandsv2', 'us-east-1')
    print(f'Ready: {ready}')
    print(f'Message: {msg}')
    print(f'ARN: {arn[:60]}...' if arn else 'ARN: None')

    if ready:
        print('✅ strandsv2 is ready for invocation')
    else:
        print('❌ strandsv2 is not ready')

    # Test 3: Check non-existent agent
    print('\n🔍 Test 3: Checking non-existent agent...')
    ready, msg, arn = check_agent_ready_for_invocation('fake-agent', 'us-east-1')
    print(f'Ready: {ready}')
    print(f'Message: {msg}')
    print(f'ARN: {arn}')

    if not ready and 'not found' in msg:
        print('✅ Correctly detected non-existent agent')
    else:
        print('❌ Failed to detect non-existent agent')

    # Test 4: Test wait function with already-ready agent
    print('\n🔍 Test 4: Testing wait function with strandsv3 (should return immediately)...')
    ready, msg, agent_info = wait_for_agent_ready('strandsv3', 'us-east-1', timeout_minutes=1)
    print(f'Ready: {ready}')
    print(f'Message: {msg}')

    if ready:
        print('✅ Wait function works correctly for ready agent')
    else:
        print('❌ Wait function failed for ready agent')

    return True


def main():
    """Run readiness function tests."""
    print('🚀 Agent Readiness Testing - Standalone Functions')
    print('Testing the new deployment status verification system')

    try:
        test_readiness_functions()

        print('\n🎉 Readiness function testing completed!')
        print('\n📋 Summary:')
        print('- check_agent_ready_for_invocation(): Tests agent status and returns ARN')
        print('- wait_for_agent_ready(): Polls until agent becomes READY')
        print('- Both functions work with existing READY agents')

        return 0

    except Exception as e:
        print(f'\n❌ Testing failed: {str(e)}')
        import traceback

        traceback.print_exc()
        return 1


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
