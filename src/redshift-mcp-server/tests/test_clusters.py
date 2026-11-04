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
import time
from awslabs.redshift_mcp_server import clusters as clusters_module
from awslabs.redshift_mcp_server.clusters import (
    _fetch_provisioned_clusters,
    _fetch_serverless_workgroups,
    _provisioned_cluster,
    _serverless_cluster,
    discover_clusters,
    resolve_cluster,
)
from botocore.exceptions import ClientError, EndpointConnectionError
from datetime import datetime, timezone
from helpers import _client_error
from mcp.server.mcpserver.exceptions import ToolError


class TestDiscoveryReadsEverything:
    """Discovery is the source of every cluster identifier, so what it drops is unreachable."""

    def _client(self, mocker, method, pages):
        """Patch one discovery client to page through `pages`."""
        client = mocker.Mock()
        client.get_paginator.return_value.paginate.return_value = pages
        mocker.patch(
            f'awslabs.redshift_mcp_server.clusters.client_manager.{method}', return_value=client
        )
        return client

    def test_every_page_of_provisioned_clusters_is_read(self, mocker):
        """Read one page, a cluster past it was missing from list_clusters and 'not found'."""
        self._client(
            mocker,
            'redshift_client',
            [
                {'Clusters': [{'ClusterIdentifier': 'a'}]},
                {'Clusters': [{'ClusterIdentifier': 'b'}]},
            ],
        )

        assert [c['ClusterIdentifier'] for c in _fetch_provisioned_clusters()] == ['a', 'b']

    def test_every_page_of_serverless_workgroups_is_read(self, mocker):
        """The same for workgroups."""
        self._client(
            mocker,
            'redshift_serverless_client',
            [{'workgroups': [{'workgroupName': 'a'}]}, {'workgroups': [{'workgroupName': 'b'}]}],
        )

        assert [w['workgroupName'] for w, _ in _fetch_serverless_workgroups()] == ['a', 'b']

    def test_a_tag_read_that_cannot_connect_leaves_the_workgroup_listed(self, mocker):
        """Tags are best effort against any failure, not only an AWS error.

        Caught as a ClientError alone, one tag read that could not connect failed all of
        discovery - list_clusters, and every statement that resolved while no discovery was stored.
        """
        client = self._client(
            mocker,
            'redshift_serverless_client',
            [
                {
                    'workgroups': [
                        {'workgroupName': 'wg', 'status': 'AVAILABLE', 'workgroupArn': 'arn:x'}
                    ]
                }
            ],
        )
        client.list_tags_for_resource.side_effect = EndpointConnectionError(
            endpoint_url='https://redshift-serverless'
        )

        assert [(w['workgroupName'], tags) for w, tags in _fetch_serverless_workgroups()] == [
            ('wg', [])
        ]

    def test_a_provisioned_cluster_reports_its_own_database(self):
        """A cluster created with another default database is not reported as 'dev'."""
        cluster = _provisioned_cluster(
            {'ClusterIdentifier': 'c', 'ClusterStatus': 'available', 'DBName': 'analytics'}
        )

        assert cluster.database_name == 'analytics'

    def test_every_provisioned_field_is_mapped(self):
        """list_clusters reports each field DescribeClusters gives, rather than null."""
        created = datetime(2024, 1, 2, tzinfo=timezone.utc)
        cluster = _provisioned_cluster(
            {
                'ClusterIdentifier': 'c1',
                'ClusterStatus': 'available',
                'DBName': 'analytics',
                'Endpoint': {'Address': 'c1.example', 'Port': 5439},
                'VpcId': 'vpc-1',
                'NodeType': 'ra3.xlplus',
                'NumberOfNodes': 2,
                'ClusterCreateTime': created,
                'MasterUsername': 'admin',
                'PubliclyAccessible': False,
                'Encrypted': True,
                'Tags': [],
            }
        )

        assert cluster.vpc_id == 'vpc-1'
        assert cluster.creation_time == created
        assert cluster.master_username == 'admin'
        assert cluster.publicly_accessible is False
        assert cluster.encrypted is True

    def test_a_workgroup_reports_when_it_was_created(self):
        """The same for a workgroup's creation date."""
        created = datetime(2024, 1, 2, tzinfo=timezone.utc)
        workgroup = _serverless_cluster(
            {'workgroupName': 'w1', 'status': 'AVAILABLE', 'creationDate': created}, []
        )

        assert workgroup.creation_time == created


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
                        'workgroupArn': ('arn:aws:redshift-serverless:us-east-1:1:workgroup/wg-1'),
                        'endpoint': {
                            'address': 'test.serverless.amazonaws.com',
                            'port': 5439,
                            'vpcEndpoints': [{'vpcEndpointId': 'vpce-1', 'vpcId': 'vpc-123'}],
                        },
                        # Still present, and no longer where vpc_id comes from.
                        'subnetIds': ['subnet-123'],
                        'publiclyAccessible': True,
                    }
                ]
            }
        ]
        mock_serverless_client.list_tags_for_resource.return_value = {
            'tags': [{'key': 'team', 'value': 'data'}]
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
        # Asked of ListTagsForResource, keyed by the workgroup's ARN. No serverless API returns a
        # workgroup's tags with the workgroup, so reading them off the entry reported every
        # workgroup untagged.
        assert workgroup.tags == {'team': 'data'}
        mock_serverless_client.list_tags_for_resource.assert_called_once_with(
            resourceArn='arn:aws:redshift-serverless:us-east-1:1:workgroup/wg-1'
        )

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
                        'workgroupArn': ('arn:aws:redshift-serverless:us-east-1:1:workgroup/wg-1'),
                        'configParameters': [],
                        'endpoint': {'address': 'test.serverless.amazonaws.com', 'port': 5439},
                        'subnetIds': [],  # present but empty - previously caused IndexError
                    }
                ]
            }
        ]
        mock_serverless_client.list_tags_for_resource.return_value = {'tags': []}

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

        # Stored before the denial, so a resolve would otherwise answer while list_clusters fails.
        clusters_module._discovered = (time.monotonic(), [])

        with pytest.raises(ToolError, match='IAM lacks both redshift and redshift-serverless'):
            await discover_clusters()

        assert clusters_module._discovered is None

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
                        'configParameters': [{'parameterValue': 'dev'}],
                        'workgroupArn': ('arn:aws:redshift-serverless:us-east-1:1:workgroup/wg-1'),
                        'endpoint': {'address': 'wg.serverless.amazonaws.com', 'port': 5439},
                        'subnetIds': ['subnet-abc'],
                        'publiclyAccessible': False,
                    }
                ]
            }
        ]
        mock_serverless_client.list_tags_for_resource.return_value = {'tags': []}

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


