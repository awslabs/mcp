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

"""Tests for the ROSA user handler."""

import json
import pytest
from awslabs.rosa_mcp_server.rosa_user_handler import RosaUserHandler
from unittest.mock import AsyncMock


class TestRosaListUsers:
    """Tests for rosa_list_users."""

    @pytest.mark.asyncio
    async def test_given_cluster_when_list_users_then_gets_groups_and_users(
        self, mock_mcp, mock_ocm_client, mock_context
    ):
        """Test rosa_list_users gets groups and users for each group."""
        # Mock the request method that the handler uses
        groups_response = {
            'items': [
                {'id': 'dedicated-admins'},
                {'id': 'cluster-admins'},
            ],
        }
        users_response = {
            'items': [
                {'id': 'testuser'},
            ],
        }

        call_count = [0]

        async def mock_request(method, path, **kwargs):
            call_count[0] += 1
            if '/groups/' in path and '/users' in path:
                return users_response
            return groups_response

        mock_ocm_client.request = AsyncMock(side_effect=mock_request)
        handler = RosaUserHandler(mock_mcp, mock_ocm_client, allow_write=False)
        result = await handler.rosa_list_users(mock_context, cluster_id='test-id')

        assert isinstance(result, list)
        data = json.loads(result[0].text)
        assert data['cluster_id'] == 'test-id'
        assert 'groups' in data
        assert len(data['groups']) == 2
        assert data['groups'][0]['group'] == 'dedicated-admins'
        assert data['groups'][0]['users'] == [{'id': 'testuser'}]


class TestRosaGrantUser:
    """Tests for rosa_grant_user."""

    @pytest.mark.asyncio
    async def test_given_write_disabled_when_grant_then_raises_value_error(
        self, mock_mcp, mock_ocm_client, mock_context
    ):
        """Test rosa_grant_user requires allow_write."""
        handler = RosaUserHandler(mock_mcp, mock_ocm_client, allow_write=False)

        with pytest.raises(ValueError, match='Write operations disabled'):
            await handler.rosa_grant_user(
                mock_context, cluster_id='test-id', username='newuser'
            )

    @pytest.mark.asyncio
    async def test_given_dedicated_admins_when_grant_then_adds_to_group(
        self, mock_mcp, mock_ocm_client, mock_context
    ):
        """Test rosa_grant_user adds to dedicated-admins."""
        mock_ocm_client.request = AsyncMock(return_value={'id': 'newuser'})
        handler = RosaUserHandler(mock_mcp, mock_ocm_client, allow_write=True)
        result = await handler.rosa_grant_user(
            mock_context,
            cluster_id='test-id',
            username='newuser',
            group='dedicated-admins',
        )

        mock_ocm_client.request.assert_called_once_with(
            'POST',
            '/api/clusters_mgmt/v1/clusters/test-id/groups/dedicated-admins/users',
            body={'id': 'newuser'},
        )
        data = json.loads(result[0].text)
        assert data['status'] == 'granted'

    @pytest.mark.asyncio
    async def test_given_cluster_admins_when_grant_then_adds_to_cluster_admins(
        self, mock_mcp, mock_ocm_client, mock_context
    ):
        """Test rosa_grant_user adds to cluster-admins."""
        mock_ocm_client.request = AsyncMock(return_value={'id': 'admin-user'})
        handler = RosaUserHandler(mock_mcp, mock_ocm_client, allow_write=True)
        await handler.rosa_grant_user(
            mock_context,
            cluster_id='test-id',
            username='admin-user',
            group='cluster-admins',
        )

        call_args = mock_ocm_client.request.call_args
        assert '/groups/cluster-admins/users' in call_args[0][1]

class TestRosaRevokeUser:
    """Tests for rosa_revoke_user."""

    @pytest.mark.asyncio
    async def test_given_write_disabled_when_revoke_then_raises_value_error(
        self, mock_mcp, mock_ocm_client, mock_context
    ):
        """Test rosa_revoke_user requires allow_write."""
        handler = RosaUserHandler(mock_mcp, mock_ocm_client, allow_write=False)

        with pytest.raises(ValueError, match='Write operations disabled'):
            await handler.rosa_revoke_user(
                mock_context, cluster_id='test-id', username='user1'
            )

    @pytest.mark.asyncio
    async def test_given_valid_group_when_revoke_then_removes_from_group(
        self, mock_mcp, mock_ocm_client, mock_context
    ):
        """Test rosa_revoke_user removes user from group."""
        mock_ocm_client.request = AsyncMock(return_value=None)
        handler = RosaUserHandler(mock_mcp, mock_ocm_client, allow_write=True)
        result = await handler.rosa_revoke_user(
            mock_context,
            cluster_id='test-id',
            username='testuser',
            group='dedicated-admins',
        )

        mock_ocm_client.request.assert_called_once_with(
            'DELETE',
            '/api/clusters_mgmt/v1/clusters/test-id/groups/dedicated-admins/users/testuser',
        )
        data = json.loads(result[0].text)
        assert data['status'] == 'revoked'
        assert data['username'] == 'testuser'
        assert data['group'] == 'dedicated-admins'

