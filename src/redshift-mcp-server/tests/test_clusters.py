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


"""Tests for cluster discovery."""

import pytest
from awslabs.redshift_mcp_server import clusters as clusters_module
from awslabs.redshift_mcp_server.clusters import discover_clusters, resolve_cluster
from botocore.exceptions import ClientError
from mcp.server.mcpserver.exceptions import ToolError


class TestDiscoverFunctions:
    """Tests for discover_*() functions."""

    @pytest.mark.asyncio
    async def test_discover_clusters_provisioned(self, mocker):
        """Test discover_clusters function with provisioned clusters.

        Tests both complete cluster data and clusters with optional fields omitted
        to ensure proper default handling (e.g., DBName defaults to 'dev').
        Fixes: https://github.com/awslabs/mcp/issues/2331
        """
        # Define minimal cluster first (with defaults omitted)
        minimal_cluster = {
            'ClusterIdentifier': 'minimal-cluster',
            'ClusterStatus': 'available',
            # DBName intentionally omitted - tests .get('DBName', 'dev')
            'Endpoint': {'Address': 'minimal.redshift.amazonaws.com', 'Port': 5439},
            'VpcId': 'vpc-456',
            'NodeType': 'ra3.xlplus',
            'NumberOfNodes': 1,
            'ClusterCreateTime': '2024-06-01T00:00:00Z',
            'MasterUsername': 'admin',
            'PubliclyAccessible': False,
            'Encrypted': True,
            'Tags': [],
        }

        # Full cluster extends minimal (avoids code duplication)
        full_cluster = {
            **minimal_cluster,
            'ClusterIdentifier': 'test-cluster',
            'DBName': 'dev',
            'Endpoint': {'Address': 'test.redshift.amazonaws.com', 'Port': 5439},
            'VpcId': 'vpc-123',
            'NodeType': 'dc2.large',
            'NumberOfNodes': 2,
            'ClusterCreateTime': '2024-01-01T00:00:00Z',
            'Tags': [{'Key': 'env', 'Value': 'test'}],
        }

        # Mock redshift client with both clusters
        mock_redshift_client = mocker.Mock()
        mock_redshift_client.get_paginator.return_value.paginate.return_value = [
            {'Clusters': [full_cluster, minimal_cluster]}
        ]

        # Mock serverless client (empty response)
        mock_serverless_client = mocker.Mock()
        mock_serverless_client.get_paginator.return_value.paginate.return_value = [
            {'workgroups': []}
        ]

        # Mock client manager
        mocker.patch(
            'awslabs.redshift_mcp_server.redshift.client_manager.redshift_client',
            return_value=mock_redshift_client,
        )
        mocker.patch(
            'awslabs.redshift_mcp_server.redshift.client_manager.redshift_serverless_client',
            return_value=mock_serverless_client,
        )

        result = await discover_clusters()

        assert len(result) == 2

        # Verify full cluster (with all fields)
        cluster = result[0]
        assert cluster.identifier == 'test-cluster'
        assert cluster.type == 'provisioned'
        assert cluster.status == 'available'
        assert cluster.database_name == 'dev'
        assert cluster.endpoint == 'test.redshift.amazonaws.com'
        assert cluster.port == 5439
        assert cluster.node_type == 'dc2.large'
        assert cluster.number_of_nodes == 2
        assert cluster.tags == {'env': 'test'}

        # Verify minimal cluster (with defaults applied)
        minimal = result[1]
        assert minimal.identifier == 'minimal-cluster'
        assert minimal.type == 'provisioned'
        assert minimal.status == 'available'
        assert minimal.database_name == 'dev'  # default to 'dev'
        assert minimal.endpoint == 'minimal.redshift.amazonaws.com'
        assert minimal.port == 5439
        assert minimal.node_type == 'ra3.xlplus'
        assert minimal.number_of_nodes == 1
        assert minimal.tags == {}

    @pytest.mark.asyncio
    async def test_discover_clusters_provisioned_error(self, mocker):
        """Test error handling when discovering provisioned clusters fails."""
        mock_redshift_client = mocker.Mock()
        mock_paginator = mocker.Mock()
        mock_paginator.paginate.side_effect = Exception('AWS API Error')
        mock_redshift_client.get_paginator.return_value = mock_paginator

        mock_serverless_client = mocker.Mock()
        mock_serverless_client.list_workgroups.return_value = {'workgroups': []}

        mocker.patch(
            'awslabs.redshift_mcp_server.redshift.client_manager.redshift_client',
            return_value=mock_redshift_client,
        )
        mocker.patch(
            'awslabs.redshift_mcp_server.redshift.client_manager.redshift_serverless_client',
            return_value=mock_serverless_client,
        )

        with pytest.raises(Exception, match='AWS API Error'):
            await discover_clusters()

    @pytest.mark.asyncio
    async def test_discover_clusters_serverless(self, mocker):
        """Test discover_clusters with serverless workgroups.

        The serverless database_name is always reported as the built-in 'dev';
        """
        # Mock redshift client (empty response)
        mock_redshift_client = mocker.Mock()
        mock_redshift_client.get_paginator.return_value.paginate.return_value = [{'Clusters': []}]

        # Mock serverless client with one workgroup
        mock_serverless_client = mocker.Mock()
        mock_serverless_client.get_paginator.return_value.paginate.return_value = [
            {
                'workgroups': [
                    {
                        'workgroupName': 'test-workgroup',
                        'status': 'AVAILABLE',
                        'creationDate': '2024-01-01T00:00:00Z',
                    }
                ]
            }
        ]
        mock_serverless_client.get_workgroup.return_value = {
            'workgroup': {
                'endpoint': {
                    'address': 'test.serverless.amazonaws.com',
                    'port': 5439,
                    'vpcEndpoints': [{'vpcEndpointId': 'vpce-1', 'vpcId': 'vpc-123'}],
                },
                # Still present, and no longer where vpc_id comes from.
                'subnetIds': ['subnet-123'],
                'publiclyAccessible': True,
                'tags': [{'key': 'team', 'value': 'data'}],
            }
        }

        # Mock client manager
        mocker.patch(
            'awslabs.redshift_mcp_server.redshift.client_manager.redshift_client',
            return_value=mock_redshift_client,
        )
        mocker.patch(
            'awslabs.redshift_mcp_server.redshift.client_manager.redshift_serverless_client',
            return_value=mock_serverless_client,
        )

        result = await discover_clusters()

        assert len(result) == 1

        workgroup = result[0]
        assert workgroup.identifier == 'test-workgroup'
        assert workgroup.type == 'serverless'
        # Lowercased, though this API answers 'AVAILABLE', so one comparison serves both
        # cluster types.
        assert workgroup.status == 'available'
        assert workgroup.database_name == 'dev'
        assert workgroup.endpoint == 'test.serverless.amazonaws.com'
        assert workgroup.port == 5439
        # The VPC, not the subnet that used to be reported under this name.
        assert workgroup.vpc_id == 'vpc-123'
        assert workgroup.node_type is None
        assert workgroup.number_of_nodes is None
        assert workgroup.encrypted is True
        assert workgroup.tags == {'team': 'data'}

    @pytest.mark.asyncio
    async def test_discover_clusters_serverless_empty_subnet_ids(self, mocker):
        """Serverless workgroup with an empty subnetIds list must not raise (vpc_id=None)."""
        mock_redshift_client = mocker.Mock()
        mock_redshift_client.get_paginator.return_value.paginate.return_value = [{'Clusters': []}]

        mock_serverless_client = mocker.Mock()
        mock_serverless_client.get_paginator.return_value.paginate.return_value = [
            {
                'workgroups': [
                    {
                        'workgroupName': 'test-workgroup',
                        'status': 'AVAILABLE',
                        'creationDate': '2024-01-01T00:00:00Z',
                    }
                ]
            }
        ]
        mock_serverless_client.get_workgroup.return_value = {
            'workgroup': {
                'configParameters': [],
                'endpoint': {'address': 'test.serverless.amazonaws.com', 'port': 5439},
                'subnetIds': [],  # present but empty - previously caused IndexError
            }
        }

        mocker.patch(
            'awslabs.redshift_mcp_server.redshift.client_manager.redshift_client',
            return_value=mock_redshift_client,
        )
        mocker.patch(
            'awslabs.redshift_mcp_server.redshift.client_manager.redshift_serverless_client',
            return_value=mock_serverless_client,
        )

        result = await discover_clusters()

        assert len(result) == 1
        assert result[0].vpc_id is None

    @pytest.mark.asyncio
    async def test_discover_clusters_serverless_error(self, mocker):
        """Test error handling when discovering serverless workgroups fails."""
        mock_redshift_client = mocker.Mock()
        mock_paginator = mocker.Mock()
        mock_paginator.paginate.return_value = []
        mock_redshift_client.get_paginator.return_value = mock_paginator

        mock_serverless_client = mocker.Mock()
        mock_serverless_paginator = mocker.Mock()
        mock_serverless_paginator.paginate.side_effect = Exception('Serverless API Error')
        mock_serverless_client.get_paginator.return_value = mock_serverless_paginator

        mocker.patch(
            'awslabs.redshift_mcp_server.redshift.client_manager.redshift_client',
            return_value=mock_redshift_client,
        )
        mocker.patch(
            'awslabs.redshift_mcp_server.redshift.client_manager.redshift_serverless_client',
            return_value=mock_serverless_client,
        )

        with pytest.raises(Exception, match='Serverless API Error'):
            await discover_clusters()

    @pytest.mark.asyncio
    async def test_discover_clusters_both_access_denied_raises_tool_error(self, mocker):
        """Test that ToolError is raised when both clients get access-denied."""
        mock_redshift_client = mocker.Mock()
        mock_paginator = mocker.Mock()
        mock_paginator.paginate.side_effect = ClientError(
            {'Error': {'Code': 'AccessDenied', 'Message': 'Not authorized'}},
            'DescribeClusters',
        )
        mock_redshift_client.get_paginator.return_value = mock_paginator

        mock_serverless_client = mocker.Mock()
        mock_serverless_paginator = mocker.Mock()
        mock_serverless_paginator.paginate.side_effect = ClientError(
            {'Error': {'Code': 'AccessDeniedException', 'Message': 'Not authorized'}},
            'ListWorkgroups',
        )
        mock_serverless_client.get_paginator.return_value = mock_serverless_paginator

        mocker.patch(
            'awslabs.redshift_mcp_server.redshift.client_manager.redshift_client',
            return_value=mock_redshift_client,
        )
        mocker.patch(
            'awslabs.redshift_mcp_server.redshift.client_manager.redshift_serverless_client',
            return_value=mock_serverless_client,
        )

        with pytest.raises(ToolError, match='IAM lacks both redshift and redshift-serverless'):
            await discover_clusters()

    @pytest.mark.asyncio
    async def test_discover_clusters_provisioned_access_denied_serverless_succeeds(self, mocker):
        """Test partial results when provisioned gets access-denied but serverless succeeds."""
        mock_redshift_client = mocker.Mock()
        mock_paginator = mocker.Mock()
        mock_paginator.paginate.side_effect = ClientError(
            {'Error': {'Code': 'AccessDenied', 'Message': 'Not authorized'}},
            'DescribeClusters',
        )
        mock_redshift_client.get_paginator.return_value = mock_paginator

        mock_serverless_client = mocker.Mock()
        mock_serverless_client.get_paginator.return_value.paginate.return_value = [
            {
                'workgroups': [
                    {
                        'workgroupName': 'my-workgroup',
                        'status': 'AVAILABLE',
                        'creationDate': '2024-01-01T00:00:00Z',
                    }
                ]
            }
        ]
        mock_serverless_client.get_workgroup.return_value = {
            'workgroup': {
                'configParameters': [{'parameterValue': 'dev'}],
                'endpoint': {'address': 'wg.serverless.amazonaws.com', 'port': 5439},
                'subnetIds': ['subnet-abc'],
                'publiclyAccessible': False,
                'tags': [],
            }
        }

        mocker.patch(
            'awslabs.redshift_mcp_server.redshift.client_manager.redshift_client',
            return_value=mock_redshift_client,
        )
        mocker.patch(
            'awslabs.redshift_mcp_server.redshift.client_manager.redshift_serverless_client',
            return_value=mock_serverless_client,
        )

        result = await discover_clusters()

        assert len(result) == 1
        assert result[0].identifier == 'my-workgroup'
        assert result[0].type == 'serverless'

    @pytest.mark.asyncio
    async def test_discover_clusters_serverless_access_denied_provisioned_succeeds(self, mocker):
        """Test partial results when serverless gets access-denied but provisioned succeeds."""
        mock_redshift_client = mocker.Mock()
        mock_redshift_client.get_paginator.return_value.paginate.return_value = [
            {
                'Clusters': [
                    {
                        'ClusterIdentifier': 'my-cluster',
                        'ClusterStatus': 'available',
                        'DBName': 'dev',
                        'Endpoint': {'Address': 'cluster.redshift.amazonaws.com', 'Port': 5439},
                        'VpcId': 'vpc-123',
                        'NodeType': 'dc2.large',
                        'NumberOfNodes': 2,
                        'ClusterCreateTime': '2024-01-01T00:00:00Z',
                        'MasterUsername': 'admin',
                        'PubliclyAccessible': False,
                        'Encrypted': True,
                        'Tags': [],
                    }
                ]
            }
        ]

        mock_serverless_client = mocker.Mock()
        mock_serverless_paginator = mocker.Mock()
        mock_serverless_paginator.paginate.side_effect = ClientError(
            {'Error': {'Code': 'AccessDeniedException', 'Message': 'Not authorized'}},
            'ListWorkgroups',
        )
        mock_serverless_client.get_paginator.return_value = mock_serverless_paginator

        mocker.patch(
            'awslabs.redshift_mcp_server.redshift.client_manager.redshift_client',
            return_value=mock_redshift_client,
        )
        mocker.patch(
            'awslabs.redshift_mcp_server.redshift.client_manager.redshift_serverless_client',
            return_value=mock_serverless_client,
        )

        result = await discover_clusters()

        assert len(result) == 1
        assert result[0].identifier == 'my-cluster'
        assert result[0].type == 'provisioned'

    @pytest.mark.asyncio
    async def test_discover_clusters_non_access_denied_provisioned_bubbles_up(self, mocker):
        """Test that non-access-denied ClientError from provisioned discovery re-raises immediately."""
        mock_redshift_client = mocker.Mock()
        mock_paginator = mocker.Mock()
        mock_paginator.paginate.side_effect = ClientError(
            {'Error': {'Code': 'InternalServerError', 'Message': 'Something broke'}},
            'DescribeClusters',
        )
        mock_redshift_client.get_paginator.return_value = mock_paginator

        mock_serverless_client = mocker.Mock()
        mock_serverless_client.get_paginator.return_value.paginate.return_value = [
            {'workgroups': []}
        ]

        mocker.patch(
            'awslabs.redshift_mcp_server.redshift.client_manager.redshift_client',
            return_value=mock_redshift_client,
        )
        mocker.patch(
            'awslabs.redshift_mcp_server.redshift.client_manager.redshift_serverless_client',
            return_value=mock_serverless_client,
        )

        with pytest.raises(ClientError):
            await discover_clusters()

    @pytest.mark.asyncio
    async def test_discover_clusters_non_access_denied_serverless_bubbles_up(self, mocker):
        """Test that non-access-denied ClientError from serverless discovery re-raises immediately."""
        mock_redshift_client = mocker.Mock()
        mock_redshift_client.get_paginator.return_value.paginate.return_value = [{'Clusters': []}]

        mock_serverless_client = mocker.Mock()
        mock_serverless_paginator = mocker.Mock()
        mock_serverless_paginator.paginate.side_effect = ClientError(
            {'Error': {'Code': 'ThrottlingException', 'Message': 'Rate exceeded'}},
            'ListWorkgroups',
        )
        mock_serverless_client.get_paginator.return_value = mock_serverless_paginator

        mocker.patch(
            'awslabs.redshift_mcp_server.redshift.client_manager.redshift_client',
            return_value=mock_redshift_client,
        )
        mocker.patch(
            'awslabs.redshift_mcp_server.redshift.client_manager.redshift_serverless_client',
            return_value=mock_serverless_client,
        )

        with pytest.raises(ClientError):
            await discover_clusters()

    @pytest.mark.asyncio
    async def test_discover_clusters_both_non_access_denied_first_bubbles_up(self, mocker):
        """Test that when both clients raise non-access-denied ClientError, the first one (provisioned) re-raises."""
        mock_redshift_client = mocker.Mock()
        mock_paginator = mocker.Mock()
        mock_paginator.paginate.side_effect = ClientError(
            {'Error': {'Code': 'InternalServerError', 'Message': 'Provisioned broke'}},
            'DescribeClusters',
        )
        mock_redshift_client.get_paginator.return_value = mock_paginator

        mock_serverless_client = mocker.Mock()
        mock_serverless_paginator = mocker.Mock()
        mock_serverless_paginator.paginate.side_effect = ClientError(
            {'Error': {'Code': 'ThrottlingException', 'Message': 'Rate exceeded'}},
            'ListWorkgroups',
        )
        mock_serverless_client.get_paginator.return_value = mock_serverless_paginator

        mocker.patch(
            'awslabs.redshift_mcp_server.redshift.client_manager.redshift_client',
            return_value=mock_redshift_client,
        )
        mocker.patch(
            'awslabs.redshift_mcp_server.redshift.client_manager.redshift_serverless_client',
            return_value=mock_serverless_client,
        )

        with pytest.raises(ClientError, match='Provisioned broke'):
            await discover_clusters()


