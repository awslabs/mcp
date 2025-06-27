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

"""Tests for the Redshift MCP Server tools."""

import pytest
from awslabs.redshift_mcp_server.models import (
    QueryResult,
    RedshiftCluster,
    RedshiftColumn,
    RedshiftDatabase,
    RedshiftSchema,
    RedshiftTable,
)
from awslabs.redshift_mcp_server.server import (
    execute_query_tool,
    list_clusters_tool,
    list_columns_tool,
    list_databases_tool,
    list_schemas_tool,
    list_tables_tool,
)
from mcp.server.fastmcp import Context


class TestListClustersTool:
    """Tests for the list_clusters MCP tool."""

    @pytest.mark.asyncio
    async def test_list_clusters_tool_success(self, mocker):
        """Test successful cluster discovery with both provisioned and serverless clusters."""
        # Mock redshift client
        mock_redshift_client = mocker.Mock()
        mock_redshift_client.get_paginator.return_value.paginate.return_value = [
            {
                'Clusters': [
                    {
                        'ClusterIdentifier': 'test-cluster',
                        'ClusterStatus': 'available',
                        'DBName': 'dev',
                        'Endpoint': {
                            'Address': 'test-cluster.abc123.us-east-1.redshift.amazonaws.com',
                            'Port': 5439,
                        },
                        'VpcId': 'vpc-12345',
                        'NodeType': 'dc2.large',
                        'NumberOfNodes': 2,
                        'ClusterCreateTime': '2023-01-01T00:00:00Z',
                        'MasterUsername': 'testuser',
                        'PubliclyAccessible': False,
                        'Encrypted': True,
                        'Tags': [{'Key': 'Environment', 'Value': 'test'}],
                    }
                ]
            }
        ]

        # Mock serverless client
        mock_serverless_client = mocker.Mock()
        mock_serverless_client.get_paginator.return_value.paginate.return_value = [
            {
                'workgroups': [
                    {
                        'workgroupName': 'test-workgroup',
                        'status': 'AVAILABLE',
                        'creationDate': '2023-01-01T00:00:00Z',
                    }
                ]
            }
        ]
        mock_serverless_client.get_workgroup.return_value = {
            'workgroup': {
                'workgroupName': 'test-workgroup',
                'status': 'AVAILABLE',
                'creationDate': '2023-01-01T00:00:00Z',
                'endpoint': {
                    'address': 'test-workgroup.123456.us-east-1.redshift-serverless.amazonaws.com',
                    'port': 5439,
                },
                'subnetIds': ['subnet-12345'],
                'securityGroupIds': ['sg-12345'],
            }
        }

        # Patch client manager methods
        mocker.patch(
            'awslabs.redshift_mcp_server.redshift.client_manager.redshift_client',
            return_value=mock_redshift_client,
        )
        mocker.patch(
            'awslabs.redshift_mcp_server.redshift.client_manager.redshift_serverless_client',
            return_value=mock_serverless_client,
        )

        # Test the tool
        result = await list_clusters_tool(Context())

        # Verify results
        assert len(result) == 2
        assert all(isinstance(cluster, RedshiftCluster) for cluster in result)

        # Check provisioned cluster
        provisioned = next(c for c in result if c.type == 'provisioned')
        assert provisioned.identifier == 'test-cluster'
        assert provisioned.status == 'available'
        assert provisioned.database_name == 'dev'
        assert provisioned.port == 5439

        # Check serverless workgroup
        serverless = next(c for c in result if c.type == 'serverless')
        assert serverless.identifier == 'test-workgroup'
        assert serverless.status == 'AVAILABLE'

    @pytest.mark.asyncio
    async def test_list_clusters_tool_empty(self, mocker):
        """Test when no clusters are found."""
        # Mock empty responses
        mock_redshift_client = mocker.Mock()
        mock_redshift_client.get_paginator.return_value.paginate.return_value = [{'Clusters': []}]

        mock_serverless_client = mocker.Mock()
        mock_serverless_client.get_paginator.return_value.paginate.return_value = [
            {'workgroups': []}
        ]

        # Patch client manager methods
        mocker.patch(
            'awslabs.redshift_mcp_server.redshift.client_manager.redshift_client',
            return_value=mock_redshift_client,
        )
        mocker.patch(
            'awslabs.redshift_mcp_server.redshift.client_manager.redshift_serverless_client',
            return_value=mock_serverless_client,
        )

        # Test the tool
        result = await list_clusters_tool(Context())

        # Verify empty result
        assert len(result) == 0
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_list_clusters_tool_error(self, mocker):
        """Test error handling when AWS API calls fail."""
        # Mock client that raises exception
        mock_redshift_client = mocker.Mock()
        mock_redshift_client.get_paginator.side_effect = Exception('AWS API Error')

        mock_serverless_client = mocker.Mock()
        mock_serverless_client.get_paginator.return_value.paginate.return_value = [
            {'workgroups': []}
        ]

        # Mock context
        mock_context = mocker.Mock()
        mock_context.error = mocker.AsyncMock()

        # Patch client manager methods
        mocker.patch(
            'awslabs.redshift_mcp_server.redshift.client_manager.redshift_client',
            return_value=mock_redshift_client,
        )
        mocker.patch(
            'awslabs.redshift_mcp_server.redshift.client_manager.redshift_serverless_client',
            return_value=mock_serverless_client,
        )

        # Test the tool - should raise exception
        with pytest.raises(Exception, match='AWS API Error'):
            await list_clusters_tool(mock_context)


