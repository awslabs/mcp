"""Tests for the container_ls functionality."""

import pytest
from awslabs.finch_mcp_server.consts import STATUS_ERROR, STATUS_SUCCESS
from awslabs.finch_mcp_server.models import ContainerLSResult
from awslabs.finch_mcp_server.server import finch_container_ls
from unittest.mock import patch


class TestContainerLs:
    """Tests for the container_ls functionality."""

    @pytest.mark.asyncio
    async def test_finch_container_ls_success(self):
        """Test successful finch_container_ls resource."""
        with (
            patch('awslabs.finch_mcp_server.server.check_finch_installation') as mock_check_finch,
            patch('awslabs.finch_mcp_server.server.ensure_vm_running') as mock_ensure_vm,
            patch('awslabs.finch_mcp_server.server.list_containers') as mock_list_containers,
        ):
            # Mock raw JSON output
            raw_output = '{"ID":"test-container-1","Image":"python:3.9-alpine","Command":"python app.py","Created":"2023-01-01 12:00:00","Status":"Up 2 hours","Ports":"8080/tcp","Names":"my-python-app"}\n{"ID":"test-container-2","Image":"nginx:latest","Command":"nginx -g daemon off;","Created":"2023-01-02 12:00:00","Status":"Up 1 hour","Ports":"80/tcp, 443/tcp","Names":"my-nginx"}'

            mock_check_finch.return_value = {'status': STATUS_SUCCESS}
            mock_ensure_vm.return_value = {'status': STATUS_SUCCESS}
            mock_list_containers.return_value = {
                'status': STATUS_SUCCESS,
                'message': 'Successfully listed containers',
                'raw_output': raw_output,
            }

            result = await finch_container_ls()

            assert isinstance(result, ContainerLSResult)
            assert result.status == STATUS_SUCCESS
            assert 'Successfully listed containers' in result.message
            assert result.raw_output == raw_output

            # Verify that the mocks were called
            mock_check_finch.assert_called_once()
            mock_ensure_vm.assert_called_once()
            # Verify that list_containers was called with default parameters
            mock_list_containers.assert_called_once_with(
                all_containers=True,
                filter_expr=None,
                format_str=None,
                last=None,
                latest=False,
                no_trunc=False,
                quiet=False,
                size=False,
            )

    @pytest.mark.asyncio
    async def test_finch_container_ls_error(self):
        """Test finch_container_ls resource when an error occurs."""
        with (
            patch('awslabs.finch_mcp_server.server.check_finch_installation') as mock_check_finch,
            patch('awslabs.finch_mcp_server.server.ensure_vm_running') as mock_ensure_vm,
            patch('awslabs.finch_mcp_server.server.list_containers') as mock_list_containers,
        ):
            mock_check_finch.return_value = {'status': STATUS_SUCCESS}
            mock_ensure_vm.return_value = {'status': STATUS_SUCCESS}
            mock_list_containers.return_value = {
                'status': STATUS_ERROR,
                'message': 'Failed to list containers',
            }

            result = await finch_container_ls()

            assert isinstance(result, ContainerLSResult)
            assert result.status == STATUS_ERROR
            assert 'Failed to list containers' in result.message

            mock_check_finch.assert_called_once()
            mock_ensure_vm.assert_called_once()
            mock_list_containers.assert_called_once_with(
                all_containers=True,
                filter_expr=None,
                format_str=None,
                last=None,
                latest=False,
                no_trunc=False,
                quiet=False,
                size=False,
            )

    @pytest.mark.asyncio
    async def test_finch_container_ls_exception(self):
        """Test finch_container_ls resource when an exception occurs."""
        with (
            patch('awslabs.finch_mcp_server.server.check_finch_installation') as mock_check_finch,
            patch('awslabs.finch_mcp_server.server.ensure_vm_running') as mock_ensure_vm,
            patch('awslabs.finch_mcp_server.server.list_containers') as mock_list_containers,
        ):
            mock_check_finch.return_value = {'status': STATUS_SUCCESS}
            mock_ensure_vm.return_value = {'status': STATUS_SUCCESS}
            mock_list_containers.side_effect = Exception('Unexpected error')

            result = await finch_container_ls()

            assert isinstance(result, ContainerLSResult)
            assert result.status == STATUS_ERROR
            assert 'Error listing containers' in result.message

            mock_check_finch.assert_called_once()
            mock_ensure_vm.assert_called_once()
            mock_list_containers.assert_called_once_with(
                all_containers=True,
                filter_expr=None,
                format_str=None,
                last=None,
                latest=False,
                no_trunc=False,
                quiet=False,
                size=False,
            )