class TestAClusterHiddenByIam:
    """A cluster IAM cannot list is not a cluster that does not exist."""

    def _denied(self, mocker, *, provisioned: bool, serverless: bool):
        """Wire discovery with either half refused, and nothing found on the other."""
        redshift_client = mocker.Mock()
        if provisioned:
            redshift_client.get_paginator.return_value.paginate.side_effect = ClientError(
                {'Error': {'Code': 'AccessDenied', 'Message': 'Not authorized'}},
                'DescribeClusters',
            )
        else:
            redshift_client.get_paginator.return_value.paginate.return_value = [{'Clusters': []}]

        serverless_client = mocker.Mock()
        if serverless:
            serverless_client.get_paginator.return_value.paginate.side_effect = ClientError(
                {'Error': {'Code': 'AccessDeniedException', 'Message': 'Not authorized'}},
                'ListWorkgroups',
            )
        else:
            serverless_client.get_paginator.return_value.paginate.return_value = [
                {'workgroups': []}
            ]

        mocker.patch(
            'awslabs.redshift_mcp_server.redshift.client_manager.redshift_client',
            return_value=redshift_client,
        )
        mocker.patch(
            'awslabs.redshift_mcp_server.redshift.client_manager.redshift_serverless_client',
            return_value=serverless_client,
        )

    @pytest.mark.parametrize(
        ('provisioned', 'serverless', 'expected'),
        [
            (False, True, 'Listing serverless clusters was denied'),
            (True, False, 'Listing provisioned clusters was denied'),
        ],
        ids=['serverless_denied', 'provisioned_denied'],
    )
    @pytest.mark.asyncio
    async def test_a_refused_listing_is_named_in_the_refusal(
        self, mocker, provisioned, serverless, expected
    ):
        """Discovery swallows a denial, so a hidden cluster answered as one that is not there.

        The advice compounded it: list_clusters runs the same discovery and omits the cluster
        too, so a caller following the message could never find it. Either half can be the one
        refused, and each names itself.
        """
        self._denied(mocker, provisioned=provisioned, serverless=serverless)

        with pytest.raises(ToolError) as raised:
            await resolve_cluster('some-cluster')

        assert 'not found' in str(raised.value)
        assert expected in str(raised.value)
        assert 'grant the listing permission' in str(raised.value)

    @pytest.mark.asyncio
    async def test_nothing_is_claimed_when_both_halves_answered(self, mocker):
        """With discovery complete, not found is the whole truth and needs no qualification."""
        self._denied(mocker, provisioned=False, serverless=False)

        with pytest.raises(ToolError) as raised:
            await resolve_cluster('some-cluster')

        assert 'not found' in str(raised.value)
        assert 'denied' not in str(raised.value)


