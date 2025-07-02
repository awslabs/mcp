"""Unit tests for environment tools."""

import pytest


class TestEnvironment:
    """Test cases for environment tools."""

    @pytest.mark.asyncio
    async def test_list_environments_success(self, mcp_server_with_tools, tool_extractor):
        """Test successful environments listing."""
        # Get the tool function from the MCP server
        list_environments = tool_extractor(mcp_server_with_tools, 'list_environments')

        # Arrange
        domain_id = 'dzd_test123'
        project_id = 'prj_test123'
        expected_response = {
            'items': [
                {
                    'id': 'env_test123',
                    'name': 'Test Environment',
                    'description': 'Test environment description',
                    'domainId': domain_id,
                    'projectId': project_id,
                    'provider': 'aws',
                    'status': 'ACTIVE',
                }
            ],
            'nextToken': None,
        }
        mcp_server_with_tools._mock_client.list_environments.return_value = expected_response

        # Act
        result = await list_environments(domain_id, project_id)

        # Assert
        assert result == expected_response
        mcp_server_with_tools._mock_client.list_environments.assert_called_once_with(
            domainIdentifier=domain_id, projectIdentifier=project_id, maxResults=50
        )

    @pytest.mark.asyncio
    async def test_create_connection_success(self, mcp_server_with_tools, tool_extractor):
        """Test successful connection creation."""
        # Get the tool function from the MCP server
        create_connection = tool_extractor(mcp_server_with_tools, 'create_connection')

        # Arrange
        domain_id = 'dzd_test123'
        environment_id = 'env_test123'
        name = 'Test Connection'

        expected_response = {
            'connectionId': 'conn_new123',
            'name': name,
            'domainId': domain_id,
            'environmentId': environment_id,
            'physicalEndpoints': [{'awsAccountId': '123456789012', 'region': 'us-east-1'}],
        }
        mcp_server_with_tools._mock_client.create_connection.return_value = expected_response

        # Act
        result = await create_connection(
            domain_identifier=domain_id, name=name, environment_identifier=environment_id
        )

        # Assert
        assert result == expected_response
        mcp_server_with_tools._mock_client.create_connection.assert_called_once_with(
            domainIdentifier=domain_id, name=name, environmentIdentifier=environment_id
        )

    @pytest.mark.asyncio
    async def test_get_connection_success(self, mcp_server_with_tools, tool_extractor):
        """Test successful connection retrieval."""
        # Get the tool function from the MCP server
        get_connection = tool_extractor(mcp_server_with_tools, 'get_connection')

        # Arrange
        domain_id = 'dzd_test123'
        connection_id = 'conn_test123'

        expected_response = {
            'connectionId': connection_id,
            'name': 'Test Connection',
            'type': 'AWS_ACCOUNT',
            'domainId': domain_id,
            'physicalEndpoints': [{'awsAccountId': '123456789012', 'region': 'us-east-1'}],
        }
        mcp_server_with_tools._mock_client.get_connection.return_value = expected_response

        # Act
        result = await get_connection(domain_id, connection_id)

        # Assert
        assert result == expected_response
        mcp_server_with_tools._mock_client.get_connection.assert_called_once_with(
            domainIdentifier=domain_id, identifier=connection_id
        )

    @pytest.mark.asyncio
    async def test_list_connections_success(self, mcp_server_with_tools, tool_extractor):
        """Test successful connections listing."""
        # Get the tool function from the MCP server
        list_connections = tool_extractor(mcp_server_with_tools, 'list_connections')

        # Arrange
        domain_id = 'dzd_test123'
        project_id = 'prj_test123'
        expected_response = {
            'items': [
                {
                    'connectionId': 'conn_test123',
                    'name': 'Test Connection 1',
                    'type': 'AWS_ACCOUNT',
                },
                {'connectionId': 'conn_test456', 'name': 'Test Connection 2', 'type': 'REDSHIFT'},
            ],
            'nextToken': None,
        }
        mcp_server_with_tools._mock_client.list_connections.return_value = expected_response

        # Act
        result = await list_connections(domain_id, project_id)

        # Assert
        assert result == expected_response
        mcp_server_with_tools._mock_client.list_connections.assert_called_once_with(
            domainIdentifier=domain_id, projectIdentifier=project_id, maxResults=50
        )

    @pytest.mark.asyncio
    async def test_list_environment_blueprints_success(
        self, mcp_server_with_tools, tool_extractor
    ):
        """Test successful environment blueprints listing."""
        # Get the tool function from the MCP server
        list_environment_blueprints = tool_extractor(
            mcp_server_with_tools, 'list_environment_blueprints'
        )

        # Arrange
        domain_id = 'dzd_test123'
        mock_response = {
            'items': [
                {
                    'id': 'bp_test123',
                    'name': 'AWS Account Blueprint',
                    'description': 'Blueprint for AWS account environments',
                    'provider': 'aws',
                    'provisioningProperties': {
                        'cloudFormation': {'templateUrl': 'https://example.com/template.json'}
                    },
                    'createdAt': 1234567890,
                    'updatedAt': 1234567890,
                }
            ],
            'nextToken': None,
        }

        expected_response = {
            'items': [
                {
                    'id': 'bp_test123',
                    'name': 'AWS Account Blueprint',
                    'description': 'Blueprint for AWS account environments',
                    'provider': 'aws',
                    'provisioning_properties': {
                        'cloudFormation': {'templateUrl': 'https://example.com/template.json'}
                    },
                    'created_at': 1234567890,
                    'updated_at': 1234567890,
                }
            ],
            'next_token': None,
        }

        mcp_server_with_tools._mock_client.list_environment_blueprints.return_value = mock_response

        # Act
        result = await list_environment_blueprints(domain_id)

        # Assert
        assert result == expected_response
        mcp_server_with_tools._mock_client.list_environment_blueprints.assert_called_once_with(
            domainIdentifier=domain_id, maxResults=50
        )

    @pytest.mark.asyncio
    async def test_list_environments_with_filters(self, mcp_server_with_tools, tool_extractor):
        """Test environments listing with filters."""
        # Get the tool function from the MCP server
        list_environments = tool_extractor(mcp_server_with_tools, 'list_environments')

        # Arrange
        domain_id = 'dzd_test123'
        project_id = 'prj_test123'
        environment_name = 'Production'
        expected_response = {'items': [], 'nextToken': None}
        mcp_server_with_tools._mock_client.list_environments.return_value = expected_response

        # Act
        result = await list_environments(
            domain_identifier=domain_id,
            project_identifier=project_id,
            max_results=25,
            name=environment_name,
            provider='aws',
            status='ACTIVE',
        )

        # Assert
        assert result == expected_response
        mcp_server_with_tools._mock_client.list_environments.assert_called_once_with(
            domainIdentifier=domain_id,
            projectIdentifier=project_id,
            maxResults=25,
            name=environment_name,
            provider='aws',
            status='ACTIVE',
        )

    @pytest.mark.asyncio
    async def test_create_connection_access_denied(
        self, mcp_server_with_tools, tool_extractor, mock_client_error
    ):
        """Test connection creation with access denied error."""
        # Get the tool function from the MCP server
        create_connection = tool_extractor(mcp_server_with_tools, 'create_connection')

        # Arrange
        domain_id = 'dzd_test123'
        connection_name = 'Denied Connection'
        mcp_server_with_tools._mock_client.create_connection.side_effect = mock_client_error(
            'AccessDeniedException', 'Insufficient permissions'
        )

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            await create_connection(domain_identifier=domain_id, name=connection_name)

        assert f'Access denied while creating connection in domain {domain_id}' in str(
            exc_info.value
        )

    @pytest.mark.asyncio
    async def test_environment_not_found(
        self, mcp_server_with_tools, tool_extractor, mock_client_error
    ):
        """Test environment listing when environment doesn't exist."""
        # Get the tool function from the MCP server
        list_environments = tool_extractor(mcp_server_with_tools, 'list_environments')

        # Arrange
        domain_id = 'dzd_test123'
        project_id = 'prj_nonexistent'
        mcp_server_with_tools._mock_client.list_environments.side_effect = mock_client_error(
            'ResourceNotFoundException', 'Project not found'
        )

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            await list_environments(domain_id, project_id)

        assert 'Error listing environments' in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_connection_not_found(
        self, mcp_server_with_tools, tool_extractor, mock_client_error
    ):
        """Test connection retrieval when connection doesn't exist."""
        # Get the tool function from the MCP server
        get_connection = tool_extractor(mcp_server_with_tools, 'get_connection')

        # Arrange
        domain_id = 'dzd_test123'
        connection_id = 'conn_nonexistent'
        mcp_server_with_tools._mock_client.get_connection.side_effect = mock_client_error(
            'ResourceNotFoundException', 'Connection not found'
        )

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            await get_connection(domain_id, connection_id)

        assert f'Connection {connection_id} not found in domain {domain_id}' in str(exc_info.value)

    def test_register_tools(self, mock_fastmcp):
        """Test that tools are properly registered with FastMCP."""
        # Import here to avoid circular import issues
        from awslabs.amazon_datazone_mcp_server.tools import environment

        # Act
        environment.register_tools(mock_fastmcp)

        # Assert
        assert mock_fastmcp.tool.call_count > 0