class TestWorkgroupTags:
    """A workgroup's tags are a call of their own, so its failures are their own too."""

    def _discovery(self, mocker, workgroup_count=1, fields=None, provisioned=False):
        """Wire discovery with `workgroup_count` workgroups, each carrying `fields`."""
        redshift_client = mocker.Mock()
        redshift_client.get_paginator.return_value.paginate.return_value = [
            {
                'Clusters': [{'ClusterIdentifier': 'provisioned-1', 'ClusterStatus': 'available'}]
                if provisioned
                else []
            }
        ]

        extra = (
            fields
            if fields is not None
            else {'workgroupArn': 'arn:aws:redshift-serverless:us-east-1:1:workgroup/wg'}
        )
        serverless_client = mocker.Mock()
        serverless_client.get_paginator.return_value.paginate.return_value = [
            {
                'workgroups': [
                    {'workgroupName': f'wg-{n}', 'status': 'AVAILABLE', **extra}
                    for n in range(workgroup_count)
                ]
            }
        ]

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
    async def test_a_denial_reports_the_workgroup_untagged(self, mocker):
        """Tags are all this permission carries, so losing the workgroup with them is worse."""
        serverless_client = self._discovery(mocker)
        serverless_client.list_tags_for_resource.side_effect = _client_error(
            'AccessDeniedException', 'Not authorized', status=403, operation='ListTagsForResource'
        )

        result = await discover_clusters()

        assert [one.identifier for one in result] == ['wg-0']
        assert result[0].tags == {}

    @pytest.mark.asyncio
    async def test_a_denial_on_one_workgroup_does_not_silence_the_others(self, mocker):
        """A policy scoped to some ARNs is ordinary, and the rest are still readable.

        Skipping the remaining calls after the first refusal reported workgroups the principal
        can read as untagged, indistinguishable from genuinely having no tags.
        """
        serverless_client = self._discovery(mocker, workgroup_count=3)
        readable = {'tags': [{'key': 'Environment', 'value': 'production'}]}
        serverless_client.list_tags_for_resource.side_effect = [
            _client_error('AccessDeniedException', 'Not authorized', status=403),
            readable,
            readable,
        ]

        result = await discover_clusters()

        assert [one.tags for one in result] == [
            {},
            {'Environment': 'production'},
            {'Environment': 'production'},
        ]
        assert serverless_client.list_tags_for_resource.call_count == 3

    @pytest.mark.asyncio
    async def test_any_failure_leaves_the_rest_of_discovery_standing(self, mocker):
        """Tags are the one field this call carries, and raising costs the whole cluster list.

        The serverless arm of discover_clusters drops the provisioned clusters it had already
        collected, and resolve_cluster discovers when no discovery is stored, so a statement on a healthy
        provisioned cluster failed because a workgroup's tags were throttled.
        """
        serverless_client = self._discovery(mocker, provisioned=True)
        serverless_client.list_tags_for_resource.side_effect = _client_error(
            'ThrottlingException', 'Rate exceeded', status=429, operation='ListTagsForResource'
        )

        result = await discover_clusters()

        assert sorted(one.identifier for one in result) == ['provisioned-1', 'wg-0']
        assert all(one.tags == {} for one in result if one.type == 'serverless')

    @pytest.mark.asyncio
    async def test_a_workgroup_deleted_mid_scan_is_reported_untagged(self, mocker):
        """ListTagsForResource models ResourceNotFoundException, and it is not a denial."""
        serverless_client = self._discovery(mocker)
        serverless_client.list_tags_for_resource.side_effect = _client_error(
            'ResourceNotFoundException', 'Not found', status=404, operation='ListTagsForResource'
        )

        result = await discover_clusters()

        assert [one.identifier for one in result] == ['wg-0']
        assert result[0].tags == {}

    @pytest.mark.asyncio
    async def test_an_entry_without_an_arn_is_not_a_crash(self, mocker):
        """Tags are keyed by ARN, and subscripting a missing one would fail all of discovery."""
        serverless_client = self._discovery(mocker, fields={})

        result = await discover_clusters()

        assert [one.identifier for one in result] == ['wg-0']
        assert result[0].tags == {}
        serverless_client.list_tags_for_resource.assert_not_called()

    @pytest.mark.asyncio
    async def test_the_workgroup_detail_is_never_asked_for_separately(self, mocker):
        """ListWorkgroups already answers with the whole Workgroup shape.

        The per-workgroup GetWorkgroup this used to make added nothing and could not fail safely:
        a workgroup deleted between the two answers ResourceNotFoundException, which is not a
        denial, so it failed all of discovery - taking every healthy provisioned cluster with it,
        and with them every statement, since resolve_cluster discovers when no discovery is stored.
        """
        serverless_client = self._discovery(
            mocker,
            fields={
                'workgroupArn': 'arn:aws:redshift-serverless:us-east-1:1:workgroup/wg',
                'endpoint': {
                    'address': 'wg.serverless.amazonaws.com',
                    'port': 5439,
                    'vpcEndpoints': [{'vpcId': 'vpc-9'}],
                },
                'publiclyAccessible': True,
            },
        )
        serverless_client.list_tags_for_resource.return_value = {'tags': []}

        result = await discover_clusters()

        serverless_client.get_workgroup.assert_not_called()
        # And every field the model reports came out of the list entry.
        assert result[0].endpoint == 'wg.serverless.amazonaws.com'
        assert result[0].port == 5439
        assert result[0].vpc_id == 'vpc-9'
        assert result[0].publicly_accessible is True

    @pytest.mark.asyncio
    async def test_a_workgroup_with_no_endpoint_yet_still_reports_its_port(self, mocker):
        """The port is on the workgroup as well, and is stated before the endpoint exists.

        Read from the endpoint alone, it came back null while the service was reporting it.
        """
        self._discovery(mocker, fields={'port': 5439})

        result = await discover_clusters()

        assert result[0].endpoint is None
        assert result[0].port == 5439


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
        ('provisioned', 'serverless', 'cluster_type', 'expected'),
        [
            (False, True, 'serverless', 'Listing serverless clusters was denied'),
            (True, False, 'provisioned', 'Listing provisioned clusters was denied'),
        ],
        ids=['serverless_denied', 'provisioned_denied'],
    )
    @pytest.mark.asyncio
    async def test_a_refused_listing_is_named_in_the_refusal(
        self, mocker, provisioned, serverless, cluster_type, expected
    ):
        """Discovery swallows a denial, so a hidden cluster answered as one that is not there.

        The advice compounded it: list_clusters runs the same discovery and omits the cluster
        too, so a caller following the message could never find it. Either half can be the one
        refused, and each names itself.
        """
        self._denied(mocker, provisioned=provisioned, serverless=serverless)

        with pytest.raises(ToolError) as raised:
            await resolve_cluster('some-cluster', cluster_type)

        assert 'not found' in str(raised.value)
        assert expected in str(raised.value)
        assert 'grant the listing permission' in str(raised.value)

    @pytest.mark.asyncio
    async def test_nothing_is_claimed_when_both_halves_answered(self, mocker):
        """With discovery complete, not found is the whole truth and needs no qualification."""
        self._denied(mocker, provisioned=False, serverless=False)

        with pytest.raises(ToolError) as raised:
            await resolve_cluster('some-cluster', 'provisioned')

        assert 'not found' in str(raised.value)
        assert 'denied' not in str(raised.value)

    @pytest.mark.asyncio
    async def test_a_denied_listing_is_not_named_for_a_type_it_could_not_hide(self, mocker):
        """A provisioned cluster cannot be a workgroup, so a denied serverless listing is beside it.

        Named anyway, it sent the caller to grant a permission that could not help.
        """
        self._denied(mocker, provisioned=False, serverless=True)

        with pytest.raises(ToolError) as raised:
            await resolve_cluster('some-cluster', 'provisioned')

        assert 'not found' in str(raised.value)
        assert 'denied' not in str(raised.value)

    @pytest.mark.asyncio
    async def test_a_hidden_type_asked_for_is_not_answered_with_the_other(self, mocker):
        """The type the caller named can be the half the denial hid.

        Reached only when nothing at all was found, the note was skipped whenever the other type
        answered to the same identifier: the caller was told the workgroup does not exist and
        handed the provisioned cluster of that name to use instead - a different warehouse,
        holding its own data.
        """
        redshift_client = mocker.Mock()
        redshift_client.get_paginator.return_value.paginate.return_value = [
            {'Clusters': [{'ClusterIdentifier': 'analytics', 'ClusterStatus': 'available'}]}
        ]

        serverless_client = mocker.Mock()
        serverless_client.get_paginator.return_value.paginate.side_effect = _client_error(
            'AccessDeniedException', 'Not authorized', status=403, operation='ListWorkgroups'
        )

        mocker.patch(
            'awslabs.redshift_mcp_server.redshift.client_manager.redshift_client',
            return_value=redshift_client,
        )
        mocker.patch(
            'awslabs.redshift_mcp_server.redshift.client_manager.redshift_serverless_client',
            return_value=serverless_client,
        )

        with pytest.raises(ToolError) as raised:
            await resolve_cluster('analytics', 'serverless')

        message = str(raised.value)
        assert 'No serverless cluster named analytics' in message
        assert 'Listing serverless clusters was denied' in message
        assert 'grant the listing permission' in message


