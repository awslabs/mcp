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
    async def test_get_asset_with_revision(
        self, mcp_server_with_tools, tool_extractor, test_data_helper
    ):
        """Test asset retrieval with revision parameter - covers line 52."""
        get_asset = tool_extractor(mcp_server_with_tools, 'get_asset')

        domain_id = 'dzd_test123'
        asset_id = 'asset_test123'
        revision = 'rev_123'
        expected_response = test_data_helper.get_asset_response(asset_id)
        mcp_server_with_tools._mock_client.get_asset.return_value = expected_response

        result = await get_asset(domain_id, asset_id, revision)

        assert result == expected_response
        mcp_server_with_tools._mock_client.get_asset.assert_called_once_with(
            domainIdentifier=domain_id, identifier=asset_id, revision=revision
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
    async def test_get_data_source_success(self, mcp_server_with_tools, tool_extractor):
        """Test successful data source retrieval."""
        # Get the tool function from the MCP server
        get_data_source = tool_extractor(mcp_server_with_tools, 'get_data_source')

        # Arrange
        domain_id = 'dzd_test123'
        ds_id = 'ds_test123'
        expected_response = {
            'id': ds_id,
            'name': 'Test Data Source',
            'domainId': domain_id,
            'status': 'ACTIVE',
        }
        mcp_server_with_tools._mock_client.get_data_source.return_value = expected_response

        # Act
        result = await get_data_source(domain_id, ds_id)

        # Assert
        assert result == expected_response
        mcp_server_with_tools._mock_client.get_data_source.assert_called_once_with(
            domainIdentifier=domain_id, identifier=ds_id
        )

    @pytest.mark.asyncio
    async def test_start_data_source_run_success(self, mcp_server_with_tools, tool_extractor):
        """Test successful data source run start."""
        # Get the tool function from the MCP server
        start_data_source_run = tool_extractor(mcp_server_with_tools, 'start_data_source_run')

        # Arrange
        domain_id = 'dzd_test123'
        ds_id = 'ds_test123'
        expected_response = {
            'id': 'run_test123',
            'dataSourceId': ds_id,
            'domainId': domain_id,
            'status': 'REQUESTED',
            'createdAt': 1234567890,
        }
        mcp_server_with_tools._mock_client.start_data_source_run.return_value = expected_response

        # Act
        result = await start_data_source_run(domain_id, ds_id)

        # Assert
        assert result == expected_response
        mcp_server_with_tools._mock_client.start_data_source_run.assert_called_once_with(
            domainIdentifier=domain_id, dataSourceIdentifier=ds_id
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
        reason = 'Need access to customer data'
        listings = [{'identifier': 'listing_test123', 'revision': '1'}]
        principals = [{'identifier': 'user_test123', 'type': 'USER'}]

        expected_response = {
            'id': 'sub_req_test123',
            'domainId': domain_id,
            'requestReason': reason,
            'status': 'PENDING',
            'createdAt': 1234567890,
        }
        mcp_server_with_tools._mock_client.create_subscription_request.return_value = (
            expected_response
        )

        # Act
        result = await create_subscription_request(
            domain_identifier=domain_id,
            request_reason=reason,
            subscribed_listings=listings,
            subscribed_principals=principals,
        )

        # Assert
        assert result == expected_response
        mcp_server_with_tools._mock_client.create_subscription_request.assert_called_once_with(
            domainIdentifier=domain_id,
            requestReason=reason,
            subscribedListings=listings,
            subscribedPrincipals=principals,
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
        request_id = 'sub_req_test123'
        expected_response = {
            'id': request_id,
            'domainId': domain_id,
            'status': 'GRANTED',
            'updatedAt': 1234567890,
        }
        mcp_server_with_tools._mock_client.accept_subscription_request.return_value = (
            expected_response
        )

        # Act
        result = await accept_subscription_request(domain_id, request_id)

        # Assert
        assert result == expected_response
        mcp_server_with_tools._mock_client.accept_subscription_request.assert_called_once_with(
            domainIdentifier=domain_id, identifier=request_id
        )

    @pytest.mark.asyncio
    async def test_get_form_type_success(self, mcp_server_with_tools, tool_extractor):
        """Test successful form type retrieval."""
        # Get the tool function from the MCP server
        get_form_type = tool_extractor(mcp_server_with_tools, 'get_form_type')

        # Arrange
        domain_id = 'dzd_test123'
        form_type_id = 'form_type_test123'
        expected_response = {
            'domainId': domain_id,
            'name': 'Test Form Type',
            'revision': '1',
            'status': 'ENABLED',
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
        """Test create_asset with access denied error."""
        # Get the tool function from the MCP server
        create_asset = tool_extractor(mcp_server_with_tools, 'create_asset')

        # Arrange
        domain_id = 'dzd_test123'
        mcp_server_with_tools._mock_client.create_asset.side_effect = mock_client_error(
            'AccessDeniedException'
        )

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            await create_asset(
                domain_identifier=domain_id,
                name='Test Asset',
                type_identifier='amazon.datazone.RelationalTable',
                owning_project_identifier='prj_test123',
            )

        assert 'Access denied' in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_asset_not_found(self, mcp_server_with_tools, tool_extractor, mock_client_error):
        """Test get_asset with asset not found error."""
        # Get the tool function from the MCP server
        get_asset = tool_extractor(mcp_server_with_tools, 'get_asset')

        # Arrange
        domain_id = 'dzd_test123'
        asset_id = 'nonexistent_asset'
        mcp_server_with_tools._mock_client.get_asset.side_effect = mock_client_error(
            'ResourceNotFoundException'
        )

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            await get_asset(domain_id, asset_id)

        assert 'not found' in str(exc_info.value)

    def test_register_tools(self, mock_fastmcp):
        """Test that tools are registered with FastMCP instance."""
        from awslabs.amazon_datazone_mcp_server.tools import data_management

        # Call the register_tools function
        data_management.register_tools(mock_fastmcp)

        # Verify that the mock was called (tools were registered)
        # The exact number of calls depends on how many tools are registered
        assert mock_fastmcp.tool.called
        # Should have multiple tool registrations
        assert mock_fastmcp.tool.call_count > 5

    # Test for comprehensive error handling to improve coverage
    @pytest.mark.asyncio
    async def test_start_data_source_run_all_error_types(
        self, mcp_server_with_tools, tool_extractor, client_error_helper
    ):
        """Test start_data_source_run with all error types to cover lines 1008-1031."""
        start_data_source_run = tool_extractor(mcp_server_with_tools, 'start_data_source_run')

        domain_id = 'dzd_test123'
        ds_id = 'ds_test123'

        # Test all specific error codes
        error_codes = [
            'AccessDeniedException',
            'ConflictException',
            'InternalServerException',
            'ResourceNotFoundException',
            'ServiceQuotaExceededException',
            'ThrottlingException',
            'UnauthorizedException',
            'ValidationException',
            'UnknownErrorCode',  # This will test the 'else' branch
        ]

        for error_code in error_codes:
            mcp_server_with_tools._mock_client.start_data_source_run.side_effect = (
                client_error_helper(error_code)
            )

            with pytest.raises(Exception) as exc_info:
                await start_data_source_run(domain_id, ds_id)

            # Verify the error message contains relevant information
            error_message = str(exc_info.value)
            assert ds_id in error_message
            assert domain_id in error_message

    @pytest.mark.asyncio
    async def test_start_data_source_run_unexpected_exception(
        self, mcp_server_with_tools, tool_extractor
    ):
        """Test start_data_source_run with unexpected exception to cover line 1012-1013."""
        start_data_source_run = tool_extractor(mcp_server_with_tools, 'start_data_source_run')

        domain_id = 'dzd_test123'
        ds_id = 'ds_test123'

        # Test unexpected exception (non-ClientError)
        mcp_server_with_tools._mock_client.start_data_source_run.side_effect = ValueError(
            'Unexpected error'
        )

        with pytest.raises(Exception) as exc_info:
            await start_data_source_run(domain_id, ds_id)

        assert 'Unexpected error starting data source run' in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_start_data_source_run_with_client_token(
        self, mcp_server_with_tools, tool_extractor
    ):
        """Test start_data_source_run with client_token to cover line 1008."""
        start_data_source_run = tool_extractor(mcp_server_with_tools, 'start_data_source_run')

        domain_id = 'dzd_test123'
        ds_id = 'ds_test123'
        client_token = 'test_token_123'

        expected_response = {
            'id': 'run_test123',
            'dataSourceId': ds_id,
            'domainId': domain_id,
            'status': 'REQUESTED',
        }
        mcp_server_with_tools._mock_client.start_data_source_run.return_value = expected_response

        result = await start_data_source_run(domain_id, ds_id, client_token)

        assert result == expected_response
        mcp_server_with_tools._mock_client.start_data_source_run.assert_called_once_with(
            domainIdentifier=domain_id, dataSourceIdentifier=ds_id, clientToken=client_token
        )


class TestDataManagementParameterValidation:
    """Test cases for parameter validation in data management tools."""

    @pytest.mark.asyncio
    async def test_create_asset_with_all_optional_params(
        self, mcp_server_with_tools, tool_extractor
    ):
        """Test create_asset with all optional parameters."""
        create_asset = tool_extractor(mcp_server_with_tools, 'create_asset')

        # Arrange
        params = {
            'domain_identifier': 'dzd_test123',
            'name': 'Test Asset',
            'type_identifier': 'amazon.datazone.RelationalTable',
            'owning_project_identifier': 'prj_test123',
            'description': 'A test asset',
            'external_identifier': 'ext_123',
            'forms_input': [{'formName': 'test_form', 'content': 'test_content'}],
            'glossary_terms': ['term1', 'term2'],
            'prediction_configuration': {'businessNameGeneration': {'enabled': True}},
            'type_revision': '1',
            'client_token': 'test_token',
        }

        expected_response = {'id': 'asset_new123', 'status': 'ACTIVE'}
        mcp_server_with_tools._mock_client.create_asset.return_value = expected_response

        # Act
        result = await create_asset(**params)

        # Assert
        assert result == expected_response
        mcp_server_with_tools._mock_client.create_asset.assert_called_once_with(
            domainIdentifier=params['domain_identifier'],
            name=params['name'],
            typeIdentifier=params['type_identifier'],
            owningProjectIdentifier=params['owning_project_identifier'],
            description=params['description'],
            externalIdentifier=params['external_identifier'],
            formsInput=params['forms_input'],
            glossaryTerms=params['glossary_terms'],
            predictionConfiguration=params['prediction_configuration'],
            typeRevision=params['type_revision'],
            clientToken=params['client_token'],
        )

    @pytest.mark.asyncio
    async def test_search_listings_max_results_validation(
        self, mcp_server_with_tools, tool_extractor
    ):
        """Test search_listings with max_results validation."""
        search_listings = tool_extractor(mcp_server_with_tools, 'search_listings')

        # Arrange
        domain_id = 'dzd_test123'
        expected_response = {'items': [], 'nextToken': None}
        mcp_server_with_tools._mock_client.search_listings.return_value = expected_response

        # Test with max_results > 50 (should be clamped to 50)
        result = await search_listings(domain_identifier=domain_id, max_results=100)

        assert result == expected_response
        mcp_server_with_tools._mock_client.search_listings.assert_called_once_with(
            domainIdentifier=domain_id, maxResults=50
        )


class TestDataManagementPragmaNoCoverHandling:
    """Test pragma no cover scenarios in data management tools."""

    @pytest.mark.asyncio
    async def test_create_subscription_request_with_optional_params_pragma_coverage(
        self, mcp_server_with_tools, tool_extractor
    ):
        """Test create_subscription_request with optional parameters - covers pragma no cover."""
        create_subscription_request = tool_extractor(
            mcp_server_with_tools, 'create_subscription_request'
        )

        mcp_server_with_tools._mock_client.create_subscription_request.return_value = {
            'id': 'sub-123'
        }

        await create_subscription_request(
            domain_identifier='test-domain',
            request_reason='Need access for analysis',
            subscribed_listings=[{'id': 'listing-123'}],
            subscribed_principals=[{'type': 'USER', 'id': 'user-123'}],
            metadata_forms=[{'form': 'value'}],
            client_token='token-123',
        )

        call_kwargs = mcp_server_with_tools._mock_client.create_subscription_request.call_args[1]
        assert call_kwargs['metadataForms'] == [{'form': 'value'}]
        assert call_kwargs['clientToken'] == 'token-123'

    @pytest.mark.asyncio
    async def test_accept_subscription_request_with_optional_params_pragma_coverage(
        self, mcp_server_with_tools, tool_extractor
    ):
        """Test accept_subscription_request with optional parameters - covers pragma no cover."""
        accept_subscription_request = tool_extractor(
            mcp_server_with_tools, 'accept_subscription_request'
        )

        mcp_server_with_tools._mock_client.accept_subscription_request.return_value = {
            'status': 'APPROVED'
        }

        await accept_subscription_request(
            domain_identifier='test-domain',
            identifier='sub-123',
            asset_scopes=[{'assetId': 'asset-123'}],
            decision_comment='Approved for analysis',
        )

        call_kwargs = mcp_server_with_tools._mock_client.accept_subscription_request.call_args[1]
        assert call_kwargs['assetScopes'] == [{'assetId': 'asset-123'}]
        assert call_kwargs['decisionComment'] == 'Approved for analysis'

    @pytest.mark.asyncio
    async def test_get_subscription_client_error_pragma_coverage(
        self, mcp_server_with_tools, tool_extractor, mock_client_error
    ):
        """Test get_subscription ClientError handling - covers line 894."""
        get_subscription = tool_extractor(mcp_server_with_tools, 'get_subscription')

        # Mock ClientError for get_subscription
        mock_client_error.return_value = Exception(
            'Error getting subscription test-subscription in domain test-domain: An error occurred (AccessDenied) when calling the GetSubscription operation: Access denied'
        )
        mcp_server_with_tools._mock_client.get_subscription.side_effect = (
            mock_client_error.return_value
        )

        with pytest.raises(Exception) as exc_info:
            await get_subscription(domain_identifier='test-domain', identifier='test-subscription')

        assert 'Error getting subscription test-subscription in domain test-domain' in str(
            exc_info.value
        )

    @pytest.mark.asyncio
    async def test_get_form_type_with_revision_pragma_coverage(
        self, mcp_server_with_tools, tool_extractor
    ):
        """Test get_form_type with optional revision parameter - covers pragma no cover."""
        get_form_type = tool_extractor(mcp_server_with_tools, 'get_form_type')

        mcp_server_with_tools._mock_client.get_form_type.return_value = {'name': 'test-form'}

        await get_form_type(
            domain_identifier='test-domain', form_type_identifier='form-123', revision='1.0.0'
        )

        call_kwargs = mcp_server_with_tools._mock_client.get_form_type.call_args[1]
        assert call_kwargs['revision'] == '1.0.0'

    @pytest.mark.asyncio
    async def test_get_form_type_client_error_pragma_coverage(
        self, mcp_server_with_tools, tool_extractor, mock_client_error
    ):
        """Test get_form_type ClientError handling - covers pragma no cover."""
        get_form_type = tool_extractor(mcp_server_with_tools, 'get_form_type')

        mcp_server_with_tools._mock_client.get_form_type.side_effect = mock_client_error(
            'ResourceNotFoundException', 'Form type not found'
        )

        with pytest.raises(Exception) as exc_info:
            await get_form_type(domain_identifier='test-domain', form_type_identifier='form-123')

        assert 'Error getting form type form-123 in domain test-domain' in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_form_type_with_optional_params_pragma_coverage(
        self, mcp_server_with_tools, tool_extractor
    ):
        """Test create_form_type with optional description parameter - covers pragma no cover."""
        create_form_type = tool_extractor(mcp_server_with_tools, 'create_form_type')

        mcp_server_with_tools._mock_client.create_form_type.return_value = {'id': 'form-123'}

        await create_form_type(
            domain_identifier='test-domain',
            name='Test Form',
            model={'type': 'object'},
            owning_project_identifier='project-123',
            description='Test form description',
            status='ENABLED',
        )

        call_kwargs = mcp_server_with_tools._mock_client.create_form_type.call_args[1]
        assert call_kwargs['description'] == 'Test form description'

    @pytest.mark.asyncio
    async def test_list_data_sources_with_all_optional_params_pragma_coverage(
        self, mcp_server_with_tools, tool_extractor
    ):
        """Test list_data_sources with all optional parameters - covers pragma no cover."""
        list_data_sources = tool_extractor(mcp_server_with_tools, 'list_data_sources')

        mcp_server_with_tools._mock_client.list_data_sources.return_value = {'dataSources': []}

        await list_data_sources(
            domain_identifier='test-domain',
            project_identifier='project-123',
            connection_identifier='conn-123',
            environment_identifier='env-123',
            max_results=25,
            name='test-data-source',
            next_token='token-123',
            status='READY',
            data_source_type='S3',
        )

        call_kwargs = mcp_server_with_tools._mock_client.list_data_sources.call_args[1]
        assert call_kwargs['nextToken'] == 'token-123'
        assert call_kwargs['status'] == 'READY'
        assert call_kwargs['connectionIdentifier'] == 'conn-123'
        assert call_kwargs['environmentIdentifier'] == 'env-123'
        assert call_kwargs['name'] == 'test-data-source'
        assert call_kwargs['type'] == 'S3'

    @pytest.mark.asyncio
    async def test_list_data_sources_client_error_pragma_coverage(
        self, mcp_server_with_tools, tool_extractor, mock_client_error
    ):
        """Test list_data_sources ClientError handling - covers pragma no cover."""
        list_data_sources = tool_extractor(mcp_server_with_tools, 'list_data_sources')

        mcp_server_with_tools._mock_client.list_data_sources.side_effect = mock_client_error(
            'AccessDeniedException', 'Access denied'
        )

        with pytest.raises(Exception) as exc_info:
            await list_data_sources(
                domain_identifier='test-domain', project_identifier='project-123'
            )

        assert 'Error listing data sources in project project-123 in domain test-domain' in str(
            exc_info.value
        )

    @pytest.mark.asyncio
    async def test_accept_subscription_request_error_handling_pragma_coverage(
        self, mcp_server_with_tools, tool_extractor, mock_client_error
    ):
        """Test accept_subscription_request error handling - covers pragma no cover."""
        accept_subscription_request = tool_extractor(
            mcp_server_with_tools, 'accept_subscription_request'
        )

        mcp_server_with_tools._mock_client.accept_subscription_request.side_effect = (
            mock_client_error('ValidationException', 'Invalid request')
        )

        with pytest.raises(Exception) as exc_info:
            await accept_subscription_request(
                domain_identifier='test-domain', identifier='sub-123'
            )

        assert 'Error accepting subscription request sub-123 in domain test-domain' in str(
            exc_info.value
        )

    @pytest.mark.asyncio
    async def test_create_subscription_request_error_handling_pragma_coverage(
        self, mcp_server_with_tools, tool_extractor, mock_client_error
    ):
        """Test create_subscription_request error handling - covers pragma no cover."""
        create_subscription_request = tool_extractor(
            mcp_server_with_tools, 'create_subscription_request'
        )

        mcp_server_with_tools._mock_client.create_subscription_request.side_effect = (
            mock_client_error('AccessDeniedException', 'Access denied')
        )

        with pytest.raises(Exception) as exc_info:
            await create_subscription_request(
                domain_identifier='test-domain',
                request_reason='Need access',
                subscribed_listings=[{'id': 'listing-123'}],
                subscribed_principals=[{'type': 'USER', 'id': 'user-123'}],
            )

        assert 'Error creating subscription request in domain test-domain' in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_form_type_error_handling_pragma_coverage(
        self, mcp_server_with_tools, tool_extractor, mock_client_error
    ):
        """Test create_form_type error handling - covers pragma no cover."""
        create_form_type = tool_extractor(mcp_server_with_tools, 'create_form_type')

        mcp_server_with_tools._mock_client.create_form_type.side_effect = mock_client_error(
            'ConflictException', 'Form type already exists'
        )

        with pytest.raises(Exception) as exc_info:
            await create_form_type(
                domain_identifier='test-domain',
                name='Test Form',
                model={'type': 'object'},
                owning_project_identifier='project-123',
                status='ENABLED',
            )

        assert 'Error creating form type in domain test-domain' in str(exc_info.value)
