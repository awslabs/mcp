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

"""Tests for cross-account credential manager."""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from awslabs.aws_api_mcp_server.core.aws.credential_manager import (
    CachedCredentials,
    CredentialManager,
    get_credential_manager,
)
from awslabs.aws_api_mcp_server.core.common.models import Credentials

ROLE_ARN = 'arn:aws:iam::123456789012:role/TestRole'
ROLE_ARN_CN = 'arn:aws-cn:iam::123456789012:role/TestRole'
ROLE_ARN_2 = 'arn:aws:iam::987654321098:role/OtherRole'

MOCK_STS_RESPONSE = {
    'Credentials': {
        'AccessKeyId': 'ASIA_TEST_KEY',
        'SecretAccessKey': 'test_secret',
        'SessionToken': 'test_token',
        'Expiration': datetime.now() + timedelta(hours=1),
    },
    'AssumedRoleUser': {
        'AssumedRoleId': 'AROA_TEST:mcp-session',
        'Arn': ROLE_ARN,
    },
}


def _make_sts_mock():
    """Create a mock STS client that returns MOCK_STS_RESPONSE."""
    mock_client = MagicMock()
    mock_client.assume_role.return_value = MOCK_STS_RESPONSE
    return mock_client


# --- CredentialManager unit tests ---


async def test_cache_miss_calls_sts():
    """First call for a role should call STS AssumeRole."""
    mgr = CredentialManager(max_cache_size=10, default_duration_seconds=3600)
    mock_client = _make_sts_mock()

    with patch('boto3.client', return_value=mock_client):
        creds = await mgr.get_credentials(role_arn=ROLE_ARN)

    mock_client.assume_role.assert_called_once()
    assert creds.access_key_id == 'ASIA_TEST_KEY'
    assert creds.secret_access_key == 'test_secret'
    assert creds.session_token == 'test_token'


async def test_cache_hit_skips_sts():
    """Second call for same role should use cache, not call STS again."""
    mgr = CredentialManager(max_cache_size=10, default_duration_seconds=3600)
    mock_client = _make_sts_mock()

    with patch('boto3.client', return_value=mock_client):
        await mgr.get_credentials(role_arn=ROLE_ARN)
        await mgr.get_credentials(role_arn=ROLE_ARN)

    assert mock_client.assume_role.call_count == 1


async def test_expired_credentials_refresh():
    """Expired cached credentials should trigger a new STS call."""
    mgr = CredentialManager(max_cache_size=10, default_duration_seconds=3600)

    # Pre-populate cache with expired entry
    mgr._cache[ROLE_ARN] = CachedCredentials(
        credentials=Credentials(access_key_id='old', secret_access_key='old', session_token='old'),
        expiry=datetime.now() - timedelta(minutes=1),
        role_arn=ROLE_ARN,
    )

    mock_client = _make_sts_mock()
    with patch('boto3.client', return_value=mock_client):
        creds = await mgr.get_credentials(role_arn=ROLE_ARN)

    mock_client.assume_role.assert_called_once()
    assert creds.access_key_id == 'ASIA_TEST_KEY'


async def test_lru_eviction():
    """When cache is full, oldest entry should be evicted."""
    mgr = CredentialManager(max_cache_size=2, default_duration_seconds=3600)
    mock_client = _make_sts_mock()

    with patch('boto3.client', return_value=mock_client):
        await mgr.get_credentials(role_arn=ROLE_ARN)
        await mgr.get_credentials(role_arn=ROLE_ARN_2)
        await mgr.get_credentials(role_arn=ROLE_ARN_CN)

    assert len(mgr._cache) == 2
    assert ROLE_ARN not in mgr._cache  # oldest evicted
    assert ROLE_ARN_2 in mgr._cache
    assert ROLE_ARN_CN in mgr._cache


async def test_external_id_passed_to_sts():
    """external_id should be forwarded to STS AssumeRole."""
    mgr = CredentialManager(max_cache_size=10, default_duration_seconds=3600)
    mock_client = _make_sts_mock()

    with patch('boto3.client', return_value=mock_client):
        await mgr.get_credentials(role_arn=ROLE_ARN, external_id='ext-123')

    call_kwargs = mock_client.assume_role.call_args[1]
    assert call_kwargs['ExternalId'] == 'ext-123'


async def test_no_external_id_omitted():
    """When external_id is None, ExternalId should not be in STS params."""
    mgr = CredentialManager(max_cache_size=10, default_duration_seconds=3600)
    mock_client = _make_sts_mock()

    with patch('boto3.client', return_value=mock_client):
        await mgr.get_credentials(role_arn=ROLE_ARN)

    call_kwargs = mock_client.assume_role.call_args[1]
    assert 'ExternalId' not in call_kwargs


async def test_custom_session_name():
    """Custom session_name should be used in STS call."""
    mgr = CredentialManager(max_cache_size=10, default_duration_seconds=3600)
    mock_client = _make_sts_mock()

    with patch('boto3.client', return_value=mock_client):
        await mgr.get_credentials(role_arn=ROLE_ARN, session_name='my-session')

    call_kwargs = mock_client.assume_role.call_args[1]
    assert call_kwargs['RoleSessionName'] == 'my-session'


