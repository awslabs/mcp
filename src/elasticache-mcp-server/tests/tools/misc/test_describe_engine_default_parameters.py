"""Tests for the describe engine default parameters tool."""

import pytest
from awslabs.elasticache_mcp_server.tools.misc.describe_engine_default_parameters import (
    describe_engine_default_parameters,
)
from unittest.mock import MagicMock, patch


@pytest.mark.asyncio
async def test_describe_engine_default_parameters_basic():
    """Test basic describe engine default parameters functionality."""
    mock_client = MagicMock()
    mock_client.describe_engine_default_parameters.return_value = {
        'EngineDefaults': {
            'Parameters': [
                {
                    'ParameterName': 'activerehashing',
                    'ParameterValue': 'yes',
                    'Description': 'Enable/disable active rehashing',
                    'Source': 'system',
                    'DataType': 'string',
                    'AllowedValues': 'yes,no',
                    'IsModifiable': True,
                    'MinimumEngineVersion': '2.6.13',
                },
            ],
            'CacheParameterGroupFamily': 'redis6.x',
        }
    }

    with patch(
        'awslabs.elasticache_mcp_server.common.connection.ElastiCacheConnectionManager.get_connection',
        return_value=mock_client,
    ):
        result = await describe_engine_default_parameters(cache_parameter_group_family='redis6.x')

        mock_client.describe_engine_default_parameters.assert_called_once_with(
            CacheParameterGroupFamily='redis6.x'
        )
        assert 'EngineDefaults' in result
        assert 'Parameters' in result['EngineDefaults']
        assert len(result['EngineDefaults']['Parameters']) == 1
        assert result['EngineDefaults']['CacheParameterGroupFamily'] == 'redis6.x'


@pytest.mark.asyncio
async def test_describe_engine_default_parameters_with_pagination():
    """Test describe engine default parameters with pagination parameters."""
    mock_client = MagicMock()
    mock_client.describe_engine_default_parameters.return_value = {
        'EngineDefaults': {
            'Parameters': [
                {
                    'ParameterName': 'maxmemory-policy',
                    'ParameterValue': 'volatile-lru',
                    'Description': 'Max memory policy',
                    'Source': 'system',
                    'DataType': 'string',
                    'AllowedValues': 'volatile-lru,allkeys-lru,volatile-random,allkeys-random,volatile-ttl,noeviction',
                    'IsModifiable': True,
                    'MinimumEngineVersion': '2.6.13',
                },
            ],
            'CacheParameterGroupFamily': 'redis6.x',
        },
        'Marker': 'next-page',
    }

    with patch(
        'awslabs.elasticache_mcp_server.common.connection.ElastiCacheConnectionManager.get_connection',
        return_value=mock_client,
    ):
        result = await describe_engine_default_parameters(
            cache_parameter_group_family='redis6.x',
            max_records=20,
            marker='current-page',
        )

        mock_client.describe_engine_default_parameters.assert_called_once_with(
            CacheParameterGroupFamily='redis6.x',
            MaxRecords='20',
            Marker='current-page',
        )
        assert 'Marker' in result
        assert result['Marker'] == 'next-page'


@pytest.mark.asyncio
async def test_describe_engine_default_parameters_invalid_parameter():
    """Test describe engine default parameters with invalid parameter."""
    mock_client = MagicMock()
    exception_class = 'InvalidParameterValueException'
    error_message = 'Invalid parameter value'
    mock_exception = type(exception_class, (Exception,), {})
    setattr(mock_client.exceptions, exception_class, mock_exception)
    mock_client.describe_engine_default_parameters.side_effect = mock_exception(error_message)

    with patch(
        'awslabs.elasticache_mcp_server.common.connection.ElastiCacheConnectionManager.get_connection',
        return_value=mock_client,
    ):
        result = await describe_engine_default_parameters(
            cache_parameter_group_family='invalid-family'
        )

        assert 'error' in result
        assert error_message in result['error']


@pytest.mark.asyncio
async def test_describe_engine_default_parameters_invalid_parameter_combination():
    """Test describe engine default parameters with invalid parameter combination."""
    mock_client = MagicMock()
    exception_class = 'InvalidParameterCombinationException'
    error_message = 'Invalid parameter combination'
    mock_exception = type(exception_class, (Exception,), {})
    setattr(mock_client.exceptions, exception_class, mock_exception)
    mock_client.describe_engine_default_parameters.side_effect = mock_exception(error_message)

    with patch(
        'awslabs.elasticache_mcp_server.common.connection.ElastiCacheConnectionManager.get_connection',
        return_value=mock_client,
    ):
        result = await describe_engine_default_parameters(
            cache_parameter_group_family='redis6.x',
            max_records=-1,
        )

        assert 'error' in result
        assert error_message in result['error']
