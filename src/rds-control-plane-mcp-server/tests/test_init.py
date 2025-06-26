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

"""Basic import tests for the RDS Control Plane MCP Server."""

import os


def test_awslabs_package_exists():
    """Test that the awslabs package exists."""
    # Define the path to the awslabs package
    awslabs_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'awslabs'
    )
    assert os.path.exists(awslabs_path)
    assert os.path.isdir(awslabs_path)


def test_rds_control_plane_mcp_server_package_exists():
    """Test that the rds_control_plane_mcp_server package exists."""
    # Define the path to the rds_control_plane_mcp_server package
    package_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'awslabs',
        'rds_control_plane_mcp_server',
    )
    assert os.path.exists(package_path)
    assert os.path.isdir(package_path)


def test_can_import_server():
    """Test that the server module can be imported."""
    # Import the server module
    try:
        from awslabs.rds_control_plane_mcp_server import server

        assert server is not None
    except ImportError as e:
        assert False, f'Failed to import server module: {e}'


def test_server_has_mcp_instance():
    """Test that the server module has an MCP instance."""
    # Import the server module
    from awslabs.rds_control_plane_mcp_server import server

    assert hasattr(server, '_mcp')


def test_constants_has_version():
    """Test that the constants module has a version."""
    # Import the constants module
    from awslabs.rds_control_plane_mcp_server.common.constants import MCP_SERVER_VERSION

    assert MCP_SERVER_VERSION is not None
    assert isinstance(MCP_SERVER_VERSION, str)
