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

"""Targeted tests to cover uncovered branches in PR-changed source files.

Covers:
- transport.py: normalize whitespace-only, select None/valid mode
- mechanisms/explicit.py: malformed header decode
- mechanisms/jwt_exchange.py: STS client creation, malformed token claims
- config.py: hostname validation edges, multi-tenant invalid value, inbound mechanisms
- utils/aws_utils.py: FieldInfo coercion, partition multi-tenant cache, client wrappers
- mechanisms/role_resolver.py: parse_registry_source edge cases
"""

import pytest
from awslabs.aws_healthomics_mcp_server import consts
from awslabs.aws_healthomics_mcp_server.config import (
    ServerConfig,
    TransportConfigError,
    _is_valid_hostname,
    _parse_inbound_mechanisms,
    _parse_multi_tenant,
)
from awslabs.aws_healthomics_mcp_server.transport import TransportSelector
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# transport.py: TransportSelector.normalize and TransportSelector.select
# ---------------------------------------------------------------------------


class TestTransportSelectorNormalize:
    """Cover normalize() branches for whitespace-only and empty inputs."""

    def test_normalize_whitespace_only_returns_none(self):
        """Property: Whitespace-only transport value is treated as unset."""
        assert TransportSelector.normalize('   ') is None

    def test_normalize_empty_string_returns_none(self):
        """Property: Empty string transport value is treated as unset."""
        assert TransportSelector.normalize('') is None

    def test_normalize_none_returns_none(self):
        """Property: None transport value is treated as unset."""
        assert TransportSelector.normalize(None) is None

    def test_normalize_valid_value_returns_trimmed(self):
        """Property: A valid value is returned trimmed."""
        assert TransportSelector.normalize('  streamable-http  ') == 'streamable-http'


class TestTransportSelectorSelect:
    """Cover select() branches for None mode and valid mode."""

    def test_select_none_transport_returns_default(self):
        """Property: Unset transport resolves to the default stdio transport."""
        config = ServerConfig(transport=None, host='127.0.0.1', port=8000, path='/mcp')
        assert TransportSelector.select(config) == consts.DEFAULT_TRANSPORT

    def test_select_whitespace_transport_returns_default(self):
        """Property: Whitespace-only transport resolves to the default."""
        config = ServerConfig(transport='   ', host='127.0.0.1', port=8000, path='/mcp')
        assert TransportSelector.select(config) == consts.DEFAULT_TRANSPORT

    def test_select_valid_transport_returns_mode(self):
        """Property: A valid transport mode is returned as-is."""
        config = ServerConfig(
            transport='streamable-http', host='127.0.0.1', port=8000, path='/mcp'
        )
        assert TransportSelector.select(config) == 'streamable-http'

    def test_select_sse_transport_returns_sse(self):
        """Property: The sse transport is recognized and returned."""
        config = ServerConfig(transport='sse', host='127.0.0.1', port=8000, path='/mcp')
        assert TransportSelector.select(config) == 'sse'


# ---------------------------------------------------------------------------
# config.py: _is_valid_hostname edge cases
# ---------------------------------------------------------------------------


class TestIsValidHostname:
    """Cover hostname validation edge cases: empty, too long, trailing dot only."""

    def test_empty_hostname_is_invalid(self):
        """Property: Empty string is not a valid hostname."""
        assert _is_valid_hostname('') is False

    def test_none_hostname_is_invalid(self):
        """Property: None is not a valid hostname."""
        assert _is_valid_hostname(None) is False

    def test_hostname_exceeding_max_length_is_invalid(self):
        """Property: Hostname longer than 253 characters is invalid."""
        long_host = 'a' * 254
        assert _is_valid_hostname(long_host) is False

    def test_trailing_dot_only_is_invalid(self):
        """Property: A single trailing dot (empty candidate) is invalid."""
        assert _is_valid_hostname('.') is False

    def test_valid_hostname_with_trailing_dot(self):
        """Property: A valid hostname with a trailing root label dot is valid."""
        assert _is_valid_hostname('example.com.') is True


# ---------------------------------------------------------------------------
# config.py: _parse_multi_tenant invalid value
# ---------------------------------------------------------------------------


