"""Tests for domain management tools."""

import pytest


class TestDomainManagement:
    """Test domain management functionality."""

    @pytest.mark.asyncio
    async def test_get_domain_success(
        self, mcp_server_with_tools, tool_extractor, test_data_helper
    ):
        """Test successful domain retrieval."""
        # Get the tool function from the MCP server
        get_domain = tool_extractor(mcp_server_with_tools, 'get_domain')

        domain_id = test_data_helper.get_domain_id()
        result = await get_domain(domain_id)

        # Verify the result
        assert result is not None
        assert result['id'] == domain_id
        assert result['name'] == 'Test Domain'
        assert result['status'] == 'AVAILABLE'

        # Verify the mock was called correctly
        mcp_server_with_tools._mock_client.get_domain.assert_called_once_with(identifier=domain_id)

    @pytest.mark.asyncio
    async def test_get_domain_not_found(
        self, mcp_server_with_tools, tool_extractor, client_error_helper
    ):
        """Test domain not found error handling."""
        # Configure mock to raise ResourceNotFoundException
        error = client_error_helper('ResourceNotFoundException', 'Domain not found')
        mcp_server_with_tools._mock_client.get_domain.side_effect = error

        get_domain = tool_extractor(mcp_server_with_tools, 'get_domain')

        domain_id = 'dzd_nonexistent'
        with pytest.raises(Exception) as exc_info:
            await get_domain(domain_id)

        assert 'Error getting domain dzd_nonexistent' in str(exc_info.value)

    # @pytest.mark.asyncio
    # async def test_create_domain_success(
    #     self, mcp_server_with_tools, tool_extractor, sample_domain_data
    # ):
    #     """Test successful domain creation."""
    #     create_domain = tool_extractor(mcp_server_with_tools, "create_domain")

    #     result = await create_domain(
    #         name=sample_domain_data["name"],
    #         domain_execution_role=sample_domain_data["domain_execution_role"],
    #         service_role=sample_domain_data["service_role"],
    #         domain_version=sample_domain_data["domain_version"],
    #         description=sample_domain_data["description"],
    #     )

    #     # Verify the result
    #     assert result is not None
    #     assert result["name"] == "New Test Domain"
    #     assert result["status"] == "CREATING"
    #     assert "id" in result
    #     assert "arn" in result

    #     # Verify the mock was called correctly
    #     mcp_server_with_tools._mock_client.create_domain.assert_called_once()
    #     call_args = mcp_server_with_tools._mock_client.create_domain.call_args[1]
    #     assert call_args["name"] == sample_domain_data["name"]
    #     assert call_args["domainExecutionRole"] == sample_domain_data["domain_execution_role"]
    #     assert call_args["serviceRole"] == sample_domain_data["service_role"]

    @pytest.mark.asyncio
    async def test_create_domain_conflict(
        self, mcp_server_with_tools, tool_extractor, sample_domain_data, client_error_helper
    ):
        """Test domain creation conflict error."""
        # Configure mock to raise ConflictException
        error = client_error_helper('ConflictException', 'Domain already exists')
        mcp_server_with_tools._mock_client.create_domain.side_effect = error

        create_domain = tool_extractor(mcp_server_with_tools, 'create_domain')

        with pytest.raises(Exception) as exc_info:
            await create_domain(
                name=sample_domain_data['name'],
                domain_execution_role=sample_domain_data['domain_execution_role'],
                service_role=sample_domain_data['service_role'],
            )

        assert f'Domain {sample_domain_data["name"]} already exists' in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_domain_access_denied(
        self, mcp_server_with_tools, tool_extractor, sample_domain_data, client_error_helper
    ):
        """Test domain creation access denied error."""
        # Configure mock to raise AccessDeniedException
        error = client_error_helper('AccessDeniedException', 'Access denied')
        mcp_server_with_tools._mock_client.create_domain.side_effect = error

        create_domain = tool_extractor(mcp_server_with_tools, 'create_domain')

        with pytest.raises(Exception) as exc_info:
            await create_domain(
                name=sample_domain_data['name'],
                domain_execution_role=sample_domain_data['domain_execution_role'],
                service_role=sample_domain_data['service_role'],
            )

        assert f'Access denied while creating domain {sample_domain_data["name"]}' in str(
            exc_info.value
        )

    @pytest.mark.asyncio
    async def test_list_domain_units_success(
        self, mcp_server_with_tools, tool_extractor, test_data_helper
    ):
        """Test successful domain units listing."""
        # Configure mock response
        mcp_server_with_tools._mock_client.list_domain_units_for_parent.return_value = {
            'items': [
                {
                    'id': 'unit_123',
                    'name': 'Test Unit',
                    'description': 'Test domain unit',
                    'domainId': 'dzd_test123',
                    'parentDomainUnitId': 'parent_unit_123',
                }
            ]
        }

        list_domain_units = tool_extractor(mcp_server_with_tools, 'list_domain_units')

        domain_id = test_data_helper.get_domain_id()
        parent_unit_id = 'parent_unit_123'
        result = await list_domain_units(domain_id, parent_unit_id)

        # Verify the result
        assert result is not None
        assert 'items' in result
        assert len(result['items']) == 1
        assert result['items'][0]['id'] == 'unit_123'

        # Verify the mock was called correctly
        mcp_server_with_tools._mock_client.list_domain_units_for_parent.assert_called_once_with(
            domainIdentifier=domain_id, parentDomainUnitIdentifier=parent_unit_id
        )

    @pytest.mark.asyncio
    async def test_create_domain_unit_success(
        self, mcp_server_with_tools, tool_extractor, test_data_helper
    ):
        """Test successful domain unit creation."""
        # Configure mock response
        mcp_server_with_tools._mock_client.create_domain_unit.return_value = {
            'id': 'unit_new123',
            'name': 'New Test Unit',
            'description': 'New test domain unit',
            'domainId': 'dzd_test123',
            'parentDomainUnitId': 'parent_unit_123',
        }

        create_domain_unit = tool_extractor(mcp_server_with_tools, 'create_domain_unit')

        domain_id = test_data_helper.get_domain_id()
        unit_name = 'New Test Unit'
        parent_unit_id = 'parent_unit_123'
        description = 'New test domain unit'

        result = await create_domain_unit(
            domain_identifier=domain_id,
            name=unit_name,
            parent_domain_unit_identifier=parent_unit_id,
            description=description,
        )

        # Verify the result
        assert result is not None
        assert result['name'] == unit_name
        assert result['description'] == description
        assert 'id' in result

        # Verify the mock was called correctly
        mcp_server_with_tools._mock_client.create_domain_unit.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_domain_unit_success(
        self, mcp_server_with_tools, tool_extractor, test_data_helper
    ):
        """Test successful domain unit retrieval."""
        # Configure mock response
        mcp_server_with_tools._mock_client.get_domain_unit.return_value = {
            'id': 'unit_test123',
            'name': 'Test Unit',
            'description': 'Test domain unit',
            'domainId': 'dzd_test123',
            'parentDomainUnitId': 'parent_unit_123',
        }

        get_domain_unit = tool_extractor(mcp_server_with_tools, 'get_domain_unit')

        domain_id = test_data_helper.get_domain_id()
        unit_id = 'unit_test123'
        result = await get_domain_unit(domain_id, unit_id)

        # Verify the result
        assert result is not None
        assert result['id'] == unit_id
        assert result['name'] == 'Test Unit'

        # Verify the mock was called correctly
        mcp_server_with_tools._mock_client.get_domain_unit.assert_called_once_with(
            domainIdentifier=domain_id, identifier=unit_id
        )

    @pytest.mark.asyncio
    async def test_search_success(self, mcp_server_with_tools, tool_extractor, test_data_helper):
        """Test successful search operation."""
        # Configure mock response
        mcp_server_with_tools._mock_client.search.return_value = {
            'items': [
                {
                    'id': 'search_result_123',
                    'name': 'Search Result',
                    'description': 'Test search result',
                    'assetType': 'amazon.datazone.S3Asset',
                }
            ],
            'totalMatchCount': 1,
        }

        search = tool_extractor(mcp_server_with_tools, 'search')

        domain_id = test_data_helper.get_domain_id()
        search_scope = 'ASSET'
        search_text = 'test'

        result = await search(
            domain_identifier=domain_id, search_scope=search_scope, search_text=search_text
        )

        # Verify the result
        assert result is not None
        assert 'items' in result
        assert len(result['items']) == 1
        assert result['totalMatchCount'] == 1

        # Verify the mock was called correctly
        mcp_server_with_tools._mock_client.search.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_policy_grant_success(
        self, mcp_server_with_tools, tool_extractor, test_data_helper
    ):
        """Test successful policy grant addition."""
        # Configure mock response
        mcp_server_with_tools._mock_client.add_policy_grant.return_value = {
            'policyType': 'OVERRIDE_DOMAIN_UNIT_OWNERS',
            'principal': {'domainUnitId': 'unit_123', 'domainUnitDesignation': 'OWNER'},
        }

        add_policy_grant = tool_extractor(mcp_server_with_tools, 'add_policy_grant')

        domain_id = test_data_helper.get_domain_id()
        entity_id = 'unit_123'
        entity_type = 'DOMAIN_UNIT'
        policy_type = 'OVERRIDE_DOMAIN_UNIT_OWNERS'
        principal_id = 'user_123'

        result = await add_policy_grant(
            domain_identifier=domain_id,
            entity_identifier=entity_id,
            entity_type=entity_type,
            policy_type=policy_type,
            principal_identifier=principal_id,
        )

        # Verify the result
        assert result is not None
        assert result['policyType'] == policy_type

        # Verify the mock was called correctly
        mcp_server_with_tools._mock_client.add_policy_grant.assert_called_once()

    @pytest.mark.asyncio
    async def test_error_handling_generic_error(
        self, mcp_server_with_tools, tool_extractor, test_data_helper, client_error_helper
    ):
        """Test generic error handling."""
        # Configure mock to raise a generic error
        error = client_error_helper('InternalServerException', 'Internal server error')
        mcp_server_with_tools._mock_client.get_domain.side_effect = error

        get_domain = tool_extractor(mcp_server_with_tools, 'get_domain')

        domain_id = test_data_helper.get_domain_id()
        with pytest.raises(Exception) as exc_info:
            await get_domain(domain_id)

        assert 'Error getting domain dzd_test123' in str(exc_info.value)


