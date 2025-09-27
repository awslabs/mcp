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

"""Independent Test: CloudWatch Logs Access for AgentCore Runtimes.

Test accessing CloudWatch logs for AgentCore agent runtimes to help with troubleshooting.
"""

import boto3
import sys
from datetime import datetime, timedelta


def test_cloudwatch_logs_access():
    """Test CloudWatch logs access for AgentCore agent runtime."""
    print('Testing CloudWatch Logs Access for AgentCore')
    print('=' * 60)

    # Test parameters based on your example
    agent_runtime_id = 'strandsv3-jLWV3a8FD3'
    endpoint_name = 'DEFAULT'
    log_group_name = f'/aws/bedrock-agentcore/runtimes/{agent_runtime_id}-{endpoint_name}'

    print(f'Agent Runtime ID: {agent_runtime_id}')
    print(f'Endpoint Name: {endpoint_name}')
    print(f'Log Group: {log_group_name}')
    print()

    try:
        # Create CloudWatch Logs client
        logs_client = boto3.client('logs', region_name='us-east-1')
        print('✅ CloudWatch Logs client created successfully')

        # Test 1: Check if log group exists
        print('\n📋 Test 1: Checking if log group exists...')
        try:
            response = logs_client.describe_log_groups(logGroupNamePrefix=log_group_name, limit=1)

            log_groups = response.get('logGroups', [])
            if log_groups:
                log_group = log_groups[0]
                print(f'✅ Log group found: {log_group["logGroupName"]}')
                print(f'   Created: {datetime.fromtimestamp(log_group["creationTime"] / 1000)}')
                print(f'   Size: {log_group.get("storedBytes", 0)} bytes')
            else:
                print(f'❌ Log group not found: {log_group_name}')
                print('   This could mean:')
                print("   - Agent hasn't been invoked yet")
                print('   - Different endpoint name')
                print('   - Different runtime ID format')
                return False

        except Exception as e:
            print(f'❌ Error checking log group: {str(e)}')
            return False

        # Test 2: List log streams in the group
        print('\n📋 Test 2: Listing log streams...')
        try:
            streams_response = logs_client.describe_log_streams(
                logGroupName=log_group_name, orderBy='LastEventTime', descending=True, limit=5
            )

            log_streams = streams_response.get('logStreams', [])
            print(f'✅ Found {len(log_streams)} log streams')

            for i, stream in enumerate(log_streams[:3], 1):
                stream_name = stream['logStreamName']
                last_event = (
                    datetime.fromtimestamp(stream.get('lastEventTime', 0) / 1000)
                    if stream.get('lastEventTime')
                    else 'Never'
                )
                print(f'   {i}. {stream_name}')
                print(f'      Last event: {last_event}')

        except Exception as e:
            print(f'❌ Error listing log streams: {str(e)}')
            return False

        # Test 3: Get recent log events
        print('\n📋 Test 3: Getting recent log events...')
        try:
            # Get logs from last 1 hour
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=1)

            events_response = logs_client.filter_log_events(
                logGroupName=log_group_name,
                startTime=int(start_time.timestamp() * 1000),
                endTime=int(end_time.timestamp() * 1000),
                limit=10,
            )

            events = events_response.get('events', [])
            print(f'✅ Found {len(events)} recent log events')

            if events:
                print('\n📄 Recent log entries:')
                for event in events[:5]:
                    timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
                    message = event['message'].strip()
                    print(f'   [{timestamp}] {message}')
            else:
                print('   No recent events found (agent may not have been invoked recently)')

        except Exception as e:
            print(f'❌ Error getting log events: {str(e)}')
            return False

        # Test 4: Search for error patterns
        print('\n📋 Test 4: Searching for error patterns...')
        try:
            # Search for common error patterns
            error_patterns = ['ERROR', 'Exception', 'Failed', 'Traceback']

            for pattern in error_patterns:
                error_response = logs_client.filter_log_events(
                    logGroupName=log_group_name,
                    filterPattern=pattern,
                    startTime=int((datetime.now() - timedelta(hours=24)).timestamp() * 1000),
                    limit=5,
                )

                error_events = error_response.get('events', [])
                if error_events:
                    print(f"⚠️  Found {len(error_events)} events matching '{pattern}':")
                    for event in error_events[:2]:
                        timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
                        message = event['message'].strip()[:100]
                        print(f'   [{timestamp}] {message}...')

        except Exception as e:
            print(f'⚠️  Error searching for patterns: {str(e)}')

        print('\n✅ CloudWatch logs access test completed successfully!')
        return True

    except Exception as e:
        print(f'❌ CloudWatch logs test failed: {str(e)}')
        print('\nPossible issues:')
        print('- AWS credentials not configured')
        print('- Insufficient CloudWatch Logs permissions')
        print('- Region mismatch')
        return False


def test_different_log_group_patterns():
    """Test different possible log group naming patterns."""
    print('\n📋 Testing Different Log Group Patterns')
    print('-' * 40)

    agent_runtime_id = 'strandsv3-jLWV3a8FD3'

    # Different possible patterns
    patterns = [
        f'/aws/bedrock-agentcore/runtimes/{agent_runtime_id}-DEFAULT',
        f'/aws/bedrock-agentcore/runtimes/{agent_runtime_id}',
        f'/aws/bedrock-agentcore/{agent_runtime_id}',
        f'/aws/agentcore/runtimes/{agent_runtime_id}',
        f'/aws/bedrock/{agent_runtime_id}',
    ]

    logs_client = boto3.client('logs', region_name='us-east-1')

    for pattern in patterns:
        try:
            response = logs_client.describe_log_groups(logGroupNamePrefix=pattern, limit=1)

            if response.get('logGroups'):
                print(f'✅ Found: {pattern}')
            else:
                print(f'❌ Not found: {pattern}')

        except Exception as e:
            print(f'⚠️  Error testing {pattern}: {str(e)}')


def main():
    """Run CloudWatch logs tests."""
    print('🔍 AgentCore CloudWatch Logs Testing')
    print('Testing access to agent runtime logs for troubleshooting')

    # Test 1: Specific agent logs
    success = test_cloudwatch_logs_access()

    # Test 2: Try different patterns if main test fails
    if not success:
        test_different_log_group_patterns()

    return 0 if success else 1


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