class TestParseMultiTenant:
    """Cover the invalid multi-tenant value that raises TransportConfigError."""

    def test_invalid_multi_tenant_value_raises(self):
        """Property: An unrecognized multi-tenant value raises TransportConfigError."""
        with pytest.raises(TransportConfigError):
            _parse_multi_tenant('invalid-value')

    def test_empty_string_returns_false(self):
        """Property: Empty string is treated as disabled."""
        assert _parse_multi_tenant('') is False

    def test_none_returns_false(self):
        """Property: None is treated as disabled."""
        assert _parse_multi_tenant(None) is False


# ---------------------------------------------------------------------------
# config.py: _parse_inbound_mechanisms edge cases
# ---------------------------------------------------------------------------


class TestParseInboundMechanisms:
    """Cover inbound mechanism parsing: empty tokens, invalid, ordering."""

    def test_none_returns_empty_tuple(self):
        """Property: None value yields empty tuple."""
        assert _parse_inbound_mechanisms(None) == ()

    def test_empty_string_returns_empty_tuple(self):
        """Property: Empty string yields empty tuple."""
        assert _parse_inbound_mechanisms('') == ()

    def test_whitespace_only_returns_empty_tuple(self):
        """Property: Whitespace-only string yields empty tuple."""
        assert _parse_inbound_mechanisms('   ') == ()

    def test_single_valid_mechanism(self):
        """Property: Single valid mechanism is returned in a tuple."""
        result = _parse_inbound_mechanisms('jwt')
        assert 'jwt' in result

    def test_multiple_mechanisms_ordered_by_precedence(self):
        """Property: Multiple mechanisms are returned in precedence order."""
        result = _parse_inbound_mechanisms('explicit,sigv4,jwt')
        # sigv4 > jwt > explicit is the defined precedence
        assert result.index('sigv4') < result.index('jwt')
        assert result.index('jwt') < result.index('explicit')

    def test_empty_tokens_between_commas_are_skipped(self):
        """Property: Empty tokens (consecutive commas) are ignored."""
        result = _parse_inbound_mechanisms('sigv4,,jwt,')
        assert 'sigv4' in result
        assert 'jwt' in result

    def test_invalid_mechanism_raises_transport_config_error(self):
        """Property: An unrecognized mechanism raises TransportConfigError."""
        with pytest.raises(TransportConfigError):
            _parse_inbound_mechanisms('oauth2')

    def test_case_insensitive_matching(self):
        """Property: Mechanism names are matched case-insensitively."""
        result = _parse_inbound_mechanisms('SigV4,JWT')
        assert 'sigv4' in result
        assert 'jwt' in result


# ---------------------------------------------------------------------------
# mechanisms/explicit.py: malformed header decode
# ---------------------------------------------------------------------------


class TestExplicitMalformedHeaders:
    """Cover the exception path in _extract_headers for malformed entries."""

    def test_malformed_header_entries_are_skipped(self):
        """Property: Non-decodable header entries are skipped gracefully."""
        from awslabs.aws_healthomics_mcp_server.mechanisms.explicit import _read_headers

        # Create a scope with a header whose name/value causes AttributeError
        # (e.g., None instead of bytes)
        scope = {
            'headers': [
                (None, b'value'),  # name is not bytes -> AttributeError
                (b'good-header', b'good-value'),
            ]
        }
        headers = _read_headers(scope)
        # The malformed entry is skipped, but the good one is kept
        assert 'good-header' in headers
        assert headers['good-header'] == 'good-value'

    def test_unicode_decode_error_is_skipped(self):
        """Property: Headers that cause UnicodeDecodeError are skipped."""
        from awslabs.aws_healthomics_mcp_server.mechanisms.explicit import _read_headers

        # Create a mock that raises UnicodeDecodeError on decode
        class BadBytes:
            def decode(self, encoding):
                raise UnicodeDecodeError(encoding, b'', 0, 1, 'mock error')

        scope = {
            'headers': [
                (BadBytes(), b'value'),
                (b'valid-header', b'valid-value'),
            ]
        }
        headers = _read_headers(scope)
        assert 'valid-header' in headers
        assert len(headers) == 1


