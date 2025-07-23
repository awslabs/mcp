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

"""Tests for cache cluster processor functions."""

import pytest
from awslabs.elasticache_mcp_server.tools.cc.processors import process_scale_config


def test_process_scale_config_shorthand():
    """Test processing shorthand format scale configuration."""
    config = 'ReplicasPerNodeGroup=2,AutomaticFailoverEnabled=true'
    result = process_scale_config(config)

    assert result['ReplicasPerNodeGroup'] == 2
    assert result['AutomaticFailoverEnabled'] is True


def test_process_scale_config_json():
    """Test processing JSON format scale configuration."""
    config = {
        'ReplicasPerNodeGroup': 3,
        'AutomaticFailoverEnabled': True,
        'ScaleOutEnabled': True,
        'ScaleInEnabled': False,
        'TargetCapacity': 5,
        'MinCapacity': 2,
        'MaxCapacity': 10,
    }
    result = process_scale_config(config)

    assert result['ReplicasPerNodeGroup'] == 3
    assert result['AutomaticFailoverEnabled'] is True
    assert result['ScaleOutEnabled'] is True
    assert result['ScaleInEnabled'] is False
    assert result['TargetCapacity'] == 5
    assert result['MinCapacity'] == 2
    assert result['MaxCapacity'] == 10


def test_process_scale_config_invalid_type():
    """Test processing invalid input type."""
    # Test with list (neither string nor dict)
    config: list = [1, 2, 3]  # type: ignore
    with pytest.raises(ValueError) as excinfo:
        process_scale_config(config)  # type: ignore
    assert 'must be a dictionary or a shorthand string' in str(excinfo.value)


def test_process_scale_config_invalid_field_types():
    """Test processing JSON format with invalid field types."""
    # Test integer field with string
    config = {'ReplicasPerNodeGroup': '2'}
    with pytest.raises(ValueError) as excinfo:
        process_scale_config(config)
    assert 'ReplicasPerNodeGroup must be of type int' in str(excinfo.value)

    # Test boolean field with string
    config = {'AutomaticFailoverEnabled': 'true'}
    with pytest.raises(ValueError) as excinfo:
        process_scale_config(config)
    assert 'AutomaticFailoverEnabled must be of type bool' in str(excinfo.value)


def test_process_scale_config_capacity_validation():
    """Test capacity validation in JSON format."""
    # Valid capacity values
    config = {
        'MinCapacity': 2,
        'TargetCapacity': 5,
        'MaxCapacity': 10,
    }
    result = process_scale_config(config)
    assert result['MinCapacity'] == 2
    assert result['TargetCapacity'] == 5
    assert result['MaxCapacity'] == 10

    # Invalid: Min > Max
    config = {
        'MinCapacity': 10,
        'MaxCapacity': 5,
    }
    with pytest.raises(ValueError) as excinfo:
        process_scale_config(config)
    assert 'MinCapacity cannot be greater than MaxCapacity' in str(excinfo.value)

    # Invalid: Target < Min
    config = {
        'MinCapacity': 5,
        'TargetCapacity': 3,
        'MaxCapacity': 10,
    }
    with pytest.raises(ValueError) as excinfo:
        process_scale_config(config)
    assert 'TargetCapacity must be between MinCapacity and MaxCapacity' in str(excinfo.value)

    # Invalid: Target > Max
    config = {
        'MinCapacity': 5,
        'TargetCapacity': 15,
        'MaxCapacity': 10,
    }
    with pytest.raises(ValueError) as excinfo:
        process_scale_config(config)
    assert 'TargetCapacity must be between MinCapacity and MaxCapacity' in str(excinfo.value)


def test_process_scale_config_partial_json():
    """Test processing partial JSON configurations."""
    # Only integer field
    config = {'ReplicasPerNodeGroup': 3}
    result = process_scale_config(config)
    assert result == {'ReplicasPerNodeGroup': 3}

    # Only boolean field
    config = {'AutomaticFailoverEnabled': True}
    result = process_scale_config(config)
    assert result == {'AutomaticFailoverEnabled': True}

    # Mix of fields
    config = {'MinCapacity': 1, 'MaxCapacity': 5}
    result = process_scale_config(config)
    assert result == {'MinCapacity': 1, 'MaxCapacity': 5}


def test_process_scale_config_invalid_shorthand():
    """Test processing invalid shorthand syntax."""
    with pytest.raises(ValueError) as excinfo:
        process_scale_config('InvalidParam=2')
    assert 'Invalid scale config shorthand syntax' in str(excinfo.value)
