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
"""CloudWatch Logs Insights query helpers for snapshot tools."""

import time
from .. import aws_clients
from botocore.exceptions import ClientError


def _execute_cloudwatch_query(
    query_string: str,
    start_epoch: int,
    end_epoch: int,
    log_group_name: str,
    max_timeout: int = 30,
) -> dict:
    """Execute a CloudWatch Logs Insights query and poll for results."""
    logs = aws_clients.logs_client

    try:
        start_response = logs.start_query(
            logGroupName=log_group_name,
            startTime=start_epoch,
            endTime=end_epoch,
            queryString=query_string,
        )
    except ClientError as exc:
        return {
            'status': 'Error',
            'error': f'Failed to start query: {exc}',
            'results': [],
        }
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return {'status': 'Error', 'error': str(exc), 'results': []}

    query_id = start_response.get('queryId')
    if not query_id:
        return {
            'status': 'Error',
            'error': f'start_query did not return a queryId (response: {start_response})',
            'results': [],
        }

    poll_start = time.time()
    while poll_start + max_timeout > time.time():
        try:
            response = logs.get_query_results(queryId=query_id)
        except ClientError as exc:
            return {
                'status': 'Error',
                'error': f'Failed to get results: {exc}',
                'results': [],
                'queryId': query_id,
            }
        except Exception as exc:  # pylint: disable=broad-exception-caught
            return {
                'status': 'Error',
                'error': str(exc),
                'results': [],
                'queryId': query_id,
            }

        status = response.get('status', 'Unknown')
        if status in {'Complete', 'Failed', 'Cancelled'}:
            results = [
                {field.get('field', ''): field.get('value', '') for field in line}
                for line in response.get('results', [])
            ]
            return {
                'status': status,
                'queryId': query_id,
                'results': results,
                'messages': response.get('messages', []),
            }

        time.sleep(1)

    return {
        'status': 'Polling Timeout',
        'queryId': query_id,
        'results': [],
        'error': f'Query did not complete within {max_timeout} seconds.',
    }