# ---------------------------------------------------------------------------
# mechanisms/jwt_exchange.py: STS client creation and malformed claims
# ---------------------------------------------------------------------------


class TestJwtExchangeHelpers:
    """Cover get_sts_client and _decode_jwt_claims edge cases."""

    @patch('awslabs.aws_healthomics_mcp_server.mechanisms.jwt_exchange.boto3.Session')
    @patch('awslabs.aws_healthomics_mcp_server.mechanisms.jwt_exchange.botocore.session.Session')
    def test_get_sts_client_creates_session_with_region(self, mock_botocore, mock_boto3):
        """Property: get_sts_client builds a boto3 STS client with the given region."""
        from awslabs.aws_healthomics_mcp_server.mechanisms.jwt_exchange import get_sts_client

        mock_session_instance = MagicMock()
        mock_boto3.return_value = mock_session_instance
        mock_botocore_instance = MagicMock()
        mock_botocore.return_value = mock_botocore_instance

        client = get_sts_client('us-west-2')

        mock_boto3.assert_called_once_with(
            botocore_session=mock_botocore_instance, region_name='us-west-2'
        )
        mock_session_instance.client.assert_called_once_with('sts')
        assert client == mock_session_instance.client.return_value

    def test_decode_jwt_claims_non_dict_raises(self):
        """Property: A JWT whose claims decode to a non-dict raises."""
        import base64
        import json
        from awslabs.aws_healthomics_mcp_server.mechanisms.jwt_exchange import (
            CredentialDerivationError,
            _decode_jwt_claims,
        )

        # Build a token whose payload is a JSON array (not an object)
        header = base64.urlsafe_b64encode(b'{"alg":"none"}').rstrip(b'=').decode()
        payload = base64.urlsafe_b64encode(json.dumps([1, 2, 3]).encode()).rstrip(b'=').decode()
        token = f'{header}.{payload}.sig'

        with pytest.raises(CredentialDerivationError, match='not an object'):
            _decode_jwt_claims(token)

    def test_decode_jwt_claims_invalid_base64_raises(self):
        """Property: A JWT with invalid base64 payload raises."""
        from awslabs.aws_healthomics_mcp_server.mechanisms.jwt_exchange import (
            CredentialDerivationError,
            _decode_jwt_claims,
        )

        token = 'header.!!!invalid-base64!!!.sig'
        with pytest.raises(CredentialDerivationError, match='undecodable'):
            _decode_jwt_claims(token)


# ---------------------------------------------------------------------------
# mechanisms/role_resolver.py: parse_registry_source edge cases
# ---------------------------------------------------------------------------


class TestParseRegistrySource:
    """Cover parse_registry_source edges: file with bad netloc, empty path, ddb empty table."""

    def test_file_uri_with_invalid_netloc_raises(self):
        """Property: file://hostname/path with non-localhost netloc raises."""
        from awslabs.aws_healthomics_mcp_server.mechanisms.role_resolver import (
            parse_registry_source,
        )

        with pytest.raises(ValueError, match='Unsupported'):
            parse_registry_source('file://remotehost/some/path')

    def test_file_uri_with_empty_path_raises(self):
        """Property: file:// with no path raises."""
        from awslabs.aws_healthomics_mcp_server.mechanisms.role_resolver import (
            parse_registry_source,
        )

        with pytest.raises(ValueError, match='Unsupported'):
            parse_registry_source('file://')

    def test_dynamodb_uri_with_empty_table_raises(self):
        """Property: dynamodb:// with no table name raises."""
        from awslabs.aws_healthomics_mcp_server.mechanisms.role_resolver import (
            parse_registry_source,
        )

        with pytest.raises(ValueError, match='Unsupported'):
            parse_registry_source('dynamodb://')

    def test_file_uri_with_localhost_netloc_succeeds(self):
        """Property: file://localhost/path is a valid file source."""
        from awslabs.aws_healthomics_mcp_server.mechanisms.role_resolver import (
            FileRegistrySource,
            parse_registry_source,
        )

        source = parse_registry_source('file://localhost/etc/map.json')
        assert isinstance(source, FileRegistrySource)

    def test_unsupported_scheme_raises(self):
        """Property: An unknown scheme raises ValueError."""
        from awslabs.aws_healthomics_mcp_server.mechanisms.role_resolver import (
            parse_registry_source,
        )

        with pytest.raises(ValueError, match='Unsupported'):
            parse_registry_source('http://example.com/map.json')