async def test_auto_generated_session_name():
    """When session_name is None, an auto-generated name should be used."""
    mgr = CredentialManager(max_cache_size=10, default_duration_seconds=3600)
    mock_client = _make_sts_mock()

    with patch('boto3.client', return_value=mock_client):
        await mgr.get_credentials(role_arn=ROLE_ARN)

    call_kwargs = mock_client.assume_role.call_args[1]
    assert call_kwargs['RoleSessionName'].startswith('mcp-')


async def test_sts_uses_default_region():
    """STS client should use DEFAULT_REGION."""
    mgr = CredentialManager(max_cache_size=10, default_duration_seconds=3600)
    mock_client = _make_sts_mock()

    with patch('boto3.client', return_value=mock_client) as mock_boto3_client, \
         patch('awslabs.aws_api_mcp_server.core.aws.credential_manager.DEFAULT_REGION', 'eu-west-1'):
        await mgr.get_credentials(role_arn=ROLE_ARN)

    mock_boto3_client.assert_called_with('sts', region_name='eu-west-1')


async def test_clear_cache_specific_role():
    """clear_cache with role_arn should only remove that role."""
    mgr = CredentialManager(max_cache_size=10, default_duration_seconds=3600)
    mock_client = _make_sts_mock()

    with patch('boto3.client', return_value=mock_client):
        await mgr.get_credentials(role_arn=ROLE_ARN)
        await mgr.get_credentials(role_arn=ROLE_ARN_2)

    await mgr.clear_cache(role_arn=ROLE_ARN)
    assert ROLE_ARN not in mgr._cache
    assert ROLE_ARN_2 in mgr._cache


async def test_clear_cache_all():
    """clear_cache without role_arn should clear everything."""
    mgr = CredentialManager(max_cache_size=10, default_duration_seconds=3600)
    mock_client = _make_sts_mock()

    with patch('boto3.client', return_value=mock_client):
        await mgr.get_credentials(role_arn=ROLE_ARN)
        await mgr.get_credentials(role_arn=ROLE_ARN_2)

    await mgr.clear_cache()
    assert len(mgr._cache) == 0


async def test_clear_cache_nonexistent_role():
    """clear_cache for a role not in cache should not raise."""
    mgr = CredentialManager(max_cache_size=10, default_duration_seconds=3600)
    await mgr.clear_cache(role_arn='arn:aws:iam::000000000000:role/NoSuchRole')
    assert len(mgr._cache) == 0


async def test_get_cache_stats_empty():
    """get_cache_stats on empty cache."""
    mgr = CredentialManager(max_cache_size=5, default_duration_seconds=3600)
    stats = mgr.get_cache_stats()
    assert stats['size'] == 0
    assert stats['capacity'] == 5
    assert stats['cached_roles'] == []


async def test_get_cache_stats_with_entries():
    """get_cache_stats should report cached roles."""
    mgr = CredentialManager(max_cache_size=10, default_duration_seconds=3600)
    mock_client = _make_sts_mock()

    with patch('boto3.client', return_value=mock_client):
        await mgr.get_credentials(role_arn=ROLE_ARN)

    stats = mgr.get_cache_stats()
    assert stats['size'] == 1
    assert len(stats['cached_roles']) == 1
    assert stats['cached_roles'][0]['role_arn'] == ROLE_ARN
    assert stats['cached_roles'][0]['expires_in_seconds'] > 0


async def test_is_valid_true():
    """_is_valid returns True for non-expired credentials."""
    mgr = CredentialManager()
    cached = CachedCredentials(
        credentials=Credentials(access_key_id='a', secret_access_key='b', session_token='c'),
        expiry=datetime.now() + timedelta(minutes=30),
        role_arn=ROLE_ARN,
    )
    assert mgr._is_valid(cached) is True


async def test_is_valid_false():
    """_is_valid returns False for expired credentials."""
    mgr = CredentialManager()
    cached = CachedCredentials(
        credentials=Credentials(access_key_id='a', secret_access_key='b', session_token='c'),
        expiry=datetime.now() - timedelta(minutes=1),
        role_arn=ROLE_ARN,
    )
    assert mgr._is_valid(cached) is False


# --- get_credential_manager singleton tests ---


def test_get_credential_manager_returns_instance():
    """get_credential_manager should return a CredentialManager."""
    with patch(
        'awslabs.aws_api_mcp_server.core.aws.credential_manager._credential_manager', None
    ):
        mgr = get_credential_manager()
        assert isinstance(mgr, CredentialManager)


def test_get_credential_manager_singleton():
    """get_credential_manager should return the same instance on repeated calls."""
    with patch(
        'awslabs.aws_api_mcp_server.core.aws.credential_manager._credential_manager', None
    ):
        mgr1 = get_credential_manager()
        mgr2 = get_credential_manager()
        assert mgr1 is mgr2