class TestDomainManagementParameterValidation:
    """Test parameter validation for domain management tools."""

    @pytest.mark.asyncio
    async def test_search_with_all_parameters(
        self, mcp_server_with_tools, tool_extractor, test_data_helper
    ):
        """Test search with all optional parameters."""
        # Configure mock response
        mcp_server_with_tools._mock_client.search.return_value = {
            'items': [],
            'totalMatchCount': 0,
        }

        search = tool_extractor(mcp_server_with_tools, 'search')

        domain_id = test_data_helper.get_domain_id()

        # Test with all parameters
        await search(
            domain_identifier=domain_id,
            search_scope='ASSET',
            additional_attributes=['BUSINESS_NAME'],
            filters={'assetType': 'amazon.datazone.S3Asset'},
            max_results=25,
            next_token='token123',
            owning_project_identifier='prj_test123',
            search_in=[{'attribute': 'name'}],
            search_text='test query',
            sort={'attribute': 'name', 'order': 'asc'},
        )

        # Verify the mock was called with all parameters
        mcp_server_with_tools._mock_client.search.assert_called_once()
        call_args = mcp_server_with_tools._mock_client.search.call_args[1]
        assert call_args['domainIdentifier'] == domain_id
        assert call_args['searchScope'] == 'ASSET'
        assert call_args['additionalAttributes'] == ['BUSINESS_NAME']
        assert call_args['maxResults'] == 25


