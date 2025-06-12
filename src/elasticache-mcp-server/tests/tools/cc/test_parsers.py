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

"""Tests for cache cluster parser functions."""

import pytest
from awslabs.elasticache_mcp_server.tools.cc.parsers import parse_shorthand_scale_config


def test_parse_shorthand_scale_config_basic():
    """Test basic scale configuration parsing."""
    config = 'ReplicasPerNodeGroup=2,AutomaticFailoverEnabled=true'
    result = parse_shorthand_scale_config(config)

    assert result['ReplicasPerNodeGroup'] == 2
    assert result['AutomaticFailoverEnabled'] is True


def test_parse_shorthand_scale_config_full():
    """Test parsing full scale configuration."""
    config = (
        'ReplicasPerNodeGroup=3,AutomaticFailoverEnabled=true,ScaleOutEnabled=true,'
        'ScaleInEnabled=false,TargetCapacity=5,MinCapacity=2,MaxCapacity=10'
    )
    result = parse_shorthand_scale_config(config)

    assert result['ReplicasPerNodeGroup'] == 3
    assert result['AutomaticFailoverEnabled'] is True
    assert result['ScaleOutEnabled'] is True
    assert result['ScaleInEnabled'] is False
    assert result['TargetCapacity'] == 5
    assert result['MinCapacity'] == 2
    assert result['MaxCapacity'] == 10


def test_parse_shorthand_scale_config_boolean_values():
    """Test parsing different boolean value formats."""
    # Test true variations
    config = 'ScaleOutEnabled=true,ScaleInEnabled=True,AutomaticFailoverEnabled=TRUE'
    result = parse_shorthand_scale_config(config)
    assert result['ScaleOutEnabled'] is True
    assert result['ScaleInEnabled'] is True
    assert result['AutomaticFailoverEnabled'] is True

    # Test false variations
    config = 'ScaleOutEnabled=false,ScaleInEnabled=False,AutomaticFailoverEnabled=FALSE'
    result = parse_shorthand_scale_config(config)
    assert result['ScaleOutEnabled'] is False
    assert result['ScaleInEnabled'] is False
    assert result['AutomaticFailoverEnabled'] is False


def test_parse_shorthand_scale_config_capacity_validation():
    """Test capacity value validation."""
    # Valid capacity values
    config = 'MinCapacity=2,TargetCapacity=5,MaxCapacity=10'
    result = parse_shorthand_scale_config(config)
    assert result['MinCapacity'] == 2
    assert result['TargetCapacity'] == 5
    assert result['MaxCapacity'] == 10

    # Invalid: Min > Max
    with pytest.raises(ValueError) as excinfo:
        parse_shorthand_scale_config('MinCapacity=10,MaxCapacity=5')
    assert 'MinCapacity cannot be greater than MaxCapacity' in str(excinfo.value)

    # Invalid: Target < Min
    with pytest.raises(ValueError) as excinfo:
        parse_shorthand_scale_config('MinCapacity=5,TargetCapacity=3,MaxCapacity=10')
    assert 'TargetCapacity must be between MinCapacity and MaxCapacity' in str(excinfo.value)

    # Invalid: Target > Max
    with pytest.raises(ValueError) as excinfo:
        parse_shorthand_scale_config('MinCapacity=5,TargetCapacity=15,MaxCapacity=10')
    assert 'TargetCapacity must be between MinCapacity and MaxCapacity' in str(excinfo.value)


def test_parse_shorthand_scale_config_invalid_format():
    """Test invalid format handling."""
    # Empty config
    with pytest.raises(ValueError) as excinfo:
        parse_shorthand_scale_config('')
    assert 'Empty scale configuration' in str(excinfo.value)

    # Missing equals sign
    with pytest.raises(ValueError) as excinfo:
        parse_shorthand_scale_config('ReplicasPerNodeGroup:2')
    assert 'Each parameter must be in key=value format' in str(excinfo.value)

    # Empty key
    with pytest.raises(ValueError) as excinfo:
        parse_shorthand_scale_config('=2')
    assert 'Empty key or value' in str(excinfo.value)

    # Empty value
    with pytest.raises(ValueError) as excinfo:
        parse_shorthand_scale_config('ReplicasPerNodeGroup=')
    assert 'Empty key or value' in str(excinfo.value)


def test_parse_shorthand_scale_config_invalid_parameters():
    """Test invalid parameter handling."""
    # Invalid parameter name
    with pytest.raises(ValueError) as excinfo:
        parse_shorthand_scale_config('InvalidParam=2')
    assert 'Invalid parameter: InvalidParam' in str(excinfo.value)

    # Invalid integer value
    with pytest.raises(ValueError) as excinfo:
        parse_shorthand_scale_config('ReplicasPerNodeGroup=abc')
    assert 'Invalid value for ReplicasPerNodeGroup' in str(excinfo.value)


def test_parse_shorthand_scale_config_partial():
    """Test parsing partial configurations."""
    # Only integer parameter
    result = parse_shorthand_scale_config('ReplicasPerNodeGroup=3')
    assert result == {'ReplicasPerNodeGroup': 3}

    # Only boolean parameter
    result = parse_shorthand_scale_config('AutomaticFailoverEnabled=true')
    assert result == {'AutomaticFailoverEnabled': True}

    # Mix of parameters
    result = parse_shorthand_scale_config('MinCapacity=1,MaxCapacity=5')
    assert result == {'MinCapacity': 1, 'MaxCapacity': 5}
