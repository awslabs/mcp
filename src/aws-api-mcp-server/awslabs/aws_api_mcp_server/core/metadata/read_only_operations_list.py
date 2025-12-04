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
import importlib.resources
import json
import requests
from collections import defaultdict
from loguru import logger
from typing import List


SERVICE_REFERENCE_URL = 'https://servicereference.us-east-1.amazonaws.com/'
METADATA_FILE = 'data/api_metadata.json'
DEFAULT_REQUEST_TIMEOUT = 5
OVERRIDES = {
    'sts': {
        'AssumeRole': False,
        'AssumeRoleWithWebIdentity': False,
        'AssumeRoleWithSAML': False,
        'GetSessionToken': False,
        'GetFederationToken': False,
        'AssumeRoot': False,
    },
    'iam': {
        'CreateAccessKey': False,
    },
    'cognito-identity': {
        'GetCredentialsForIdentity': False,
        'GetOpenIdToken': False,
    },
    'sso': {
        'GetRoleCredentials': False,
    },
}


class ServiceReferenceUrlsByService(dict):
    """Service reference urls by service."""

    def __init__(self):
        """Initialize the urls by service map."""
        super().__init__()
        try:
            response = requests.get(SERVICE_REFERENCE_URL, timeout=DEFAULT_REQUEST_TIMEOUT).json()
        except Exception as e:
            logger.error(f'Error retrieving the service reference document: {e}')
            raise RuntimeError(f'Error retrieving the service reference document: {e}')
        for service_reference in response:
            self[service_reference['service']] = service_reference['url']


class ReadOnlyOperations(dict):
    """Read only operations list by service."""

    def __init__(self, service_reference_urls_by_service: dict[str, str]):
        """Initialize the read only operations list."""
        super().__init__()
        self._service_reference_urls_by_service = service_reference_urls_by_service
        self._known_readonly_operations = self._get_known_readonly_operations_from_metadata()
        for service, operations in self._get_custom_readonly_operations().items():
            if service in self._known_readonly_operations:
                self._known_readonly_operations[service] = [
                    *self._known_readonly_operations[service],
                    *operations,
                ]
            else:
                self._known_readonly_operations[service] = operations

    def has(self, service, operation) -> bool:
        """Check if the operation is in the read only operations list."""
        logger.info(f'checking in read only list : {service} - {operation}')
        if service in OVERRIDES and operation in OVERRIDES[service]:
            return OVERRIDES[service][operation]
        if (
            service in self._known_readonly_operations
            and operation in self._known_readonly_operations[service]
        ):
            return True
        if service not in self:
            if service not in self._service_reference_urls_by_service:
                return False
            self._cache_ready_only_operations_for_service(service)
        return operation in self[service]

    def _cache_ready_only_operations_for_service(self, service: str):
        try:
            response = requests.get(
                self._service_reference_urls_by_service[service], timeout=DEFAULT_REQUEST_TIMEOUT
            ).json()
        except Exception as e:
            logger.error(f'Error retrieving the service reference document: {e}')
            raise RuntimeError(f'Error retrieving the service reference document: {e}')
        self[service] = []
        for action in response['Actions']:
            if not action['Annotations']['Properties']['IsWrite']:
                self[service].append(action['Name'])

    def _get_known_readonly_operations_from_metadata(self) -> dict[str, List[str]]:
        known_readonly_operations = defaultdict(list)
        with (
            importlib.resources.files('awslabs.aws_api_mcp_server.core')
            .joinpath(METADATA_FILE)
            .open() as metadata_file
        ):
            data = json.load(metadata_file)
        for service, operations in data.items():
            for operation, operation_metadata in operations.items():
                operation_type = operation_metadata.get('type')
                if operation_type == 'ReadOnly':
                    known_readonly_operations[service].append(operation)
        return known_readonly_operations

    @staticmethod
    def _get_custom_readonly_operations() -> dict[str, List[str]]:
        return {
            's3': ['ls', 'presign'],
            'cloudfront': ['sign'],
            'cloudtrail': ['validate-logs'],
            'codeartifact': ['login'],
            'codecommit': ['credential-helper'],
            'datapipeline': ['list-runs'],
            'ecr': ['get-login', 'get-login-password'],
            'ecr-public': ['get-login-password'],
            'eks': ['get-token'],
            'emr': ['describe-cluster'],
            'gamelift': ['get-game-session-log'],
            'logs': ['start-live-tail'],
            'rds': ['generate-db-auth-token'],
            'configservice': ['get-status'],
        }


def get_read_only_operations() -> ReadOnlyOperations:
    """Get the read only operations."""
    return ReadOnlyOperations(ServiceReferenceUrlsByService())