class TestListDatabasesTool:
    """Tests for the list_databases MCP tool."""

    @pytest.mark.asyncio
    async def test_list_databases_tool_success(self, mocker):
        """Test successful database discovery with explicit database_name."""
        # Mock data client for query execution
        mock_data_client = mocker.Mock()
        mock_data_client.batch_execute_statement.return_value = {'Id': 'batch-query-123'}
        mock_data_client.describe_statement.return_value = {
            'Status': 'FINISHED',
            'SubStatements': [
                {'Id': 'sub-query-0'},  # BEGIN READ ONLY
                {'Id': 'query-123'},  # Our actual SQL query
                {'Id': 'sub-query-2'},  # END
            ],
        }
        mock_data_client.get_statement_result.return_value = {
            'Records': [
                [
                    {'stringValue': 'dev'},
                    {'longValue': 100},
                    {'stringValue': 'local'},
                    {'stringValue': 'user=admin'},
                    {'stringValue': 'encoding=utf8'},
                    {'stringValue': 'Snapshot Isolation'},
                ],
                [
                    {'stringValue': 'test'},
                    {'longValue': 101},
                    {'stringValue': 'local'},
                    {'stringValue': 'user=testuser'},
                    {'stringValue': 'encoding=utf8'},
                    {'stringValue': 'Serializable'},
                ],
            ]
        }

        # Mock cluster discovery to return a valid cluster
        mock_discover_clusters = mocker.patch(
            'awslabs.redshift_mcp_server.redshift.discover_clusters'
        )
        mock_discover_clusters.return_value = [
            {'identifier': 'test-cluster', 'type': 'provisioned'}
        ]

        # Patch client manager
        mocker.patch(
            'awslabs.redshift_mcp_server.redshift.client_manager.redshift_data_client',
            return_value=mock_data_client,
        )

        # Test the tool with explicit database_name
        result = await list_databases_tool(
            Context(), cluster_identifier='test-cluster', database_name='custom_db'
        )

        # Verify results
        assert len(result) == 2
        assert all(isinstance(db, RedshiftDatabase) for db in result)

        # Check first database
        assert result[0].database_name == 'dev'
        assert result[0].database_owner == 100
        assert result[0].database_type == 'local'

        # Check second database
        assert result[1].database_name == 'test'
        assert result[1].database_owner == 101
        assert result[1].database_type == 'local'

    @pytest.mark.asyncio
    async def test_list_databases_tool_empty(self, mocker):
        """Test when no databases are found."""
        # Mock data client with empty results
        mock_data_client = mocker.Mock()
        mock_data_client.batch_execute_statement.return_value = {'Id': 'batch-query-123'}
        mock_data_client.describe_statement.return_value = {
            'Status': 'FINISHED',
            'SubStatements': [
                {'Id': 'sub-query-0'},  # BEGIN READ ONLY
                {'Id': 'query-123'},  # Our actual SQL query
                {'Id': 'sub-query-2'},  # END
            ],
        }
        mock_data_client.get_statement_result.return_value = {'Records': []}

        # Mock cluster discovery to return a serverless workgroup
        mock_discover_clusters = mocker.patch(
            'awslabs.redshift_mcp_server.redshift.discover_clusters'
        )
        mock_discover_clusters.return_value = [
            {'identifier': 'test-workgroup', 'type': 'serverless'}
        ]

        # Patch client manager
        mocker.patch(
            'awslabs.redshift_mcp_server.redshift.client_manager.redshift_data_client',
            return_value=mock_data_client,
        )

        # Test the tool
        result = await list_databases_tool(
            Context(), cluster_identifier='test-workgroup', database_name='dev'
        )

        # Verify empty result
        assert len(result) == 0
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_list_databases_tool_error(self, mocker):
        """Test error handling when AWS API calls fail."""
        # Mock data client that raises exception
        mock_data_client = mocker.Mock()
        mock_data_client.batch_execute_statement.side_effect = Exception('AWS API Error')

        # Mock cluster discovery
        mock_discover_clusters = mocker.patch(
            'awslabs.redshift_mcp_server.redshift.discover_clusters'
        )
        mock_discover_clusters.return_value = [
            {'identifier': 'test-cluster', 'type': 'provisioned'}
        ]

        # Mock context
        mock_context = mocker.Mock()
        mock_context.error = mocker.AsyncMock()

        # Patch client manager
        mocker.patch(
            'awslabs.redshift_mcp_server.redshift.client_manager.redshift_data_client',
            return_value=mock_data_client,
        )

        # Test the tool - should raise exception
        with pytest.raises(Exception, match='AWS API Error'):
            await list_databases_tool(
                mock_context, cluster_identifier='test-cluster', database_name='dev'
            )


