"""Tests for the get_all_state_machines function."""

import pytest
from unittest.mock import MagicMock, patch


with pytest.MonkeyPatch().context() as CTX:
    CTX.setattr('boto3.Session', MagicMock)
    from awslabs.stepfunctions_tool_mcp_server.server import get_all_state_machines


class TestGetAllStateMachines:
    """Tests for the get_all_state_machines function."""

    @patch('awslabs.stepfunctions_tool_mcp_server.server.sfn_client')
    def test_single_page(self, mock_sfn_client):
        """Test retrieving state machines when the API returns a single page."""
        mock_sfn_client.get_paginator.return_value.paginate.return_value = [
            {
                'stateMachines': [
                    {'name': 'machine1', 'stateMachineArn': 'arn:aws:states:machine1'},
                    {'name': 'machine2', 'stateMachineArn': 'arn:aws:states:machine2'},
                ]
            }
        ]

        result = get_all_state_machines()

        assert len(result) == 2
        assert result[0]['name'] == 'machine1'
        assert result[1]['name'] == 'machine2'
        mock_sfn_client.get_paginator.assert_called_once_with('list_state_machines')

    @patch('awslabs.stepfunctions_tool_mcp_server.server.sfn_client')
    def test_multiple_pages(self, mock_sfn_client):
        """Test retrieving state machines that span multiple pages via nextToken."""
        mock_sfn_client.get_paginator.return_value.paginate.return_value = [
            {
                'stateMachines': [
                    {'name': 'machine1', 'stateMachineArn': 'arn:aws:states:machine1'}
                ]
            },
            {
                'stateMachines': [
                    {'name': 'machine2', 'stateMachineArn': 'arn:aws:states:machine2'}
                ]
            },
            {
                'stateMachines': [
                    {'name': 'machine3', 'stateMachineArn': 'arn:aws:states:machine3'}
                ]
            },
        ]

        result = get_all_state_machines()

        assert len(result) == 3
        assert [sm['name'] for sm in result] == ['machine1', 'machine2', 'machine3']

    @patch('awslabs.stepfunctions_tool_mcp_server.server.sfn_client')
    def test_empty_result(self, mock_sfn_client):
        """Test retrieving state machines when there are none."""
        mock_sfn_client.get_paginator.return_value.paginate.return_value = [{'stateMachines': []}]

        result = get_all_state_machines()

        assert result == []
