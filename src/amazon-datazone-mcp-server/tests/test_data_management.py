"""Unit tests for data_management tools."""

import pytest


class TestDataManagement:
    """Test cases for data management tools."""

    @pytest.mark.asyncio
    async def test_get_asset_success(
        self, mcp_server_with_tools, tool_extractor, test_data_helper
    ):
        """Test successful asset retrieval."""
        # Get the tool function from the MCP server
        get_asset = tool_extractor(mcp_server_with_tools, 'get_asset')

        # Arrange
        domain_id = 'dzd_test123'
        asset_id = 'asset_test123'
        expected_response = test_data_helper.get_asset_response(asset_id)
        mcp_server_with_tools._mock_client.get_asset.return_value = expected_response

        # Act
        result = await get_asset(domain_id, asset_id)

        # Assert
        assert result == expected_response
        mcp_server_with_tools._mock_client.get_asset.assert_called_once_with(
            domainIdentifier=domain_id, identifier=asset_id
        )

    @pytest.mark.asyncio
    async def test_create_asset_success(
        self, mcp_server_with_tools, tool_extractor, sample_asset_data
    ):
        """Test successful asset creation."""
        # Get the tool function from the MCP server
        create_asset = tool_extractor(mcp_server_with_tools, 'create_asset')

        # Arrange
        expected_response = {
            'id': 'asset_new123',
            'name': sample_asset_data['name'],
            'description': sample_asset_data['description'],
            'domainId': sample_asset_data['domain_identifier'],
            'owningProjectId': sample_asset_data['owning_project_identifier'],
            'assetType': sample_asset_data['type_identifier'],
            'revision': '1',
            'status': 'ACTIVE',
        }
        mcp_server_with_tools._mock_client.create_asset.return_value = expected_response

        # Act
        result = await create_asset(
            domain_identifier=sample_asset_data['domain_identifier'],
            name=sample_asset_data['name'],
            type_identifier=sample_asset_data['type_identifier'],
            owning_project_identifier=sample_asset_data['owning_project_identifier'],
            description=sample_asset_data['description'],
        )

        # Assert
        assert result == expected_response
        mcp_server_with_tools._mock_client.create_asset.assert_called_once_with(
            domainIdentifier=sample_asset_data['domain_identifier'],
            name=sample_asset_data['name'],
            typeIdentifier=sample_asset_data['type_identifier'],
            owningProjectIdentifier=sample_asset_data['owning_project_identifier'],
            description=sample_asset_data['description'],
        )

    @pytest.mark.asyncio
    async def test_publish_asset_success(self, mcp_server_with_tools, tool_extractor):
        """Test successful asset publishing."""
        # Get the tool function from the MCP server
        publish_asset = tool_extractor(mcp_server_with_tools, 'publish_asset')

        # Arrange
        domain_id = 'dzd_test123'
        asset_id = 'asset_test123'
        expected_response = {
            'assetId': asset_id,
            'assetType': 'amazon.datazone.RelationalTable',
            'createdAt': 1234567890,
            'domainId': domain_id,
            'listingId': 'listing_test123',
            'status': 'ACTIVE',
        }
        mcp_server_with_tools._mock_client.publish_asset.return_value = expected_response

        # Act
        result = await publish_asset(domain_id, asset_id)

        # Assert
        assert result == expected_response
        mcp_server_with_tools._mock_client.publish_asset.assert_called_once_with(
            domainIdentifier=domain_id, identifier=asset_id
        )

    @pytest.mark.asyncio
    async def test_get_listing_success(self, mcp_server_with_tools, tool_extractor):
        """Test successful listing retrieval."""
        # Get the tool function from the MCP server
        get_listing = tool_extractor(mcp_server_with_tools, 'get_listing')

        # Arrange
        domain_id = 'dzd_test123'
        listing_id = 'listing_test123'
        expected_response = {
            'id': listing_id,
            'listingRevision': '1',
            'item': {
                'assetListing': {
                    'assetId': 'asset_test123',
                    'assetType': 'amazon.datazone.RelationalTable',
                }
            },
            'status': 'ACTIVE',
            'createdAt': 1234567890,
        }
        mcp_server_with_tools._mock_client.get_listing.return_value = expected_response

        # Act
        result = await get_listing(domain_id, listing_id)

        # Assert
        assert result == expected_response
        mcp_server_with_tools._mock_client.get_listing.assert_called_once_with(
            domainIdentifier=domain_id, identifier=listing_id
        )

    @pytest.mark.asyncio
    async def test_search_listings_success(self, mcp_server_with_tools, tool_extractor):
        """Test successful listings search."""
        # Get the tool function from the MCP server
        search_listings = tool_extractor(mcp_server_with_tools, 'search_listings')

        # Arrange
        domain_id = 'dzd_test123'
        search_text = 'customer data'
        expected_response = {
            'items': [
                {
                    'id': 'listing_search123',
                    'name': 'Customer Data Asset',
                    'description': 'Customer data table',
                }
            ],
            'nextToken': None,
            'totalMatchCount': 1,
        }
        mcp_server_with_tools._mock_client.search_listings.return_value = expected_response

        # Act
        result = await search_listings(domain_identifier=domain_id, search_text=search_text)

        # Assert
        assert result == expected_response
        mcp_server_with_tools._mock_client.search_listings.assert_called_once_with(
            domainIdentifier=domain_id, maxResults=50, searchText=search_text
        )

    @pytest.mark.asyncio
    async def test_create_data_source_success(self, mcp_server_with_tools, tool_extractor):
        """Test successful data source creation."""
        # Get the tool function from the MCP server
        create_data_source = tool_extractor(mcp_server_with_tools, 'create_data_source')

        # Arrange
        domain_id = 'dzd_test123'
        project_id = 'prj_test123'
        source_name = 'Test Data Source'
        env_id = 'env_test123'
        source_type = 'AMAZON_S3'

        expected_response = {
            'id': 'ds_new123',
            'name': source_name,
            'domainId': domain_id,
            'projectId': project_id,
            'environmentId': env_id,
            'type': source_type,
            'status': 'CREATING',
        }
        mcp_server_with_tools._mock_client.create_data_source.return_value = expected_response

        # Act
        result = await create_data_source(
            domain_identifier=domain_id,
            project_identifier=project_id,
            name=source_name,
            environment_identifier=env_id,
            data_src_type=source_type,
        )

        # Assert
        assert result == expected_response
        mcp_server_with_tools._mock_client.create_data_source.assert_called_once_with(
            domainIdentifier=domain_id,
            projectIdentifier=project_id,
            name=source_name,
            type=source_type,
            enableSetting='ENABLED',
            publishOnImport=False,
            environmentIdentifier=env_id,
        )

    @pytest.mark.asyncio
    async def test_start_data_source_run_success(self, mcp_server_with_tools, tool_extractor):
        """Test successful data source run start."""
        # Get the tool function from the MCP server
        start_data_source_run = tool_extractor(mcp_server_with_tools, 'start_data_source_run')

        # Arrange
        domain_id = 'dzd_test123'
        data_source_id = 'ds_test123'
        expected_response = {
            'id': 'run_new123',
            'dataSourceId': data_source_id,
            'domainId': domain_id,
            'projectId': 'prj_test123',
            'status': 'REQUESTED',
            'type': 'PRIORITIZED',
            'createdAt': 1234567890,
        }
        mcp_server_with_tools._mock_client.start_data_source_run.return_value = expected_response

        # Act
        result = await start_data_source_run(
            domain_identifier=domain_id, data_source_identifier=data_source_id
        )

        # Assert
        assert result == expected_response
        mcp_server_with_tools._mock_client.start_data_source_run.assert_called_once_with(
            domainIdentifier=domain_id, dataSourceIdentifier=data_source_id
        )

    @pytest.mark.asyncio
    async def test_create_subscription_request_success(
        self, mcp_server_with_tools, tool_extractor
    ):
        """Test successful subscription request creation."""
        # Get the tool function from the MCP server
        create_subscription_request = tool_extractor(
            mcp_server_with_tools, 'create_subscription_request'
        )

        # Arrange
        domain_id = 'dzd_test123'
        request_reason = 'Need access for analytics'
        subscribed_listings = [{'identifier': 'listing_test123'}]
        subscribed_principals = [{'identifier': 'prj_test123'}]

        expected_response = {
            'id': 'sub_req_new123',
            'domainId': domain_id,
            'status': 'PENDING',
            'subscribedListings': subscribed_listings,
            'subscribedPrincipals': subscribed_principals,
            'requestReason': request_reason,
            'createdAt': 1234567890,
        }
        mcp_server_with_tools._mock_client.create_subscription_request.return_value = (
            expected_response
        )

        # Act
        result = await create_subscription_request(
            domain_identifier=domain_id,
            request_reason=request_reason,
            subscribed_listings=subscribed_listings,
            subscribed_principals=subscribed_principals,
        )

        # Assert
        assert result == expected_response
        mcp_server_with_tools._mock_client.create_subscription_request.assert_called_once_with(
            domainIdentifier=domain_id,
            requestReason=request_reason,
            subscribedListings=subscribed_listings,
            subscribedPrincipals=subscribed_principals,
        )

    @pytest.mark.asyncio
    async def test_accept_subscription_request_success(
        self, mcp_server_with_tools, tool_extractor
    ):
        """Test successful subscription request acceptance."""
        # Get the tool function from the MCP server
        accept_subscription_request = tool_extractor(
            mcp_server_with_tools, 'accept_subscription_request'
        )

        # Arrange
        domain_id = 'dzd_test123'
        subscription_id = 'sub_req_test123'
        decision_comment = 'Approved for analytics use'

        expected_response = {
            'id': subscription_id,
            'domainId': domain_id,
            'status': 'APPROVED',
            'decisionComment': decision_comment,
            'updatedAt': 1234567890,
        }
        mcp_server_with_tools._mock_client.accept_subscription_request.return_value = (
            expected_response
        )

        # Act
        result = await accept_subscription_request(
            domain_identifier=domain_id,
            identifier=subscription_id,
            decision_comment=decision_comment,
        )

        # Assert
        assert result == expected_response
        mcp_server_with_tools._mock_client.accept_subscription_request.assert_called_once_with(
            domainIdentifier=domain_id,
            identifier=subscription_id,
            decisionComment=decision_comment,
        )

    @pytest.mark.asyncio
    async def test_get_form_type_success(self, mcp_server_with_tools, tool_extractor):
        """Test successful form type retrieval."""
        # Get the tool function from the MCP server
        get_form_type = tool_extractor(mcp_server_with_tools, 'get_form_type')

        # Arrange
        domain_id = 'dzd_test123'
        form_type_id = 'ft_test123'
        expected_response = {
            'domainId': domain_id,
            'name': 'Test Form Type',
            'revision': '1',
            'model': {'smithy': 'structure TestForm { field1: String }'},
            'status': 'ENABLED',
            'description': 'Test form type for metadata',
        }
        mcp_server_with_tools._mock_client.get_form_type.return_value = expected_response

        # Act
        result = await get_form_type(domain_id, form_type_id)

        # Assert
        assert result == expected_response
        mcp_server_with_tools._mock_client.get_form_type.assert_called_once_with(
            domainIdentifier=domain_id, formTypeIdentifier=form_type_id
        )

    @pytest.mark.asyncio
    async def test_create_asset_access_denied(
        self, mcp_server_with_tools, tool_extractor, mock_client_error
    ):
        """Test asset creation with access denied error."""
        # Get the tool function from the MCP server
        create_asset = tool_extractor(mcp_server_with_tools, 'create_asset')

        # Arrange
        domain_id = 'dzd_test123'
        asset_name = 'Denied Asset'
        mcp_server_with_tools._mock_client.create_asset.side_effect = mock_client_error(
            'AccessDeniedException', 'Insufficient permissions'
        )

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            await create_asset(
                domain_identifier=domain_id,
                name=asset_name,
                type_identifier='amazon.datazone.RelationalTable',
                owning_project_identifier='prj_test123',
            )

        assert 'Access denied' in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_asset_not_found(self, mcp_server_with_tools, tool_extractor, mock_client_error):
        """Test asset retrieval when asset doesn't exist."""
        # Get the tool function from the MCP server
        get_asset = tool_extractor(mcp_server_with_tools, 'get_asset')

        # Arrange
        domain_id = 'dzd_test123'
        asset_id = 'asset_nonexistent'
        mcp_server_with_tools._mock_client.get_asset.side_effect = mock_client_error(
            'ResourceNotFoundException', 'Asset not found'
        )

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            await get_asset(domain_id, asset_id)

        assert 'not found' in str(exc_info.value)

    def test_register_tools(self, mock_fastmcp):
        """Test that all data management tools are registered."""
        # Import here to avoid circular import issues
        from awslabs.datazone_mcp_server.tools import data_management

        # Act
        data_management.register_tools(mock_fastmcp)

        # Assert - check that tool decorator was called for each expected tool
        expected_calls = [
            'get_asset',
            'create_asset',
            'publish_asset',
            'get_listing',
            'search_listings',
            'create_data_source',
            'get_data_source',
            'start_data_source_run',
            'create_subscription_request',
            'accept_subscription_request',
            'get_subscription',
            'get_form_type',
            'list_form_types',
            'create_form_type',
        ]

        # Check that tool was called for each expected function
        assert mock_fastmcp.tool.call_count >= len(expected_calls)


