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

"""Tests for ``RegistryRoleResolver.resolve`` in ``mechanisms/role_resolver.py``.

Exercises the resolver's fail-closed behavior against BOTH registry backends --
the file-based JSON map (:class:`FileRegistrySource`) and the DynamoDB table
(:class:`DynamoDbRegistrySource`) -- so the record-handling rules are proven
backend-agnostic. The file backend reads a ``tmp_path`` JSON fixture and the
DynamoDB backend uses a stubbed client factory, so no real AWS calls are made.

Covered scenarios (Requirement Registry-based role resolution): a valid enabled
record resolves to the mapped ``RoleTarget`` (hit); a missing record, a disabled
record, a record missing its
``role_arn`` or ``external_id``, an ``external_id`` longer than 1224 characters,
and a source read/query failure each fail closed with
``CredentialDerivationError``; and a decoded-claims set with a missing or empty
caller claim fails closed before the source is ever touched.

Validates: Requirements Registry-based role resolution.
"""

import json
import pytest
from awslabs.aws_healthomics_mcp_server.mechanisms.role_resolver import (
    DynamoDbRegistrySource,
    FileRegistrySource,
    RegistryRoleResolver,
    RoleTarget,
)
from awslabs.aws_healthomics_mcp_server.utils.aws_utils import CredentialDerivationError
from boto3.dynamodb.types import TypeSerializer
from botocore.exceptions import BotoCoreError


_ROLE_ARN = 'arn:aws:iam::111122223333:role/Customer'
_EXTERNAL_ID = 'ext-uuid'
_IDENTITY = 'user-123'


def _serialize_item(record: dict) -> dict:
    """Serialize a plain-Python record into DynamoDB attribute-value form."""
    serializer = TypeSerializer()
    return {key: serializer.serialize(value) for key, value in record.items()}


class _StubDynamoDbClient:
    """Returns a canned ``get_item`` response or raises, with no real AWS calls."""

    def __init__(self, item=None, error=None):
        self._item = item
        self._error = error

    def get_item(self, **kwargs):
        if self._error is not None:
            raise self._error
        if self._item is None:
            return {}
        return {'Item': self._item}


class _UnusedSource:
    """Registry source that must never be queried; asserts if it ever is."""

    def get_record(self, identity: str) -> dict | None:
        raise AssertionError('source should not be read when the caller claim is unusable')


class _FileBackend:
    """Builds file-backed resolvers from a ``tmp_path`` JSON fixture."""

    name = 'file'

    def __init__(self, tmp_path):
        self._tmp_path = tmp_path

    def _resolver_for_map(self, registry_map: dict, caller_claim: str) -> RegistryRoleResolver:
        map_path = self._tmp_path / 'registry.json'
        map_path.write_text(json.dumps(registry_map), encoding='utf-8')
        return RegistryRoleResolver(FileRegistrySource(str(map_path)), caller_claim=caller_claim)

    def resolver_with_record(
        self, record: dict, caller_claim: str = 'sub'
    ) -> RegistryRoleResolver:
        return self._resolver_for_map({_IDENTITY: record}, caller_claim)

    def resolver_with_no_record(self, caller_claim: str = 'sub') -> RegistryRoleResolver:
        return self._resolver_for_map({}, caller_claim)

    def resolver_with_read_failure(self, caller_claim: str = 'sub') -> RegistryRoleResolver:
        # A path that does not exist raises ``OSError`` on read, which the source
        # maps to ``RegistrySourceError``.
        missing_path = self._tmp_path / 'does-not-exist.json'
        return RegistryRoleResolver(
            FileRegistrySource(str(missing_path)), caller_claim=caller_claim
        )


class _DynamoDbBackend:
    """Builds DynamoDB-backed resolvers from a stubbed client factory."""

    name = 'dynamodb'

    @staticmethod
    def _resolver_for_client(client, caller_claim: str) -> RegistryRoleResolver:
        source = DynamoDbRegistrySource(
            'registry-table', client_factory=lambda region=None: client
        )
        return RegistryRoleResolver(source, caller_claim=caller_claim)

    def resolver_with_record(
        self, record: dict, caller_claim: str = 'sub'
    ) -> RegistryRoleResolver:
        client = _StubDynamoDbClient(item=_serialize_item(record))
        return self._resolver_for_client(client, caller_claim)

    def resolver_with_no_record(self, caller_claim: str = 'sub') -> RegistryRoleResolver:
        client = _StubDynamoDbClient(item=None)
        return self._resolver_for_client(client, caller_claim)

    def resolver_with_read_failure(self, caller_claim: str = 'sub') -> RegistryRoleResolver:
        client = _StubDynamoDbClient(error=BotoCoreError())
        return self._resolver_for_client(client, caller_claim)


@pytest.fixture(params=['file', 'dynamodb'])
def backend(request, tmp_path):
    """Parametrized registry backend so each test runs against both sources."""
    if request.param == 'file':
        return _FileBackend(tmp_path)
    return _DynamoDbBackend()