class TestListSchemasTool:
    """Tests for the list_schemas MCP tool."""

    @pytest.mark.asyncio
    async def test_list_schemas_tool_success(self, mocker):
        """Test successful schema discovery with explicit schema_database_name."""
        # Mock data client for query execution
        mock_data_client = mocker.Mock()
        mock_data_client.batch_execute_statement.return_value = {'Id': 'batch-query-123'}
        mock_data_client.describe_statement.return_value = {
            'Status': 'FINISHED',
            'SubStatements': [
                {'Id': 'sub-query-0'},  # BEGIN READ ONLY
                {'Id': 'query-123'},  # Our actual SQL query
                {'Id': 'sub-query-2'},  # END
            ],
        }
        mock_data_client.get_statement_result.return_value = {
            'Records': [
                [
                    {'stringValue': 'dev'},  # database_name
                    {'stringValue': 'public'},  # schema_name
                    {'longValue': 100},  # schema_owner
                    {'stringValue': 'local'},  # schema_type
                    {'stringValue': 'user=admin'},  # schema_acl
                    {'stringValue': None},  # source_database
                    {'stringValue': None},  # schema_option
                ],
                [
                    {'stringValue': 'dev'},  # database_name
                    {'stringValue': 'analytics'},  # schema_name
                    {'longValue': 101},  # schema_owner
                    {'stringValue': 'external'},  # schema_type
                    {'stringValue': 'user=analyst'},  # schema_acl
                    {'stringValue': 'external_db'},  # source_database
                    {'stringValue': 'external_opt'},  # schema_option
                ],
            ]
        }

        # Mock cluster discovery to return a valid cluster
        mock_discover_clusters = mocker.patch(
            'awslabs.redshift_mcp_server.redshift.discover_clusters'
        )
        mock_discover_clusters.return_value = [
            {'identifier': 'test-cluster', 'type': 'provisioned'}
        ]

        # Patch client manager
        mocker.patch(
            'awslabs.redshift_mcp_server.redshift.client_manager.redshift_data_client',
            return_value=mock_data_client,
        )

        # Test the tool with explicit schema_database_name
        result = await list_schemas_tool(
            Context(), cluster_identifier='test-cluster', schema_database_name='dev'
        )

        # Verify results
        assert len(result) == 2
        assert all(isinstance(schema, RedshiftSchema) for schema in result)

        # Check first schema (local)
        assert result[0].database_name == 'dev'
        assert result[0].schema_name == 'public'
        assert result[0].schema_owner == 100
        assert result[0].schema_type == 'local'

        # Check second schema (external)
        assert result[1].database_name == 'dev'
        assert result[1].schema_name == 'analytics'
        assert result[1].schema_owner == 101
        assert result[1].schema_type == 'external'
        assert result[1].source_database == 'external_db'

    @pytest.mark.asyncio
    async def test_list_schemas_tool_empty(self, mocker):
        """Test when no schemas are found."""
        # Mock data client with empty results
        mock_data_client = mocker.Mock()
        mock_data_client.batch_execute_statement.return_value = {'Id': 'batch-query-123'}
        mock_data_client.describe_statement.return_value = {
            'Status': 'FINISHED',
            'SubStatements': [
                {'Id': 'sub-query-0'},  # BEGIN READ ONLY
                {'Id': 'query-123'},  # Our actual SQL query
                {'Id': 'sub-query-2'},  # END
            ],
        }
        mock_data_client.get_statement_result.return_value = {'Records': []}

        # Mock cluster discovery to return a serverless workgroup
        mock_discover_clusters = mocker.patch(
            'awslabs.redshift_mcp_server.redshift.discover_clusters'
        )
        mock_discover_clusters.return_value = [
            {'identifier': 'test-workgroup', 'type': 'serverless'}
        ]

        # Patch client manager
        mocker.patch(
            'awslabs.redshift_mcp_server.redshift.client_manager.redshift_data_client',
            return_value=mock_data_client,
        )

        # Test the tool
        result = await list_schemas_tool(
            Context(), cluster_identifier='test-workgroup', schema_database_name='test_db'
        )

        # Verify empty result
        assert len(result) == 0
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_list_schemas_tool_error(self, mocker):
        """Test error handling when AWS API calls fail."""
        # Mock data client that raises exception
        mock_data_client = mocker.Mock()
        mock_data_client.batch_execute_statement.side_effect = Exception('AWS API Error')

        # Mock cluster discovery
        mock_discover_clusters = mocker.patch(
            'awslabs.redshift_mcp_server.redshift.discover_clusters'
        )
        mock_discover_clusters.return_value = [
            {'identifier': 'test-cluster', 'type': 'provisioned'}
        ]

        # Mock context
        mock_context = mocker.Mock()
        mock_context.error = mocker.AsyncMock()

        # Patch client manager
        mocker.patch(
            'awslabs.redshift_mcp_server.redshift.client_manager.redshift_data_client',
            return_value=mock_data_client,
        )

        # Test the tool - should raise exception
        with pytest.raises(Exception, match='AWS API Error'):
            await list_schemas_tool(
                mock_context, cluster_identifier='test-cluster', schema_database_name='dev'
            )