# ---------------------------------------------------------------------------
# utils/aws_utils.py: FieldInfo coercion in DefaultCredentialResolver
# ---------------------------------------------------------------------------


class TestDefaultCredentialResolverFieldInfoCoercion:
    """Cover the FieldInfo coercion branches in DefaultCredentialResolver.resolve."""

    @patch('awslabs.aws_healthomics_mcp_server.utils.aws_utils.boto3.Session')
    @patch('awslabs.aws_healthomics_mcp_server.utils.aws_utils.botocore.session.Session')
    @patch(
        'awslabs.aws_healthomics_mcp_server.utils.aws_utils.get_region', return_value='us-east-1'
    )
    def test_fieldinfo_region_coerced_to_none(self, mock_get_region, mock_botocore, mock_boto3):
        """Property: A non-str/non-None region (FieldInfo) is coerced to None."""
        from awslabs.aws_healthomics_mcp_server.utils.aws_utils import (
            CredentialRequest,
            DefaultCredentialResolver,
        )

        resolver = DefaultCredentialResolver()
        # Pass an object (simulating FieldInfo) as region
        request = CredentialRequest(region=object(), profile=None)
        resolver.resolve(request)

        # Should use get_region() fallback since region was coerced to None
        mock_get_region.assert_called()

    @patch('awslabs.aws_healthomics_mcp_server.utils.aws_utils.boto3.Session')
    @patch('awslabs.aws_healthomics_mcp_server.utils.aws_utils.botocore.session.Session')
    @patch(
        'awslabs.aws_healthomics_mcp_server.utils.aws_utils.get_region', return_value='us-east-1'
    )
    def test_fieldinfo_profile_coerced_to_none(self, mock_get_region, mock_botocore, mock_boto3):
        """Property: A non-str/non-None profile (FieldInfo) is coerced to None."""
        from awslabs.aws_healthomics_mcp_server.utils.aws_utils import (
            CredentialRequest,
            DefaultCredentialResolver,
        )

        resolver = DefaultCredentialResolver()
        # Pass an object (simulating FieldInfo) as profile
        request = CredentialRequest(region='us-west-2', profile=object())
        resolver.resolve(request)

        # Should not pass profile_name to Session kwargs
        call_kwargs = mock_boto3.call_args[1]
        assert 'profile_name' not in call_kwargs


# ---------------------------------------------------------------------------
# utils/aws_utils.py: partition cache hit in multi-tenant mode
# ---------------------------------------------------------------------------


