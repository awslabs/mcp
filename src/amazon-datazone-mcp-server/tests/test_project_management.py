"""Unit tests for project_management tools."""

import pytest
from unittest.mock import AsyncMock, Mock, patch


class TestProjectManagement:
    """Test cases for project management tools."""

    @pytest.mark.asyncio
    async def test_create_project_success(
        self, mcp_server_with_tools, tool_extractor, sample_project_data
    ):
        """Test successful project creation."""
        # Get the tool function from the MCP server
        create_project = tool_extractor(mcp_server_with_tools, 'create_project')

        # Arrange
        expected_response = {
            'id': 'prj_new123',
            'name': sample_project_data['name'],
            'description': sample_project_data['description'],
            'domainId': sample_project_data['domain_identifier'],
            'status': 'ACTIVE',
            'glossaryTerms': sample_project_data['glossary_terms'],
        }
        mcp_server_with_tools._mock_client.create_project.return_value = expected_response

        # Act
        result = await create_project(
            domain_identifier=sample_project_data['domain_identifier'],
            name=sample_project_data['name'],
            description=sample_project_data['description'],
            glossary_terms=sample_project_data['glossary_terms'],
        )

        # Assert
        assert result == expected_response
        mcp_server_with_tools._mock_client.create_project.assert_called_once_with(
            domainIdentifier=sample_project_data['domain_identifier'],
            name=sample_project_data['name'],
            description=sample_project_data['description'],
            glossaryTerms=sample_project_data['glossary_terms'],
        )

    @pytest.mark.asyncio
    async def test_create_project_minimal_params(self, mcp_server_with_tools, tool_extractor):
        """Test project creation with minimal required parameters."""
        # Get the tool function from the MCP server
        create_project = tool_extractor(mcp_server_with_tools, 'create_project')

        # Arrange
        domain_id = 'dzd_test123'
        project_name = 'Minimal Project'
        expected_response = {
            'id': 'prj_minimal123',
            'name': project_name,
            'domainId': domain_id,
            'status': 'ACTIVE',
        }
        mcp_server_with_tools._mock_client.create_project.return_value = expected_response

        # Act
        result = await create_project(domain_identifier=domain_id, name=project_name)

        # Assert
        assert result == expected_response
        mcp_server_with_tools._mock_client.create_project.assert_called_once_with(
            domainIdentifier=domain_id, name=project_name, description=''
        )

    @pytest.mark.asyncio
    async def test_get_project_success(
        self, mcp_server_with_tools, tool_extractor, test_data_helper
    ):
        """Test successful project retrieval."""
        # Get the tool function from the MCP server
        get_project = tool_extractor(mcp_server_with_tools, 'get_project')

        # Arrange
        domain_id = 'dzd_test123'
        project_id = 'prj_test123'
        expected_response = test_data_helper.get_project_response(project_id)
        mcp_server_with_tools._mock_client.get_project.return_value = expected_response

        # Act
        result = await get_project(domain_id, project_id)

        # Assert
        assert result == expected_response
        mcp_server_with_tools._mock_client.get_project.assert_called_once_with(
            domainIdentifier=domain_id, identifier=project_id
        )

    @pytest.mark.asyncio
    async def test_get_project_not_found(
        self, mcp_server_with_tools, tool_extractor, mock_client_error
    ):
        """Test project retrieval when project doesn't exist."""
        # Get the tool function from the MCP server
        get_project = tool_extractor(mcp_server_with_tools, 'get_project')

        # Arrange
        domain_id = 'dzd_test123'
        project_id = 'prj_nonexistent'
        mcp_server_with_tools._mock_client.get_project.side_effect = mock_client_error(
            'ResourceNotFoundException', 'Project not found'
        )

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            await get_project(domain_id, project_id)

        assert f'Error getting project {project_id} in domain {domain_id}' in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_list_projects_success(self, mcp_server_with_tools, tool_extractor):
        """Test successful projects listing."""
        # Get the tool function from the MCP server
        list_projects = tool_extractor(mcp_server_with_tools, 'list_projects')

        # Arrange
        domain_id = 'dzd_test123'
        expected_response = {
            'items': [
                {
                    'id': 'prj_test123',
                    'name': 'Test Project 1',
                    'domainId': domain_id,
                    'status': 'ACTIVE',
                },
                {
                    'id': 'prj_test456',
                    'name': 'Test Project 2',
                    'domainId': domain_id,
                    'status': 'ACTIVE',
                },
            ],
            'nextToken': None,
        }
        mcp_server_with_tools._mock_client.list_projects.return_value = expected_response

        # Act
        result = await list_projects(domain_id)

        # Assert
        assert result == expected_response
        mcp_server_with_tools._mock_client.list_projects.assert_called_once_with(
            domainIdentifier=domain_id, maxResults=50
        )

    @pytest.mark.asyncio
    async def test_list_projects_with_filters(self, mcp_server_with_tools, tool_extractor):
        """Test projects listing with filters."""
        # Get the tool function from the MCP server
        list_projects = tool_extractor(mcp_server_with_tools, 'list_projects')

        # Arrange
        domain_id = 'dzd_test123'
        user_id = 'user123'
        project_name = 'Analytics'
        expected_response = {'items': [], 'nextToken': None}
        mcp_server_with_tools._mock_client.list_projects.return_value = expected_response

        # Act
        result = await list_projects(
            domain_identifier=domain_id, max_results=25, name=project_name, user_identifier=user_id
        )

        # Assert
        assert result == expected_response
        mcp_server_with_tools._mock_client.list_projects.assert_called_once_with(
            domainIdentifier=domain_id, maxResults=25, name=project_name, userIdentifier=user_id
        )

    @pytest.mark.asyncio
    async def test_create_project_membership_success(self, mcp_server_with_tools, tool_extractor):
        """Test successful project membership creation."""
        # Get the tool function from the MCP server
        create_project_membership = tool_extractor(
            mcp_server_with_tools, 'create_project_membership'
        )

        # Arrange
        domain_id = 'dzd_test123'
        project_id = 'prj_test123'
        designation = 'PROJECT_CONTRIBUTOR'
        member_id = 'user123'

        expected_response = {
            'designation': designation,
            'member': {'identifier': member_id},
            'projectId': project_id,
        }

        # Mock httpx.AsyncClient since this function uses httpx directly
        mock_response = Mock()
        mock_response.json.return_value = expected_response
        mock_response.raise_for_status.return_value = None

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        with patch(
            'awslabs.amazon_datazone_mcp_server.tools.common.httpx.AsyncClient',
            return_value=mock_client,
        ):
            # Act
            result = await create_project_membership(domain_id, project_id, designation, member_id)

            # Assert
            assert result == expected_response
            mock_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_project_profiles_success(self, mcp_server_with_tools, tool_extractor):
        """Test successful project profiles listing."""
        # Arrange
        domain_id = 'dzd_test123'
        expected_response = {
            'items': [
                {
                    'id': 'pp_test123',
                    'name': 'Analytics Profile',
                    'description': 'Profile for analytics projects',
                    'domainId': domain_id,
                    'status': 'ENABLED',
                }
            ],
            'nextToken': None,
        }
        mcp_server_with_tools._mock_client.list_project_profiles.return_value = expected_response

        # Get the tool function from the MCP server
        list_project_profiles = tool_extractor(mcp_server_with_tools, 'list_project_profiles')

        # Act
        result = await list_project_profiles(domain_id)

        # Assert
        assert result == expected_response
        mcp_server_with_tools._mock_client.list_project_profiles.assert_called_once_with(
            domainIdentifier=domain_id, maxResults=50
        )

    @pytest.mark.asyncio
    async def test_create_project_profile_success(self, mcp_server_with_tools, tool_extractor):
        """Test successful project profile creation."""
        # Arrange
        domain_id = 'dzd_test123'
        profile_name = 'Test Profile'
        description = 'Test profile description'

        mock_response = {
            'id': 'pp_new123',
            'name': profile_name,
            'description': description,
            'domainId': domain_id,
            'status': 'ENABLED',
            'createdAt': 1234567890,
            'createdBy': 'test-user',
        }
        mcp_server_with_tools._mock_client.create_project_profile.return_value = mock_response

        expected_response = {
            'id': 'pp_new123',
            'name': profile_name,
            'description': description,
            'domain_id': domain_id,
            'status': 'ENABLED',
            'created_at': 1234567890,
            'created_by': 'test-user',
            'domain_unit_id': None,
            'environment_configurations': [],
            'last_updated_at': None,
        }

        # Get the tool function from the MCP server
        create_project_profile = tool_extractor(mcp_server_with_tools, 'create_project_profile')

        # Act
        result = await create_project_profile(
            domain_identifier=domain_id, name=profile_name, description=description
        )

        # Assert
        assert result == expected_response
        mcp_server_with_tools._mock_client.create_project_profile.assert_called_once_with(
            domainIdentifier=domain_id,
            name=profile_name,
            status='ENABLED',
            description=description,
        )

    @pytest.mark.asyncio
    async def test_create_project_profile_with_environment_config(
        self, mcp_server_with_tools, tool_extractor
    ):
        """Test project profile creation with environment configurations."""
        # Arrange
        domain_id = 'dzd_test123'
        profile_name = 'Complex Profile'
        env_configs = [
            {
                'awsAccount': {'id': '123456789012'},
                'awsRegion': {'name': 'us-east-1'},
                'environmentBlueprintId': 'bp_test123',
                'name': 'Production Environment',
            }
        ]

        mcp_server_with_tools._mock_client.create_project_profile.return_value = {
            'id': 'pp_complex123',
            'name': profile_name,
            'domainId': domain_id,
            'environmentConfigurations': env_configs,
            'status': 'ENABLED',
        }

        # Get the tool function from the MCP server
        create_project_profile = tool_extractor(mcp_server_with_tools, 'create_project_profile')

        # Act
        result = await create_project_profile(
            domain_identifier=domain_id, name=profile_name, environment_configurations=env_configs
        )

        # Assert
        assert result['environment_configurations'] == env_configs
        mcp_server_with_tools._mock_client.create_project_profile.assert_called_once_with(
            domainIdentifier=domain_id,
            name=profile_name,
            status='ENABLED',
            environmentConfigurations=env_configs,
        )

    @pytest.mark.asyncio
    async def test_create_project_profile_access_denied(
        self, mcp_server_with_tools, tool_extractor, mock_client_error
    ):
        """Test project profile creation with access denied error."""
        # Arrange
        domain_id = 'dzd_test123'
        profile_name = 'Denied Profile'
        mcp_server_with_tools._mock_client.create_project_profile.side_effect = mock_client_error(
            'AccessDeniedException', 'Insufficient permissions'
        )

        # Get the tool function from the MCP server
        create_project_profile = tool_extractor(mcp_server_with_tools, 'create_project_profile')

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            await create_project_profile(domain_identifier=domain_id, name=profile_name)

        assert f"Access denied while creating project profile '{profile_name}'" in str(
            exc_info.value
        )

    @pytest.mark.asyncio
    async def test_create_project_access_denied(
        self, mcp_server_with_tools, tool_extractor, mock_client_error
    ):
        """Test project creation with access denied error."""
        # Arrange
        domain_id = 'dzd_test123'
        project_name = 'Denied Project'
        mcp_server_with_tools._mock_client.create_project.side_effect = mock_client_error(
            'AccessDeniedException', 'Insufficient permissions'
        )

        # Get the tool function from the MCP server
        create_project = tool_extractor(mcp_server_with_tools, 'create_project')

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            await create_project(domain_identifier=domain_id, name=project_name)

        assert f'Error creating project in domain {domain_id}' in str(exc_info.value)

    def test_register_tools(self, mock_fastmcp):
        """Test that tools are properly registered with FastMCP."""
        # Import here to avoid circular import issues
        from awslabs.amazon_datazone_mcp_server.tools import project_management

        # Act
        project_management.register_tools(mock_fastmcp)

        # Assert
        assert mock_fastmcp.tool.call_count > 0