class TestListTablesTool:
    """Tests for the list_tables MCP tool."""

    @pytest.mark.asyncio
    async def test_list_tables_tool_success(self, mocker):
        """Test successful table discovery with explicit parameters."""
        # Mock data client for query execution
        mock_data_client = mocker.Mock()
        mock_data_client.batch_execute_statement.return_value = {'Id': 'batch-query-123'}
        mock_data_client.describe_statement.return_value = {
            'Status': 'FINISHED',
            'SubStatements': [
                {'Id': 'sub-query-0'},  # BEGIN READ ONLY
                {'Id': 'query-123'},  # Our actual SQL query
                {'Id': 'sub-query-2'},  # END
            ],
        }
        mock_data_client.get_statement_result.return_value = {
            'Records': [
                [
                    {'stringValue': 'dev'},  # database_name
                    {'stringValue': 'public'},  # schema_name
                    {'stringValue': 'users'},  # table_name
                    {'stringValue': 'user=admin'},  # table_acl
                    {'stringValue': 'TABLE'},  # table_type
                    {'stringValue': 'User data'},  # remarks
                ],
                [
                    {'stringValue': 'dev'},  # database_name
                    {'stringValue': 'public'},  # schema_name
                    {'stringValue': 'user_view'},  # table_name
                    {'stringValue': 'user=analyst'},  # table_acl
                    {'stringValue': 'VIEW'},  # table_type
                    {'stringValue': 'User view'},  # remarks
                ],
            ]
        }

        # Mock cluster discovery to return a valid cluster
        mock_discover_clusters = mocker.patch(
            'awslabs.redshift_mcp_server.redshift.discover_clusters'
        )
        mock_discover_clusters.return_value = [
            {'identifier': 'test-cluster', 'type': 'provisioned'}
        ]

        # Patch client manager
        mocker.patch(
            'awslabs.redshift_mcp_server.redshift.client_manager.redshift_data_client',
            return_value=mock_data_client,
        )

        # Test the tool with explicit parameters
        result = await list_tables_tool(
            Context(),
            cluster_identifier='test-cluster',
            table_database_name='dev',
            table_schema_name='public',
        )

        # Verify results
        assert len(result) == 2
        assert all(isinstance(table, RedshiftTable) for table in result)

        # Check first table (base table)
        assert result[0].database_name == 'dev'
        assert result[0].schema_name == 'public'
        assert result[0].table_name == 'users'
        assert result[0].table_type == 'TABLE'
        assert result[0].remarks == 'User data'

        # Check second table (view)
        assert result[1].database_name == 'dev'
        assert result[1].schema_name == 'public'
        assert result[1].table_name == 'user_view'
        assert result[1].table_type == 'VIEW'
        assert result[1].remarks == 'User view'

    @pytest.mark.asyncio
    async def test_list_tables_tool_empty(self, mocker):
        """Test when no tables are found."""
        # Mock data client with empty results
        mock_data_client = mocker.Mock()
        mock_data_client.batch_execute_statement.return_value = {'Id': 'batch-query-123'}
        mock_data_client.describe_statement.return_value = {
            'Status': 'FINISHED',
            'SubStatements': [
                {'Id': 'sub-query-0'},  # BEGIN READ ONLY
                {'Id': 'query-123'},  # Our actual SQL query
                {'Id': 'sub-query-2'},  # END
            ],
        }
        mock_data_client.get_statement_result.return_value = {'Records': []}

        # Mock cluster discovery to return a serverless workgroup
        mock_discover_clusters = mocker.patch(
            'awslabs.redshift_mcp_server.redshift.discover_clusters'
        )
        mock_discover_clusters.return_value = [
            {'identifier': 'test-workgroup', 'type': 'serverless'}
        ]

        # Patch client manager
        mocker.patch(
            'awslabs.redshift_mcp_server.redshift.client_manager.redshift_data_client',
            return_value=mock_data_client,
        )

        # Test the tool
        result = await list_tables_tool(
            Context(),
            cluster_identifier='test-workgroup',
            table_database_name='test_db',
            table_schema_name='empty_schema',
        )

        # Verify empty result
        assert len(result) == 0
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_list_tables_tool_error(self, mocker):
        """Test error handling when AWS API calls fail."""
        # Mock data client that raises exception
        mock_data_client = mocker.Mock()
        mock_data_client.batch_execute_statement.side_effect = Exception('AWS API Error')

        # Mock cluster discovery
        mock_discover_clusters = mocker.patch(
            'awslabs.redshift_mcp_server.redshift.discover_clusters'
        )
        mock_discover_clusters.return_value = [
            {'identifier': 'test-cluster', 'type': 'provisioned'}
        ]

        # Mock context
        mock_context = mocker.Mock()
        mock_context.error = mocker.AsyncMock()

        # Patch client manager
        mocker.patch(
            'awslabs.redshift_mcp_server.redshift.client_manager.redshift_data_client',
            return_value=mock_data_client,
        )

        # Test the tool - should raise exception
        with pytest.raises(Exception, match='AWS API Error'):
            await list_tables_tool(
                mock_context,
                cluster_identifier='test-cluster',
                table_database_name='dev',
                table_schema_name='public',
            )