class TestPartitionCacheMultiTenant:
    """Cover the multi-tenant partition cache hit branch (move_to_end)."""

    @patch(
        'awslabs.aws_healthomics_mcp_server.utils.aws_utils.get_region', return_value='us-east-1'
    )
    def test_partition_cache_hit_returns_cached_value(self, mock_get_region):
        """Property: A cached partition value is returned on cache hit."""
        from awslabs.aws_healthomics_mcp_server.utils.aws_utils import (
            CredentialContext,
            RequestScopedCredentialResolver,
            _get_partition,
            _partition_cache,
            get_active_resolver,
            set_active_resolver,
            set_credential_context,
        )

        # Set up multi-tenant resolver
        mock_resolver = MagicMock(spec=RequestScopedCredentialResolver)
        mock_resolver.__class__ = RequestScopedCredentialResolver

        original_resolver = get_active_resolver()
        try:
            set_active_resolver(mock_resolver)

            # Set up a credential context
            ctx = CredentialContext(
                access_key_id='AKIAIOSFODNN7EXAMPLE',
                secret_access_key='wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY',  # pragma: allowlist secret
                session_token='token',
                identity_key='test-identity',
                source='explicit',
            )
            set_credential_context(ctx)

            # Pre-populate the cache
            cache_key = ('test-identity', 'us-east-1')
            _partition_cache[cache_key] = 'aws'

            # Call get_partition - should hit the cache
            result = _get_partition(region_name='us-east-1')
            assert result == 'aws'

            # Resolver.resolve should NOT have been called (cache hit)
            mock_resolver.resolve.assert_not_called()
        finally:
            set_active_resolver(original_resolver)
            set_credential_context(None)
            _partition_cache.clear()

    @patch(
        'awslabs.aws_healthomics_mcp_server.utils.aws_utils.get_region', return_value='us-east-1'
    )
    def test_partition_no_context_raises(self, mock_get_region):
        """Property: Missing credential context in multi-tenant mode raises."""
        from awslabs.aws_healthomics_mcp_server.utils.aws_utils import (
            NoRequestIdentityError,
            RequestScopedCredentialResolver,
            _get_partition,
            get_active_resolver,
            set_active_resolver,
            set_credential_context,
        )

        mock_resolver = MagicMock(spec=RequestScopedCredentialResolver)
        mock_resolver.__class__ = RequestScopedCredentialResolver

        original_resolver = get_active_resolver()
        try:
            set_active_resolver(mock_resolver)
            set_credential_context(None)

            with pytest.raises(NoRequestIdentityError):
                _get_partition()
        finally:
            set_active_resolver(original_resolver)


# ---------------------------------------------------------------------------
# utils/aws_utils.py: client wrapper functions (get_ecr_client, etc.)
# ---------------------------------------------------------------------------


class TestClientWrapperFunctions:
    """Cover the simple client wrapper functions."""

    @patch('awslabs.aws_healthomics_mcp_server.utils.aws_utils.create_aws_client')
    def test_get_ecr_client(self, mock_create):
        """Property: get_ecr_client delegates to create_aws_client with 'ecr'."""
        from awslabs.aws_healthomics_mcp_server.utils.aws_utils import get_ecr_client

        get_ecr_client(region_name='us-west-2')
        mock_create.assert_called_once_with('ecr', region_name='us-west-2', profile_name=None)

    @patch('awslabs.aws_healthomics_mcp_server.utils.aws_utils.create_aws_client')
    def test_get_codebuild_client(self, mock_create):
        """Property: get_codebuild_client delegates to create_aws_client with 'codebuild'."""
        from awslabs.aws_healthomics_mcp_server.utils.aws_utils import get_codebuild_client

        get_codebuild_client(region_name='eu-west-1')
        mock_create.assert_called_once_with(
            'codebuild', region_name='eu-west-1', profile_name=None
        )

    @patch('awslabs.aws_healthomics_mcp_server.utils.aws_utils.create_aws_client')
    def test_get_iam_client(self, mock_create):
        """Property: get_iam_client delegates to create_aws_client with 'iam'."""
        from awslabs.aws_healthomics_mcp_server.utils.aws_utils import get_iam_client

        get_iam_client(profile_name='dev')
        mock_create.assert_called_once_with('iam', region_name=None, profile_name='dev')


# ---------------------------------------------------------------------------
# mechanisms/role_resolver.py: get_dynamodb_client
# ---------------------------------------------------------------------------