class TestDataManagementParameterValidation:
    """Test parameter validation for data management tools."""

    @pytest.mark.asyncio
    async def test_create_asset_with_all_optional_params(
        self, mcp_server_with_tools, tool_extractor
    ):
        """Test create_asset with all optional parameters."""
        # Get the tool function from the MCP server
        create_asset = tool_extractor(mcp_server_with_tools, 'create_asset')

        # Arrange
        mcp_server_with_tools._mock_client.create_asset.return_value = {
            'id': 'asset_full123',
            'name': 'Full Asset',
            'status': 'ACTIVE',
        }

        forms_input = [
            {
                'content': '{"field1": "value1"}',
                'formName': 'TestForm',
                'typeIdentifier': 'form_type_123',
                'typeRevision': '1',
            }
        ]

        glossary_terms = ['term1', 'term2']

        prediction_config = {'businessNameGeneration': {'enabled': True}}

        # Act
        await create_asset(
            domain_identifier='dzd_test123',
            name='Full Asset',
            type_identifier='amazon.datazone.RelationalTable',
            owning_project_identifier='prj_test123',
            description='Full test asset with all params',
            external_identifier='ext_123',
            forms_input=forms_input,
            glossary_terms=glossary_terms,
            prediction_configuration=prediction_config,
            type_revision='2',
            client_token='token_123',
        )

        # Assert
        mcp_server_with_tools._mock_client.create_asset.assert_called_once_with(
            domainIdentifier='dzd_test123',
            name='Full Asset',
            typeIdentifier='amazon.datazone.RelationalTable',
            owningProjectIdentifier='prj_test123',
            description='Full test asset with all params',
            externalIdentifier='ext_123',
            formsInput=forms_input,
            glossaryTerms=glossary_terms,
            predictionConfiguration=prediction_config,
            typeRevision='2',
            clientToken='token_123',
        )

    @pytest.mark.asyncio
    async def test_search_listings_max_results_validation(
        self, mcp_server_with_tools, tool_extractor
    ):
        """Test that max_results is capped at 50."""
        # Get the tool function from the MCP server
        search_listings = tool_extractor(mcp_server_with_tools, 'search_listings')

        # Arrange
        mcp_server_with_tools._mock_client.search_listings.return_value = {'items': []}

        # Act
        await search_listings(
            domain_identifier='dzd_test123',
            max_results=100,  # Should be capped at 50
        )

        # Assert
        mcp_server_with_tools._mock_client.search_listings.assert_called_once_with(
            domainIdentifier='dzd_test123',
            maxResults=50,  # Capped value
        )