class TestResolveAnswersFromTheStoredDiscovery:
    """Every statement resolves, so a discovery per resolve taxed each one with the control plane."""

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
                        'workgroupArn': ('arn:aws:redshift-serverless:us-east-1:1:workgroup/wg-1'),
                        'endpoint': {
                            'address': 'wg.serverless.amazonaws.com',
                            'port': 5439,
                            'vpcEndpoints': [{'vpcId': 'vpc-1'}],
                        },
                        'publiclyAccessible': False,
                    }
                ]
            }
        ]
        serverless_client.list_tags_for_resource.return_value = {'tags': []}

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
        """Answered from the stored discovery, so a second resolve asks nothing."""
        serverless_client = self._discovery(mocker)

        first = await resolve_cluster('wg', 'serverless')
        second = await resolve_cluster('wg', 'serverless')

        assert second is first
        assert serverless_client.get_paginator.call_count == 1

    @pytest.mark.asyncio
    async def test_the_stored_discovery_expires(self, mocker):
        """Bounded, so a cluster that changes type is not believed forever."""
        serverless_client = self._discovery(mocker)
        await resolve_cluster('wg', 'serverless')

        mocker.patch('awslabs.redshift_mcp_server.clusters.CLUSTER_RESOLVE_TTL', 0)
        await resolve_cluster('wg', 'serverless')

        assert serverless_client.get_paginator.call_count == 2

    @pytest.mark.asyncio
    async def test_a_name_missing_from_the_stored_discovery_is_refused_with_its_age(self, mocker):
        """Answered from the stored discovery, so a cluster created since reads as not found.

        Told only 'not found', a caller would take a cluster that exists for one that does not.
        """
        serverless_client = self._discovery(mocker)
        await resolve_cluster('wg', 'serverless')

        with pytest.raises(ToolError) as raised:
            await resolve_cluster('appears-later', 'serverless')

        assert 'not found' in str(raised.value)
        assert 'Clusters were last looked up' in str(raised.value)
        assert 'list_clusters looks again' in str(raised.value)
        assert serverless_client.get_paginator.call_count == 1

    @pytest.mark.asyncio
    async def test_a_discovery_picks_up_a_cluster_created_since(self, mocker):
        """The discovery list_clusters runs replaces the stored one, so the new name resolves."""
        serverless_client = self._discovery(mocker)
        await resolve_cluster('wg', 'serverless')
        serverless_client.get_paginator.return_value.paginate.return_value = [
            {'workgroups': [{'workgroupName': 'appears-later', 'status': 'AVAILABLE'}]}
        ]

        await discover_clusters()

        assert (await resolve_cluster('appears-later', 'serverless')).identifier == 'appears-later'

    @pytest.mark.asyncio
    async def test_a_discovery_forgets_a_cluster_it_no_longer_finds(self, mocker):
        """It saw the whole account, so a name missing from it no longer exists.

        Kept, the name reached the deleted cluster until the TTL ran out, and a write there was
        reported as possibly applied rather than as not found.
        """
        serverless_client = self._discovery(mocker)
        await resolve_cluster('wg', 'serverless')
        serverless_client.get_paginator.return_value.paginate.return_value = [{'workgroups': []}]

        await discover_clusters()

        with pytest.raises(ToolError, match='not found'):
            await resolve_cluster('wg', 'serverless')

    @pytest.mark.asyncio
    async def test_a_discovery_a_denial_cut_short_clears_the_stored_one(self, mocker):
        """Kept, the stored discovery refused a cluster list_clusters had just shown.

        Its advice, to run list_clusters, could not help until the stored discovery expired.
        """
        serverless_client = self._discovery(mocker)
        await resolve_cluster('wg', 'serverless')
        serverless_client.get_paginator.return_value.paginate.side_effect = _client_error(
            'AccessDeniedException', 'Not authorized', status=403, operation='ListWorkgroups'
        )
        mocker.patch(
            'awslabs.redshift_mcp_server.redshift.client_manager.redshift_client'
        ).return_value.get_paginator.return_value.paginate.return_value = [
            {'Clusters': [{'ClusterIdentifier': 'new', 'ClusterStatus': 'available'}]}
        ]

        # What list_clusters runs.
        await discover_clusters()

        assert clusters_module._discovered is None
        assert (await resolve_cluster('new', 'provisioned')).identifier == 'new'

    @pytest.mark.asyncio
    async def test_a_fresh_resolve_asks_again(self, mocker):
        """For a caller that reads what can change, such as the node type after a resize."""
        serverless_client = self._discovery(mocker)
        await resolve_cluster('wg', 'serverless')

        await resolve_cluster('wg', 'serverless', fresh=True)

        assert serverless_client.get_paginator.call_count == 2


