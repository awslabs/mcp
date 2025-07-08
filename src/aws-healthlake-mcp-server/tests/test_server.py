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

import pytest
from unittest.mock import Mock, patch
from awslabs.healthlake_mcp_server.server import get_healthlake_client


def test_get_healthlake_client_default_region():
    """Test that get_healthlake_client uses default region when none specified."""
    with patch('boto3.client') as mock_client:
        get_healthlake_client()
        mock_client.assert_called_once()
        args, kwargs = mock_client.call_args
        assert args[0] == 'healthlake'
        assert 'config' in kwargs


def test_get_healthlake_client_custom_region():
    """Test that get_healthlake_client uses custom region when specified."""
    with patch('boto3.client') as mock_client:
        get_healthlake_client('us-east-1')
        mock_client.assert_called_once()
        args, kwargs = mock_client.call_args
        assert args[0] == 'healthlake'
        assert kwargs['config'].region_name == 'us-east-1'


@patch.dict('os.environ', {'AWS_REGION': 'eu-west-1'})
def test_get_healthlake_client_env_region():
    """Test that get_healthlake_client uses AWS_REGION environment variable."""
    with patch('boto3.client') as mock_client:
        get_healthlake_client()
        mock_client.assert_called_once()
        args, kwargs = mock_client.call_args
        assert args[0] == 'healthlake'
        assert kwargs['config'].region_name == 'eu-west-1'
