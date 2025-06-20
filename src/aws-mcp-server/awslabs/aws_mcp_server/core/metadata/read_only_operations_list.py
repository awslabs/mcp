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

import boto3
from itertools import chain
from loguru import logger


READONLY_POLICY_ARN = 'arn:aws:iam::aws:policy/ReadOnlyAccess'


class ReadOnlyOperations(dict):
    """Read only operations list."""

    def __init__(self, policy_version=None):
        """Initialize the read only operations list."""
        super().__init__()
        self['metadata'] = {'policy_version': policy_version}
        self._version = policy_version

    @property
    def version(self):
        """Get the version of the read only operations list."""
        return self._version

    def has(self, service, operation) -> bool:
        """Check if the operation is in the read only operations list."""
        logger.info(f'checking in read only list : {service} - {operation}')
        if '*' in self:
            # in cases like "*" or "*:*" which allows everything
            return True

        if service not in self:
            return False

        operations = self[service]
        # Operations can end with * wildcard
        for op in operations:
            if op.endswith('*'):
                if operation.startswith(op[:-1]):
                    return True
            elif op == operation:
                return True

        return False


def get_readonly_policy_document():
    """Get the read only policy document."""
    iam = boto3.client('iam')
    try:
        # Verify the policy exists and get its details
        get_policy_response = iam.get_policy(PolicyArn=READONLY_POLICY_ARN)
        default_version = get_policy_response['Policy']['DefaultVersionId']

        version_response = iam.get_policy_version(
            PolicyArn=READONLY_POLICY_ARN, VersionId=default_version
        )

        policy_document = version_response['PolicyVersion']['Document']
        return default_version, policy_document
    except Exception as e:
        logger.error(f'Error retrieving ReadOnly policy document: {str(e)}')
        raise RuntimeError(
            'Could not read ReadOnly operations from ReadOnly policy document'
        ) from e


def get_read_only_operations() -> ReadOnlyOperations:
    """Get the read only operations."""
    policy_version, policy_document = get_readonly_policy_document()

    # Extract the list of actions
    # Statement list can have multiple statement objects. Needs to merge actions from all of them
    actions = chain.from_iterable(
        statement['Action'] for statement in policy_document['Statement']
    )

    actions_grouped_by_service = ReadOnlyOperations(policy_version=policy_version)
    for action in actions:
        if action == '*':
            # if action is plain "*", then allow all service and all operations
            actions_grouped_by_service['*'] = ['*']
            continue

        action_split = action.split(':')
        service = action_split[0]
        operation = action_split[1]
        actions_grouped_by_service[service] = actions_grouped_by_service.get(service, [])
        actions_grouped_by_service[service].append(operation)

    return actions_grouped_by_service