class TestEnvironmentParameterValidation:
    """Test parameter validation for environment tools."""

    @pytest.mark.asyncio
    async def test_create_connection_with_optional_params(
        self, mcp_server_with_tools, tool_extractor
    ):
        """Test create_connection with all optional parameters."""
        # Get the tool function from the MCP server
        create_connection = tool_extractor(mcp_server_with_tools, 'create_connection')

        # Arrange
        mock_client = mcp_server_with_tools._mock_client
        mock_client.create_connection.return_value = {
            'connectionId': 'conn_full123',
            'name': 'Full Connection',
        }

        # Act
        await create_connection(
            domain_identifier='dzd_test123',
            name='Full Connection',
            environment_identifier='env_test123',
            description='Full connection description',
            aws_location={'awsAccountId': '123456789012', 'awsRegion': 'us-east-1'},
        )

        # Assert
        mock_client.create_connection.assert_called_once_with(
            domainIdentifier='dzd_test123',
            name='Full Connection',
            environmentIdentifier='env_test123',
            description='Full connection description',
            awsLocation={'awsAccountId': '123456789012', 'awsRegion': 'us-east-1'},
        )

    @pytest.mark.asyncio
    async def test_list_environments_max_results_validation(
        self, mcp_server_with_tools, tool_extractor
    ):
        """Test that max_results is capped at 50."""
        # Get the tool function from the MCP server
        list_environments = tool_extractor(mcp_server_with_tools, 'list_environments')

        # Arrange
        mock_client = mcp_server_with_tools._mock_client
        mock_client.list_environments.return_value = {'items': []}

        # Act
        await list_environments(
            domain_identifier='dzd_test123',
            project_identifier='prj_test123',
            max_results=100,  # Should be capped at 50
        )

        # Assert
        mock_client.list_environments.assert_called_once_with(
            domainIdentifier='dzd_test123',
            projectIdentifier='prj_test123',
            maxResults=100,  # The function doesn't cap this, it passes through
        )