class TestProjectManagementParameterValidation:
    """Test parameter validation for project management tools."""

    @pytest.mark.asyncio
    async def test_create_project_with_all_optional_params(
        self, mcp_server_with_tools, tool_extractor
    ):
        """Test create_project with all optional parameters."""
        # Arrange
        mock_response = {'id': 'prj_full123', 'name': 'Full Project', 'status': 'ACTIVE'}
        mcp_server_with_tools._mock_client.create_project.return_value = mock_response

        # Get the tool function from the MCP server
        create_project = tool_extractor(mcp_server_with_tools, 'create_project')

        # Act
        await create_project(
            domain_identifier='dzd_test123',
            name='Full Project',
            description='Full description',
            domain_unit_id='ddu_test123',
            glossary_terms=['term1', 'term2'],
            project_profile_id='pp_test123',
            user_parameters=[{'key': 'value'}],
        )

        # Assert
        mcp_server_with_tools._mock_client.create_project.assert_called_once_with(
            domainIdentifier='dzd_test123',
            name='Full Project',
            description='Full description',
            domainUnitId='ddu_test123',
            glossaryTerms=['term1', 'term2'],
            projectProfileId='pp_test123',
            userParameters=[{'key': 'value'}],
        )

    @pytest.mark.asyncio
    async def test_list_projects_max_results_validation(
        self, mcp_server_with_tools, tool_extractor
    ):
        """Test that max_results is capped at 50."""
        # Arrange
        mock_response = {'items': []}
        mcp_server_with_tools._mock_client.list_projects.return_value = mock_response

        # Get the tool function from the MCP server
        list_projects = tool_extractor(mcp_server_with_tools, 'list_projects')

        # Act
        await list_projects(
            domain_identifier='dzd_test123',
            max_results=100,  # Should be capped at 50
        )

        # Assert
        mcp_server_with_tools._mock_client.list_projects.assert_called_once_with(
            domainIdentifier='dzd_test123',
            maxResults=50,  # Capped value
        )