class TestOneNameTwoWarehouses:
    """A provisioned cluster and a serverless workgroup can share a name.

    Confirmed against AWS: CreateWorkgroup accepts the name of an existing cluster, because the
    two are separate namespaces. Both then answer to one identifier, and only the type tells them
    apart.
    """

    def _discovery(self, mocker, name='shared'):
        """Wire discovery so `name` is both a provisioned cluster and a serverless workgroup."""
        redshift_client = mocker.Mock()
        redshift_client.get_paginator.return_value.paginate.return_value = [
            {'Clusters': [{'ClusterIdentifier': name, 'ClusterStatus': 'available'}]}
        ]

        serverless_client = mocker.Mock()
        serverless_client.get_paginator.return_value.paginate.return_value = [
            {'workgroups': [{'workgroupName': name, 'status': 'AVAILABLE'}]}
        ]

        mocker.patch(
            'awslabs.redshift_mcp_server.redshift.client_manager.redshift_client',
            return_value=redshift_client,
        )
        mocker.patch(
            'awslabs.redshift_mcp_server.redshift.client_manager.redshift_serverless_client',
            return_value=serverless_client,
        )

    def _workgroup_appears_later(self, mocker):
        """Wire discovery so a workgroup named like the cluster appears on the second discovery."""
        redshift_client = mocker.Mock()
        redshift_client.get_paginator.return_value.paginate.return_value = [
            {'Clusters': [{'ClusterIdentifier': 'shared', 'ClusterStatus': 'available'}]}
        ]

        # The workgroup from the second discovery on, however many there are. A list of answers
        # runs out, and the StopIteration raised on the worker thread leaves the awaiting call
        # hung rather than failed.
        first = iter([[{'workgroups': []}]])
        serverless_client = mocker.Mock()
        serverless_client.get_paginator.return_value.paginate.side_effect = lambda: next(
            first, [{'workgroups': [{'workgroupName': 'shared', 'status': 'AVAILABLE'}]}]
        )

        mocker.patch(
            'awslabs.redshift_mcp_server.redshift.client_manager.redshift_client',
            return_value=redshift_client,
        )
        mocker.patch(
            'awslabs.redshift_mcp_server.redshift.client_manager.redshift_serverless_client',
            return_value=serverless_client,
        )
        return serverless_client.get_paginator.return_value.paginate

    @pytest.mark.asyncio
    async def test_a_type_missing_from_the_stored_discovery_is_refused_with_its_age(self, mocker):
        """A workgroup created since is not in the stored discovery, so it is not found yet.

        Told only that, with the provisioned cluster named as found instead, a caller could move
        to a different warehouse. Told how old the lookup is, it looks again.
        """
        discoveries = self._workgroup_appears_later(mocker)
        assert (await resolve_cluster('shared', 'provisioned')).type == 'provisioned'

        with pytest.raises(ToolError) as raised:
            await resolve_cluster('shared', 'serverless')

        assert 'No serverless cluster named shared' in str(raised.value)
        assert 'list_clusters looks again' in str(raised.value)
        assert discoveries.call_count == 1

        # What list_clusters runs.
        await discover_clusters()

        assert (await resolve_cluster('shared', 'serverless')).type == 'serverless'

    @pytest.mark.asyncio
    async def test_a_discovery_a_denial_cut_short_is_not_stored(self, mocker):
        """Stored while a half was denied, the lookup hid that half for the rest of the TTL.

        Even after the denial cleared, a resolve answered from it, and its refusal named the age
        of the lookup rather than the denial.
        """
        redshift_client = mocker.Mock()
        redshift_client.get_paginator.return_value.paginate.return_value = [
            {'Clusters': [{'ClusterIdentifier': 'shared', 'ClusterStatus': 'available'}]}
        ]

        serverless_client = mocker.Mock()
        # Denied on the first discovery, restored on the second.
        serverless_client.get_paginator.return_value.paginate.side_effect = [
            _client_error(
                'AccessDeniedException', 'Not authorized', status=403, operation='ListWorkgroups'
            ),
            [{'workgroups': [{'workgroupName': 'shared', 'status': 'AVAILABLE'}]}],
            AssertionError('discovered more often than scripted'),
        ]

        mocker.patch(
            'awslabs.redshift_mcp_server.redshift.client_manager.redshift_client',
            return_value=redshift_client,
        )
        mocker.patch(
            'awslabs.redshift_mcp_server.redshift.client_manager.redshift_serverless_client',
            return_value=serverless_client,
        )

        # Answered from what was found, since a principal permanently denied one half has to keep
        # working, but not stored.
        assert (await resolve_cluster('shared', 'provisioned')).type == 'provisioned'
        assert clusters_module._discovered is None

        # So the next resolve asks again and sees the workgroup.
        assert (await resolve_cluster('shared', 'serverless')).type == 'serverless'

    @pytest.mark.asyncio
    async def test_the_cluster_type_says_which_one(self, mocker):
        """Each type reaches its own warehouse."""
        self._discovery(mocker)

        assert (await resolve_cluster('shared', 'provisioned')).type == 'provisioned'
        assert (await resolve_cluster('shared', 'serverless')).type == 'serverless'

    @pytest.mark.asyncio
    async def test_a_type_matching_nothing_names_what_was_found(self, mocker):
        """Told only 'not found', a caller would look for a cluster that is right there."""
        self._discovery(mocker, name='only-serverless')
        mocker.patch(
            'awslabs.redshift_mcp_server.redshift.client_manager.redshift_client'
        ).return_value.get_paginator.return_value.paginate.return_value = [{'Clusters': []}]

        with pytest.raises(ToolError) as raised:
            await resolve_cluster('only-serverless', 'provisioned')

        assert 'No provisioned cluster named only-serverless' in str(raised.value)
        assert 'Found instead: a serverless one' in str(raised.value)
