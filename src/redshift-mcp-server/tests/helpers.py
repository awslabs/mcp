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


"""Builders the test modules share, kept here so each one reads as its own subject."""

from awslabs.redshift_mcp_server.models import RedshiftCluster
from botocore.exceptions import ClientError


def _fake_cluster(identifier='test-cluster', type='provisioned', status='available'):
    """Build a RedshiftCluster for mocking discover_clusters() return values."""
    return RedshiftCluster.model_validate(
        {'identifier': identifier, 'type': type, 'status': status, 'database_name': 'dev'}
    )


def _fake_sub(index, status='FINISHED', has_result_set=False, error=None):
    """Build one sub-statement of a batch, numbered as the Data API numbers them."""
    sub = {'Id': f'batch-id:{index + 1}', 'Status': status, 'HasResultSet': has_result_set}
    if error is not None:
        sub['Error'] = error
    return sub


def _fake_batch(subs, status=None, error=None, session_id=None):
    """Build the terminal batch response that _execute_batch() returns.

    Each entry of `subs` is either a status string or the keyword arguments for _fake_sub.
    The batch status defaults to whatever its statements imply.
    """
    sub_statements = [
        _fake_sub(i, **(sub if isinstance(sub, dict) else {'status': sub}))
        for i, sub in enumerate(subs)
    ]
    if status is None:
        status = (
            'FINISHED' if all(sub['Status'] == 'FINISHED' for sub in sub_statements) else 'FAILED'
        )
    batch = {'Id': 'batch-id', 'Status': status, 'SubStatements': sub_statements}
    if error is not None:
        batch['Error'] = error
    if session_id is not None:
        batch['SessionId'] = session_id
    return batch


def _batch_denied_error(action='redshift-data:BatchExecuteStatement'):
    """Build the AccessDeniedException the Data API raises for a denied action."""
    return ClientError(
        {
            'Error': {
                'Code': 'AccessDeniedException',
                'Message': (
                    'User: arn:aws:sts::1:assumed-role/r/s is not authorized to perform: '
                    f'{action} on resource: arn:aws:redshift:us-east-1:1:cluster:c'
                ),
            }
        },
        'BatchExecuteStatement',
    )
