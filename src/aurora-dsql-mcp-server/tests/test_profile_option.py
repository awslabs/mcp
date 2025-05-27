# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance
# with the License. A copy of the License is located at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# or in the 'license' file accompanying this file. This file is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions
# and limitations under the License.
"""Tests for the profile option in server.py."""

import awslabs.aurora_dsql_mcp_server.server
from awslabs.aurora_dsql_mcp_server.server import main
from unittest.mock import patch


class TestProfileOption:
    """Tests for the profile option."""

    @patch(
        'sys.argv',
        [
            'awslabs.aurora-dsql-mcp-server',
            '--cluster_endpoint',
            'test_ce',
            '--database_user',
            'test_user',
            '--region',
            'us-west-2',
            '--profile',
            'test-profile',
        ],
    )
    def test_main_with_profile_argument(self, mocker):
        mock_boto3_session = mocker.patch('boto3.Session')
        mock_session = mock_boto3_session.return_value
        mock_dsql_client = mock_session.client.return_value

        mock_execute_query = mocker.patch('awslabs.aurora_dsql_mcp_server.server.execute_query')
        mock_execute_query.return_value = {'column': 1}

        mock_mcp_run = mocker.patch('awslabs.aurora_dsql_mcp_server.server.mcp.run')

        main()

        # Check that the profile was set correctly
        assert awslabs.aurora_dsql_mcp_server.server.aws_profile == 'test-profile'

        # Check that boto3.Session was called with the correct profile
        mock_boto3_session.assert_called_once_with(profile_name='test-profile')

        # Check that the session's client method was called with the correct service and region
        mock_session.client.assert_called_once_with('dsql', region_name='us-west-2')

        # Check that the dsql client was set correctly
        assert awslabs.aurora_dsql_mcp_server.server.dsql_client == mock_dsql_client

        # Check that the server was started
        mock_execute_query.assert_called_once()
        mock_mcp_run.assert_called_once()

    @patch(
        'sys.argv',
        [
            'awslabs.aurora-dsql-mcp-server',
            '--cluster_endpoint',
            'test_ce',
            '--database_user',
            'test_user',
            '--region',
            'us-west-2',
        ],
    )
    def test_main_without_profile_argument(self, mocker):
        mock_boto3_session = mocker.patch('boto3.Session')
        mock_session = mock_boto3_session.return_value
        mock_dsql_client = mock_session.client.return_value

        mock_execute_query = mocker.patch('awslabs.aurora_dsql_mcp_server.server.execute_query')
        mock_execute_query.return_value = {'column': 1}

        mock_mcp_run = mocker.patch('awslabs.aurora_dsql_mcp_server.server.mcp.run')

        main()

        # Check that the profile was not set
        assert awslabs.aurora_dsql_mcp_server.server.aws_profile is None

        # Check that boto3.Session was called without a profile
        mock_boto3_session.assert_called_once_with()

        # Check that the session's client method was called with the correct service and region
        mock_session.client.assert_called_once_with('dsql', region_name='us-west-2')

        # Check that the dsql client was set correctly
        assert awslabs.aurora_dsql_mcp_server.server.dsql_client == mock_dsql_client

        # Check that the server was started
        mock_execute_query.assert_called_once()
        mock_mcp_run.assert_called_once()