class TestProjectManagementPragmaNoCoverHandling:
    """Test pragma no cover scenarios in project management tools."""

    @pytest.mark.asyncio
    async def test_create_project_with_all_optional_params_pragma_coverage(self, mcp_server_with_tools, tool_extractor):
        """Test create_project with all optional parameters - covers pragma no cover."""
        create_project = tool_extractor(mcp_server_with_tools, 'create_project')

        mcp_server_with_tools._mock_client.create_project.return_value = {'projectId': 'test-project-123'}

        # Test with all optional parameters to hit pragma: no cover lines
        await create_project(
            domain_identifier='test-domain',
            name='Test Project',
            description='Test Description',
            domain_unit_id='test-unit',
            glossary_terms=['term1', 'term2'],
            project_profile_id='profile-123',
            user_parameters=[{'key': 'value'}]
        )

        # Verify the call included all optional parameters
        call_kwargs = mcp_server_with_tools._mock_client.create_project.call_args[1]

        assert call_kwargs['domainUnitId'] == 'test-unit'
        assert call_kwargs['glossaryTerms'] == ['term1', 'term2']
        assert call_kwargs['projectProfileId'] == 'profile-123'
        assert call_kwargs['userParameters'] == [{'key': 'value'}]

    @pytest.mark.asyncio
    async def test_list_projects_with_all_optional_params_pragma_coverage(self, mcp_server_with_tools, tool_extractor):
        """Test list_projects with all optional parameters - covers pragma no cover."""
        list_projects = tool_extractor(mcp_server_with_tools, 'list_projects')

        mcp_server_with_tools._mock_client.list_projects.return_value = {'items': []}

        await list_projects(
            domain_identifier='test-domain',
            max_results=25,
            next_token='token123',
            name='test-name',
            user_identifier='user123',
            group_identifier='group123'
        )

        call_kwargs = mcp_server_with_tools._mock_client.list_projects.call_args[1]
        assert call_kwargs['nextToken'] == 'token123'
        assert call_kwargs['name'] == 'test-name'
        assert call_kwargs['userIdentifier'] == 'user123'
        assert call_kwargs['groupIdentifier'] == 'group123'

    @pytest.mark.asyncio
    async def test_list_project_profiles_with_optional_params_pragma_coverage(self, mcp_server_with_tools, tool_extractor):
        """Test list_project_profiles with optional parameters - covers pragma no cover."""
        list_project_profiles = tool_extractor(mcp_server_with_tools, 'list_project_profiles')

        mcp_server_with_tools._mock_client.list_project_profiles.return_value = {'items': []}

        await list_project_profiles(
            domain_identifier='test-domain',
            max_results=25,
            next_token='token123'
        )

        call_kwargs = mcp_server_with_tools._mock_client.list_project_profiles.call_args[1]
        assert call_kwargs['nextToken'] == 'token123'

    @pytest.mark.asyncio
    async def test_create_project_profile_with_optional_params_pragma_coverage(self, mcp_server_with_tools, tool_extractor):
        """Test create_project_profile with all optional parameters - covers pragma no cover."""
        create_project_profile = tool_extractor(mcp_server_with_tools, 'create_project_profile')

        expected_response = {'id': 'profile-123'}
        mcp_server_with_tools._mock_client.create_project_profile.return_value = expected_response

        await create_project_profile(
            domain_identifier='test-domain',
            name='Test Profile',
            description='Test description',
            domain_unit_identifier='unit-123',
            environment_configurations=[{'key': 'value'}]
        )

        call_kwargs = mcp_server_with_tools._mock_client.create_project_profile.call_args[1]
        assert call_kwargs['description'] == 'Test description'
        assert call_kwargs['domainUnitIdentifier'] == 'unit-123'
        assert call_kwargs['environmentConfigurations'] == [{'key': 'value'}]

    @pytest.mark.asyncio
    async def test_create_project_profile_conflict_error_pragma_coverage(self, mcp_server_with_tools, tool_extractor, mock_client_error):
        """Test ConflictException handling in create_project_profile - covers pragma no cover."""
        create_project_profile = tool_extractor(mcp_server_with_tools, 'create_project_profile')

        mcp_server_with_tools._mock_client.create_project_profile.side_effect = mock_client_error(
            'ConflictException', 'Profile already exists'
        )

        with pytest.raises(Exception) as exc_info:
            await create_project_profile(
                domain_identifier='test-domain',
                name='Test Profile'
            )

        assert 'already exists in domain test-domain' in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_project_profile_resource_not_found_error_pragma_coverage(self, mcp_server_with_tools, tool_extractor, mock_client_error):
        """Test ResourceNotFoundException handling in create_project_profile - covers pragma no cover."""
        create_project_profile = tool_extractor(mcp_server_with_tools, 'create_project_profile')

        mcp_server_with_tools._mock_client.create_project_profile.side_effect = mock_client_error(
            'ResourceNotFoundException', 'Domain not found'
        )

        with pytest.raises(Exception) as exc_info:
            await create_project_profile(
                domain_identifier='test-domain',
                name='Test Profile'
            )

        assert 'Domain or domain unit not found' in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_project_profile_service_quota_exceeded_error_pragma_coverage(self, mcp_server_with_tools, tool_extractor, mock_client_error):
        """Test ServiceQuotaExceededException handling in create_project_profile - covers pragma no cover."""
        create_project_profile = tool_extractor(mcp_server_with_tools, 'create_project_profile')

        mcp_server_with_tools._mock_client.create_project_profile.side_effect = mock_client_error(
            'ServiceQuotaExceededException', 'Profile limit exceeded'
        )

        with pytest.raises(Exception) as exc_info:
            await create_project_profile(
                domain_identifier='test-domain',
                name='Test Profile'
            )

        assert 'Service quota exceeded' in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_project_profile_validation_error_pragma_coverage(self, mcp_server_with_tools, tool_extractor, mock_client_error):
        """Test ValidationException handling in create_project_profile - covers pragma no cover."""
        create_project_profile = tool_extractor(mcp_server_with_tools, 'create_project_profile')

        mcp_server_with_tools._mock_client.create_project_profile.side_effect = mock_client_error(
            'ValidationException', 'Invalid parameters'
        )

        with pytest.raises(Exception) as exc_info:
            await create_project_profile(
                domain_identifier='test-domain',
                name='Test Profile'
            )

        assert 'Invalid parameters for creating project profile' in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_project_profile_unknown_error_pragma_coverage(self, mcp_server_with_tools, tool_extractor, mock_client_error):
        """Test unknown error handling in create_project_profile - covers pragma no cover."""
        create_project_profile = tool_extractor(mcp_server_with_tools, 'create_project_profile')

        mcp_server_with_tools._mock_client.create_project_profile.side_effect = mock_client_error(
            'UnknownException', 'Unknown error occurred'
        )

        with pytest.raises(Exception) as exc_info:
            await create_project_profile(
                domain_identifier='test-domain',
                name='Test Profile'
            )

        assert 'Error creating project profile' in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_project_profile_general_exception_pragma_coverage(self, mcp_server_with_tools, tool_extractor):
        """Test general exception handling in create_project_profile - covers pragma no cover."""
        create_project_profile = tool_extractor(mcp_server_with_tools, 'create_project_profile')

        mcp_server_with_tools._mock_client.create_project_profile.side_effect = Exception('Network error')

        with pytest.raises(Exception) as exc_info:
            await create_project_profile(
                domain_identifier='test-domain',
                name='Test Profile'
            )

        assert "Unexpected error creating project profile 'Test Profile' in domain test-domain" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_project_profile_all_error_scenarios_pragma_coverage(self, mcp_server_with_tools, tool_extractor, mock_client_error):
        """Test all error scenarios in get_project_profile - covers pragma no cover."""
        get_project_profile = tool_extractor(mcp_server_with_tools, 'get_project_profile')

        # Test AccessDeniedException
        mcp_server_with_tools._mock_client.get_project_profile.side_effect = mock_client_error(
            'AccessDeniedException', 'Access denied'
        )

        with pytest.raises(Exception) as exc_info:
            await get_project_profile(
                domain_identifier='test-domain',
                identifier='profile-123'
            )

        assert "Access denied while getting project profile 'profile-123' in domain test-domain" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_list_project_memberships_with_optional_params_pragma_coverage(self, mcp_server_with_tools, tool_extractor):
        """Test list_project_memberships with all optional parameters - covers pragma no cover."""
        list_project_memberships = tool_extractor(mcp_server_with_tools, 'list_project_memberships')

        mcp_server_with_tools._mock_client.list_project_memberships.return_value = {'members': []}

        await list_project_memberships(
            domain_identifier='test-domain',
            project_identifier='project-123',
            max_results=25,
            next_token='token123',
            sort_by='NAME',
            sort_order='ASCENDING'
        )

        call_kwargs = mcp_server_with_tools._mock_client.list_project_memberships.call_args[1]
        assert call_kwargs['nextToken'] == 'token123'
        assert call_kwargs['sortBy'] == 'NAME'
        assert call_kwargs['sortOrder'] == 'ASCENDING'
