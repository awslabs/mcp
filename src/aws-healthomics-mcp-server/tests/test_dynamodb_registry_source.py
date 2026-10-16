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

"""Tests for ``DynamoDbRegistrySource`` in ``mechanisms/role_resolver.py``.

Covers the DynamoDB registry backend (Requirements 3.2 and 3.7): the source
queries the configured table using the identity as the partition key via a
client built from the server's own credentials, deserializes the returned item
into plain Python values, returns ``None`` when no item exists, and maps any
read/query failure to ``RegistrySourceError`` (which ``RegistryRoleResolver``
maps to ``CredentialDerivationError``). A stubbed client factory keeps the tests
free of real AWS calls.
"""

import pytest
from awslabs.aws_healthomics_mcp_server.mechanisms.role_resolver import (
    DynamoDbRegistrySource,
    RegistryRoleResolver,
    RegistrySourceError,
    RoleTarget,
)
from awslabs.aws_healthomics_mcp_server.utils.aws_utils import CredentialDerivationError
from botocore.exceptions import BotoCoreError, ClientError


class _StubDynamoDbClient:
    """Records ``get_item`` calls and returns a canned response or raises."""

    def __init__(self, response=None, error=None):
        self._response = response if response is not None else {}
        self._error = error
        self.calls = []

    def get_item(self, **kwargs):
        self.calls.append(kwargs)
        if self._error is not None:
            raise self._error
        return self._response


class _RecordingClientFactory:
    """Callable client factory that records the region and returns ``client``."""

    def __init__(self, client):
        self._client = client
        self.region = None

    def __call__(self, region=None):
        self.region = region
        return self._client


def _factory_for(client):
    """Build a client factory that records the region and returns ``client``."""
    return _RecordingClientFactory(client)


class TestDynamoDbRegistrySourceGetRecord:
    """Behavior of ``DynamoDbRegistrySource.get_record``.

    Validates: Requirements Registry-based role resolution.
    """

    def test_returns_deserialized_record_for_existing_item(self):
        """An existing item is returned as a dict of plain Python values."""
        client = _StubDynamoDbClient(
            response={
                'Item': {
                    'identity': {'S': 'user-123'},
                    'role_arn': {'S': 'arn:aws:iam::111122223333:role/Customer'},
                    'external_id': {'S': 'ext-uuid'},
                    'account_id': {'S': '111122223333'},
                    'enabled': {'BOOL': True},
                }
            }
        )
        source = DynamoDbRegistrySource('registry-table', client_factory=_factory_for(client))

        record = source.get_record('user-123')

        assert record == {
            'identity': 'user-123',
            'role_arn': 'arn:aws:iam::111122223333:role/Customer',
            'external_id': 'ext-uuid',
            'account_id': '111122223333',
            'enabled': True,
        }

    def test_queries_table_using_identity_as_partition_key(self):
        """The item is read with the identity as the partition-key value."""
        client = _StubDynamoDbClient(response={'Item': {'role_arn': {'S': 'arn'}}})
        source = DynamoDbRegistrySource('registry-table', client_factory=_factory_for(client))

        source.get_record('caller-identity')

        assert client.calls == [
            {
                'TableName': 'registry-table',
                'Key': {'identity': {'S': 'caller-identity'}},
            }
        ]

    def test_uses_configured_partition_key_name(self):
        """A custom partition-key attribute name is honored on the query."""
        client = _StubDynamoDbClient(response={'Item': {'role_arn': {'S': 'arn'}}})
        source = DynamoDbRegistrySource(
            'registry-table',
            partition_key='sub',
            client_factory=_factory_for(client),
        )

        source.get_record('caller-identity')

        assert client.calls[0]['Key'] == {'sub': {'S': 'caller-identity'}}

    def test_passes_region_to_client_factory(self):
        """The configured region is forwarded to the client factory."""
        client = _StubDynamoDbClient(response={'Item': {'role_arn': {'S': 'arn'}}})
        factory = _factory_for(client)
        source = DynamoDbRegistrySource(
            'registry-table', region='us-west-2', client_factory=factory
        )

        source.get_record('user-123')

        assert factory.region == 'us-west-2'

    def test_returns_none_when_no_item(self):
        """A missing item (no ``Item`` key) yields ``None``."""
        client = _StubDynamoDbClient(response={})
        source = DynamoDbRegistrySource('registry-table', client_factory=_factory_for(client))

        assert source.get_record('absent') is None

    def test_client_error_maps_to_registry_source_error(self):
        """A DynamoDB ``ClientError`` becomes a ``RegistrySourceError``."""
        error = ClientError(
            {'Error': {'Code': 'ResourceNotFoundException', 'Message': 'nope'}},
            'GetItem',
        )
        client = _StubDynamoDbClient(error=error)
        source = DynamoDbRegistrySource('registry-table', client_factory=_factory_for(client))

        with pytest.raises(RegistrySourceError):
            source.get_record('user-123')

    def test_botocore_error_maps_to_registry_source_error(self):
        """A ``BotoCoreError`` becomes a ``RegistrySourceError``."""
        client = _StubDynamoDbClient(error=BotoCoreError())
        source = DynamoDbRegistrySource('registry-table', client_factory=_factory_for(client))

        with pytest.raises(RegistrySourceError):
            source.get_record('user-123')

    def test_error_message_omits_identity_and_record(self):
        """The mapped error surfaces only the table name and exception type."""
        error = ClientError(
            {'Error': {'Code': 'AccessDeniedException', 'Message': 'denied'}},
            'GetItem',
        )
        client = _StubDynamoDbClient(error=error)
        source = DynamoDbRegistrySource('registry-table', client_factory=_factory_for(client))

        with pytest.raises(RegistrySourceError) as excinfo:
            source.get_record('secret-identity')

        message = str(excinfo.value)
        assert 'secret-identity' not in message
        assert 'registry-table' in message


class TestDynamoDbRegistrySourceWithResolver:
    """End-to-end behavior through ``RegistryRoleResolver`` (Requirement 3.7)."""

    def test_resolver_returns_target_from_dynamodb_record(self):
        """A valid enabled record resolves to the mapped ``RoleTarget``."""
        client = _StubDynamoDbClient(
            response={
                'Item': {
                    'identity': {'S': 'user-123'},
                    'role_arn': {'S': 'arn:aws:iam::111122223333:role/Customer'},
                    'external_id': {'S': 'ext-uuid'},
                }
            }
        )
        source = DynamoDbRegistrySource('registry-table', client_factory=_factory_for(client))
        resolver = RegistryRoleResolver(source)

        target = resolver.resolve({'sub': 'user-123'})

        assert target == RoleTarget(
            role_arn='arn:aws:iam::111122223333:role/Customer',
            external_id='ext-uuid',
        )

    def test_query_failure_fails_closed_with_credential_derivation_error(self):
        """A source query failure surfaces as ``CredentialDerivationError``."""
        client = _StubDynamoDbClient(error=BotoCoreError())
        source = DynamoDbRegistrySource('registry-table', client_factory=_factory_for(client))
        resolver = RegistryRoleResolver(source)

        with pytest.raises(CredentialDerivationError):
            resolver.resolve({'sub': 'user-123'})