class TestListColumnsTool:
    """Tests for the list_columns MCP tool."""

    @pytest.mark.asyncio
    async def test_list_columns_tool_success(self, mocker):
        """Test successful column discovery with explicit parameters."""
        # Mock data client for query execution
        mock_data_client = mocker.Mock()
        mock_data_client.batch_execute_statement.return_value = {'Id': 'batch-query-301'}
        mock_data_client.describe_statement.return_value = {
            'Status': 'FINISHED',
            'SubStatements': [
                {'Id': 'sub-query-0'},  # BEGIN READ ONLY
                {'Id': 'query-301'},  # Our actual SQL query
                {'Id': 'sub-query-2'},  # END
            ],
        }
        mock_data_client.get_statement_result.return_value = {
            'Records': [
                [
                    {'stringValue': 'dev'},  # database_name
                    {'stringValue': 'public'},  # schema_name
                    {'stringValue': 'users'},  # table_name
                    {'stringValue': 'id'},  # column_name
                    {'longValue': 1},  # ordinal_position
                    {'stringValue': None},  # column_default
                    {'stringValue': 'NO'},  # is_nullable
                    {'stringValue': 'integer'},  # data_type
                    {'longValue': None},  # character_maximum_length
                    {'longValue': None},  # numeric_precision
                    {'longValue': None},  # numeric_scale
                    {'stringValue': 'SK'},  # remarks
                ],
                [
                    {'stringValue': 'dev'},  # database_name
                    {'stringValue': 'public'},  # schema_name
                    {'stringValue': 'users'},  # table_name
                    {'stringValue': 'name'},  # column_name
                    {'longValue': 2},  # ordinal_position
                    {'stringValue': None},  # column_default
                    {'stringValue': 'YES'},  # is_nullable
                    {'stringValue': 'varchar'},  # data_type
                    {'longValue': 255},  # character_maximum_length
                    {'longValue': None},  # numeric_precision
                    {'longValue': None},  # numeric_scale
                    {'stringValue': 'User name'},  # remarks
                ],
            ]
        }

        # Mock cluster discovery to return a valid cluster
        mock_discover_clusters = mocker.patch(
            'awslabs.redshift_mcp_server.redshift.discover_clusters'
        )
        mock_discover_clusters.return_value = [
            {'identifier': 'test-cluster', 'type': 'provisioned'}
        ]

        # Patch client manager
        mocker.patch(
            'awslabs.redshift_mcp_server.redshift.client_manager.redshift_data_client',
            return_value=mock_data_client,
        )

        # Test the tool with explicit parameters
        result = await list_columns_tool(
            Context(),
            cluster_identifier='test-cluster',
            column_database_name='dev',
            column_schema_name='public',
            column_table_name='users',
        )

        # Verify results
        assert len(result) == 2
        assert all(isinstance(column, RedshiftColumn) for column in result)

        # Check first column (integer, not nullable)
        assert result[0].database_name == 'dev'
        assert result[0].schema_name == 'public'
        assert result[0].table_name == 'users'
        assert result[0].column_name == 'id'
        assert result[0].ordinal_position == 1
        assert result[0].is_nullable == 'NO'
        assert result[0].data_type == 'integer'
        assert result[0].remarks == 'SK'

        # Check second column (varchar, nullable)
        assert result[1].database_name == 'dev'
        assert result[1].schema_name == 'public'
        assert result[1].table_name == 'users'
        assert result[1].column_name == 'name'
        assert result[1].ordinal_position == 2
        assert result[1].is_nullable == 'YES'
        assert result[1].data_type == 'varchar'
        assert result[1].character_maximum_length == 255
        assert result[1].remarks == 'User name'

    @pytest.mark.asyncio
    async def test_list_columns_tool_empty(self, mocker):
        """Test when no columns are found."""
        # Mock data client with empty results
        mock_data_client = mocker.Mock()
        mock_data_client.batch_execute_statement.return_value = {'Id': 'batch-query-402'}
        mock_data_client.describe_statement.return_value = {
            'Status': 'FINISHED',
            'SubStatements': [
                {'Id': 'sub-query-0'},  # BEGIN READ ONLY
                {'Id': 'query-402'},  # Our actual SQL query
                {'Id': 'sub-query-2'},  # END
            ],
        }
        mock_data_client.get_statement_result.return_value = {'Records': []}

        # Mock cluster discovery to return a serverless workgroup
        mock_discover_clusters = mocker.patch(
            'awslabs.redshift_mcp_server.redshift.discover_clusters'
        )
        mock_discover_clusters.return_value = [
            {'identifier': 'test-workgroup', 'type': 'serverless'}
        ]

        # Patch client manager
        mocker.patch(
            'awslabs.redshift_mcp_server.redshift.client_manager.redshift_data_client',
            return_value=mock_data_client,
        )

        # Test the tool
        result = await list_columns_tool(
            Context(),
            cluster_identifier='test-workgroup',
            column_database_name='test_db',
            column_schema_name='empty_schema',
            column_table_name='empty_table',
        )

        # Verify empty result
        assert len(result) == 0
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_list_columns_tool_error(self, mocker):
        """Test error handling when AWS API calls fail."""
        # Mock data client that raises exception
        mock_data_client = mocker.Mock()
        mock_data_client.batch_execute_statement.side_effect = Exception('AWS API Error')

        # Mock cluster discovery
        mock_discover_clusters = mocker.patch(
            'awslabs.redshift_mcp_server.redshift.discover_clusters'
        )
        mock_discover_clusters.return_value = [
            {'identifier': 'test-cluster', 'type': 'provisioned'}
        ]

        # Mock context
        mock_context = mocker.Mock()
        mock_context.error = mocker.AsyncMock()

        # Patch client manager
        mocker.patch(
            'awslabs.redshift_mcp_server.redshift.client_manager.redshift_data_client',
            return_value=mock_data_client,
        )

        # Test the tool - should raise exception
        with pytest.raises(Exception, match='AWS API Error'):
            await list_columns_tool(
                mock_context,
                cluster_identifier='test-cluster',
                column_database_name='dev',
                column_schema_name='public',
                column_table_name='users',
            )