class TestGetDynamoDbClient:
    """Cover get_dynamodb_client creation path."""

    @patch('awslabs.aws_healthomics_mcp_server.mechanisms.role_resolver.boto3.Session')
    @patch('awslabs.aws_healthomics_mcp_server.mechanisms.role_resolver.botocore.session.Session')
    def test_get_dynamodb_client_creates_client(self, mock_botocore, mock_boto3):
        """Property: get_dynamodb_client builds a DynamoDB client with the given region."""
        from awslabs.aws_healthomics_mcp_server.mechanisms.role_resolver import (
            get_dynamodb_client,
        )

        mock_session_instance = MagicMock()
        mock_boto3.return_value = mock_session_instance
        mock_botocore_instance = MagicMock()
        mock_botocore.return_value = mock_botocore_instance

        client = get_dynamodb_client('us-east-1')

        mock_boto3.assert_called_once_with(
            botocore_session=mock_botocore_instance, region_name='us-east-1'
        )
        mock_session_instance.client.assert_called_once_with('dynamodb')
        assert client == mock_session_instance.client.return_value

    @patch(
        'awslabs.aws_healthomics_mcp_server.utils.aws_utils._derive_partition', return_value='aws'
    )
    @patch(
        'awslabs.aws_healthomics_mcp_server.utils.aws_utils.get_region', return_value='us-east-1'
    )
    def test_partition_cache_miss_resolves_and_caches(self, mock_get_region, mock_derive):
        """Property: Cache miss calls resolver.resolve and caches the result."""
        from awslabs.aws_healthomics_mcp_server.utils.aws_utils import (
            CredentialContext,
            RequestScopedCredentialResolver,
            _get_partition,
            _partition_cache,
            get_active_resolver,
            set_active_resolver,
            set_credential_context,
        )

        mock_resolver = MagicMock(spec=RequestScopedCredentialResolver)
        mock_resolver.__class__ = RequestScopedCredentialResolver
        mock_session = MagicMock()
        mock_resolver.resolve.return_value = mock_session

        original_resolver = get_active_resolver()
        try:
            set_active_resolver(mock_resolver)

            ctx = CredentialContext(
                access_key_id='AKIAIOSFODNN7EXAMPLE',
                secret_access_key='wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY',  # pragma: allowlist secret
                session_token='token',
                identity_key='cache-miss-identity',
                source='jwt',
            )
            set_credential_context(ctx)

            # Ensure cache is empty for this key
            cache_key = ('cache-miss-identity', 'us-east-1')
            _partition_cache.pop(cache_key, None)

            result = _get_partition(region_name='us-east-1')

            assert result == 'aws'
            mock_resolver.resolve.assert_called_once()
            mock_derive.assert_called_once_with(mock_session)
            # Value should now be cached
            assert _partition_cache[cache_key] == 'aws'
        finally:
            set_active_resolver(original_resolver)
            set_credential_context(None)
            _partition_cache.clear()

    @patch(
        'awslabs.aws_healthomics_mcp_server.utils.aws_utils._derive_partition', return_value='aws'
    )
    @patch(
        'awslabs.aws_healthomics_mcp_server.utils.aws_utils.get_region', return_value='us-east-1'
    )
    def test_partition_cache_eviction_when_full(self, mock_get_region, mock_derive):
        """Property: Cache evicts oldest entry when exceeding max size."""
        from awslabs.aws_healthomics_mcp_server.utils.aws_utils import (
            _MAX_PARTITION_CACHE_ENTRIES,
            CredentialContext,
            RequestScopedCredentialResolver,
            _get_partition,
            _partition_cache,
            get_active_resolver,
            set_active_resolver,
            set_credential_context,
        )

        mock_resolver = MagicMock(spec=RequestScopedCredentialResolver)
        mock_resolver.__class__ = RequestScopedCredentialResolver
        mock_resolver.resolve.return_value = MagicMock()

        original_resolver = get_active_resolver()
        try:
            set_active_resolver(mock_resolver)

            # Fill cache to max capacity
            _partition_cache.clear()
            for i in range(_MAX_PARTITION_CACHE_ENTRIES):
                _partition_cache[(f'identity-{i}', 'us-east-1')] = 'aws'

            # Now add one more (triggers eviction)
            ctx = CredentialContext(
                access_key_id='AKIAIOSFODNN7EXAMPLE',
                secret_access_key='wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY',  # pragma: allowlist secret
                session_token='token',
                identity_key='overflow-identity',
                source='explicit',
            )
            set_credential_context(ctx)

            _get_partition(region_name='us-east-1')

            # Cache should not exceed max size
            assert len(_partition_cache) <= _MAX_PARTITION_CACHE_ENTRIES
            # The oldest entry should have been evicted
            assert ('identity-0', 'us-east-1') not in _partition_cache
            # The new entry should be present
            assert ('overflow-identity', 'us-east-1') in _partition_cache
        finally:
            set_active_resolver(original_resolver)
            set_credential_context(None)
            _partition_cache.clear()
