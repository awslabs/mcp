"""Unit tests for error handling in data management tools."""

import pytest


class TestDataManagementErrorHandling:
    """Test error handling for data management functions."""

    # Error handling tests for get_asset function
    @pytest.mark.asyncio
    async def test_get_asset_access_denied(
        self, mcp_server_with_tools, tool_extractor, client_error_helper
    ):
        """Test get_asset with AccessDeniedException."""
        get_asset = tool_extractor(mcp_server_with_tools, 'get_asset')

        domain_id = 'dzd_test123'
        asset_id = 'asset_test123'
        mcp_server_with_tools._mock_client.get_asset.side_effect = client_error_helper(
            'AccessDeniedException'
        )

        with pytest.raises(Exception) as exc_info:
            await get_asset(domain_id, asset_id)

        assert f'Access denied while getting asset {asset_id} in domain {domain_id}' in str(
            exc_info.value
        )

    @pytest.mark.asyncio
    async def test_get_asset_internal_server_error(
        self, mcp_server_with_tools, tool_extractor, client_error_helper
    ):
        """Test get_asset with InternalServerException."""
        get_asset = tool_extractor(mcp_server_with_tools, 'get_asset')

        domain_id = 'dzd_test123'
        asset_id = 'asset_test123'
        mcp_server_with_tools._mock_client.get_asset.side_effect = client_error_helper(
            'InternalServerException'
        )

        with pytest.raises(Exception) as exc_info:
            await get_asset(domain_id, asset_id)

        assert (
            f'Unknown error, exception or failure while getting asset {asset_id} in domain {domain_id}'
            in str(exc_info.value)
        )

    @pytest.mark.asyncio
    async def test_get_asset_resource_not_found(
        self, mcp_server_with_tools, tool_extractor, client_error_helper
    ):
        """Test get_asset with ResourceNotFoundException."""
        get_asset = tool_extractor(mcp_server_with_tools, 'get_asset')

        domain_id = 'dzd_test123'
        asset_id = 'asset_test123'
        mcp_server_with_tools._mock_client.get_asset.side_effect = client_error_helper(
            'ResourceNotFoundException'
        )

        with pytest.raises(Exception) as exc_info:
            await get_asset(domain_id, asset_id)

        assert f'Data asset {asset_id} or domain {domain_id} not found' in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_asset_throttling_error(
        self, mcp_server_with_tools, tool_extractor, client_error_helper
    ):
        """Test get_asset with ThrottlingException."""
        get_asset = tool_extractor(mcp_server_with_tools, 'get_asset')

        domain_id = 'dzd_test123'
        asset_id = 'asset_test123'
        mcp_server_with_tools._mock_client.get_asset.side_effect = client_error_helper(
            'ThrottlingException'
        )

        with pytest.raises(Exception) as exc_info:
            await get_asset(domain_id, asset_id)

        assert f'Request throttled while getting asset {asset_id} in domain {domain_id}' in str(
            exc_info.value
        )

    @pytest.mark.asyncio
    async def test_get_asset_unauthorized(
        self, mcp_server_with_tools, tool_extractor, client_error_helper
    ):
        """Test get_asset with UnauthorizedException."""
        get_asset = tool_extractor(mcp_server_with_tools, 'get_asset')

        domain_id = 'dzd_test123'
        asset_id = 'asset_test123'
        mcp_server_with_tools._mock_client.get_asset.side_effect = client_error_helper(
            'UnauthorizedException'
        )

        with pytest.raises(Exception) as exc_info:
            await get_asset(domain_id, asset_id)

        assert f'Unauthorized to get asset {asset_id} in domain {domain_id}' in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_asset_validation_exception(
        self, mcp_server_with_tools, tool_extractor, client_error_helper
    ):
        """Test get_asset with ValidationException."""
        get_asset = tool_extractor(mcp_server_with_tools, 'get_asset')

        domain_id = 'dzd_test123'
        asset_id = 'asset_test123'
        mcp_server_with_tools._mock_client.get_asset.side_effect = client_error_helper(
            'ValidationException'
        )

        with pytest.raises(Exception) as exc_info:
            await get_asset(domain_id, asset_id)

        assert f'Invalid input while getting asset {asset_id} in domain {domain_id}' in str(
            exc_info.value
        )

    @pytest.mark.asyncio
    async def test_get_asset_unknown_error(
        self, mcp_server_with_tools, tool_extractor, client_error_helper
    ):
        """Test get_asset with unknown error code."""
        get_asset = tool_extractor(mcp_server_with_tools, 'get_asset')

        domain_id = 'dzd_test123'
        asset_id = 'asset_test123'
        mcp_server_with_tools._mock_client.get_asset.side_effect = client_error_helper(
            'UnknownErrorCode'
        )

        with pytest.raises(Exception) as exc_info:
            await get_asset(domain_id, asset_id)

        assert f'Error getting asset {asset_id} in domain {domain_id}' in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_asset_unexpected_exception(self, mcp_server_with_tools, tool_extractor):
        """Test get_asset with unexpected non-ClientError exception."""
        get_asset = tool_extractor(mcp_server_with_tools, 'get_asset')

        domain_id = 'dzd_test123'
        asset_id = 'asset_test123'
        mcp_server_with_tools._mock_client.get_asset.side_effect = ValueError('Unexpected error')

        with pytest.raises(Exception) as exc_info:
            await get_asset(domain_id, asset_id)

        assert f'Unexpected error getting asset {asset_id} in domain {domain_id}' in str(
            exc_info.value
        )

    # Error handling tests for create_asset function
    @pytest.mark.asyncio
    async def test_create_asset_access_denied(
        self, mcp_server_with_tools, tool_extractor, client_error_helper
    ):
        """Test create_asset with AccessDeniedException."""
        create_asset = tool_extractor(mcp_server_with_tools, 'create_asset')

        domain_id = 'dzd_test123'
        mcp_server_with_tools._mock_client.create_asset.side_effect = client_error_helper(
            'AccessDeniedException'
        )

        with pytest.raises(Exception) as exc_info:
            await create_asset(
                domain_identifier=domain_id,
                name='Test Asset',
                type_identifier='amazon.datazone.RelationalTable',
                owning_project_identifier='prj_test123',
            )

        assert f'Access denied while creating asset in domain {domain_id}' in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_asset_internal_server_error(
        self, mcp_server_with_tools, tool_extractor, client_error_helper
    ):
        """Test create_asset with InternalServerException."""
        create_asset = tool_extractor(mcp_server_with_tools, 'create_asset')

        domain_id = 'dzd_test123'
        mcp_server_with_tools._mock_client.create_asset.side_effect = client_error_helper(
            'InternalServerException'
        )

        with pytest.raises(Exception) as exc_info:
            await create_asset(
                domain_identifier=domain_id,
                name='Test Asset',
                type_identifier='amazon.datazone.RelationalTable',
                owning_project_identifier='prj_test123',
            )

        assert (
            f'Unknown error, exception or failure while creating asset in domain {domain_id}'
            in str(exc_info.value)
        )

    @pytest.mark.asyncio
    async def test_create_asset_resource_not_found(
        self, mcp_server_with_tools, tool_extractor, client_error_helper
    ):
        """Test create_asset with ResourceNotFoundException."""
        create_asset = tool_extractor(mcp_server_with_tools, 'create_asset')

        domain_id = 'dzd_test123'
        mcp_server_with_tools._mock_client.create_asset.side_effect = client_error_helper(
            'ResourceNotFoundException'
        )

        with pytest.raises(Exception) as exc_info:
            await create_asset(
                domain_identifier=domain_id,
                name='Test Asset',
                type_identifier='amazon.datazone.RelationalTable',
                owning_project_identifier='prj_test123',
            )

        assert f'Domain {domain_id} not found' in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_asset_throttling_error(
        self, mcp_server_with_tools, tool_extractor, client_error_helper
    ):
        """Test create_asset with ThrottlingException."""
        create_asset = tool_extractor(mcp_server_with_tools, 'create_asset')

        domain_id = 'dzd_test123'
        mcp_server_with_tools._mock_client.create_asset.side_effect = client_error_helper(
            'ThrottlingException'
        )

        with pytest.raises(Exception) as exc_info:
            await create_asset(
                domain_identifier=domain_id,
                name='Test Asset',
                type_identifier='amazon.datazone.RelationalTable',
                owning_project_identifier='prj_test123',
            )

        assert f'Request throttled while creating asset in domain {domain_id}' in str(
            exc_info.value
        )

    @pytest.mark.asyncio
    async def test_create_asset_unauthorized(
        self, mcp_server_with_tools, tool_extractor, client_error_helper
    ):
        """Test create_asset with UnauthorizedException."""
        create_asset = tool_extractor(mcp_server_with_tools, 'create_asset')

        domain_id = 'dzd_test123'
        mcp_server_with_tools._mock_client.create_asset.side_effect = client_error_helper(
            'UnauthorizedException'
        )

        with pytest.raises(Exception) as exc_info:
            await create_asset(
                domain_identifier=domain_id,
                name='Test Asset',
                type_identifier='amazon.datazone.RelationalTable',
                owning_project_identifier='prj_test123',
            )

        assert f'Unauthorized to create asset in domain {domain_id}' in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_asset_validation_exception(
        self, mcp_server_with_tools, tool_extractor, client_error_helper
    ):
        """Test create_asset with ValidationException."""
        create_asset = tool_extractor(mcp_server_with_tools, 'create_asset')

        domain_id = 'dzd_test123'
        mcp_server_with_tools._mock_client.create_asset.side_effect = client_error_helper(
            'ValidationException'
        )

        with pytest.raises(Exception) as exc_info:
            await create_asset(
                domain_identifier=domain_id,
                name='Test Asset',
                type_identifier='amazon.datazone.RelationalTable',
                owning_project_identifier='prj_test123',
            )

        assert f'Invalid input while creating asset in domain {domain_id}' in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_asset_conflict_exception(
        self, mcp_server_with_tools, tool_extractor, client_error_helper
    ):
        """Test create_asset with ConflictException."""
        create_asset = tool_extractor(mcp_server_with_tools, 'create_asset')

        domain_id = 'dzd_test123'
        mcp_server_with_tools._mock_client.create_asset.side_effect = client_error_helper(
            'ConflictException'
        )

        with pytest.raises(Exception) as exc_info:
            await create_asset(
                domain_identifier=domain_id,
                name='Test Asset',
                type_identifier='amazon.datazone.RelationalTable',
                owning_project_identifier='prj_test123',
            )

        assert f'There is a conflict while creating asset in domain {domain_id}' in str(
            exc_info.value
        )

    @pytest.mark.asyncio
    async def test_create_asset_unknown_error(
        self, mcp_server_with_tools, tool_extractor, client_error_helper
    ):
        """Test create_asset with unknown error code."""
        create_asset = tool_extractor(mcp_server_with_tools, 'create_asset')

        domain_id = 'dzd_test123'
        mcp_server_with_tools._mock_client.create_asset.side_effect = client_error_helper(
            'UnknownErrorCode'
        )

        with pytest.raises(Exception) as exc_info:
            await create_asset(
                domain_identifier=domain_id,
                name='Test Asset',
                type_identifier='amazon.datazone.RelationalTable',
                owning_project_identifier='prj_test123',
            )

        assert f'Error creating asset in domain {domain_id}' in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_asset_unexpected_exception(self, mcp_server_with_tools, tool_extractor):
        """Test create_asset with unexpected non-ClientError exception."""
        create_asset = tool_extractor(mcp_server_with_tools, 'create_asset')

        domain_id = 'dzd_test123'
        mcp_server_with_tools._mock_client.create_asset.side_effect = ValueError(
            'Unexpected error'
        )

        with pytest.raises(Exception) as exc_info:
            await create_asset(
                domain_identifier=domain_id,
                name='Test Asset',
                type_identifier='amazon.datazone.RelationalTable',
                owning_project_identifier='prj_test123',
            )

        assert f'Unexpected error creating asset in domain {domain_id}' in str(exc_info.value)

    # Error handling tests for publish_asset function
    @pytest.mark.asyncio
    async def test_publish_asset_client_error(
        self, mcp_server_with_tools, tool_extractor, client_error_helper
    ):
        """Test publish_asset with ClientError."""
        publish_asset = tool_extractor(mcp_server_with_tools, 'publish_asset')

        domain_id = 'dzd_test123'
        asset_id = 'asset_test123'
        mcp_server_with_tools._mock_client.publish_asset.side_effect = client_error_helper(
            'AccessDeniedException'
        )

        with pytest.raises(Exception) as exc_info:
            await publish_asset(domain_id, asset_id)

        assert f'Error publishing asset {asset_id} in domain {domain_id}' in str(exc_info.value)

    # Error handling tests for get_listing function
    @pytest.mark.asyncio
    async def test_get_listing_client_error(
        self, mcp_server_with_tools, tool_extractor, client_error_helper
    ):
        """Test get_listing with ClientError."""
        get_listing = tool_extractor(mcp_server_with_tools, 'get_listing')

        domain_id = 'dzd_test123'
        listing_id = 'listing_test123'
        mcp_server_with_tools._mock_client.get_listing.side_effect = client_error_helper(
            'ResourceNotFoundException'
        )

        with pytest.raises(Exception) as exc_info:
            await get_listing(domain_id, listing_id)

        assert f'Error getting listing {listing_id} in domain {domain_id}' in str(exc_info.value)

    # Error handling tests for search_listings function
    @pytest.mark.asyncio
    async def test_search_listings_client_error(
        self, mcp_server_with_tools, tool_extractor, client_error_helper
    ):
        """Test search_listings with ClientError."""
        search_listings = tool_extractor(mcp_server_with_tools, 'search_listings')

        domain_id = 'dzd_test123'
        mcp_server_with_tools._mock_client.search_listings.side_effect = client_error_helper(
            'ValidationException'
        )

        with pytest.raises(Exception) as exc_info:
            await search_listings(domain_id)

        assert f'Error searching listings in domain {domain_id}' in str(exc_info.value)

    # Error handling tests for create_data_source function
    @pytest.mark.asyncio
    async def test_create_data_source_client_error(
        self, mcp_server_with_tools, tool_extractor, client_error_helper
    ):
        """Test create_data_source with ClientError."""
        create_data_source = tool_extractor(mcp_server_with_tools, 'create_data_source')

        domain_id = 'dzd_test123'
        project_id = 'prj_test123'
        mcp_server_with_tools._mock_client.create_data_source.side_effect = client_error_helper(
            'AccessDeniedException'
        )

        with pytest.raises(Exception) as exc_info:
            await create_data_source(
                domain_identifier=domain_id,
                project_identifier=project_id,
                name='Test Data Source',
                data_src_type='S3',
            )

        assert f'Error creating data source in domain {domain_id}' in str(exc_info.value)

    # Error handling tests for get_data_source function
    @pytest.mark.asyncio
    async def test_get_data_source_client_error(
        self, mcp_server_with_tools, tool_extractor, client_error_helper
    ):
        """Test get_data_source with ClientError."""
        get_data_source = tool_extractor(mcp_server_with_tools, 'get_data_source')

        domain_id = 'dzd_test123'
        ds_id = 'ds_test123'
        mcp_server_with_tools._mock_client.get_data_source.side_effect = client_error_helper(
            'ResourceNotFoundException'
        )

        with pytest.raises(Exception) as exc_info:
            await get_data_source(domain_id, ds_id)

        assert f'Error getting data source {ds_id}' in str(exc_info.value)