class TestExecuteQueryTool:
    """Tests for the execute_query MCP tool."""

    @pytest.mark.asyncio
    async def test_execute_query_tool_success(self, mocker):
        """Test successful query execution with mixed data types."""
        # Mock data client for query execution
        mock_data_client = mocker.Mock()
        mock_data_client.batch_execute_statement.return_value = {'Id': 'batch-query-123'}
        mock_data_client.describe_statement.return_value = {
            'Status': 'FINISHED',
            'SubStatements': [
                {'Id': 'sub-query-0'},  # BEGIN READ ONLY
                {'Id': 'query-123'},  # Our actual SQL query
                {'Id': 'sub-query-2'},  # END
            ],
        }
        mock_data_client.get_statement_result.return_value = {
            'ColumnMetadata': [
                {'name': 'id'},
                {'name': 'name'},
                {'name': 'age'},
                {'name': 'active'},
                {'name': 'score'},
            ],
            'Records': [
                [
                    {'longValue': 1},
                    {'stringValue': 'Sergey'},
                    {'longValue': 54},
                    {'booleanValue': True},
                    {'doubleValue': 95.5},
                ],
                [
                    {'longValue': 2},
                    {'stringValue': 'Max'},
                    {'longValue': 42},
                    {'booleanValue': False},
                    {'isNull': True},
                ],
            ],
            'QueryStatus': 'FINISHED',
            'TotalExecutionTimeInMillis': 123,
        }

        # Mock cluster discovery to return a valid cluster
        mock_discover_clusters = mocker.patch(
            'awslabs.redshift_mcp_server.redshift.discover_clusters'
        )
        mock_discover_clusters.return_value = [
            {'identifier': 'test-cluster', 'type': 'provisioned'}
        ]

        # Patch client manager
        mocker.patch(
            'awslabs.redshift_mcp_server.redshift.client_manager.redshift_data_client',
            return_value=mock_data_client,
        )

        # Test the tool with a SELECT query
        result = await execute_query_tool(
            Context(),
            cluster_identifier='test-cluster',
            database_name='dev',
            sql='SELECT id, name, age, active, score FROM users LIMIT 2',
        )

        # Verify results
        assert isinstance(result, QueryResult)
        assert result.columns == ['id', 'name', 'age', 'active', 'score']
        assert result.row_count == 2
        assert result.query_id == 'query-123'
        assert result.execution_time_ms is not None
        assert result.execution_time_ms >= 0

        # Check first row data types
        assert result.rows[0] == [1, 'Sergey', 54, True, 95.5]

        # Check second row with null value
        assert result.rows[1] == [2, 'Max', 42, False, None]

    @pytest.mark.asyncio
    async def test_execute_query_tool_empty_results(self, mocker):
        """Test query execution with no results."""
        # Mock data client with empty results
        mock_data_client = mocker.Mock()
        mock_data_client.batch_execute_statement.return_value = {'Id': 'batch-query-123'}
        mock_data_client.describe_statement.return_value = {
            'Status': 'FINISHED',
            'SubStatements': [
                {'Id': 'sub-query-0'},  # BEGIN READ ONLY
                {'Id': 'query-123'},  # Our actual SQL query
                {'Id': 'sub-query-2'},  # END
            ],
        }
        mock_data_client.get_statement_result.return_value = {
            'ColumnMetadata': [{'name': 'count'}],
            'Records': [],
            'QueryStatus': 'FINISHED',
            'TotalExecutionTimeInMillis': 123,
        }

        # Mock cluster discovery to return a serverless workgroup
        mock_discover_clusters = mocker.patch(
            'awslabs.redshift_mcp_server.redshift.discover_clusters'
        )
        mock_discover_clusters.return_value = [
            {'identifier': 'test-workgroup', 'type': 'serverless'}
        ]

        # Patch client manager
        mocker.patch(
            'awslabs.redshift_mcp_server.redshift.client_manager.redshift_data_client',
            return_value=mock_data_client,
        )

        # Test the tool
        result = await execute_query_tool(
            Context(),
            cluster_identifier='test-workgroup',
            database_name='test_db',
            sql='SELECT COUNT(*) FROM empty_table',
        )

        # Verify empty result
        assert isinstance(result, QueryResult)
        assert result.columns == ['count']
        assert result.row_count == 0
        assert len(result.rows) == 0

    @pytest.mark.asyncio
    async def test_execute_query_tool_error(self, mocker):
        """Test error handling when query execution fails."""
        # Mock data client that raises exception
        mock_data_client = mocker.Mock()
        mock_data_client.batch_execute_statement.side_effect = Exception('AWS API Error')

        # Mock cluster discovery
        mock_discover_clusters = mocker.patch(
            'awslabs.redshift_mcp_server.redshift.discover_clusters'
        )
        mock_discover_clusters.return_value = [
            {'identifier': 'test-cluster', 'type': 'provisioned'}
        ]

        # Mock context
        mock_context = mocker.Mock()
        mock_context.error = mocker.AsyncMock()

        # Patch client manager
        mocker.patch(
            'awslabs.redshift_mcp_server.redshift.client_manager.redshift_data_client',
            return_value=mock_data_client,
        )

        # Test the tool - should raise exception
        with pytest.raises(Exception, match='AWS API Error'):
            await execute_query_tool(
                mock_context,
                cluster_identifier='test-cluster',
                database_name='dev',
                sql='SELECT * FROM users',
            )