class TestRegistryRoleResolverResolve:
    """Fail-closed resolution behavior across both registry backends.

    Validates: Requirements Registry-based role resolution.
    """

    def test_hit_returns_role_target_from_enabled_record(self, backend):
        """A valid enabled record resolves to its mapped ``RoleTarget``."""
        resolver = backend.resolver_with_record(
            {'role_arn': _ROLE_ARN, 'external_id': _EXTERNAL_ID, 'enabled': True}
        )

        target = resolver.resolve({'sub': _IDENTITY})

        assert target == RoleTarget(role_arn=_ROLE_ARN, external_id=_EXTERNAL_ID)

    def test_hit_treats_absent_enabled_flag_as_enabled(self, backend):
        """A record without an ``enabled`` flag is treated as enabled."""
        resolver = backend.resolver_with_record(
            {'role_arn': _ROLE_ARN, 'external_id': _EXTERNAL_ID}
        )

        target = resolver.resolve({'sub': _IDENTITY})

        assert target == RoleTarget(role_arn=_ROLE_ARN, external_id=_EXTERNAL_ID)

    def test_missing_record_fails_closed(self, backend):
        """No record for the identity fails closed."""
        resolver = backend.resolver_with_no_record()

        with pytest.raises(CredentialDerivationError):
            resolver.resolve({'sub': _IDENTITY})

    def test_disabled_record_fails_closed(self, backend):
        """A record with ``enabled`` set false denies access."""
        resolver = backend.resolver_with_record(
            {'role_arn': _ROLE_ARN, 'external_id': _EXTERNAL_ID, 'enabled': False}
        )

        with pytest.raises(CredentialDerivationError):
            resolver.resolve({'sub': _IDENTITY})

    def test_missing_role_arn_fails_closed(self, backend):
        """A record missing its role ARN fails closed."""
        resolver = backend.resolver_with_record({'external_id': _EXTERNAL_ID})

        with pytest.raises(CredentialDerivationError):
            resolver.resolve({'sub': _IDENTITY})

    def test_missing_external_id_fails_closed(self, backend):
        """A record missing its ExternalId fails closed."""
        resolver = backend.resolver_with_record({'role_arn': _ROLE_ARN})

        with pytest.raises(CredentialDerivationError):
            resolver.resolve({'sub': _IDENTITY})

    def test_external_id_too_long_fails_closed(self, backend):
        """An ExternalId longer than 1224 characters fails closed."""
        resolver = backend.resolver_with_record({'role_arn': _ROLE_ARN, 'external_id': 'e' * 1225})

        with pytest.raises(CredentialDerivationError):
            resolver.resolve({'sub': _IDENTITY})

    def test_external_id_at_max_length_resolves(self, backend):
        """An ExternalId of exactly 1224 characters is accepted (boundary)."""
        max_external_id = 'e' * 1224
        resolver = backend.resolver_with_record(
            {'role_arn': _ROLE_ARN, 'external_id': max_external_id}
        )

        target = resolver.resolve({'sub': _IDENTITY})

        assert target == RoleTarget(role_arn=_ROLE_ARN, external_id=max_external_id)

    def test_source_read_failure_fails_closed(self, backend):
        """A source read/query failure surfaces as ``CredentialDerivationError``."""
        resolver = backend.resolver_with_read_failure()

        with pytest.raises(CredentialDerivationError):
            resolver.resolve({'sub': _IDENTITY})


class TestRegistryRoleResolverCallerClaim:
    """Caller-claim extraction is enforced before the source is touched.

    Validates: Requirements Registry-based role resolution.
    """

    def test_missing_caller_claim_fails_closed_without_reading_source(self):
        """Absent caller claim fails closed and never reads the source."""
        resolver = RegistryRoleResolver(_UnusedSource())

        with pytest.raises(CredentialDerivationError):
            resolver.resolve({'other': _IDENTITY})

    def test_empty_caller_claim_fails_closed_without_reading_source(self):
        """Empty caller claim fails closed and never reads the source."""
        resolver = RegistryRoleResolver(_UnusedSource())

        with pytest.raises(CredentialDerivationError):
            resolver.resolve({'sub': ''})

    def test_non_string_caller_claim_fails_closed_without_reading_source(self):
        """A non-string caller claim fails closed and never reads the source."""
        resolver = RegistryRoleResolver(_UnusedSource())

        with pytest.raises(CredentialDerivationError):
            resolver.resolve({'sub': 12345})

    def test_custom_caller_claim_is_used_for_lookup(self, backend):
        """A configured caller claim keys the registry lookup."""
        resolver = backend.resolver_with_record(
            {'role_arn': _ROLE_ARN, 'external_id': _EXTERNAL_ID}, caller_claim='email'
        )

        target = resolver.resolve({'email': _IDENTITY, 'sub': 'ignored'})

        assert target == RoleTarget(role_arn=_ROLE_ARN, external_id=_EXTERNAL_ID)
