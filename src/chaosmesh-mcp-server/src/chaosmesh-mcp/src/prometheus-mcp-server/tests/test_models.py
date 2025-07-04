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

"""Tests for data models."""

import pytest
from pydantic import ValidationError


def test_prometheus_config_valid():
    """Test creating a valid PrometheusConfig."""
    from awslabs.prometheus_mcp_server.models import PrometheusConfig

    # Execute
    config = PrometheusConfig(
        prometheus_url='https://aps-workspaces.us-east-1.amazonaws.com/workspaces/ws-123',
        aws_region='us-east-1',
        aws_profile='test-profile',
        service_name='aps',
        retry_delay=2,
        max_retries=5,
    )

    # Assert
    assert (
        config.prometheus_url == 'https://aps-workspaces.us-east-1.amazonaws.com/workspaces/ws-123'
    )
    assert config.aws_region == 'us-east-1'
    assert config.aws_profile == 'test-profile'
    assert config.service_name == 'aps'
    assert config.retry_delay == 2
    assert config.max_retries == 5


def test_prometheus_config_defaults():
    """Test PrometheusConfig with default values."""
    from awslabs.prometheus_mcp_server.models import PrometheusConfig

    # Execute
    config = PrometheusConfig(
        prometheus_url='https://aps-workspaces.us-east-1.amazonaws.com/workspaces/ws-123',
        aws_region='us-east-1',
        aws_profile=None,
    )

    # Assert
    assert (
        config.prometheus_url == 'https://aps-workspaces.us-east-1.amazonaws.com/workspaces/ws-123'
    )
    assert config.aws_region == 'us-east-1'
    assert config.aws_profile is None
    assert config.service_name == 'aps'
    assert config.retry_delay == 1
    assert config.max_retries == 3


def test_prometheus_config_invalid_url():
    """Test PrometheusConfig with invalid URL."""
    from awslabs.prometheus_mcp_server.models import PrometheusConfig

    # Execute and assert
    with pytest.raises(ValidationError):
        PrometheusConfig(
            prometheus_url='invalid-url',
            aws_region='us-east-1',
            aws_profile=None,
        )


def test_prometheus_config_empty_url():
    """Test PrometheusConfig with empty URL."""
    from awslabs.prometheus_mcp_server.models import PrometheusConfig

    # Execute and assert
    with pytest.raises(ValidationError):
        PrometheusConfig(
            prometheus_url='',
            aws_region='us-east-1',
            aws_profile=None,
        )


def test_prometheus_config_invalid_retry_delay():
    """Test PrometheusConfig with invalid retry delay."""
    from awslabs.prometheus_mcp_server.models import PrometheusConfig

    # Execute and assert
    with pytest.raises(ValidationError):
        PrometheusConfig(
            prometheus_url='https://aps-workspaces.us-east-1.amazonaws.com/workspaces/ws-123',
            aws_region='us-east-1',
            aws_profile=None,
            retry_delay=0,  # Must be >= 1
        )


def test_prometheus_config_invalid_max_retries():
    """Test PrometheusConfig with invalid max retries."""
    from awslabs.prometheus_mcp_server.models import PrometheusConfig

    # Execute and assert
    with pytest.raises(ValidationError):
        PrometheusConfig(
            prometheus_url='https://aps-workspaces.us-east-1.amazonaws.com/workspaces/ws-123',
            aws_region='us-east-1',
            aws_profile=None,
            max_retries=11,  # Must be <= 10
        )


def test_metrics_list():
    """Test MetricsList model."""
    from awslabs.prometheus_mcp_server.models import MetricsList

    # Execute
    metrics = MetricsList(metrics=['metric1', 'metric2', 'metric3'])

    # Assert
    assert metrics.metrics == ['metric1', 'metric2', 'metric3']


def test_server_info():
    """Test ServerInfo model."""
    from awslabs.prometheus_mcp_server.models import ServerInfo

    # Execute
    info = ServerInfo(
        prometheus_url='https://aps-workspaces.us-east-1.amazonaws.com/workspaces/ws-123',
        aws_region='us-east-1',
        aws_profile='test-profile',
        service_name='aps',
    )

    # Assert
    assert (
        info.prometheus_url == 'https://aps-workspaces.us-east-1.amazonaws.com/workspaces/ws-123'
    )
    assert info.aws_region == 'us-east-1'
    assert info.aws_profile == 'test-profile'
    assert info.service_name == 'aps'


def test_query_response():
    """Test QueryResponse model."""
    from awslabs.prometheus_mcp_server.models import QueryResponse

    # Execute - success case
    success_response = QueryResponse(
        status='success',
        data={'result': [{'metric': {'__name__': 'up'}, 'value': [1620000000, '1']}]},
        error=None,
    )

    # Assert
    assert success_response.status == 'success'
    assert success_response.data['result'][0]['metric']['__name__'] == 'up'
    assert success_response.error is None

    # Execute - error case
    error_response = QueryResponse(
        status='error',
        data={},
        error='Invalid query',
    )

    # Assert
    assert error_response.status == 'error'
    assert error_response.error == 'Invalid query'