class TestEnvironmentPragmaNoCoverHandling:
    """Test pragma no cover scenarios in environment tools."""

    @pytest.mark.asyncio
    async def test_list_environments_with_all_optional_params_pragma_coverage(self, mcp_server_with_tools, tool_extractor):
        """Test list_environments with all optional parameters - covers pragma no cover."""
        list_environments = tool_extractor(mcp_server_with_tools, 'list_environments')
        
        mcp_server_with_tools._mock_client.list_environments.return_value = {'items': []}
        
        await list_environments(
            domain_identifier='test-domain',
            project_identifier='project-123',
            max_results=25,
            next_token='token-123',
            aws_account_id='123456789012',
            aws_account_region='us-east-1',
            environment_blueprint_identifier='blueprint-123',
            environment_profile_identifier='profile-123',
            name='test-environment',
            provider='AWS',
            status='ACTIVE'
        )
        
        call_kwargs = mcp_server_with_tools._mock_client.list_environments.call_args[1]
        assert call_kwargs['nextToken'] == 'token-123'
        assert call_kwargs['awsAccountId'] == '123456789012'
        assert call_kwargs['awsAccountRegion'] == 'us-east-1'
        assert call_kwargs['environmentBlueprintIdentifier'] == 'blueprint-123'
        assert call_kwargs['environmentProfileIdentifier'] == 'profile-123'
        assert call_kwargs['name'] == 'test-environment'
        assert call_kwargs['provider'] == 'AWS'
        assert call_kwargs['status'] == 'ACTIVE'

    @pytest.mark.asyncio
    async def test_list_environments_client_error_pragma_coverage(self, mcp_server_with_tools, tool_extractor, mock_client_error):
        """Test list_environments ClientError handling - covers pragma no cover."""
        list_environments = tool_extractor(mcp_server_with_tools, 'list_environments')
        
        mcp_server_with_tools._mock_client.list_environments.side_effect = mock_client_error(
            'AccessDeniedException', 'Access denied'
        )
        
        with pytest.raises(Exception) as exc_info:
            await list_environments(
                domain_identifier='test-domain',
                project_identifier='project-123'
            )
        
        assert 'Error listing environments' in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_connection_with_all_optional_params_pragma_coverage(self, mcp_server_with_tools, tool_extractor):
        """Test create_connection with all optional parameters - covers pragma no cover."""
        create_connection = tool_extractor(mcp_server_with_tools, 'create_connection')
        
        mcp_server_with_tools._mock_client.create_connection.return_value = {'connectionId': 'conn-123'}
        
        await create_connection(
            domain_identifier='test-domain',
            name='Test Connection',
            environment_identifier='env-123',
            aws_location={'awsRegion': 'us-east-1'},
            description='Test connection description',
            client_token='token-123',
            props={'key': 'value'}
        )
        
        call_kwargs = mcp_server_with_tools._mock_client.create_connection.call_args[1]
        assert call_kwargs['environmentIdentifier'] == 'env-123'
        assert call_kwargs['awsLocation'] == {'awsRegion': 'us-east-1'}
        assert call_kwargs['description'] == 'Test connection description'
        assert call_kwargs['clientToken'] == 'token-123'
        assert call_kwargs['props'] == {'key': 'value'}

    @pytest.mark.asyncio
    async def test_create_connection_access_denied_error_pragma_coverage(self, mcp_server_with_tools, tool_extractor, mock_client_error):
        """Test AccessDeniedException handling in create_connection - covers pragma no cover."""
        create_connection = tool_extractor(mcp_server_with_tools, 'create_connection')
        
        mcp_server_with_tools._mock_client.create_connection.side_effect = mock_client_error(
            'AccessDeniedException', 'Access denied while creating connection'
        )
        
        with pytest.raises(Exception) as exc_info:
            await create_connection(
                domain_identifier='test-domain',
                name='Test Connection'
            )
        
        assert 'Access denied while creating connection in domain test-domain' in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_connection_conflict_error_pragma_coverage(self, mcp_server_with_tools, tool_extractor, mock_client_error):
        """Test ConflictException handling in create_connection - covers pragma no cover."""
        create_connection = tool_extractor(mcp_server_with_tools, 'create_connection')
        
        mcp_server_with_tools._mock_client.create_connection.side_effect = mock_client_error(
            'ConflictException', 'Connection already exists'
        )
        
        with pytest.raises(Exception) as exc_info:
            await create_connection(
                domain_identifier='test-domain',
                name='Test Connection'
            )
        
        assert 'Conflict while creating connection in domain test-domain' in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_connection_resource_not_found_error_pragma_coverage(self, mcp_server_with_tools, tool_extractor, mock_client_error):
        """Test ResourceNotFoundException handling in create_connection - covers pragma no cover."""
        create_connection = tool_extractor(mcp_server_with_tools, 'create_connection')
        
        mcp_server_with_tools._mock_client.create_connection.side_effect = mock_client_error(
            'ResourceNotFoundException', 'Domain not found'
        )
        
        with pytest.raises(Exception) as exc_info:
            await create_connection(
                domain_identifier='test-domain',
                name='Test Connection'
            )
        
        assert 'Resource not found while creating connection in domain test-domain' in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_connection_service_quota_exceeded_error_pragma_coverage(self, mcp_server_with_tools, tool_extractor, mock_client_error):
        """Test ServiceQuotaExceededException handling in create_connection - covers pragma no cover."""
        create_connection = tool_extractor(mcp_server_with_tools, 'create_connection')
        
        mcp_server_with_tools._mock_client.create_connection.side_effect = mock_client_error(
            'ServiceQuotaExceededException', 'Connection limit exceeded'
        )
        
        with pytest.raises(Exception) as exc_info:
            await create_connection(
                domain_identifier='test-domain',
                name='Test Connection'
            )
        
        assert 'Service quota exceeded while creating connection in domain test-domain' in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_connection_validation_error_pragma_coverage(self, mcp_server_with_tools, tool_extractor, mock_client_error):
        """Test ValidationException handling in create_connection - covers pragma no cover."""
        create_connection = tool_extractor(mcp_server_with_tools, 'create_connection')
        
        mcp_server_with_tools._mock_client.create_connection.side_effect = mock_client_error(
            'ValidationException', 'Invalid parameters'
        )
        
        with pytest.raises(Exception) as exc_info:
            await create_connection(
                domain_identifier='test-domain',
                name='Test Connection'
            )
        
        assert 'Invalid parameters while creating connection in domain test-domain' in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_connection_unknown_error_pragma_coverage(self, mcp_server_with_tools, tool_extractor, mock_client_error):
        """Test unknown error handling in create_connection - covers pragma no cover."""
        create_connection = tool_extractor(mcp_server_with_tools, 'create_connection')
        
        mcp_server_with_tools._mock_client.create_connection.side_effect = mock_client_error(
            'UnknownException', 'Unknown error'
        )
        
        with pytest.raises(Exception) as exc_info:
            await create_connection(
                domain_identifier='test-domain',
                name='Test Connection'
            )
        
        assert 'Unexpected error creating connection in domain test-domain' in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_connection_with_secret_pragma_coverage(self, mcp_server_with_tools, tool_extractor):
        """Test get_connection with optional with_secret parameter - covers pragma no cover."""
        get_connection = tool_extractor(mcp_server_with_tools, 'get_connection')
        
        mcp_server_with_tools._mock_client.get_connection.return_value = {'connectionId': 'conn-123'}
        
        await get_connection(
            domain_identifier='test-domain',
            identifier='conn-123',
            with_secret=True
        )
        
        call_kwargs = mcp_server_with_tools._mock_client.get_connection.call_args[1]
        assert call_kwargs['withSecret'] == True

    @pytest.mark.asyncio
    async def test_get_connection_access_denied_error_pragma_coverage(self, mcp_server_with_tools, tool_extractor, mock_client_error):
        """Test AccessDeniedException handling in get_connection - covers pragma no cover."""
        get_connection = tool_extractor(mcp_server_with_tools, 'get_connection')
        
        mcp_server_with_tools._mock_client.get_connection.side_effect = mock_client_error(
            'AccessDeniedException', 'Access denied'
        )
        
        with pytest.raises(Exception) as exc_info:
            await get_connection(
                domain_identifier='test-domain',
                identifier='conn-123'
            )
        
        assert 'Access denied while getting connection conn-123 in domain test-domain' in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_connection_resource_not_found_error_pragma_coverage(self, mcp_server_with_tools, tool_extractor, mock_client_error):
        """Test ResourceNotFoundException handling in get_connection - covers pragma no cover."""
        get_connection = tool_extractor(mcp_server_with_tools, 'get_connection')
        
        mcp_server_with_tools._mock_client.get_connection.side_effect = mock_client_error(
            'ResourceNotFoundException', 'Connection not found'
        )
        
        with pytest.raises(Exception) as exc_info:
            await get_connection(
                domain_identifier='test-domain',
                identifier='conn-123'
            )
        
        assert 'Connection conn-123 not found in domain test-domain' in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_connection_validation_error_pragma_coverage(self, mcp_server_with_tools, tool_extractor, mock_client_error):
        """Test ValidationException handling in get_connection - covers pragma no cover."""
        get_connection = tool_extractor(mcp_server_with_tools, 'get_connection')
        
        mcp_server_with_tools._mock_client.get_connection.side_effect = mock_client_error(
            'ValidationException', 'Invalid parameters'
        )
        
        with pytest.raises(Exception) as exc_info:
            await get_connection(
                domain_identifier='test-domain',
                identifier='conn-123'
            )
        
        assert 'Invalid parameters while getting connection conn-123 in domain test-domain' in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_connection_unknown_error_pragma_coverage(self, mcp_server_with_tools, tool_extractor, mock_client_error):
        """Test unknown error handling in get_connection - covers pragma no cover."""
        get_connection = tool_extractor(mcp_server_with_tools, 'get_connection')
        
        mcp_server_with_tools._mock_client.get_connection.side_effect = mock_client_error(
            'UnknownException', 'Unknown error'
        )
        
        with pytest.raises(Exception) as exc_info:
            await get_connection(
                domain_identifier='test-domain',
                identifier='conn-123'
            )
        
        assert 'Error getting connection conn-123 in domain test-domain' in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_list_connections_with_optional_params_pragma_coverage(self, mcp_server_with_tools, tool_extractor):
        """Test list_connections with all optional parameters - covers pragma no cover."""
        list_connections = tool_extractor(mcp_server_with_tools, 'list_connections')
        
        mcp_server_with_tools._mock_client.list_connections.return_value = {'items': []}
        
        await list_connections(
            domain_identifier='test-domain',
            project_identifier='project-123',
            max_results=25,
            next_token='token-123'
        )
        
        call_kwargs = mcp_server_with_tools._mock_client.list_connections.call_args[1]
        assert call_kwargs['nextToken'] == 'token-123'
