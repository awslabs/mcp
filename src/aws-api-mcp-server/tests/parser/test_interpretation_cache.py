"""Tests for the boto3 client cache in core.parser.interpretation."""

import pytest
from awslabs.aws_api_mcp_server.core.parser import interpretation
from awslabs.aws_api_mcp_server.core.parser.interpretation import (
    _client_cache,
    _credentials_fingerprint,
    _get_or_create_client,
    clear_client_cache,
    interpret,
)
from botocore.config import Config
from botocore.exceptions import ClientError
from unittest.mock import MagicMock, patch


def _make_config(user_agent_extra: str = 'ua/test') -> Config:
    return Config(region_name='us-east-1', user_agent_extra=user_agent_extra)


def test_credentials_fingerprint_changes_when_any_field_changes():
    """Different credential tuples must yield different fingerprints."""
    base = _credentials_fingerprint('AKIA', 'secret', 'token')
    assert base != _credentials_fingerprint('AKIB', 'secret', 'token')
    assert base != _credentials_fingerprint('AKIA', 'secret2', 'token')
    assert base != _credentials_fingerprint('AKIA', 'secret', 'token2')
    assert base != _credentials_fingerprint('AKIA', 'secret', None)


def test_credentials_fingerprint_is_deterministic():
    """Same inputs produce the same fingerprint."""
    a = _credentials_fingerprint('AKIA', 'secret', 'token')
    b = _credentials_fingerprint('AKIA', 'secret', 'token')
    assert a == b


def test_credentials_fingerprint_does_not_contain_raw_secret():
    """Raw secret must not appear in the fingerprint."""
    secret = 'supersecret1234'
    fp = _credentials_fingerprint('AKIA', secret, None)
    assert secret not in fp


def test_get_or_create_client_reuses_cached_client():
    """Repeated calls with the same key return the same boto3 client instance."""
    with patch.object(interpretation, 'boto3') as mock_boto3:
        mock_boto3.client.return_value = MagicMock()
        c1 = _get_or_create_client('s3', 'AKIA', 'secret', None, 'us-east-1', _make_config(), None)
        c2 = _get_or_create_client('s3', 'AKIA', 'secret', None, 'us-east-1', _make_config(), None)

    assert c1 is c2
    assert mock_boto3.client.call_count == 1


def test_get_or_create_client_separates_by_service_and_region():
    """Different service/region combinations get distinct clients."""
    with patch.object(interpretation, 'boto3') as mock_boto3:
        mock_boto3.client.side_effect = [
            MagicMock(name='s3'),
            MagicMock(name='ec2'),
            MagicMock(name='s3-eu'),
        ]
        a = _get_or_create_client('s3', 'K', 'S', None, 'us-east-1', _make_config(), None)
        b = _get_or_create_client('ec2', 'K', 'S', None, 'us-east-1', _make_config(), None)
        c = _get_or_create_client('s3', 'K', 'S', None, 'eu-west-1', _make_config(), None)

    assert a is not b
    assert a is not c
    assert mock_boto3.client.call_count == 3


def test_get_or_create_client_separates_by_credentials():
    """Different credentials must not share a cached client."""
    with patch.object(interpretation, 'boto3') as mock_boto3:
        mock_boto3.client.side_effect = [MagicMock(), MagicMock()]
        a = _get_or_create_client('s3', 'K1', 'S1', None, 'us-east-1', _make_config(), None)
        b = _get_or_create_client('s3', 'K2', 'S2', None, 'us-east-1', _make_config(), None)

    assert a is not b


def test_get_or_create_client_separates_by_user_agent_extra():
    """Clients with different user_agent_extra must not be shared.

    Covers the streamable-http multi-client case where telemetry must track
    the originating MCP client.
    """
    with patch.object(interpretation, 'boto3') as mock_boto3:
        mock_boto3.client.side_effect = [MagicMock(), MagicMock()]
        a = _get_or_create_client(
            's3', 'K', 'S', None, 'us-east-1', _make_config('ua/client-one'), None
        )
        b = _get_or_create_client(
            's3', 'K', 'S', None, 'us-east-1', _make_config('ua/client-two'), None
        )

    assert a is not b


def test_get_or_create_client_lru_eviction():
    """Oldest client is evicted once the cache is full."""
    with patch.object(interpretation, '_MAX_CACHED_CLIENTS', 2):
        with patch.object(interpretation, 'boto3') as mock_boto3:
            mock_boto3.client.side_effect = [MagicMock(), MagicMock(), MagicMock()]
            _get_or_create_client('s3', 'K', 'S', None, 'us-east-1', _make_config(), None)
            _get_or_create_client('ec2', 'K', 'S', None, 'us-east-1', _make_config(), None)
            _get_or_create_client('iam', 'K', 'S', None, 'us-east-1', _make_config(), None)

    assert len(_client_cache) == 2


def test_interpret_evicts_client_on_auth_error():
    """Auth errors remove the cached client so the next call recreates it."""
    ir = MagicMock()
    ir.service_name = 's3'
    ir.operation_python_name = 'list_buckets'
    ir.operation_name = 'ListBuckets'
    ir.parameters = {}
    ir.has_streaming_output = False
    ir.output_file = None

    mock_client = MagicMock()
    mock_client.can_paginate.return_value = False
    mock_client.list_buckets.side_effect = ClientError(
        {'Error': {'Code': 'ExpiredTokenException', 'Message': 'expired'}}, 'ListBuckets'
    )

    clear_client_cache()
    with patch.object(interpretation, 'boto3') as mock_boto3:
        mock_boto3.client.return_value = mock_client
        with pytest.raises(ClientError):
            interpret(ir, 'K', 'S', None, 'us-east-1')

    assert len(_client_cache) == 0


def test_interpret_keeps_client_on_non_auth_error():
    """Non-auth errors must leave the cached client in place."""
    ir = MagicMock()
    ir.service_name = 's3'
    ir.operation_python_name = 'list_buckets'
    ir.operation_name = 'ListBuckets'
    ir.parameters = {}
    ir.has_streaming_output = False
    ir.output_file = None

    mock_client = MagicMock()
    mock_client.can_paginate.return_value = False
    mock_client.list_buckets.side_effect = ClientError(
        {'Error': {'Code': 'ThrottlingException', 'Message': 'slow down'}}, 'ListBuckets'
    )

    clear_client_cache()
    with patch.object(interpretation, 'boto3') as mock_boto3:
        mock_boto3.client.return_value = mock_client
        with pytest.raises(ClientError):
            interpret(ir, 'K', 'S', None, 'us-east-1')

    assert len(_client_cache) == 1