class TestDomainManagementUncoveredLines:
    """Test domain management scenarios to cover all uncovered lines."""

    @pytest.mark.asyncio
    async def test_create_domain_with_all_optional_params_coverage(
        self, mcp_server_with_tools, tool_extractor
    ):
        """Test create_domain with all optional parameters - covers lines 103, 105, 107, 109, 111."""
        create_domain = tool_extractor(mcp_server_with_tools, 'create_domain')

        mcp_server_with_tools._mock_client.create_domain.return_value = {
            'id': 'dzd_123456789',
            'arn': 'arn:aws:datazone:us-east-1:123456789012:domain/dzd_123456789',
            'name': 'test-domain',
            'description': 'Test domain description',
            'domainVersion': 'V2',
            'status': 'AVAILABLE',
            'portalUrl': 'https://test-domain.us-east-1.datazone.aws.dev',
            'rootDomainUnitId': 'root-unit-123',
        }

        # Test with all optional parameters to cover the uncovered lines
        await create_domain(
            name='test-domain',
            domain_execution_role='arn:aws:iam::123456789012:role/DataZoneExecutionRole',
            service_role='arn:aws:iam::123456789012:role/DataZoneServiceRole',
            domain_version='V2',
            description='Test domain description',
            kms_key_identifier='arn:aws:kms:us-east-1:123456789012:key/key-123',
            tags={'Environment': 'Test', 'Project': 'DataZone'},
            single_sign_on={'type': 'IAM_IDC', 'userAssignment': 'AUTOMATIC'},
        )

        # Verify all optional parameters were passed
        call_kwargs = mcp_server_with_tools._mock_client.create_domain.call_args[1]
        assert call_kwargs['description'] == 'Test domain description'
        assert call_kwargs['kmsKeyIdentifier'] == 'arn:aws:kms:us-east-1:123456789012:key/key-123'
        assert call_kwargs['tags'] == {'Environment': 'Test', 'Project': 'DataZone'}
        assert call_kwargs['singleSignOn'] == {'type': 'IAM_IDC', 'userAssignment': 'AUTOMATIC'}
        assert call_kwargs['serviceRole'] == 'arn:aws:iam::123456789012:role/DataZoneServiceRole'

    @pytest.mark.asyncio
    async def test_create_domain_access_denied_error_coverage(
        self, mcp_server_with_tools, tool_extractor, mock_client_error
    ):
        """Test create_domain AccessDeniedException handling - covers lines 128-129."""
        create_domain = tool_extractor(mcp_server_with_tools, 'create_domain')

        mcp_server_with_tools._mock_client.create_domain.side_effect = mock_client_error(
            'AccessDeniedException', 'Access denied'
        )

        with pytest.raises(Exception) as exc_info:
            await create_domain(
                name='test-domain',
                domain_execution_role='arn:aws:iam::123456789012:role/DataZoneExecutionRole',
                service_role='arn:aws:iam::123456789012:role/DataZoneServiceRole',
            )

        assert 'Access denied while creating domain test-domain' in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_domain_conflict_error_coverage(
        self, mcp_server_with_tools, tool_extractor, mock_client_error
    ):
        """Test create_domain ConflictException handling - covers lines 130-131."""
        create_domain = tool_extractor(mcp_server_with_tools, 'create_domain')

        mcp_server_with_tools._mock_client.create_domain.side_effect = mock_client_error(
            'ConflictException', 'Domain already exists'
        )

        with pytest.raises(Exception) as exc_info:
            await create_domain(
                name='test-domain',
                domain_execution_role='arn:aws:iam::123456789012:role/DataZoneExecutionRole',
                service_role='arn:aws:iam::123456789012:role/DataZoneServiceRole',
            )

        assert 'Domain test-domain already exists' in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_domain_validation_error_coverage(
        self, mcp_server_with_tools, tool_extractor, mock_client_error
    ):
        """Test create_domain ValidationException handling - covers lines 132-133."""
        create_domain = tool_extractor(mcp_server_with_tools, 'create_domain')

        mcp_server_with_tools._mock_client.create_domain.side_effect = mock_client_error(
            'ValidationException', 'Invalid parameters'
        )

        with pytest.raises(Exception) as exc_info:
            await create_domain(
                name='test-domain',
                domain_execution_role='arn:aws:iam::123456789012:role/DataZoneExecutionRole',
                service_role='arn:aws:iam::123456789012:role/DataZoneServiceRole',
            )

        assert 'Invalid parameters for creating domain test-domain' in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_domain_unknown_error_coverage(
        self, mcp_server_with_tools, tool_extractor, mock_client_error
    ):
        """Test create_domain unknown error handling - covers lines 134-135."""
        create_domain = tool_extractor(mcp_server_with_tools, 'create_domain')

        mcp_server_with_tools._mock_client.create_domain.side_effect = mock_client_error(
            'UnknownException', 'Unknown error'
        )

        with pytest.raises(Exception) as exc_info:
            await create_domain(
                name='test-domain',
                domain_execution_role='arn:aws:iam::123456789012:role/DataZoneExecutionRole',
                service_role='arn:aws:iam::123456789012:role/DataZoneServiceRole',
            )

        assert 'Error creating domain test-domain' in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_domain_general_exception_coverage(
        self, mcp_server_with_tools, tool_extractor
    ):
        """Test create_domain general exception handling - covers lines 136-137."""
        create_domain = tool_extractor(mcp_server_with_tools, 'create_domain')

        # Mock a non-ClientError exception
        mcp_server_with_tools._mock_client.create_domain.side_effect = ValueError('Test exception')

        with pytest.raises(Exception) as exc_info:
            await create_domain(
                name='test-domain',
                domain_execution_role='arn:aws:iam::123456789012:role/DataZoneExecutionRole',
                service_role='arn:aws:iam::123456789012:role/DataZoneServiceRole',
            )

        assert 'Unexpected error creating domain test-domain' in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_list_domains_with_optional_params_coverage(
        self, mcp_server_with_tools, tool_extractor
    ):
        """Test list_domains with optional parameters - covers lines 171-172."""
        list_domains = tool_extractor(mcp_server_with_tools, 'list_domains')

        mcp_server_with_tools._mock_client.list_domains.return_value = {
            'items': [
                {
                    'id': 'dzd_123456789',
                    'name': 'test-domain',
                    'status': 'AVAILABLE',
                    'arn': 'arn:aws:datazone:us-east-1:123456789012:domain/dzd_123456789',
                }
            ],
            'nextToken': 'next-token-123',
        }

        # Test with optional parameters
        await list_domains(max_results=10, next_token='token-123', status='AVAILABLE')

        call_kwargs = mcp_server_with_tools._mock_client.list_domains.call_args[1]
        assert call_kwargs['nextToken'] == 'token-123'
        assert call_kwargs['status'] == 'AVAILABLE'
        assert call_kwargs['maxResults'] == 10

    @pytest.mark.asyncio
    async def test_list_domains_access_denied_coverage(
        self, mcp_server_with_tools, tool_extractor, mock_client_error
    ):
        """Test list_domains AccessDeniedException handling - covers lines 196."""
        list_domains = tool_extractor(mcp_server_with_tools, 'list_domains')

        mcp_server_with_tools._mock_client.list_domains.side_effect = mock_client_error(
            'AccessDeniedException', 'Access denied'
        )

        with pytest.raises(Exception) as exc_info:
            await list_domains()

        assert 'Access denied while listing domains' in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_list_domains_internal_server_error_coverage(
        self, mcp_server_with_tools, tool_extractor, mock_client_error
    ):
        """Test list_domains InternalServerException handling - covers lines 198-200."""
        list_domains = tool_extractor(mcp_server_with_tools, 'list_domains')

        mcp_server_with_tools._mock_client.list_domains.side_effect = mock_client_error(
            'InternalServerException', 'Internal server error'
        )

        with pytest.raises(Exception) as exc_info:
            await list_domains()

        assert 'The request has failed because of an unknown error, exception or failure' in str(
            exc_info.value
        )

    @pytest.mark.asyncio
    async def test_list_domains_throttling_error_coverage(
        self, mcp_server_with_tools, tool_extractor, mock_client_error
    ):
        """Test list_domains ThrottlingException handling - covers lines 202-203."""
        list_domains = tool_extractor(mcp_server_with_tools, 'list_domains')

        mcp_server_with_tools._mock_client.list_domains.side_effect = mock_client_error(
            'ThrottlingException', 'Request throttled'
        )

        with pytest.raises(Exception) as exc_info:
            await list_domains()

        assert 'The request was denied due to request throttling' in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_list_domains_conflict_error_coverage(
        self, mcp_server_with_tools, tool_extractor, mock_client_error
    ):
        """Test list_domains ConflictException handling - covers line 207."""
        list_domains = tool_extractor(mcp_server_with_tools, 'list_domains')

        mcp_server_with_tools._mock_client.list_domains.side_effect = mock_client_error(
            'ConflictException', 'Conflict error'
        )

        with pytest.raises(Exception) as exc_info:
            await list_domains()

        assert 'There is a conflict listing the domains' in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_list_domains_unauthorized_error_coverage(
        self, mcp_server_with_tools, tool_extractor, mock_client_error
    ):
        """Test list_domains UnauthorizedException handling - covers line 211."""
        list_domains = tool_extractor(mcp_server_with_tools, 'list_domains')

        mcp_server_with_tools._mock_client.list_domains.side_effect = mock_client_error(
            'UnauthorizedException', 'Unauthorized'
        )

        with pytest.raises(Exception) as exc_info:
            await list_domains()

        assert 'Insufficient permission to list domains' in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_list_domains_validation_error_coverage(
        self, mcp_server_with_tools, tool_extractor, mock_client_error
    ):
        """Test list_domains ValidationException handling - covers lines 213-214."""
        list_domains = tool_extractor(mcp_server_with_tools, 'list_domains')

        mcp_server_with_tools._mock_client.list_domains.side_effect = mock_client_error(
            'ValidationException', 'Validation error'
        )

        with pytest.raises(Exception) as exc_info:
            await list_domains()

        assert 'input fails to satisfy the constraints specified by the Amazon service' in str(
            exc_info.value
        )

    @pytest.mark.asyncio
    async def test_list_domains_resource_not_found_coverage(
        self, mcp_server_with_tools, tool_extractor, mock_client_error
    ):
        """Test list_domains ResourceNotFoundException handling - covers line 218."""
        list_domains = tool_extractor(mcp_server_with_tools, 'list_domains')

        mcp_server_with_tools._mock_client.list_domains.side_effect = mock_client_error(
            'ResourceNotFoundException', 'Resource not found'
        )

        with pytest.raises(Exception) as exc_info:
            await list_domains()

        assert 'input fails to satisfy the constraints specified by the Amazon service' in str(
            exc_info.value
        )

    @pytest.mark.asyncio
    async def test_list_domains_general_exception_coverage(
        self, mcp_server_with_tools, tool_extractor
    ):
        """Test list_domains general exception handling - covers line 230."""
        list_domains = tool_extractor(mcp_server_with_tools, 'list_domains')

        # Mock a non-ClientError exception
        mcp_server_with_tools._mock_client.list_domains.side_effect = ValueError('Test exception')

        with pytest.raises(Exception) as exc_info:
            await list_domains()

        assert 'Unexpected error listing domains' in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_domain_unit_with_optional_params_coverage(
        self, mcp_server_with_tools, tool_extractor
    ):
        """Test create_domain_unit with optional parameters - covers lines 232-235."""
        create_domain_unit = tool_extractor(mcp_server_with_tools, 'create_domain_unit')

        mcp_server_with_tools._mock_client.create_domain_unit.return_value = {
            'id': 'unit-123',
            'name': 'test-unit',
        }

        # Test with optional parameters
        await create_domain_unit(
            domain_identifier='dzd_123456789',
            name='test-unit',
            parent_domain_unit_identifier='parent-unit-123',
            description='Test domain unit description',
            client_token='test-client-token',
        )

        call_kwargs = mcp_server_with_tools._mock_client.create_domain_unit.call_args[1]
        assert call_kwargs['description'] == 'Test domain unit description'
        assert call_kwargs['clientToken'] == 'test-client-token'

    @pytest.mark.asyncio
    async def test_create_domain_unit_access_denied_coverage(
        self, mcp_server_with_tools, tool_extractor, mock_client_error
    ):
        """Test create_domain_unit AccessDeniedException handling - covers lines 237-238."""
        create_domain_unit = tool_extractor(mcp_server_with_tools, 'create_domain_unit')

        mcp_server_with_tools._mock_client.create_domain_unit.side_effect = mock_client_error(
            'AccessDeniedException', 'Access denied'
        )

        with pytest.raises(Exception) as exc_info:
            await create_domain_unit(
                domain_identifier='dzd_123456789',
                name='test-unit',
                parent_domain_unit_identifier='parent-unit-123',
            )

        assert "Access denied while creating domain unit 'test-unit'" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_domain_unit_conflict_error_coverage(
        self, mcp_server_with_tools, tool_extractor, mock_client_error
    ):
        """Test create_domain_unit ConflictException handling - covers line 240."""
        create_domain_unit = tool_extractor(mcp_server_with_tools, 'create_domain_unit')

        mcp_server_with_tools._mock_client.create_domain_unit.side_effect = mock_client_error(
            'ConflictException', 'Domain unit already exists'
        )

        with pytest.raises(Exception) as exc_info:
            await create_domain_unit(
                domain_identifier='dzd_123456789',
                name='test-unit',
                parent_domain_unit_identifier='parent-unit-123',
            )

        assert "Domain unit 'test-unit' already exists in domain dzd_123456789" in str(
            exc_info.value
        )

    @pytest.mark.asyncio
    async def test_create_domain_unit_resource_not_found_coverage(
        self, mcp_server_with_tools, tool_extractor, mock_client_error
    ):
        """Test create_domain_unit ResourceNotFoundException handling - covers line 243."""
        create_domain_unit = tool_extractor(mcp_server_with_tools, 'create_domain_unit')

        mcp_server_with_tools._mock_client.create_domain_unit.side_effect = mock_client_error(
            'ResourceNotFoundException', 'Domain not found'
        )

        with pytest.raises(Exception) as exc_info:
            await create_domain_unit(
                domain_identifier='dzd_123456789',
                name='test-unit',
                parent_domain_unit_identifier='parent-unit-123',
            )

        assert "Error creating domain unit 'test-unit' in domain dzd_123456789" in str(
            exc_info.value
        )

    @pytest.mark.asyncio
    async def test_create_domain_unit_service_quota_error_coverage(
        self, mcp_server_with_tools, tool_extractor, mock_client_error
    ):
        """Test create_domain_unit ServiceQuotaExceededException handling - covers lines 247-248."""
        create_domain_unit = tool_extractor(mcp_server_with_tools, 'create_domain_unit')

        mcp_server_with_tools._mock_client.create_domain_unit.side_effect = mock_client_error(
            'ServiceQuotaExceededException', 'Service quota exceeded'
        )

        with pytest.raises(Exception) as exc_info:
            await create_domain_unit(
                domain_identifier='dzd_123456789',
                name='test-unit',
                parent_domain_unit_identifier='parent-unit-123',
            )

        assert "Service quota exceeded while creating domain unit 'test-unit'" in str(
            exc_info.value
        )

    @pytest.mark.asyncio
    async def test_create_domain_unit_validation_error_coverage(
        self, mcp_server_with_tools, tool_extractor, mock_client_error
    ):
        """Test create_domain_unit ValidationException handling - covers lines 250-251."""
        create_domain_unit = tool_extractor(mcp_server_with_tools, 'create_domain_unit')

        mcp_server_with_tools._mock_client.create_domain_unit.side_effect = mock_client_error(
            'ValidationException', 'Invalid parameters'
        )

        with pytest.raises(Exception) as exc_info:
            await create_domain_unit(
                domain_identifier='dzd_123456789',
                name='test-unit',
                parent_domain_unit_identifier='parent-unit-123',
            )

        assert "Invalid parameters for creating domain unit 'test-unit'" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_domain_unit_unknown_error_coverage(
        self, mcp_server_with_tools, tool_extractor, mock_client_error
    ):
        """Test create_domain_unit unknown error handling - covers lines 253-254."""
        create_domain_unit = tool_extractor(mcp_server_with_tools, 'create_domain_unit')

        mcp_server_with_tools._mock_client.create_domain_unit.side_effect = mock_client_error(
            'UnknownException', 'Unknown error'
        )

        with pytest.raises(Exception) as exc_info:
            await create_domain_unit(
                domain_identifier='dzd_123456789',
                name='test-unit',
                parent_domain_unit_identifier='parent-unit-123',
            )

        assert "Error creating domain unit 'test-unit' in domain dzd_123456789" in str(
            exc_info.value
        )

    @pytest.mark.asyncio
    async def test_create_domain_unit_general_exception_coverage(
        self, mcp_server_with_tools, tool_extractor
    ):
        """Test create_domain_unit general exception handling - covers line 256."""
        create_domain_unit = tool_extractor(mcp_server_with_tools, 'create_domain_unit')

        # Mock a non-ClientError exception
        mcp_server_with_tools._mock_client.create_domain_unit.side_effect = ValueError(
            'Test exception'
        )

        with pytest.raises(Exception) as exc_info:
            await create_domain_unit(
                domain_identifier='dzd_123456789',
                name='test-unit',
                parent_domain_unit_identifier='parent-unit-123',
            )

        assert "Unexpected error creating domain unit 'test-unit' in domain dzd_123456789" in str(
            exc_info.value
        )

    @pytest.mark.asyncio
    async def test_add_entity_owner_with_optional_params_coverage(
        self, mcp_server_with_tools, tool_extractor
    ):
        """Test add_entity_owner with optional parameters - covers lines 445-446."""
        add_entity_owner = tool_extractor(mcp_server_with_tools, 'add_entity_owner')

        mcp_server_with_tools._mock_client.add_entity_owner.return_value = {}

        # Test with optional parameters
        await add_entity_owner(
            domain_identifier='dzd_123456789',
            entity_identifier='entity-123',
            owner_identifier='user-123',
            entity_type='DOMAIN_UNIT',
            owner_type='USER',
            client_token='test-client-token',
        )

        call_kwargs = mcp_server_with_tools._mock_client.add_entity_owner.call_args[1]
        assert call_kwargs['clientToken'] == 'test-client-token'

    @pytest.mark.asyncio
    async def test_add_policy_grant_with_optional_params_coverage(
        self, mcp_server_with_tools, tool_extractor
    ):
        """Test add_policy_grant with optional parameters - covers lines 466-467."""
        add_policy_grant = tool_extractor(mcp_server_with_tools, 'add_policy_grant')

        mcp_server_with_tools._mock_client.add_policy_grant.return_value = {}

        # Test with optional parameters
        await add_policy_grant(
            domain_identifier='dzd_123456789',
            entity_identifier='entity-123',
            entity_type='DOMAIN_UNIT',
            policy_type='OVERRIDE_DOMAIN_UNIT_OWNERS',
            principal_identifier='user-123',
            principal_type='USER',
            client_token='test-client-token',
            detail={'permissions': ['READ', 'WRITE']},
        )

        call_kwargs = mcp_server_with_tools._mock_client.add_policy_grant.call_args[1]
        assert call_kwargs['clientToken'] == 'test-client-token'
        assert call_kwargs['detail'] == {'permissions': ['READ', 'WRITE']}

    @pytest.mark.asyncio
    async def test_add_policy_grant_error_handling_coverage(
        self, mcp_server_with_tools, tool_extractor, mock_client_error
    ):
        """Test add_policy_grant error handling - covers line 577."""
        add_policy_grant = tool_extractor(mcp_server_with_tools, 'add_policy_grant')

        mcp_server_with_tools._mock_client.add_policy_grant.side_effect = mock_client_error(
            'AccessDeniedException', 'Access denied'
        )

        with pytest.raises(Exception) as exc_info:
            await add_policy_grant(
                domain_identifier='dzd_123456789',
                entity_identifier='entity-123',
                entity_type='DOMAIN_UNIT',
                policy_type='OVERRIDE_DOMAIN_UNIT_OWNERS',
                principal_identifier='user-123',
            )

        assert 'Error adding policy grant to entity entity-123 in domain dzd_123456789' in str(
            exc_info.value
        )

    @pytest.mark.asyncio
    async def test_search_with_all_optional_params_coverage(
        self, mcp_server_with_tools, tool_extractor
    ):
        """Test search with all optional parameters - covers lines 496, 498, 500, 505, 508."""
        search = tool_extractor(mcp_server_with_tools, 'search')

        mcp_server_with_tools._mock_client.search.return_value = {'items': []}

        # Test with all optional parameters
        await search(
            domain_identifier='dzd_123456789',
            search_scope='ASSET',
            additional_attributes=['BUSINESS_NAME'],
            filters={'status': 'PUBLISHED'},
            max_results=25,
            next_token='token-123',
            owning_project_identifier='project-123',
            search_in=[{'attribute': 'name'}],
            search_text='test search',
            sort={'attribute': 'name', 'order': 'ASC'},
        )

        call_kwargs = mcp_server_with_tools._mock_client.search.call_args[1]
        assert call_kwargs['additionalAttributes'] == ['BUSINESS_NAME']
        assert call_kwargs['filters'] == {'status': 'PUBLISHED'}
        assert call_kwargs['nextToken'] == 'token-123'
        assert call_kwargs['owningProjectIdentifier'] == 'project-123'
        assert call_kwargs['searchIn'] == [{'attribute': 'name'}]
        assert call_kwargs['searchText'] == 'test search'
        assert call_kwargs['sort'] == {'attribute': 'name', 'order': 'ASC'}

    @pytest.mark.asyncio
    async def test_search_error_handling_coverage(
        self, mcp_server_with_tools, tool_extractor, mock_client_error
    ):
        """Test search specific error handling - covers lines 714-729."""
        search = tool_extractor(mcp_server_with_tools, 'search')

        mcp_server_with_tools._mock_client.search.side_effect = mock_client_error(
            'AccessDeniedException', 'Access denied'
        )

        with pytest.raises(Exception) as exc_info:
            await search(domain_identifier='dzd_123456789', search_scope='ASSET')

        assert 'Access denied while searching in domain dzd_123456789' in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_search_general_exception_coverage(self, mcp_server_with_tools, tool_extractor):
        """Test search general exception handling - covers line 730."""
        search = tool_extractor(mcp_server_with_tools, 'search')

        # Mock a non-ClientError exception
        mcp_server_with_tools._mock_client.search.side_effect = ValueError('Test exception')

        with pytest.raises(Exception) as exc_info:
            await search(domain_identifier='dzd_123456789', search_scope='ASSET')

        assert 'Unexpected error searching in domain dzd_123456789' in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_search_types_with_optional_params_coverage(
        self, mcp_server_with_tools, tool_extractor
    ):
        """Test search_types with optional parameters - covers lines 520, 524, 526, 529."""
        search_types = tool_extractor(mcp_server_with_tools, 'search_types')

        mcp_server_with_tools._mock_client.search_types.return_value = {'items': []}

        # Test with optional parameters
        await search_types(
            domain_identifier='dzd_123456789',
            managed=True,
            search_scope='ASSET_TYPE',
            filters={'status': 'ENABLED'},
            max_results=25,
            next_token='token-123',
            search_in=[{'attribute': 'name'}],
            search_text='test type',
            sort={'attribute': 'name', 'order': 'ASC'},
        )

        call_kwargs = mcp_server_with_tools._mock_client.search_types.call_args[1]
        assert call_kwargs['filters'] == {'status': 'ENABLED'}
        assert call_kwargs['nextToken'] == 'token-123'
        assert call_kwargs['searchIn'] == [{'attribute': 'name'}]
        assert call_kwargs['searchText'] == 'test type'
        assert call_kwargs['sort'] == {'attribute': 'name', 'order': 'ASC'}

    @pytest.mark.asyncio
    async def test_search_types_error_handling_coverage(
        self, mcp_server_with_tools, tool_extractor, mock_client_error
    ):
        """Test search_types error handling - covers lines 833-849."""
        search_types = tool_extractor(mcp_server_with_tools, 'search_types')

        mcp_server_with_tools._mock_client.search_types.side_effect = mock_client_error(
            'AccessDeniedException', 'Access denied'
        )

        with pytest.raises(Exception) as exc_info:
            await search_types(
                domain_identifier='dzd_123456789', managed=True, search_scope='ASSET_TYPE'
            )

        assert 'Access denied while searching types in domain dzd_123456789' in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_user_profile_with_optional_params_coverage(
        self, mcp_server_with_tools, tool_extractor
    ):
        """Test get_user_profile with optional user_type parameter - covers line 894."""
        get_user_profile = tool_extractor(mcp_server_with_tools, 'get_user_profile')

        mcp_server_with_tools._mock_client.get_user_profile.return_value = {'id': 'user-123'}

        # Test with optional user_type - use IAM instead of IAM_USER
        await get_user_profile(
            domain_identifier='dzd_123456789',
            user_identifier='user-123',
            user_type='IAM',
        )

        call_kwargs = mcp_server_with_tools._mock_client.get_user_profile.call_args[1]
        assert call_kwargs['type'] == 'IAM'

    @pytest.mark.asyncio
    async def test_get_user_profile_error_handling_coverage(
        self, mcp_server_with_tools, tool_extractor, mock_client_error
    ):
        """Test get_user_profile error handling - covers line 897."""
        get_user_profile = tool_extractor(mcp_server_with_tools, 'get_user_profile')

        mcp_server_with_tools._mock_client.get_user_profile.side_effect = mock_client_error(
            'ResourceNotFoundException', 'User not found'
        )

        with pytest.raises(Exception) as exc_info:
            await get_user_profile(
                domain_identifier='dzd_123456789',
                user_identifier='user-123',
            )

        assert 'Error getting user user-123 profile in domain dzd_123456789' in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_search_user_profiles_with_optional_params_coverage(
        self, mcp_server_with_tools, tool_extractor
    ):
        """Test search_user_profiles with optional parameters - covers lines 975-976."""
        search_user_profiles = tool_extractor(mcp_server_with_tools, 'search_user_profiles')

        mcp_server_with_tools._mock_client.search_user_profiles.return_value = {'userProfiles': []}

        # Test with optional parameters - use correct user_type value
        await search_user_profiles(
            domain_identifier='dzd_123456789',
            user_type='DATAZONE_IAM_USER',
            max_results=25,
            next_token='token-123',
            search_text='john',
        )

        call_kwargs = mcp_server_with_tools._mock_client.search_user_profiles.call_args[1]
        assert call_kwargs['nextToken'] == 'token-123'
        assert call_kwargs['searchText'] == 'john'

    @pytest.mark.asyncio
    async def test_search_user_profiles_error_handling_coverage(
        self, mcp_server_with_tools, tool_extractor, mock_client_error
    ):
        """Test search_user_profiles error handling - covers line 990."""
        search_user_profiles = tool_extractor(mcp_server_with_tools, 'search_user_profiles')

        mcp_server_with_tools._mock_client.search_user_profiles.side_effect = mock_client_error(
            'AccessDeniedException', 'Access denied'
        )

        with pytest.raises(Exception) as exc_info:
            await search_user_profiles(
                domain_identifier='dzd_123456789',
                user_type='DATAZONE_IAM_USER',
            )

        assert (
            'Access denied while searching DATAZONE_IAM_USER user profiles in domain dzd_123456789'
            in str(exc_info.value)
        )

    @pytest.mark.asyncio
    async def test_search_group_profiles_with_all_optional_params_coverage(
        self, mcp_server_with_tools, tool_extractor
    ):
        """Test search_group_profiles with all optional parameters - covers lines 1092-1096."""
        search_group_profiles = tool_extractor(mcp_server_with_tools, 'search_group_profiles')

        mcp_server_with_tools._mock_client.search_group_profiles.return_value = {'items': []}

        # Test with all optional parameters
        await search_group_profiles(
            domain_identifier='dzd_123456789',
            group_type='SSO_GROUP',
            max_results=25,
            next_token='token-123',
            search_text='admin',
        )

        call_kwargs = mcp_server_with_tools._mock_client.search_group_profiles.call_args[1]
        assert call_kwargs['searchText'] == 'admin'
        assert call_kwargs['nextToken'] == 'token-123'

    @pytest.mark.asyncio
    async def test_search_group_profiles_access_denied_coverage(
        self, mcp_server_with_tools, tool_extractor, mock_client_error
    ):
        """Test search_group_profiles AccessDeniedException handling - covers line 1100."""
        search_group_profiles = tool_extractor(mcp_server_with_tools, 'search_group_profiles')

        mcp_server_with_tools._mock_client.search_group_profiles.side_effect = mock_client_error(
            'AccessDeniedException', 'Access denied'
        )

        with pytest.raises(Exception) as exc_info:
            await search_group_profiles(
                domain_identifier='dzd_123456789',
                group_type='SSO_GROUP',
            )

        assert (
            'Access denied while searching SSO_GROUP group profiles in domain dzd_123456789'
            in str(exc_info.value)
        )

    @pytest.mark.asyncio
    async def test_search_group_profiles_internal_server_error_coverage(
        self, mcp_server_with_tools, tool_extractor, mock_client_error
    ):
        """Test search_group_profiles InternalServerException handling - covers line 1104."""
        search_group_profiles = tool_extractor(mcp_server_with_tools, 'search_group_profiles')

        mcp_server_with_tools._mock_client.search_group_profiles.side_effect = mock_client_error(
            'InternalServerException', 'Internal server error'
        )

        with pytest.raises(Exception) as exc_info:
            await search_group_profiles(
                domain_identifier='dzd_123456789',
                group_type='SSO_GROUP',
            )

        assert (
            'Internal server error while searching SSO_GROUP group profiles in domain dzd_123456789'
            in str(exc_info.value)
        )

    @pytest.mark.asyncio
    async def test_search_group_profiles_throttling_error_coverage(
        self, mcp_server_with_tools, tool_extractor, mock_client_error
    ):
        """Test search_group_profiles ThrottlingException handling - covers line 1108."""
        search_group_profiles = tool_extractor(mcp_server_with_tools, 'search_group_profiles')

        mcp_server_with_tools._mock_client.search_group_profiles.side_effect = mock_client_error(
            'ThrottlingException', 'Request throttled'
        )

        with pytest.raises(Exception) as exc_info:
            await search_group_profiles(
                domain_identifier='dzd_123456789',
                group_type='SSO_GROUP',
            )

        assert (
            'Request throttled while searching SSO_GROUP group profiles in domain dzd_123456789'
            in str(exc_info.value)
        )

    @pytest.mark.asyncio
    async def test_search_group_profiles_unauthorized_error_coverage(
        self, mcp_server_with_tools, tool_extractor, mock_client_error
    ):
        """Test search_group_profiles UnauthorizedException handling - covers line 1112."""
        search_group_profiles = tool_extractor(mcp_server_with_tools, 'search_group_profiles')

        mcp_server_with_tools._mock_client.search_group_profiles.side_effect = mock_client_error(
            'UnauthorizedException', 'Unauthorized'
        )

        with pytest.raises(Exception) as exc_info:
            await search_group_profiles(
                domain_identifier='dzd_123456789',
                group_type='SSO_GROUP',
            )

        assert 'Unauthorized to search SSO_GROUP group profiles in domain dzd_123456789' in str(
            exc_info.value
        )

    @pytest.mark.asyncio
    async def test_search_group_profiles_validation_error_coverage(
        self, mcp_server_with_tools, tool_extractor, mock_client_error
    ):
        """Test search_group_profiles ValidationException handling - covers line 1116."""
        search_group_profiles = tool_extractor(mcp_server_with_tools, 'search_group_profiles')

        mcp_server_with_tools._mock_client.search_group_profiles.side_effect = mock_client_error(
            'ValidationException', 'Invalid input'
        )

        with pytest.raises(Exception) as exc_info:
            await search_group_profiles(
                domain_identifier='dzd_123456789',
                group_type='SSO_GROUP',
            )

        assert (
            'Invalid input while searching SSO_GROUP group profiles in domain dzd_123456789'
            in str(exc_info.value)
        )

    @pytest.mark.asyncio
    async def test_search_group_profiles_unknown_client_error_coverage(
        self, mcp_server_with_tools, tool_extractor, mock_client_error
    ):
        """Test search_group_profiles unknown ClientError handling - covers line 1120."""
        search_group_profiles = tool_extractor(mcp_server_with_tools, 'search_group_profiles')

        mcp_server_with_tools._mock_client.search_group_profiles.side_effect = mock_client_error(
            'UnknownException', 'Unknown error'
        )

        with pytest.raises(Exception) as exc_info:
            await search_group_profiles(
                domain_identifier='dzd_123456789',
                group_type='SSO_GROUP',
            )

        assert 'Error searching SSO_GROUP group profiles in domain dzd_123456789' in str(
            exc_info.value
        )

    @pytest.mark.asyncio
    async def test_search_group_profiles_general_exception_coverage(
        self, mcp_server_with_tools, tool_extractor
    ):
        """Test search_group_profiles general exception handling - covers lines 1119-1120."""
        search_group_profiles = tool_extractor(mcp_server_with_tools, 'search_group_profiles')

        # Mock a non-ClientError exception
        mcp_server_with_tools._mock_client.search_group_profiles.side_effect = ValueError(
            'Test exception'
        )

        with pytest.raises(Exception) as exc_info:
            await search_group_profiles(
                domain_identifier='dzd_123456789',
                group_type='SSO_GROUP',
            )

        assert (
            'Unexpected error searching tSSO_GROUP group profiles in domain dzd_123456789'
            in str(exc_info.value)
        )