class TestResolveIsCached:
    """Every statement resolves, so an uncached resolve taxed each one with the control plane."""

    def _discovery(self, mocker):
        """Wire discovery with one workgroup, and count how often it is asked."""
        redshift_client = mocker.Mock()
        redshift_client.get_paginator.return_value.paginate.return_value = [{'Clusters': []}]

        serverless_client = mocker.Mock()
        serverless_client.get_paginator.return_value.paginate.return_value = [
            {
                'workgroups': [
                    {
                        'workgroupName': 'wg',
                        'status': 'AVAILABLE',
                        'creationDate': '2024-01-01T00:00:00Z',
                    }
                ]
            }
        ]
        serverless_client.get_workgroup.return_value = {
            'workgroup': {
                'endpoint': {
                    'address': 'wg.serverless.amazonaws.com',
                    'port': 5439,
                    'vpcEndpoints': [{'vpcId': 'vpc-1'}],
                },
                'publiclyAccessible': False,
                'tags': [],
            }
        }

        mocker.patch(
            'awslabs.redshift_mcp_server.redshift.client_manager.redshift_client',
            return_value=redshift_client,
        )
        mocker.patch(
            'awslabs.redshift_mcp_server.redshift.client_manager.redshift_serverless_client',
            return_value=serverless_client,
        )
        return serverless_client

    @pytest.mark.asyncio
    async def test_a_second_resolve_asks_nothing(self, mocker):
        """The identifier and the type are what a resolve needs, and neither changes."""
        serverless_client = self._discovery(mocker)

        first = await resolve_cluster('wg')
        second = await resolve_cluster('wg')

        assert second is first
        assert serverless_client.get_paginator.call_count == 1

    @pytest.mark.asyncio
    async def test_the_cache_expires(self, mocker):
        """Bounded, so a cluster that changes kind is not believed forever."""
        serverless_client = self._discovery(mocker)
        await resolve_cluster('wg')

        mocker.patch('awslabs.redshift_mcp_server.clusters.CLUSTER_RESOLVE_TTL', 0)
        await resolve_cluster('wg')

        assert serverless_client.get_paginator.call_count == 2

    @pytest.mark.asyncio
    async def test_a_miss_is_not_cached(self, mocker):
        """Otherwise a cluster created after the first failed lookup stayed invisible."""
        self._discovery(mocker)

        with pytest.raises(ToolError, match='not found'):
            await resolve_cluster('appears-later')

        assert 'appears-later' not in clusters_module._resolved
        # And the successful entries from that same sweep were kept.
        assert 'wg' in clusters_module._resolved
